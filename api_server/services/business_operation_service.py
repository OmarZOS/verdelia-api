# services/business_operation_service.py
from __future__ import annotations

from typing import List, Dict, Any, Optional, Iterable, Set
from datetime import datetime, time, timezone
from collections import defaultdict
import logging

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm.exc import DetachedInstanceError

from core.models.models import (
    Cart,
    Delivery,
    Invoice,
    OrderedItem,
    OrderedService,
    PlacedOrder,
    ProvidedService,
    Product,
    Payment,
)
from storage import storage_broker

from core.logging_config import get_logger

logger = get_logger(__name__)



class BusinessOperationService:
    """Service for business operations — read/reporting aggregate."""

    BROKER_MAX_LIMIT = 1000
    _PAYMENT_RELS = ("payment", "payments", "invoice_payment", "invoice_payments")

    # Default amortization horizon for non-consumable resources (days).
    NON_CONSUMABLE_AMORTIZATION_DAYS = 365

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_operations(
        self,
        supplier_id: int = 0,
        client_id: int = 0,
        offset: int = 0,
        limit: int = 100,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        include_stats: bool = True,
    ) -> Dict[str, Any]:

        if limit < 1:
            limit = 1
        if limit > self.BROKER_MAX_LIMIT:
            limit = self.BROKER_MAX_LIMIT

        window = self._normalize_time_window(date_from, date_to)

        cart_ops = self._fetch_cart_operations(
            supplier_id=supplier_id, client_id=client_id,
            offset=offset, limit=limit, window=window,
        )
        delivery_ops = self._fetch_delivery_operations(
            supplier_id=supplier_id, client_id=client_id,
            offset=offset, limit=limit, window=window,
        )

        all_items = [i for op in (cart_ops + delivery_ops) for i in op["items"]]
        product_provider_map = self._load_product_provider_map(all_items)

        cart_ops = [
            op for op in (
                self._apply_supplier_filter_to_cart(op, supplier_id, product_provider_map)
                for op in cart_ops
            ) if op is not None
        ]
        delivery_ops = [
            op for op in (
                self._apply_supplier_filter_to_delivery(op, supplier_id, product_provider_map)
                for op in delivery_ops
            ) if op is not None
        ]

        merged: Dict[tuple, Dict[str, Any]] = {}
        for op in cart_ops + delivery_ops:
            key = (op["source_type"], op["source_id"])
            if key not in merged:
                merged[key] = op
            else:
                existing = merged[key]
                if op.get("delivery") and not existing.get("delivery"):
                    existing["delivery"] = op["delivery"]
                if op.get("cart") and not existing.get("cart"):
                    existing["cart"] = op["cart"]

        sorted_ops = sorted(
            merged.values(),
            key=lambda o: o.get("created_at") or datetime.min,
            reverse=True,
        )
        page = sorted_ops[offset: offset + limit]

        result: Dict[str, Any] = {
            "operations": page,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "returned": len(page),
                "total_in_window": len(sorted_ops),
            },
            "window": {
                "date_from": window[0].isoformat() if window[0] else None,
                "date_to": window[1].isoformat() if window[1] else None,
            },
        }
        if include_stats:
            result["stats"] = self._aggregate_stats(sorted_ops)
        return result

    # ------------------------------------------------------------------
    # Aggregate stats
    # ------------------------------------------------------------------

    def _aggregate_stats(self, ops: List[Dict[str, Any]]) -> Dict[str, Any]:
        totals = {
            "product_subtotal": 0.0,
            "service_subtotal": 0.0,
            "gross_subtotal": 0.0,
            "discount_amount": 0.0,
            "tax_amount": 0.0,
            "delivery_revenue": 0.0,
            "grand_total": 0.0,
            "invoice_total": 0.0,
            "paid_amount": 0.0,
            "due_amount": 0.0,
            "product_cost": 0.0,
            "consumable_service_cost": 0.0,
            "non_consumable_service_cost": 0.0,
            "labor_cost": 0.0,
            "delivery_cost": 0.0,
            "total_cost": 0.0,
            "margin_amount": 0.0,
            "item_count": 0,
            "service_count": 0,
        }
        by_status: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"count": 0, "grand_total": 0.0, "due_amount": 0.0}
        )
        by_source: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"count": 0, "grand_total": 0.0}
        )
        by_supplier: Dict[int, Dict[str, float]] = defaultdict(
            lambda: {"count": 0, "grand_total": 0.0, "due_amount": 0.0}
        )
        by_client: Dict[int, Dict[str, float]] = defaultdict(
            lambda: {"count": 0, "grand_total": 0.0, "due_amount": 0.0}
        )
        by_day: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"count": 0, "grand_total": 0.0, "due_amount": 0.0}
        )

        for op in ops:
            for k in totals:
                try:
                    totals[k] += float(op.get(k, 0) or 0)
                except (TypeError, ValueError):
                    continue

            status = op.get("status") or "unknown"
            by_status[status]["count"] += 1
            by_status[status]["grand_total"] += float(op.get("grand_total", 0) or 0)
            by_status[status]["due_amount"] += float(op.get("due_amount", 0) or 0)

            src = op.get("source_type") or "unknown"
            by_source[src]["count"] += 1
            by_source[src]["grand_total"] += float(op.get("grand_total", 0) or 0)

            sup = op.get("supplier_id")
            if sup is not None:
                by_supplier[sup]["count"] += 1
                by_supplier[sup]["grand_total"] += float(op.get("grand_total", 0) or 0)
                by_supplier[sup]["due_amount"] += float(op.get("due_amount", 0) or 0)

            cli = op.get("client_id")
            if cli is not None:
                by_client[cli]["count"] += 1
                by_client[cli]["grand_total"] += float(op.get("grand_total", 0) or 0)
                by_client[cli]["due_amount"] += float(op.get("due_amount", 0) or 0)

            created = op.get("created_at")
            if created is not None:
                day_key = self._to_utc(created).date().isoformat()
                by_day[day_key]["count"] += 1
                by_day[day_key]["grand_total"] += float(op.get("grand_total", 0) or 0)
                by_day[day_key]["due_amount"] += float(op.get("due_amount", 0) or 0)

        total_rev = totals["grand_total"]
        total_cost = totals["total_cost"]
        total_paid = totals["paid_amount"]
        total_due = totals["due_amount"]

        overall_roi = round((total_rev - total_cost) / total_cost, 4) if total_cost > 0 else None
        avg_ticket = round(total_rev / len(ops), 2) if ops else 0.0
        collection_rate = (
            round(total_paid / (total_paid + total_due), 4)
            if (total_paid + total_due) > 0 else None
        )
        discount_rate = (
            round(totals["discount_amount"] / totals["gross_subtotal"], 4)
            if totals["gross_subtotal"] > 0 else None
        )

        for k in totals:
            totals[k] = round(totals[k], 2) if isinstance(totals[k], float) else totals[k]

        def _round_buckets(d):
            return {
                k: {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                for k, v in d.items()
            }

        return {
            "totals": totals,
            "ratios": {
                "overall_roi": overall_roi,
                "average_ticket": avg_ticket,
                "collection_rate": collection_rate,
                "discount_rate": discount_rate,
            },
            "counts": {
                "operations": len(ops),
                "carts": by_source.get("cart", {}).get("count", 0),
                "deliveries": by_source.get("delivery", {}).get("count", 0),
            },
            "by_status": _round_buckets(dict(by_status)),
            "by_source": _round_buckets(dict(by_source)),
            "by_supplier": _round_buckets(dict(by_supplier)),
            "by_client": _round_buckets(dict(by_client)),
            "by_day": dict(sorted(by_day.items())),
        }

    # ------------------------------------------------------------------
    # Time window
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_time_window(date_from, date_to):
        """
        Normalize a (date_from, date_to) pair to a UTC [start, end] window.

        Rules:
        - A date with time == 00:00:00 (bare date or local midnight) is
          treated as the ENTIRE day:
              date_from -> 00:00:00.000000 UTC of that date
              date_to   -> 23:59:59.999999 UTC of that date
        - Any other time is preserved as-is, converted to UTC.
        - If start > end after normalization, swap them.

        The returned window is tz-aware UTC. When filtering against DB
        columns that are MySQL `TIMESTAMP`, convert the bounds with
        `_naive_utc()` before handing them to the broker.
        """
        start = BusinessOperationService._to_utc(date_from) if date_from else None
        end = BusinessOperationService._to_utc(date_to) if date_to else None

        if start is not None and start.time() == time(0, 0):
            start = datetime.combine(
                start.date(), time(0, 0, 0, 0), tzinfo=timezone.utc
            )

        if end is not None and end.time() == time(0, 0):
            end = datetime.combine(
                end.date(), time(23, 59, 59, 999999), tzinfo=timezone.utc
            )

        if start is not None and end is not None and start > end:
            logger.warning(
                f"Time window inverted after normalization: "
                f"start={start} > end={end}. Swapping."
            )
            start, end = end, start

        logger.info(
            f"Time window raw input: date_from={date_from!r} date_to={date_to!r}"
        )
        logger.info(
            f"Time window normalized: start={start!r} end={end!r}"
        )

        return start, end

    @staticmethod
    def _to_utc(value):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _naive_utc(value):
        """
        Convert a datetime to a naive UTC datetime.

        Use this when passing filter bounds to the storage broker for
        columns declared as MySQL `TIMESTAMP`. MySQL stores TIMESTAMP
        internally as UTC and returns it naive in the session timezone.
        When the session timezone is UTC (set on connect), the values the
        client reads are naive UTC, and comparisons must use naive UTC
        bounds.
        """
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    # ------------------------------------------------------------------
    # Cart branch
    # ------------------------------------------------------------------

    def _fetch_cart_operations(self, supplier_id, client_id, offset, limit, window):
        # The broker treats a list as SQLAlchemy expressions, applying each
        # with query.filter(). A dict is treated as equality / IN, which
        # cannot express a range.
        conditions: List[Any] = []

        if supplier_id:
            conditions.append(Cart.provider_id == supplier_id)
        if client_id:
            conditions.append(Cart.client_user_id == client_id)

        start, end = window
        start_db = self._naive_utc(start)
        end_db = self._naive_utc(end)

        if start_db is not None and end_db is not None:
            conditions.append(Cart.created_at.between(start_db, end_db))
        elif start_db is not None:
            conditions.append(Cart.created_at >= start_db)
        elif end_db is not None:
            conditions.append(Cart.created_at <= end_db)

        logger.info(
            f"Cart fetch: {len(conditions)} condition(s), "
            f"start={start_db!r} end={end_db!r}"
        )

        carts = storage_broker.get(
            Cart,
            conditions,          # ← list of SQLAlchemy expressions
            [],
            [
                {Cart.invoice: [{Invoice.payment: []}]},
                {
                    Cart.ordered_service: [
                        {
                            OrderedService.service: [
                                {ProvidedService.service_resource_requirement: []},
                                ProvidedService.service_staff_requirement,
                            ]
                        }
                    ]
                },
                {Cart.ordered_item: [{OrderedItem.product: []}]},
            ],
            offset=offset,
            limit=limit,
        )

        logger.info(f"Cart fetch: {len(carts or [])} rows returned")

        ops = [self._cart_to_operation(c) for c in (carts or [])]
        return [op for op in ops if self._in_window(op["created_at"], window)]

    def _fetch_delivery_operations(self, supplier_id, client_id, offset, limit, window):
        conditions: List[Any] = []

        if supplier_id:
            conditions.append(Delivery.delivery_provider_id == supplier_id)

        start, end = window
        start_db = self._naive_utc(start)
        end_db = self._naive_utc(end)

        if start_db is not None and end_db is not None:
            conditions.append(
                Delivery.created_at.between(start_db, end_db)
            )
        elif start_db is not None:
            conditions.append(Delivery.created_at >= start_db)
        elif end_db is not None:
            conditions.append(Delivery.created_at <= end_db)

        logger.info(
            f"Delivery fetch: {len(conditions)} condition(s), "
            f"start={start_db!r} end={end_db!r}"
        )

        deliveries = storage_broker.get(
            Delivery,
            conditions,          # ← list of SQLAlchemy expressions
            [],
            [
                {
                    Delivery.invoice: [
                        {Invoice.payment: []},
                        {
                            Invoice.placed_order: [
                                {
                                    PlacedOrder.ordered_item: [
                                        OrderedItem.product
                                    ]
                                }
                            ]
                        },
                    ]
                },
            ],
            offset=offset,
            limit=limit,
        )

        logger.info(f"Delivery fetch: {len(deliveries or [])} rows returned")

        ops: List[Dict[str, Any]] = []
        for delivery in (deliveries or []):
            op = self._delivery_to_operation(delivery, client_id=client_id)
            if op is None:
                continue
            if not self._in_window(op["created_at"], window):
                continue
            ops.append(op)
        return ops

    def _cart_to_operation(self, cart: Cart) -> Dict[str, Any]:
        invoice = getattr(cart, "invoice", None)
        items = list(getattr(cart, "ordered_item", None) or [])
        services = list(getattr(cart, "ordered_service", None) or [])

        delivery_fee = self._cart_delivery_fee(cart)

        op = {
            "source_type": "cart",
            "source_id": cart.cart_id,
            "supplier_id": cart.provider_id,
            "client_id": cart.client_user_id,
            "invoice": invoice,
            "items": items,
            "services": services,
            "cart": cart,
            "delivery": None,
            "status": cart.cart_status,
            "created_at": cart.created_at,
            "_order_discount": self._safe_float(getattr(cart, "cart_discount", 0)),
            "_delivery_fee": delivery_fee,
        }
        op.update(self._financials(items, services, invoice, op))
        return op

    @staticmethod
    def _cart_delivery_fee(cart: Cart) -> float:
        return BusinessOperationService._safe_float(
            getattr(cart, "cart_delivery_fee", 0)
        )

    # ------------------------------------------------------------------
    # Delivery branch
    # ------------------------------------------------------------------

    def _fetch_delivery_operations(self, supplier_id, client_id, offset, limit, window):
        # The broker treats a list as SQLAlchemy expressions, applying each
        # with query.filter(). A dict is treated as equality / IN, which
        # cannot express a range.
        conditions: List[Any] = []

        if supplier_id:
            conditions.append(Delivery.delivery_provider_id == supplier_id)

        start, end = window
        start_db = self._naive_utc(start)
        end_db = self._naive_utc(end)

        if start_db is not None and end_db is not None:
            conditions.append(
                Delivery.created_at.between(start_db, end_db)
            )
        elif start_db is not None:
            conditions.append(Delivery.created_at >= start_db)
        elif end_db is not None:
            conditions.append(Delivery.created_at <= end_db)

        logger.info(
            f"Delivery fetch: {len(conditions)} condition(s), "
            f"start={start_db!r} end={end_db!r}"
        )

        deliveries = storage_broker.get(
            Delivery,
            conditions,          # ← list, not dict
            [],
            [
                {
                    Delivery.invoice: [
                        {Invoice.payment: []},
                        {
                            Invoice.placed_order: [
                                {
                                    PlacedOrder.ordered_item: [
                                        OrderedItem.product
                                    ]
                                }
                            ]
                        },
                    ]
                },
            ],
            offset=offset,
            limit=limit,
        )

        logger.info(f"Delivery fetch: {len(deliveries or [])} rows returned")

        ops: List[Dict[str, Any]] = []
        for delivery in (deliveries or []):
            op = self._delivery_to_operation(delivery, client_id=client_id)
            if op is None:
                continue
            if not self._in_window(op["created_at"], window):
                continue
            ops.append(op)
        return ops

    def _delivery_to_operation(self, delivery: Delivery, client_id: int = 0):
        invoice = getattr(delivery, "invoice", None)
        placed_orders = (
            getattr(invoice, "placed_order", None) or []
            if invoice is not None else []
        )
        all_items: List[OrderedItem] = []
        order_discount = 0.0
        for po in placed_orders:
            all_items.extend(getattr(po, "ordered_item", None) or [])
            try:
                order_discount += float(getattr(po, "order_discount", 0) or 0)
            except (TypeError, ValueError):
                pass

        client = delivery.recipient_person_id
        if client is None and placed_orders:
            client = placed_orders[0].ordering_user_id

        if client_id and client != client_id:
            return None

        delivery_fee = self._safe_float(getattr(delivery, "delivery_fee", 0))

        op = {
            "source_type": "delivery",
            "source_id": delivery.delivery_source_id,
            "supplier_id": delivery.delivery_provider_id,
            "client_id": client,
            "invoice": invoice,
            "items": all_items,
            "services": [],
            "cart": None,
            "delivery": delivery,
            "status": delivery.delivery_status,
            "created_at": delivery.created_at,
            "_order_discount": order_discount,
            "_delivery_fee": delivery_fee,
        }
        op.update(self._financials(all_items, [], invoice, op))
        return op

    # ------------------------------------------------------------------
    # Window post-filter
    # ------------------------------------------------------------------

    @staticmethod
    def _in_window(created_at, window):
        """
        Post-filter using the tz-aware UTC window.

        `created_at` comes from a MySQL TIMESTAMP column, so it's naive.
        `_to_utc` treats naive values as UTC, which is correct when the
        DB session timezone is forced to UTC.
        """
        start, end = window
        if start is None and end is None:
            return True
        if created_at is None:
            return True
        ts = BusinessOperationService._to_utc(created_at)
        if start is not None and ts < start:
            return False
        if end is not None and ts > end:
            return False
        return True

    # ------------------------------------------------------------------
    # Product → provider map
    # ------------------------------------------------------------------

    def _load_product_provider_map(self, items: Iterable[OrderedItem]) -> Dict[int, int]:
        product_ids: Set[int] = set()
        for item in items:
            pid = getattr(item, "product_id", None)
            if pid is not None:
                product_ids.add(pid)

        if not product_ids:
            return {}

        mapping: Dict[int, int] = {}
        ids = list(product_ids)
        for start in range(0, len(ids), self.BROKER_MAX_LIMIT):
            chunk = ids[start: start + self.BROKER_MAX_LIMIT]
            products = storage_broker.get(
                Product,
                {Product.id_product: chunk},
                [],
                [],
                offset=0,
                limit=len(chunk),
            )
            for p in products or []:
                pid = getattr(p, "id_product", None)
                prov = getattr(p, "product_provider_id", None)
                if pid is not None and prov is not None:
                    mapping[pid] = prov

        return mapping

    # ------------------------------------------------------------------
    # Supplier filters
    # ------------------------------------------------------------------

    def _apply_supplier_filter_to_cart(self, op, supplier_id, product_provider_map):
        if not supplier_id:
            return op
        if op["supplier_id"] != supplier_id:
            return None

        items = self._filter_items_by_supplier(op["items"], supplier_id, product_provider_map)
        if not items and not op["services"]:
            return None

        op["items"] = items
        op.update(self._financials(items, op["services"], op.get("invoice"), op))
        return op

    def _apply_supplier_filter_to_delivery(self, op, supplier_id, product_provider_map):
        if not supplier_id:
            return op

        items = self._filter_items_by_supplier(op["items"], supplier_id, product_provider_map)
        if not items:
            return None

        op["items"] = items
        op.update(self._financials(items, [], op.get("invoice"), op))
        return op

    # ------------------------------------------------------------------
    # Financial rollup
    # ------------------------------------------------------------------



    def _financials(
        self,
        items: List[OrderedItem],
        services: List[OrderedService],
        invoice: Optional[Invoice],
        op: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Commercial model
        ----------------
        - `unit_price` on items is VAT-INCLUSIVE. `vat_rate` is the
          rate that was baked into it (price_with_vat = base × (1 + vat/100)).
        - `vat_rate` may be 0 when the line was priced without tax.
        - Discounts live at the ORDER level (`_order_discount`, sourced
          from PlacedOrder.order_discount or Cart.cart_discount). The
          per-item `product_discount` slot exists in the payload but is
          always null today; we still read it so a future backend that
          populates it doesn't silently drop money.

        Therefore:

            line_total       = qty × unit_price                    (VAT-incl.)
            item_discount    = product_discount (per line, default 0)
            line_net         = line_total − item_discount
            product_subtotal = Σ line_net
            service_subtotal = Σ ordered_service_total_price
            gross_subtotal   = product_subtotal + service_subtotal
            order_discount   = _order_discount
            discount_amount  = Σ item_discount + order_discount
            delivery_revenue = _delivery_fee

            grand_total      = max(gross_subtotal − order_discount, 0)
                             + delivery_revenue

        `tax_amount` is *extracted from* the line totals for reporting —
        it is already contained in `grand_total` and must NOT be added
        to it:

            tax_portion      = line_total × vat / (100 + vat)
            tax_amount       = Σ tax_portion (items) + Σ tax_portion (services)

        `due_amount` is always computed against `grand_total`, never
        against `invoice_total`. The invoice's own total is carried
        verbatim on `invoice_total` for reconciliation.
        """
        # ---------- COMMERCIAL ----------
        product_subtotal = 0.0          # VAT-inclusive, after item discounts
        item_discount_total = 0.0       # Σ per-item product_discount
        tax_from_items = 0.0            # informational only
        product_cost = 0.0

        for item in items:
            try:
                qty = float(getattr(item, "ordered_quantity", 0) or 0)
                price = float(getattr(item, "unit_price", 0) or 0)
                vat = float(getattr(item, "vat_rate", 0) or 0)
            except (TypeError, ValueError):
                continue

            line_total = qty * price

            # Per-item discount. Payload sends null today; treat null
            # and missing as zero. Guard against a string being passed.
            try:
                item_discount = float(
                    getattr(item, "product_discount", 0) or 0
                )
            except (TypeError, ValueError):
                item_discount = 0.0

            line_net = line_total - item_discount

            product_subtotal += line_net
            item_discount_total += item_discount

            if vat > 0:
                # Tax is already inside line_net; just report the split.
                tax_from_items += line_total * (vat / (100.0 + vat))

            product = self._safe_loaded(item, "product")
            if product is not None:
                base = float(getattr(product, "product_base_price", 0) or 0)
                if base > 0:
                    product_cost += base * qty

        service_subtotal = 0.0          # VAT-inclusive
        tax_from_services = 0.0         # informational only
        consumable_service_cost = 0.0
        non_consumable_service_cost = 0.0
        labor_cost = 0.0

        for svc in services:
            try:
                svc_total = float(
                    getattr(svc, "ordered_service_total_price", 0) or 0
                )
                svc_vat = float(getattr(svc, "vat_rate", 0) or 0)
            except (TypeError, ValueError):
                continue

            service_subtotal += svc_total
            if svc_vat > 0:
                tax_from_services += svc_total * (svc_vat / (100.0 + svc_vat))

            provided = self._safe_loaded(svc, "ordered_service_service")
            if provided is None:
                continue

            staff_reqs = self._safe_loaded(provided, "service_staff_requirement") or []
            for req in staff_reqs:
                try:
                    hours = float(
                        getattr(req, "service_staff_requirement_allocated_hours", 0) or 0
                    )
                    rate = float(
                        getattr(req, "service_staff_requirement_hourly_rate", 0) or 0
                    )
                    min_count = float(
                        getattr(req, "service_staff_requirement_min_count", 0) or 0
                    )
                    people = min_count if min_count > 0 else 1.0
                    labor_cost += hours * rate * people
                except (TypeError, ValueError):
                    continue

            reqs = self._safe_loaded(provided, "service_resource_requirement") or []
            for req in reqs:
                try:
                    qty = float(
                        getattr(req, "service_resource_requirement_quantity", 0) or 0
                    )
                    unit_cost = float(
                        getattr(req, "service_resource_requirement_cost_per_unit", 0) or 0
                    )
                    is_consumable = bool(
                        getattr(req, "service_resource_requirement_is_consumable", 0)
                    )
                except (TypeError, ValueError):
                    continue

                if is_consumable:
                    consumable_service_cost += qty * unit_cost
                elif self.NON_CONSUMABLE_AMORTIZATION_DAYS > 0:
                    per_use = (qty * unit_cost) / self.NON_CONSUMABLE_AMORTIZATION_DAYS
                    non_consumable_service_cost += per_use

        # ---------- DISCOUNT ----------
        order_discount = float(op.get("_order_discount", 0) or 0)
        discount_total = item_discount_total + order_discount

        gross_subtotal = product_subtotal + service_subtotal
        taxable_amount = max(gross_subtotal - order_discount, 0.0)

        # ---------- DELIVERY ----------
        delivery_revenue = float(op.get("_delivery_fee", 0) or 0)

        # ---------- GRAND TOTAL ----------
        # Tax is contained in the line totals already; it is NOT added.
        grand_total = round(taxable_amount + delivery_revenue, 2)

        # Invoice's own total, carried verbatim for reconciliation.
        invoice_total = self._invoice_total(invoice)

        # ---------- SETTLEMENT ----------
        paid_amount = round(self._sum_completed_payments(invoice), 2)
        due_amount = round(max(grand_total - paid_amount, 0.0), 2)

        invoice_status = getattr(invoice, "invoice_status", None) if invoice else None

        # ---------- COST ----------
        delivery_cost = 0.0
        delivery_obj = op.get("delivery")
        if delivery_obj is not None:
            delivery_cost = self._safe_float(
                getattr(delivery_obj, "delivery_cost", 0)
            )

        total_cost = round(
            product_cost
            + consumable_service_cost
            + non_consumable_service_cost
            + labor_cost
            + delivery_cost,
            2,
        )

        # ---------- PROFITABILITY ----------
        margin_amount = round(grand_total - total_cost, 2)
        roi = round(margin_amount / total_cost, 4) if total_cost > 0 else None

        # ---------- TAX (reporting only) ----------
        tax_total = tax_from_items + tax_from_services

        return {
            # Commercial
            "product_subtotal": round(product_subtotal, 2),
            "service_subtotal": round(service_subtotal, 2),
            "gross_subtotal": round(gross_subtotal, 2),
            "discount_amount": round(discount_total, 2),
            "item_discount_amount": round(item_discount_total, 2),
            "order_discount_amount": round(order_discount, 2),
            "tax_amount": round(tax_total, 2),
            "delivery_revenue": round(delivery_revenue, 2),
            "grand_total": grand_total,
            "invoice_total": round(invoice_total, 2),

            # Settlement
            "paid_amount": paid_amount,
            "due_amount": due_amount,
            "invoice_status": invoice_status,

            # Cost
            "product_cost": round(product_cost, 2),
            "consumable_service_cost": round(consumable_service_cost, 2),
            "non_consumable_service_cost": round(non_consumable_service_cost, 2),
            "labor_cost": round(labor_cost, 2),
            "delivery_cost": round(delivery_cost, 2),
            "total_cost": total_cost,

            # Profitability
            "margin_amount": margin_amount,
            "roi": roi,

            # Counts
            "item_count": len(items),
            "service_count": len(services),
        }

    @staticmethod
    def _invoice_total(invoice: Optional[Invoice]) -> float:
        if invoice is None:
            return 0.0
        return BusinessOperationService._safe_float(
            getattr(invoice, "grand_total", 0)
        )

    def _sum_completed_payments(self, invoice: Optional[Invoice]) -> float:
        if invoice is None:
            return 0.0
        payments = None
        for rel_name in self._PAYMENT_RELS:
            value = self._safe_loaded(invoice, rel_name)
            if value is not None:
                payments = value
                break
        if not payments:
            return 0.0
        total = 0.0
        for p in payments:
            if getattr(p, "payment_status", None) != "completed":
                continue
            total += self._safe_float(getattr(p, "payment_amount", 0))
        return total

    # ------------------------------------------------------------------
    # Detached-safe reader
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_loaded(obj: Any, attr: str) -> Any:
        if obj is None:
            return None
        try:
            state = sa_inspect(obj)
        except Exception:
            return getattr(obj, attr, None)
        if attr not in state.dict:
            return None
        try:
            return getattr(obj, attr, None)
        except DetachedInstanceError:
            return None

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    # ------------------------------------------------------------------
    # Item helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _item_provider_id(item, product_provider_map):
        pid = getattr(item, "product_id", None)
        if pid is None:
            return None
        return product_provider_map.get(pid)

    @classmethod
    def _filter_items_by_supplier(cls, items, supplier_id, product_provider_map):
        return [
            i for i in items
            if cls._item_provider_id(i, product_provider_map) == supplier_id
        ]