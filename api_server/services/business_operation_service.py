# services/business_operation_service.py
from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_UP
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


_CENT = Decimal("0.01")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
_ZERO = Decimal("0")


def _q2(value: Decimal) -> Decimal:
    """Quantize a Decimal to two places, half-up (money)."""
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _q4(value: Decimal) -> Decimal:
    """Quantize a Decimal to four places, half-up (ratios)."""
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _to_wire(value: Decimal) -> float:
    """Convert a Decimal to a float only at the JSON boundary."""
    return float(value)


class BusinessOperationService:
    """Service for business operations — read/reporting aggregate."""

    BROKER_MAX_LIMIT = 1000
    _PAYMENT_RELS = ("payment", "payments", "invoice_payment", "invoice_payments")
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
        fetch_limit = offset + limit

        cart_ops = self._fetch_cart_operations(
            supplier_id=supplier_id, client_id=client_id,
            offset=0, limit=fetch_limit, window=window,
        )
        delivery_ops = self._fetch_delivery_operations(
            supplier_id=supplier_id, client_id=client_id,
            offset=0, limit=fetch_limit, window=window,
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
        _INT_KEYS = {"item_count", "service_count"}
        _DECIMAL_KEYS = {
            "product_subtotal", "service_subtotal", "gross_subtotal",
            "discount_amount", "tax_amount", "delivery_revenue",
            "grand_total", "invoice_total", "paid_amount", "due_amount",
            "product_cost", "consumable_service_cost",
            "non_consumable_service_cost", "labor_cost", "delivery_cost",
            "total_cost", "margin_amount",
        }

        totals: Dict[str, Any] = {k: _ZERO for k in _DECIMAL_KEYS}
        totals.update({k: 0 for k in _INT_KEYS})

        by_status: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "grand_total": _ZERO, "due_amount": _ZERO}
        )
        by_source: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "grand_total": _ZERO}
        )
        by_supplier: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "grand_total": _ZERO, "due_amount": _ZERO}
        )
        by_client: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "grand_total": _ZERO, "due_amount": _ZERO}
        )
        by_day: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "grand_total": _ZERO, "due_amount": _ZERO}
        )

        for op in ops:
            for k in _DECIMAL_KEYS:
                try:
                    totals[k] += self._safe_decimal(op.get(k, 0))
                except (TypeError, ValueError):
                    continue
            for k in _INT_KEYS:
                try:
                    totals[k] += int(op.get(k, 0) or 0)
                except (TypeError, ValueError):
                    continue

            status = (op.get("status") or "unknown").strip().lower()
            by_status[status]["count"] += 1
            by_status[status]["grand_total"] += self._safe_decimal(op.get("grand_total", 0))
            by_status[status]["due_amount"] += self._safe_decimal(op.get("due_amount", 0))

            src = (op.get("source_type") or "unknown").strip().lower()
            by_source[src]["count"] += 1
            by_source[src]["grand_total"] += self._safe_decimal(op.get("grand_total", 0))

            sup = op.get("supplier_id")
            if sup is not None:
                by_supplier[sup]["count"] += 1
                by_supplier[sup]["grand_total"] += self._safe_decimal(op.get("grand_total", 0))
                by_supplier[sup]["due_amount"] += self._safe_decimal(op.get("due_amount", 0))

            cli = op.get("client_id")
            if cli is not None:
                by_client[cli]["count"] += 1
                by_client[cli]["grand_total"] += self._safe_decimal(op.get("grand_total", 0))
                by_client[cli]["due_amount"] += self._safe_decimal(op.get("due_amount", 0))

            created = op.get("created_at")
            if created is not None:
                day_key = self._to_utc(created).date().isoformat()
                by_day[day_key]["count"] += 1
                by_day[day_key]["grand_total"] += self._safe_decimal(op.get("grand_total", 0))
                by_day[day_key]["due_amount"] += self._safe_decimal(op.get("due_amount", 0))

        total_rev = totals["grand_total"]
        total_cost = totals["total_cost"]
        total_paid = totals["paid_amount"]
        total_due = totals["due_amount"]

        overall_roi = _q4((total_rev - total_cost) / total_cost) if total_cost > _ZERO else None
        avg_ticket = _q2(total_rev / Decimal(len(ops))) if ops else _ZERO
        collection_rate = (
            _q4(total_paid / (total_paid + total_due))
            if (total_paid + total_due) > _ZERO else None
        )
        discount_rate = (
            _q4(totals["discount_amount"] / totals["gross_subtotal"])
            if totals["gross_subtotal"] > _ZERO else None
        )

        totals_wire = {}
        for k, v in totals.items():
            if isinstance(v, Decimal):
                totals_wire[k] = _to_wire(_q2(v))
            else:
                totals_wire[k] = int(v)

        def _round_buckets(d):
            out = {}
            for k, v in d.items():
                out[k] = {
                    kk: (_to_wire(_q2(vv)) if isinstance(vv, Decimal)
                         else (int(vv) if isinstance(vv, int) else vv))
                    for kk, vv in v.items()
                }
            return out

        return {
            "totals": totals_wire,
            "ratios": {
                "overall_roi": _to_wire(overall_roi) if overall_roi is not None else None,
                "average_ticket": _to_wire(avg_ticket),
                "collection_rate": _to_wire(collection_rate) if collection_rate is not None else None,
                "discount_rate": _to_wire(discount_rate) if discount_rate is not None else None,
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
            "by_day": _round_buckets(dict(sorted(by_day.items()))),
        }

    # ------------------------------------------------------------------
    # Time window
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_time_window(date_from, date_to):
        start = BusinessOperationService._to_utc(date_from) if date_from else None
        end = BusinessOperationService._to_utc(date_to) if date_to else None

        if start is not None and start.time() == time(0, 0):
            start = datetime.combine(start.date(), time(0, 0, 0, 0), tzinfo=timezone.utc)
        if end is not None and end.time() == time(0, 0):
            end = datetime.combine(end.date(), time(23, 59, 59, 999999), tzinfo=timezone.utc)

        if start is not None and end is not None and start > end:
            logger.warning(
                f"Time window inverted after normalization: "
                f"start={start} > end={end}. Swapping."
            )
            start, end = end, start

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
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    # ------------------------------------------------------------------
    # Cart branch
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
                # Product.provider_id — the actual FK column on Product.
                prov = getattr(p, "provider_id", None)
                if pid is not None and prov is not None:
                    mapping[pid] = prov

        return mapping



    def _fetch_cart_operations(self, supplier_id, client_id, offset, limit, window):
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

        carts = storage_broker.get(
            Cart,
            conditions,
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
            ],
            offset=offset,
            limit=limit,
        )
        carts = carts or []

        # Fallback: fetch ordered items in a separate query keyed by
        # cart_id, so `_cart_to_operation` has them even if the broker
        # doesn't eager-load `Cart.ordered_item`.
        cart_ids = [c.cart_id for c in carts]
        items_by_cart: Dict[int, List[OrderedItem]] = defaultdict(list)

        if cart_ids:
            chunk_size = max(1, self.BROKER_MAX_LIMIT // 10)
            for start_idx in range(0, len(cart_ids), chunk_size):
                chunk = cart_ids[start_idx:start_idx + chunk_size]
                rows = storage_broker.get(
                    OrderedItem,
                    {OrderedItem.cart_id: chunk},
                    [],
                    [{OrderedItem.product: []}],
                    offset=0,
                    limit=self.BROKER_MAX_LIMIT,
                ) or []
                for item in rows:
                    cid = getattr(item, "cart_id", None)
                    if cid is not None:
                        items_by_cart[cid].append(item)

            # Log AFTER the fill loop so the count is meaningful.
            logger.warning(
                "BOS diag: cart_ids=%r → fetched %d OrderedItem rows, %d carts have items",
                cart_ids,
                sum(len(v) for v in items_by_cart.values()),
                len(items_by_cart),
            )

        ops: List[Dict[str, Any]] = []
        for cart in carts:
            op = self._cart_to_operation(
                cart,
                items=items_by_cart.get(cart.cart_id, []),
            )
            if self._in_window(op["created_at"], window):
                ops.append(op)
        return ops
    
    
    
      # ------------------------------------------------------------------
    # Delivery branch
    # ------------------------------------------------------------------

    def _fetch_delivery_operations(self, supplier_id, client_id, offset, limit, window):
        conditions: List[Any] = []

        if supplier_id:
            conditions.append(Delivery.delivery_provider_id == supplier_id)

        start, end = window
        start_db = self._naive_utc(start)
        end_db = self._naive_utc(end)

        if start_db is not None and end_db is not None:
            conditions.append(Delivery.created_at.between(start_db, end_db))
        elif start_db is not None:
            conditions.append(Delivery.created_at >= start_db)
        elif end_db is not None:
            conditions.append(Delivery.created_at <= end_db)

        deliveries = storage_broker.get(
            Delivery,
            conditions,
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

        ops: List[Dict[str, Any]] = []
        for delivery in (deliveries or []):
            op = self._delivery_to_operation(delivery, client_id=client_id)
            if op is None:
                continue
            if not self._in_window(op["created_at"], window):
                continue
            ops.append(op)
        return ops

    def _cart_to_operation(
        self,
        cart: Cart,
        items: Optional[List[OrderedItem]] = None,
    ) -> Dict[str, Any]:
        logger.warning(
            "BOS diag: _cart_to_operation cart=%s received %d items, %d services",
            cart.cart_id,
            len(items or []),
            len(getattr(cart, "ordered_service", None) or []),
        )
        invoice = getattr(cart, "invoice", None)
        services = list(getattr(cart, "ordered_service", None) or [])
        # `items` is supplied by the caller from a separate query.
        items = list(items or [])

        delivery_fee = self._cart_delivery_fee(items, services)

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
            "_order_discount": self._safe_decimal(
                getattr(cart, "discount_amount", 0)
            ),
            "_delivery_fee": delivery_fee,
            "_cart_provider_id": cart.provider_id,
        }
        op.update(self._financials(items, services, invoice, op))
        return op

    @staticmethod
    def _cart_delivery_fee(items, services) -> Decimal:
        total = _ZERO
        for item in (items or []):
            total += BusinessOperationService._safe_decimal(
                getattr(item, "delivery_fee", 0)
            )
        for svc in (services or []):
            total += BusinessOperationService._safe_decimal(
                getattr(svc, "ordered_service_delivery_fee", 0)
            )
        return total

    def _delivery_to_operation(self, delivery: Delivery, client_id: int = 0):
        invoice = getattr(delivery, "invoice", None)
        placed_orders = (
            getattr(invoice, "placed_order", None) or []
            if invoice is not None else []
        )
        all_items: List[OrderedItem] = []
        order_discount = _ZERO
        for po in placed_orders:
            all_items.extend(getattr(po, "ordered_item", None) or [])
            order_discount += self._safe_decimal(
                getattr(po, "discount_amount", 0)
            )

        client = delivery.recipient_person_id
        if client is None and placed_orders:
            client = placed_orders[0].ordering_user_id

        if client_id and client != client_id:
            return None

        delivery_fee = self._safe_decimal(getattr(delivery, "delivery_fee", 0))

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
            "_cart_provider_id": delivery.delivery_provider_id,
        }
        op.update(self._financials(all_items, [], invoice, op))
        return op

    # ------------------------------------------------------------------
    # Window post-filter
    # ------------------------------------------------------------------

    @staticmethod
    def _in_window(created_at, window):
        start, end = window
        if start is None and end is None:
            return True
        if created_at is None:
            return False
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
                prov = getattr(p, "provider_id", None)
                if pid is not None and prov is not None:
                    mapping[pid] = prov

        return mapping

    # ------------------------------------------------------------------
    # Supplier filters
    # ------------------------------------------------------------------

    def _apply_supplier_filter_to_cart(self, op, supplier_id, product_provider_map):
        if not supplier_id:
            return op
        cart_provider = op.get("_cart_provider_id", op["supplier_id"])
        items = self._filter_items_by_supplier(op["items"], supplier_id, product_provider_map)
        if not items and not op["services"]:
            return None
        services = op["services"] if cart_provider == supplier_id else []
        if cart_provider != supplier_id:
            op["_delivery_fee"] = _ZERO
        op["items"] = items
        op["services"] = services
        op.update(self._financials(items, services, op.get("invoice"), op))
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
        # ---------- COMMERCIAL ----------
        logger.warning(
            "BOS diag: _financials items=%d services=%d",
            len(items),
            len(services),
        )
        product_subtotal = _ZERO
        item_discount_total = _ZERO
        tax_from_items = _ZERO
        product_cost = _ZERO

        for item in items:
            qty = self._safe_decimal(getattr(item, "ordered_quantity", 0))
            price = self._safe_decimal(getattr(item, "unit_price", 0))
            vat = self._safe_decimal(getattr(item, "vat_rate", 0))

            line_total = qty * price
            item_discount = self._safe_decimal(
                getattr(item, "discount_amount", 0)
            )
            line_net = line_total - item_discount

            product_subtotal += line_net
            item_discount_total += item_discount

            if vat > _ZERO:
                tax_from_items += line_total * (vat / (_HUNDRED + vat))

            # Use _safe_loaded — it checks state.dict without triggering
            # a lazy load on a detached instance.
            product = self._safe_loaded(item, "product")
            if product is not None:
                base = self._safe_decimal(getattr(product, "base_price", 0))
                if base > _ZERO:
                    product_cost += base * qty

        service_subtotal = _ZERO
        tax_from_services = _ZERO
        consumable_service_cost = _ZERO
        non_consumable_service_cost = _ZERO
        labor_cost = _ZERO

        for svc in services:
            svc_total = self._safe_decimal(getattr(svc, "subtotal", 0))
            svc_qty = self._safe_decimal(
                getattr(svc, "ordered_service_quantity", 0)
            )
            svc_vat = self._safe_decimal(getattr(svc, "vat_rate", 0))

            service_subtotal += svc_total
            if svc_vat > _ZERO:
                tax_from_services += svc_total * (svc_vat / (_HUNDRED + svc_vat))

            # _safe_loaded only — never getattr on a relationship.
            provided = self._safe_loaded(svc, "service")
            if provided is None:
                continue

            staff_reqs = (
                self._safe_loaded(provided, "service_staff_requirement") or []
            )
            for req in staff_reqs:
                hours = self._safe_decimal(
                    getattr(req, "service_staff_requirement_allocated_hours", 0)
                )
                rate = self._safe_decimal(
                    getattr(req, "service_staff_requirement_hourly_rate", 0)
                )
                min_count = self._safe_decimal(
                    getattr(req, "service_staff_requirement_min_count", 0)
                )
                people = min_count if min_count > _ZERO else _ONE
                labor_cost += hours * rate * people * svc_qty

            reqs = (
                self._safe_loaded(provided, "service_resource_requirement") or []
            )
            for req in reqs:
                qty = self._safe_decimal(
                    getattr(req, "service_resource_requirement_quantity", 0)
                )
                unit_cost = self._safe_decimal(
                    getattr(
                        req,
                        "unit_price",
                        getattr(req, "service_resource_requirement_cost_per_unit", 0),
                    )
                )
                is_consumable = bool(
                    getattr(req, "service_resource_requirement_is_consumable", 0)
                )

                if is_consumable:
                    consumable_service_cost += qty * unit_cost * svc_qty
                elif self.NON_CONSUMABLE_AMORTIZATION_DAYS > 0:
                    days = Decimal(self.NON_CONSUMABLE_AMORTIZATION_DAYS)
                    non_consumable_service_cost += (
                        qty * unit_cost * svc_qty
                    ) / days

        # ---------- DISCOUNT ----------
        order_discount = self._safe_decimal(op.get("_order_discount", 0))
        discount_total = item_discount_total + order_discount

        gross_subtotal = product_subtotal + service_subtotal
        taxable_amount = gross_subtotal - order_discount
        if taxable_amount < _ZERO:
            taxable_amount = _ZERO

        # ---------- DELIVERY ----------
        delivery_revenue = self._safe_decimal(op.get("_delivery_fee", 0))
        grand_total = _q2(taxable_amount + delivery_revenue)

        invoice_total = self._invoice_total(invoice)
        paid_full = _q2(self._sum_completed_payments(invoice))

        # Allocate the invoice's payment to this supplier's slice, in
        # proportion to the slice's value against the full invoice. A cart
        # that owns its whole invoice has slice_ratio == 1 (no change). A
        # delivery that is one provider's share of a multi-provider order
        # gets only its proportional share of the customer's payment.
        if invoice_total > _ZERO:
            slice_ratio = (grand_total / invoice_total).toDecimal(
                scaleOnInfinitePrecision=8,
            ) if hasattr(grand_total / invoice_total, "toDecimal") else (grand_total / invoice_total)
            if slice_ratio > _ONE:
                slice_ratio = _ONE
            elif slice_ratio < _ZERO:
                slice_ratio = _ZERO
            paid_amount = _q2(paid_full * slice_ratio)
        else:
            paid_amount = _ZERO

        raw_due = grand_total - paid_amount
        due_amount = raw_due if raw_due > _ZERO else _ZERO
        overpaid_amount = (-raw_due) if raw_due < _ZERO else _ZERO


        invoice_status = getattr(invoice, "invoice_status", None) if invoice else None

        # ---------- COST ----------
        delivery_cost = _ZERO

        total_cost = _q2(
            product_cost
            + consumable_service_cost
            + non_consumable_service_cost
            + labor_cost
            + delivery_cost
        )

        margin_amount = _q2(grand_total - total_cost)
        roi = _q4(margin_amount / total_cost) if total_cost > _ZERO else None
        tax_total = tax_from_items + tax_from_services

        return {
            "product_subtotal": _q2(product_subtotal),
            "service_subtotal": _q2(service_subtotal),
            "gross_subtotal": _q2(gross_subtotal),
            "discount_amount": _q2(discount_total),
            "item_discount_amount": _q2(item_discount_total),
            "order_discount_amount": _q2(order_discount),
            "tax_amount": _q2(tax_total),
            "delivery_revenue": _q2(delivery_revenue),
            "grand_total": grand_total,
            "invoice_total": _q2(invoice_total),
            "paid_amount": paid_amount,
            "due_amount": due_amount,
            "overpaid_amount": overpaid_amount,
            "invoice_status": invoice_status,
            "product_cost": _q2(product_cost),
            "consumable_service_cost": _q2(consumable_service_cost),
            "non_consumable_service_cost": _q2(non_consumable_service_cost),
            "labor_cost": _q2(labor_cost),
            "delivery_cost": _q2(delivery_cost),
            "total_cost": total_cost,
            "margin_amount": margin_amount,
            "roi": roi,
            "item_count": len(items),
            "service_count": len(services),
        }

    @staticmethod
    def _invoice_total(invoice: Optional[Invoice]) -> Decimal:
        if invoice is None:
            return _ZERO
        return BusinessOperationService._safe_decimal(
            getattr(invoice, "grand_total", 0)
        )

    def _sum_completed_payments(self, invoice: Optional[Invoice]) -> Decimal:
        if invoice is None:
            return _ZERO
        for rel_name in self._PAYMENT_RELS:
            value = self._safe_loaded(invoice, rel_name)
            if value:
                total = _ZERO
                for p in value:
                    if getattr(p, "payment_status", None) != "completed":
                        continue
                    total += self._safe_decimal(getattr(p, "payment_amount", 0))
                return total
        return _ZERO

    # ------------------------------------------------------------------
    # Detached-safe readers
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
    def _safe_decimal(value: Any) -> Decimal:
        if value is None:
            return _ZERO
        if isinstance(value, Decimal):
            if not value.is_finite():
                return _ZERO
            return value
        if isinstance(value, bool):
            return Decimal(1) if value else _ZERO
        if isinstance(value, int):
            return Decimal(value)
        if isinstance(value, float):
            if not math.isfinite(value):
                return _ZERO
            return Decimal(str(value))
        if isinstance(value, str):
            try:
                d = Decimal(value.strip())
            except Exception:
                return _ZERO
            return d if d.is_finite() else _ZERO
        try:
            return Decimal(str(value))
        except Exception:
            return _ZERO

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