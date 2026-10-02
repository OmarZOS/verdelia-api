#!/usr/bin/env python3
"""
Order Router Test Runner — updated for the three-phase workflow.

Lifecycle endpoints now in play:

  POST /api/v1/business/orders                     create   → PENDING
  POST /api/v1/business/orders/{order_id}/pay      pay      → PROCESSING
  POST /api/v1/business/orders/{order_id}/confirm-inventory
  POST /api/v1/business/orders/{order_id}/finalize pay + confirm (convenience)

The runner drives each order through one of four flows, chosen per order:

  A. create only                — leaves the order in PENDING
  B. create + pay               — advances to PROCESSING, invoice paid
  C. create + pay + confirm     — full pipeline
  D. create + finalize          — same as C, single call

Run with: python test_order_runner.py
"""

import asyncio
import httpx
import json
import sys
import random
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from pathlib import Path
import time


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TestUser:
    id: int
    username: str
    email: str
    password: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    user_data: Dict[str, Any] = field(default_factory=dict)
    person_data: Dict[str, Any] = field(default_factory=dict)
    location_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password': self.password,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'user_data': self.user_data,
            'person_data': self.person_data,
            'location_data': self.location_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestUser':
        expires_at = data.get('token_expires_at')
        parsed_expires = None
        if expires_at:
            try:
                parsed_expires = datetime.fromisoformat(str(expires_at).replace('Z', '+00:00'))
                if parsed_expires.tzinfo is None:
                    parsed_expires = parsed_expires.replace(tzinfo=timezone.utc)
            except Exception:
                parsed_expires = None
        return cls(
            id=data.get('id', 0),
            username=data.get('username') or '',
            email=data.get('email') or '',
            password=data.get('password') or '',
            access_token=data.get('access_token'),
            refresh_token=data.get('refresh_token'),
            token_expires_at=parsed_expires,
            user_data=data.get('user_data', {}),
            person_data=data.get('person_data', {}),
            location_data=data.get('location_data', {}),
        )

    def is_token_valid(self, buffer_seconds: int = 10) -> bool:
        if not self.access_token or not self.token_expires_at:
            return False
        expires = self.token_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires > datetime.now(timezone.utc) + timedelta(seconds=buffer_seconds)


@dataclass
class TestContext:
    users: List[TestUser] = field(default_factory=list)
    created_orders: List[int] = field(default_factory=list)
    created_products: List[int] = field(default_factory=list)
    created_suppliers: List[int] = field(default_factory=list)
    created_organisations: List[int] = field(default_factory=list)
    created_payments: List[int] = field(default_factory=list)
    created_invoices: List[int] = field(default_factory=list)
    created_deliveries: List[int] = field(default_factory=list)
    test_results: List[Dict[str, Any]] = field(default_factory=list)

    def save(self, filename: str = "test_context.json"):
        data = {
            'users': [u.to_dict() for u in self.users],
            'created_orders': self.created_orders,
            'created_products': self.created_products,
            'created_suppliers': self.created_suppliers,
            'created_organisations': self.created_organisations,
            'created_payments': self.created_payments,
            'created_invoices': self.created_invoices,
            'created_deliveries': self.created_deliveries,
            'timestamp': datetime.now().isoformat(),
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"💾 Test context saved to {filename}")

    def load(self, filename: str = "test_context.json") -> bool:
        if not Path(filename).exists():
            return False
        with open(filename, 'r') as f:
            data = json.load(f)
        self.users = [TestUser.from_dict(u) for u in data.get('users', [])]
        self.created_orders = data.get('created_orders', [])
        self.created_products = data.get('created_products', [])
        self.created_suppliers = data.get('created_suppliers', [])
        self.created_organisations = data.get('created_organisations', [])
        self.created_payments = data.get('created_payments', [])
        self.created_invoices = data.get('created_invoices', [])
        self.created_deliveries = data.get('created_deliveries', [])
        print(f"📂 Test context loaded from {filename}")
        return True


# ============================================================================
# HELPERS
# ============================================================================

def short(text: Optional[str], n: int = 400) -> str:
    if not text:
        return ""
    return text if len(text) <= n else text[:n] + "..."


def unwrap(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        inner = payload.get("data")
        if isinstance(inner, dict):
            return inner
    return payload if isinstance(payload, dict) else {}


def extract_validation_error(body_text: str) -> str:
    try:
        payload = json.loads(body_text)
    except Exception:
        return short(body_text, 400)

    detail = payload.get("detail") or payload.get("errors")
    message = payload.get("message")

    parts = []
    if isinstance(message, str):
        parts.append(message)
    if isinstance(detail, list):
        for d in detail[:5]:
            if isinstance(d, dict):
                loc = ".".join(str(x) for x in d.get("loc", []))
                msg = d.get("msg", "")
                parts.append(f"{loc}: {msg}" if loc else msg)
    elif isinstance(detail, str):
        parts.append(detail)
    elif isinstance(detail, dict):
        parts.append(json.dumps(detail))

    return " | ".join(parts) if parts else short(body_text, 400)


# ============================================================================
# ENUMS — casings match the API
# ============================================================================
#
# The create endpoint no longer accepts arbitrary placed_order_state values
# from the caller: every new order starts in PENDING. Send it explicitly
# anyway so the payload shape matches the schema, but do not attempt to
# bypass the workflow by asking for SHIPPED.
#
# PaymentStatus is lowercase; the order payload no longer carries it.

ORDER_STATE_ON_CREATE = "PENDING"          # OrderStatus uppercase
PAYMENT_METHODS = ["cash", "card", "bank_transfer"]


# ============================================================================
# FLOW VARIANTS
# ============================================================================

FLOW_CREATE_ONLY = "create_only"
FLOW_CREATE_AND_PAY = "create_and_pay"
FLOW_CREATE_PAY_CONFIRM = "create_pay_confirm"
FLOW_CREATE_AND_FINALIZE = "create_and_finalize"

ALL_FLOWS = [
    FLOW_CREATE_ONLY,
    FLOW_CREATE_AND_PAY,
    FLOW_CREATE_PAY_CONFIRM,
    FLOW_CREATE_AND_FINALIZE,
]

# Per-order weights: create-only is the cheapest, finalize is the heaviest.
# Adjust if you want a different mix under load.
FLOW_WEIGHTS = {
    FLOW_CREATE_ONLY: 0.25,
    FLOW_CREATE_AND_PAY: 0.35,
    FLOW_CREATE_PAY_CONFIRM: 0.20,
    FLOW_CREATE_AND_FINALIZE: 0.20,
}


# ============================================================================
# RUNNER
# ============================================================================

class OptimizedOrderTestRunner:
    def __init__(
        self,
        base_url: str = "http://localhost:9000",
        silo_url: str = "http://verdelia-silo:9096",
    ):
        self.base_url = base_url
        self.silo_url = silo_url
        self.client: Optional[httpx.AsyncClient] = None
        self.context = TestContext()
        self.results: List[Dict[str, Any]] = []
        self._product_cache: Dict[int, Dict] = {}

    async def __aenter__(self):
        limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
        timeout = httpx.Timeout(30.0, connect=5.0)
        verify = not (
            self.base_url.startswith("http://localhost")
            or self.base_url.startswith("http://127.")
            or self.base_url.startswith("http://verdelia")
        )
        self.client = httpx.AsyncClient(timeout=timeout, verify=verify, limits=limits)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    # ==================== AUTH ====================

    def get_auth_headers(self, user: TestUser) -> Dict[str, str]:
        if user.access_token:
            return {"Authorization": f"Bearer {user.access_token}"}
        return {}

    async def _login_user(self, user: TestUser) -> bool:
        if not user.username or not user.password:
            print(
                f"   ❌ Login skipped for user id={user.id}: "
                f"username={'<set>' if user.username else '<empty>'} "
                f"password={'<set>' if user.password else '<empty>'}"
            )
            return False

        payload = {
            "app_user_name": user.username,
            "app_user_password": user.password,
            "username": user.username,
            "password": user.password,
            "grant_type": "password",
            "scope": "",
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/authentication/token",
                json=payload,
            )
        except Exception as e:
            print(f"   ❌ Login network error for {user.username}: {e}")
            return False

        if response.status_code != 200:
            print(
                f"   ❌ Login failed for {user.username}: "
                f"status={response.status_code} body={short(response.text)}"
            )
            return False

        try:
            raw = response.json()
        except Exception as e:
            print(f"   ❌ Login response not JSON for {user.username}: {e}")
            return False

        data = unwrap(raw)
        token = data.get("access_token") or raw.get("access_token")
        if not token:
            print(
                f"   ❌ Login HTTP 200 but no access_token for {user.username}. "
                f"Raw: {short(response.text)}"
            )
            return False

        user.access_token = token
        user.refresh_token = data.get("refresh_token") or raw.get("refresh_token")

        expires_at_str = data.get("expires_at") or raw.get("expires_at")
        if expires_at_str:
            try:
                parsed = datetime.fromisoformat(str(expires_at_str).replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                user.token_expires_at = parsed
            except Exception:
                user.token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        else:
            expires_in = data.get("expires_in") or raw.get("expires_in") or 3600
            try:
                expires_in = int(expires_in)
            except Exception:
                expires_in = 3600
            user.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        print(
            f"   ✅ Logged in {user.username} "
            f"(expires {user.token_expires_at.isoformat()})"
        )
        return True

    async def _ensure_authenticated(self, user: TestUser) -> bool:
        if user.is_token_valid():
            return True
        reason = "no token" if not user.access_token else "token expired"
        print(f"   🔐 Re-authenticating {user.username} ({reason})")
        return await self._login_user(user)

    # ==================== ORDER LIFECYCLE STEPS ====================

    async def _create_one_order(
        self,
        user: TestUser,
        headers: Dict[str, str],
        product_ids: List[int],
        payment_method: str,
        include_delivery: bool,
    ) -> Tuple[Optional[int], Optional[int], Optional[str]]:
        """
        POST /business/orders.
        Returns (order_id, invoice_id, error_string).
        """
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        num_products = random.randint(1, min(3, len(product_ids)))
        selected_products = random.sample(product_ids, num_products)

        ordered_items = []
        for product_id in selected_products:
            product = self._get_cached_product(product_id)
            if not product:
                continue
            quantity = random.randint(1, 3)
            ordered_items.append({
                "id_ordered_item": 0,
                "ordered_product_id": product_id,
                "order_ref": 0,
                "ordered_quantity": quantity,
                "unit_price": product.get('product_price', 50.0),
                "applied_vat": round(random.uniform(0, 19), 2),
                "product_discount": round(random.uniform(0, 10), 2),
            })

        if not ordered_items:
            return None, None, "no items assembled"

        # The workflow forces PENDING on creation. Send it explicitly so
        # the payload matches the schema, but do not attempt to inject a
        # later state — the policy will reject it.
        order_data = {
            "id_placed_order": 0,
            "ordered_timestamp": now,
            "placed_order_last_mod": now,
            "placed_order_state": ORDER_STATE_ON_CREATE,
            "payment_method": payment_method,
            "order_discount": round(random.uniform(0, 10), 2),
            "ordering_user_id": user.id,
            "payment_ref": "",
        }

        request_data: Dict[str, Any] = {
            "ordered_items": ordered_items,
            "submitted_order": order_data,
        }

        if include_delivery and random.random() > 0.3:
            request_data["delivery_info"] = self._generate_delivery_info()

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/orders",
                params={"payment_method": payment_method},
                json=request_data,
                headers=headers,
            )
        except Exception as e:
            return None, None, f"network: {e}"

        if response.status_code != 201:
            return (
                None,
                None,
                f"status={response.status_code} → "
                f"{extract_validation_error(response.text)}",
            )

        try:
            payload = response.json()
        except Exception as e:
            return None, None, f"bad json: {e}"

        data = unwrap(payload)
        order_id = self._extract_order_id(data)
        if not order_id or order_id <= 0:
            return None, None, "no order_id in response"

        invoice_id = self._extract_invoice_id(data)

        self.context.created_orders.append(order_id)
        if invoice_id:
            self.context.created_invoices.append(invoice_id)

        return order_id, invoice_id, None

    async def _pay_order(
        self,
        order_id: int,
        payment_method: str,
        headers: Dict[str, str],
    ) -> Optional[str]:
        """
        POST /business/orders/{order_id}/pay.
        Returns None on success, an error string otherwise.
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/orders/{order_id}/pay",
                params={"payment_method": payment_method},
                headers=headers,
            )
        except Exception as e:
            return f"network: {e}"

        if response.status_code != 200:
            return (
                f"status={response.status_code} → "
                f"{extract_validation_error(response.text)}"
            )

        try:
            data = unwrap(response.json())
        except Exception:
            data = {}

        payment_id = data.get("payment_id")
        if payment_id:
            self.context.created_payments.append(int(payment_id))
        return None

    async def _confirm_inventory(
        self,
        order_id: int,
        headers: Dict[str, str],
    ) -> Optional[str]:
        """
        POST /business/orders/{order_id}/confirm-inventory.
        Returns None on success, an error string otherwise.
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/orders/{order_id}/confirm-inventory",
                headers=headers,
            )
        except Exception as e:
            return f"network: {e}"

        if response.status_code != 200:
            return (
                f"status={response.status_code} → "
                f"{extract_validation_error(response.text)}"
            )
        return None

    async def _finalize_order(
        self,
        order_id: int,
        payment_method: str,
        headers: Dict[str, str],
    ) -> Optional[str]:
        """
        POST /business/orders/{order_id}/finalize (pay + confirm in one call).
        Returns None on success, an error string otherwise.
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/orders/{order_id}/finalize",
                params={"payment_method": payment_method},
                headers=headers,
            )
        except Exception as e:
            return f"network: {e}"

        if response.status_code != 200:
            return (
                f"status={response.status_code} → "
                f"{extract_validation_error(response.text)}"
            )

        try:
            data = unwrap(response.json())
        except Exception:
            data = {}

        payment_id = data.get("payment_id")
        if payment_id:
            self.context.created_payments.append(int(payment_id))
        return None

    # ==================== BULK CREATION ====================

    def _pick_flow(self) -> str:
        r = random.random()
        cumulative = 0.0
        for flow, weight in FLOW_WEIGHTS.items():
            cumulative += weight
            if r <= cumulative:
                return flow
        return FLOW_CREATE_ONLY

    async def create_orders_bulk(
        self,
        user: TestUser,
        product_ids: List[int],
        num_orders: int = 20,
        include_delivery: bool = True,
    ) -> Dict[str, List[int]]:
        """
        Create `num_orders` orders for `user`, driving each through a
        randomly chosen lifecycle flow.

        Returns a dict with counts per flow:
            {
              'created':          [order_id, ...],
              'paid':             [order_id, ...],
              'confirmed':        [order_id, ...],
              'finalized':        [order_id, ...],
              'failed':           [(order_id?, reason), ...],
            }
        """
        headers = self.get_auth_headers(user)
        if not headers:
            print(f"   ❌ No auth token for user {user.id}")
            return {'created': [], 'paid': [], 'confirmed': [], 'finalized': [], 'failed': []}

        print(f"   🚀 Creating {num_orders} orders concurrently...")
        start_time = time.time()

        async def run_one(index: int) -> Dict[str, Any]:
            flow = self._pick_flow()
            payment_method = random.choice(PAYMENT_METHODS)

            order_id, invoice_id, err = await self._create_one_order(
                user=user,
                headers=headers,
                product_ids=product_ids,
                payment_method=payment_method,
                include_delivery=include_delivery,
            )
            if err or not order_id:
                return {'index': index, 'flow': flow, 'error': err or 'no order_id'}

            result = {
                'index': index,
                'flow': flow,
                'order_id': order_id,
                'invoice_id': invoice_id,
                'paid': False,
                'confirmed': False,
                'finalized': False,
                'error': None,
            }

            if flow == FLOW_CREATE_ONLY:
                return result

            if flow == FLOW_CREATE_AND_PAY:
                err = await self._pay_order(order_id, payment_method, headers)
                if err:
                    result['error'] = f"pay failed: {err}"
                    return result
                result['paid'] = True
                return result

            if flow == FLOW_CREATE_PAY_CONFIRM:
                err = await self._pay_order(order_id, payment_method, headers)
                if err:
                    result['error'] = f"pay failed: {err}"
                    return result
                result['paid'] = True

                err = await self._confirm_inventory(order_id, headers)
                if err:
                    result['error'] = f"confirm failed: {err}"
                    return result
                result['confirmed'] = True
                return result

            if flow == FLOW_CREATE_AND_FINALIZE:
                err = await self._finalize_order(order_id, payment_method, headers)
                if err:
                    result['error'] = f"finalize failed: {err}"
                    return result
                result['finalized'] = True
                result['paid'] = True
                result['confirmed'] = True
                return result

            return result

        tasks = [run_one(i) for i in range(num_orders)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start_time
        print(f"   ⏱️ Completed in {elapsed:.2f}s ({len(tasks)} orders)")

        summary = {
            'created': [],
            'paid': [],
            'confirmed': [],
            'finalized': [],
            'failed': [],
        }
        failures: List[str] = []

        for r in results:
            if isinstance(r, Exception):
                summary['failed'].append((None, f"raised: {r}"))
                failures.append(f"raised: {r}")
                continue

            order_id = r.get('order_id')
            if r.get('error') and not order_id:
                summary['failed'].append((None, r['error']))
                failures.append(f"order {r['index']}: {r['error']}")
                continue

            if order_id:
                summary['created'].append(order_id)
            if r.get('paid'):
                summary['paid'].append(order_id)
            if r.get('confirmed'):
                summary['confirmed'].append(order_id)
            if r.get('finalized'):
                summary['finalized'].append(order_id)
            if r.get('error'):
                summary['failed'].append((order_id, r['error']))
                failures.append(f"order {order_id} (flow={r['flow']}): {r['error']}")

        print(
            f"   ✅ created={len(summary['created'])} "
            f"paid={len(summary['paid'])} "
            f"confirmed={len(summary['confirmed'])} "
            f"finalized={len(summary['finalized'])} "
            f"failed={len(summary['failed'])}"
        )
        if failures:
            print("   ❌ Sample failures:")
            for f in failures[:5]:
                print(f"      - {f}")
            if len(failures) > 5:
                print(f"      … and {len(failures) - 5} more")

        return summary

    def _get_cached_product(self, product_id: int) -> Optional[Dict]:
        if product_id in self._product_cache:
            return self._product_cache[product_id]
        return {
            'product_price': random.uniform(10, 200),
            'product_quantity': random.randint(50, 500),
        }

    def _generate_delivery_info(self) -> Dict[str, Any]:
        cities = ["Algiers", "Oran", "Constantine", "Annaba", "Blida"]
        streets = ["Main St", "Rue Didouche Mourad", "Avenue du 1er Novembre"]
        return {
            "destination_address": {
                "id_location": 0,
                "location_latitude": round(random.uniform(36.0, 37.0), 6),
                "location_longitude": round(random.uniform(-5.0, 8.0), 6),
                "location_name": random.choice(["Home", "Office", "Clinic"]),
                "location_address_id": 0,
                "id_address": 0,
                "address_street": f"{random.randint(1, 999)} {random.choice(streets)}",
                "address_city": random.choice(cities),
                "address_postal_code": f"{random.randint(1000, 9999)}",
                "address_country": "DZ",
            },
            "delivery_fee": round(random.uniform(0, 50), 2),
        }

    def _extract_order_id(self, response_data: Dict[str, Any]) -> int:
        for key in ("id_placed_order", "id", "order_id"):
            if key in response_data:
                try:
                    v = int(response_data[key])
                    if v > 0:
                        return v
                except (TypeError, ValueError):
                    pass
        order = response_data.get("order")
        if isinstance(order, dict):
            for key in ("id_placed_order", "id", "order_id"):
                if key in order:
                    try:
                        v = int(order[key])
                        if v > 0:
                            return v
                    except (TypeError, ValueError):
                        pass
        return 0

    def _extract_invoice_id(self, response_data: Dict[str, Any]) -> Optional[int]:
        for key in ("invoice_id", "id_invoice"):
            if key in response_data:
                try:
                    v = int(response_data[key])
                    if v > 0:
                        return v
                except (TypeError, ValueError):
                    pass
        invoice = response_data.get("invoice")
        if isinstance(invoice, dict):
            for key in ("invoice_id", "id_invoice", "id"):
                if key in invoice:
                    try:
                        v = int(invoice[key])
                        if v > 0:
                            return v
                    except (TypeError, ValueError):
                        pass
        return None

    # ==================== MAIN RUNNER ====================

    async def run_tests(
        self,
        context_file: str = "test_context.json",
        orders_per_user: int = 20,
        max_users: int = 5,
    ):
        print("\n" + "=" * 70)
        print("🚀 OPTIMIZED ORDER TEST RUNNER — three-phase workflow")
        print("=" * 70)
        print(f"📍 Base URL: {self.base_url}")
        print(f"📦 Orders per user: {orders_per_user}")
        print(f"👤 Max users: {max_users}")
        print("=" * 70)

        if not Path(context_file).exists():
            print(f"❌ Context file {context_file} not found!")
            return

        self.context.load(context_file)
        print(f"📂 Loaded {len(self.context.users)} users")
        print(f"📦 Loaded {len(self.context.created_products)} products")
        print(f"🏢 Loaded {len(self.context.created_organisations)} organisations")
        print(f"🏥 Loaded {len(self.context.created_suppliers)} suppliers")

        if not self.context.created_products:
            print("❌ No products found in context!")
            return

        for user in self.context.users[:max_users]:
            if not user.password:
                print(
                    f"   ⚠️ User {user.username} (id={user.id}) has no password."
                )

        authenticated_users: List[TestUser] = []
        for user in self.context.users[:max_users]:
            ok = await self._ensure_authenticated(user)
            if ok:
                authenticated_users.append(user)

        if not authenticated_users:
            print("❌ No authenticated users available!")
            return

        print(f"\n👤 Using {len(authenticated_users)} authenticated users")

        product_ids = self.context.created_products
        print(f"📦 Using {len(product_ids)} products for orders")

        aggregate = {
            'created': [],
            'paid': [],
            'confirmed': [],
            'finalized': [],
            'failed': [],
        }

        start_time = time.time()

        for i, user in enumerate(authenticated_users):
            print(f"\n👤 User {i+1}/{len(authenticated_users)}: {user.username} (ID: {user.id})")

            if not user.is_token_valid(buffer_seconds=0):
                if not await self._login_user(user):
                    print(f"   ⏭️ Skipping user {user.username} — auth failed")
                    continue

            per_user = await self.create_orders_bulk(
                user,
                product_ids,
                num_orders=orders_per_user,
                include_delivery=True,
            )
            for key in aggregate:
                aggregate[key].extend(per_user.get(key, []))

            await asyncio.sleep(0.2)

        elapsed = time.time() - start_time

        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)
        print(f"✅ Created:   {len(aggregate['created'])}")
        print(f"💳 Paid:      {len(aggregate['paid'])}")
        print(f"📦 Confirmed: {len(aggregate['confirmed'])}")
        print(f"⚡ Finalized: {len(aggregate['finalized'])}")
        print(f"❌ Failed:    {len(aggregate['failed'])}")
        if elapsed > 0:
            print(f"⏱️ Total time: {elapsed:.2f}s")
            print(f"📈 Rate: {len(aggregate['created']) / elapsed:.1f} orders/second")

        if aggregate['created']:
            unique_orders = list(dict.fromkeys(aggregate['created']))
            preview = ', '.join(map(str, unique_orders[:10]))
            tail = '...' if len(unique_orders) > 10 else ''
            print(f"\n📋 Order IDs: {preview}{tail}")

        self.context.save(context_file)
        print("\n" + "=" * 70)


# ============================================================================
# MAIN
# ============================================================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Optimized Order Test Runner — workflow-aware")
    parser.add_argument("--url", default="http://localhost:9000")
    parser.add_argument("--silo-url", default="http://verdelia-silo:9096")
    parser.add_argument("--context-file", default="test_context.json")
    parser.add_argument("--orders-per-user", type=int, default=20)
    parser.add_argument("--max-users", type=int, default=5)

    args = parser.parse_args()

    async with OptimizedOrderTestRunner(args.url, args.silo_url) as runner:
        await runner.run_tests(
            context_file=args.context_file,
            orders_per_user=args.orders_per_user,
            max_users=args.max_users,
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Tests interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)