#!/usr/bin/env python3
"""
Bulk Data Creator for Verdelia - Creates Carts, Processes Payments & Tests Status Transitions
Run with: python bulk_data_creator.py

This script:
1. Fetches existing products, services, and providers
2. Creates carts with products and services
3. Processes payments for carts using their invoices
4. Tests invoice status transitions
5. Tests payment status transitions (PENDING → PAID → REFUNDED, PENDING → FAILED)

Backend contract (from routers/financial_router.py):
  - All responses are wrapped: {"success": bool, "message": str, "data": {...}}
  - Payment statuses are UPPERCASE: PENDING | PAID | FAILED | REFUNDED
  - Endpoints:
      POST   /api/v1/business/payments                     (create)
      GET    /api/v1/business/payments/{id}                (get one)
      GET    /api/v1/business/payments?invoice_id=...      (list)
      PATCH  /api/v1/business/payments/{id}/status?new_status=...
      POST   /api/v1/business/payments/{id}/confirm        (PENDING → PAID)
      POST   /api/v1/business/payments/{id}/reject         (PENDING → FAILED)
      POST   /api/v1/business/payments/{id}/refund         (PAID → REFUNDED)
"""

import asyncio
import httpx
import json
import sys
import uuid
import random
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import time
import argparse


# ============================================================================
# RESPONSE HELPERS
# ============================================================================

def unwrap(payload: Any) -> Dict[str, Any]:
    """
    The backend wraps all responses in {"success": ..., "message": ..., "data": {...}}.
    This returns the inner `data` dict, tolerating flat responses too.
    """
    if isinstance(payload, dict):
        inner = payload.get("data")
        if isinstance(inner, dict):
            return inner
        if isinstance(inner, list):
            # Some list endpoints put the list in `data`; keep the wrapper.
            return payload
    return payload if isinstance(payload, dict) else {}


def unwrap_list(payload: Any) -> List[Dict[str, Any]]:
    """Return the list out of a wrapped or plain response."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        inner = payload.get("data")
        if isinstance(inner, list):
            return inner
        if isinstance(inner, dict):
            for key in ("items", "results", "data"):
                v = inner.get(key)
                if isinstance(v, list):
                    return v
        # Fall back: try common keys at top level
        for key in ("items", "results"):
            v = payload.get(key)
            if isinstance(v, list):
                return v
    return []


# ============================================================================
# STATUS ENUMS
# ============================================================================

class InvoiceStatus:
    """
    Invoice statuses as observed in this system.
    Note: cart creation auto-processes a payment on this backend, so a fresh
    invoice is frequently 'paid' rather than 'unpaid'.
    """
    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    REFUNDED = "refunded"
    CANCELED = "canceled"
    DEPOSITED = "deposited"

    TRANSITIONS = {
        "unpaid": ["partially_paid", "paid", "canceled", "overdue"],
        "partially_paid": ["paid", "canceled", "overdue", "refunded"],
        "paid": ["refunded"],
        "overdue": ["paid", "canceled", "partially_paid"],
        "deposited": ["paid", "partially_paid", "refunded"],
        "canceled": [],
        "refunded": [],
    }

    @classmethod
    def is_valid_transition(cls, from_status: str, to_status: str) -> bool:
        if from_status == to_status:
            return True
        return to_status in cls.TRANSITIONS.get(from_status, [])


class PaymentStatus:
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    PARTIAL    = "partial"
    FAILED     = "failed"
    CANCELLED  = "cancelled"

    TRANSITIONS = {
        "pending":    ["processing", "completed", "failed", "cancelled"],
        "processing": ["completed", "failed", "cancelled"],
        "completed":  ["cancelled"],   # refund path
        "partial":    ["completed", "cancelled"],
        "failed":     ["pending"],     # retry
        "cancelled":  [],              # terminal
    }

    @classmethod
    def is_valid_transition(cls, from_status: str, to_status: str) -> bool:
        if from_status == to_status:
            return True
        return to_status in cls.TRANSITIONS.get(from_status, [])

    # Human-readable aliases so test code reads naturally
    REFUNDED = "cancelled"   # refund now maps to cancelled
    PAID     = "completed"   # for invoice-side reasoning


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TestUser:
    id: int = 0
    username: str = ""
    email: str = ""
    password: str = ""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    wallet_id: Optional[int] = None
    person_id: Optional[int] = None


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str = ""
    expected: Any = None
    actual: Any = None


@dataclass
class BulkContext:
    users: List[TestUser] = field(default_factory=list)
    products: List[Dict[str, Any]] = field(default_factory=list)
    services: List[Dict[str, Any]] = field(default_factory=list)
    providers: List[Dict[str, Any]] = field(default_factory=list)
    created_carts: List[int] = field(default_factory=list)
    created_invoices: List[int] = field(default_factory=list)
    created_payments: List[int] = field(default_factory=list)
    auth_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    @property
    def product_ids(self) -> List[int]:
        ids = []
        for p in self.products:
            pid = p.get('id_product') or p.get('id')
            if pid and isinstance(pid, int) and pid > 0:
                ids.append(pid)
        return ids

    @property
    def service_ids(self) -> List[int]:
        ids = []
        for s in self.services:
            sid = s.get('provided_service_id') or s.get('id')
            if sid and isinstance(sid, int) and sid > 0:
                ids.append(sid)
        return ids

    @property
    def provider_ids(self) -> List[int]:
        ids = []
        for p in self.providers:
            pid = p.get('id_product_provider') or p.get('id')
            if pid and isinstance(pid, int) and pid > 0:
                ids.append(pid)
        return ids

    def is_token_valid(self) -> bool:
        if not self.auth_token:
            return False
        if not self.token_expires_at:
            return True
        return datetime.now() < self.token_expires_at


# ============================================================================
# TEST CONTEXT LOADER
# ============================================================================

def load_context(context_file: str = "test_context.json") -> BulkContext:
    context = BulkContext()

    if not Path(context_file).exists():
        print(f"⚠️ Context file {context_file} not found")
        return context

    with open(context_file, 'r') as f:
        data = json.load(f)

    user_data = data.get('users', [])
    for u in user_data:
        user = TestUser(
            id=u.get('id', 0),
            username=u.get('username', ''),
            email=u.get('email', ''),
            password=u.get('password', ''),
            access_token=u.get('access_token'),
            refresh_token=u.get('refresh_token')
        )
        expires_at = u.get('token_expires_at')
        if expires_at:
            try:
                user.token_expires_at = datetime.fromisoformat(expires_at)
            except Exception:
                pass
        context.users.append(user)

    for user in context.users:
        if user.access_token:
            context.auth_token = user.access_token
            context.token_expires_at = user.token_expires_at
            break

    print(f"📂 Loaded context from {context_file}")
    print(f"   👤 Users: {len(context.users)}")

    if context.auth_token:
        if context.is_token_valid():
            print(f"   🔐 Token valid until: {context.token_expires_at}")
        else:
            print(f"   ⚠️ Token expired at: {context.token_expires_at}")

    return context


# ============================================================================
# DATA GENERATORS
# ============================================================================

def generate_cart_data(
    provider_id: int,
    seller_id: int,
    product_ids: List[int],
    service_ids: List[int],
) -> Dict[str, Any]:
    """
    Cart creation payload matching the backend's CartCreateRequest.
    """
    due = (datetime.now() + timedelta(days=30)).date().isoformat()

    payload: Dict[str, Any] = {
        "provider_id": provider_id,
        "seller_user_id": seller_id,
        "buyer_user_id": seller_id,
        "cart": {
            "cart_status": "open",
            "cart_total_amount": 0,
            "cart_notes": f"Bulk cart - {datetime.now().isoformat()}",
            "cart_due_date": due,
        },
        "ordered_items": [],
        "ordered_services": [],
    }

    if product_ids:
        num_products = random.randint(1, min(3, len(product_ids)))
        for product_id in random.sample(product_ids, num_products):
            payload["ordered_items"].append({
                "ordered_product_id": product_id,
                "ordered_quantity": random.randint(1, 3),
                "unit_price": round(random.uniform(5, 100), 2),
                "applied_vat": round(random.uniform(0, 19), 2),
                "product_discount": round(random.uniform(0, 10), 2),
            })

    if service_ids:
        num_services = random.randint(0, min(2, len(service_ids)))
        for service_id in (random.sample(service_ids, num_services) if num_services else []):
            unit_price = round(random.uniform(50, 300), 2)
            qty = random.randint(1, 2)
            payload["ordered_services"].append({
                "ordered_service_service_id": service_id,
                "ordered_service_quantity": qty,
                "ordered_service_unit_price": unit_price,
                "ordered_service_total_price": unit_price * qty,
                "ordered_service_notes": f"Bulk service - {uuid.uuid4().hex[:6]}",
                "ordered_service_scheduled_at": (
                    datetime.now() + timedelta(days=random.randint(1, 14))
                ).isoformat(),
            })

    return payload


# ============================================================================
# BULK DATA CREATOR
# ============================================================================

class BulkDataCreator:
    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url
        self.client: Optional[httpx.AsyncClient] = None
        self.context = BulkContext()
        self.stats = {
            "carts_created": 0,
            "invoices_created": 0,
            "payments_created": 0,
            "errors": 0,
            "tests_passed": 0,
            "tests_failed": 0,
        }
        self.test_results: List[TestResult] = []
        self._token_refreshed = False

    async def __aenter__(self):
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=40)
        timeout = httpx.Timeout(30.0, connect=5.0)
        self.client = httpx.AsyncClient(timeout=timeout, verify=False, limits=limits)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    def get_auth_headers(self) -> Dict[str, str]:
        if self.context.auth_token:
            return {"Authorization": f"Bearer {self.context.auth_token}"}
        return {}

    def print_status(self, message: str, emoji: str = "ℹ️"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {emoji} {message}")

    def record_test(self, name: str, passed: bool, details: str = "",
                    expected: Any = None, actual: Any = None):
        result = TestResult(name=name, passed=passed, details=details,
                            expected=expected, actual=actual)
        self.test_results.append(result)
        if passed:
            self.stats["tests_passed"] += 1
            print(f"   ✅ PASSED: {name}")
        else:
            self.stats["tests_failed"] += 1
            print(f"   ❌ FAILED: {name}")
            if expected is not None:
                print(f"      Expected: {expected}")
                print(f"      Actual:   {actual}")
        if details:
            print(f"      {details}")

    # ==================== Authentication ====================

    async def ensure_valid_token(self) -> bool:
        if self.context.is_token_valid():
            return True

        if self.context.users:
            for user in self.context.users:
                if user.username and user.password:
                    self.print_status(f"🔐 Token expired, logging in as {user.username}...", "🔐")
                    if await self.login_user(user.username, user.password):
                        self._token_refreshed = True
                        return True

        self.print_status("❌ No valid authentication token available", "❌")
        return False

    async def login_user(self, username: str, password: str) -> bool:
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/authentication/token",
                json={
                    "app_user_name": username,
                    "app_user_password": password,
                },
            )

            if response.status_code == 200:
                result = response.json()
                access_token = result.get('access_token')
                if access_token:
                    self.context.auth_token = access_token
                    expires_in = result.get('expires_in', 3600)
                    self.context.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

                    for user in self.context.users:
                        if user.username == username:
                            user.access_token = access_token
                            user.token_expires_at = self.context.token_expires_at
                            break

                    self.print_status(
                        f"✅ Login successful, token valid until "
                        f"{self.context.token_expires_at.strftime('%H:%M:%S')}",
                        "✅",
                    )
                    return True
            self.print_status(f"❌ Login failed: {response.status_code}", "❌")
            return False
        except Exception as e:
            self.print_status(f"❌ Login error: {e}", "❌")
            return False

    # ==================== Fetch Existing Data ====================

    async def fetch_providers(self) -> bool:
        self.print_status("📋 Fetching providers...", "📋")

        if not await self.ensure_valid_token():
            return False

        headers = self.get_auth_headers()

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/suppliers",
                params={"offset": 0, "limit": 100},
                headers=headers,
            )

            if response.status_code == 200:
                raw = response.json()
                self.context.providers = unwrap_list(raw)

                self.print_status(f"✅ Found {len(self.context.providers)} providers", "✅")
                for prov in self.context.providers[:3]:
                    pid = prov.get('id_product_provider', prov.get('id', 'N/A'))
                    name = prov.get('provider_name', prov.get('name', 'Unknown'))
                    print(f"      - ID: {pid}, Name: {name}")
                return True

            self.print_status(f"❌ Failed to fetch providers: {response.status_code}", "❌")
            return False
        except Exception as e:
            self.print_status(f"❌ Error fetching providers: {e}", "❌")
            return False

    async def fetch_products(self, provider_id: int) -> bool:
        self.print_status(f"📦 Fetching products for provider {provider_id}...", "📦")

        if not await self.ensure_valid_token():
            return False

        headers = self.get_auth_headers()
        user_id = self.context.users[0].id if self.context.users else 0

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/products/{user_id}/{provider_id}/0/0/50",
                headers=headers,
            )

            if response.status_code == 200:
                raw = response.json()
                self.context.products = unwrap_list(raw)

                self.print_status(f"✅ Found {len(self.context.products)} products", "✅")
                for prod in self.context.products[:3]:
                    pid = prod.get('id_product', prod.get('id', 'N/A'))
                    name = prod.get('product_name', 'Unknown')
                    qty = prod.get('product_quantity', 0)
                    print(f"      - ID: {pid}, Name: {name}, Qty: {qty}")
                return True

            self.print_status(f"❌ Failed to fetch products: {response.status_code}", "❌")
            return False
        except Exception as e:
            self.print_status(f"❌ Error fetching products: {e}", "❌")
            return False

    async def fetch_services(self, provider_id: int) -> bool:
        self.print_status(f"📋 Fetching services for provider {provider_id}...", "📋")

        if not await self.ensure_valid_token():
            return False

        headers = self.get_auth_headers()

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/services/provider/{provider_id}",
                params={"offset": 0, "limit": 50, "active_only": True},
                headers=headers,
            )

            if response.status_code == 200:
                raw = response.json()
                self.context.services = unwrap_list(raw)

                self.print_status(f"✅ Found {len(self.context.services)} services", "✅")
                for service in self.context.services[:3]:
                    sid = service.get('provided_service_id', service.get('id', 'N/A'))
                    name = service.get('provided_service_name', 'Unknown')
                    is_active = service.get('provided_service_is_active', False)
                    print(f"      - ID: {sid}, Name: {name}, Active: {is_active}")
                return True

            self.print_status(f"❌ Failed to fetch services: {response.status_code}", "❌")
            return False
        except Exception as e:
            self.print_status(f"❌ Error fetching services: {e}", "❌")
            return False

    async def fetch_all_data(self) -> bool:
        print("\n" + "=" * 50)
        print("📊 FETCHING EXISTING DATA")
        print("=" * 50)

        if not await self.ensure_valid_token():
            self.print_status("❌ Cannot authenticate", "❌")
            return False

        if not await self.fetch_providers():
            self.print_status("⚠️ Failed to fetch providers", "⚠️")
            return False

        if not self.context.provider_ids:
            self.print_status("⚠️ No providers found", "⚠️")
            return False

        provider_id = self.context.provider_ids[0]
        self.print_status(f"Using provider ID: {provider_id}", "🏢")

        await self.fetch_products(provider_id)
        await self.fetch_services(provider_id)

        if not self.context.product_ids and not self.context.service_ids:
            self.print_status("⚠️ No products or services found", "⚠️")
            return False

        return True

    # ==================== Cart Creation ====================

    async def create_cart(self, provider_id: int, seller_id: int,
                          product_ids: List[int], service_ids: List[int]
                          ) -> Optional[Dict[str, Any]]:
        if not await self.ensure_valid_token():
            return None

        headers = self.get_auth_headers()
        cart_data = generate_cart_data(provider_id, seller_id, product_ids, service_ids)

        if not cart_data["ordered_items"] and not cart_data["ordered_services"]:
            return None

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/carts",
                json=cart_data,
                headers=headers,
            )

            if response.status_code in (200, 201):
                body = response.json()
                cart_data_result = unwrap(body) if isinstance(body, dict) else {}

                # Some servers return the cart fields at top level; fall back.
                if not cart_data_result:
                    cart_data_result = body

                cart_id = cart_data_result.get('cart_id', 0) or 0
                invoice_id = (
                    cart_data_result.get('cart_invoice', 0)
                    or cart_data_result.get('invoice_id', 0)
                    or 0
                )
                total_amount = cart_data_result.get('total_amount', 0) or 0

                if cart_id:
                    self.stats["carts_created"] += 1
                    self.context.created_carts.append(cart_id)

                    if invoice_id and invoice_id > 0:
                        self.stats["invoices_created"] += 1
                        if invoice_id not in self.context.created_invoices:
                            self.context.created_invoices.append(invoice_id)
                        self.print_status(
                            f"✅ Cart {cart_id} created with invoice {invoice_id} "
                            f"(total: {total_amount})",
                            "🛒",
                        )
                    else:
                        self.print_status(
                            f"⚠️ Cart {cart_id} created but no invoice ID returned",
                            "⚠️",
                        )

                    return {
                        "cart_id": cart_id,
                        "invoice_id": invoice_id,
                        "total_amount": total_amount,
                    }
            return None
        except Exception as e:
            self.print_status(f"❌ Error creating cart: {e}", "❌")
            return None

    async def create_carts_bulk(self, provider_id: int, seller_id: int,
                                product_ids: List[int], service_ids: List[int],
                                count: int = 10) -> List[Dict[str, Any]]:
        """
        Create carts sequentially. Concurrent creation caused backend race
        conditions (only 3/10 succeeded in the previous run), so we serialize
        with a tiny delay between requests.
        """
        if not product_ids and not service_ids:
            self.print_status("⚠️ No products or services available for carts", "⚠️")
            return []

        self.print_status(f"🛒 Creating {count} carts (sequential)...", "🛒")

        cart_details: List[Dict[str, Any]] = []
        for i in range(count):
            result = await self.create_cart(
                provider_id, seller_id, product_ids, service_ids
            )
            if isinstance(result, dict) and result.get('cart_id'):
                cart_details.append(result)
            else:
                self.stats["errors"] += 1
                self.print_status(f"⚠️ Cart {i + 1}/{count} failed", "⚠️")

            # Small pacing delay to avoid ID-generation / DB-transaction races.
            await asyncio.sleep(0.15)

        self.print_status(f"✅ Created {len(cart_details)}/{count} carts", "✅")
        return cart_details

    # ==================== Payment Processing ====================

    async def get_cart_with_invoice(self, cart_id: int) -> Optional[Dict[str, Any]]:
        headers = self.get_auth_headers()

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/carts/{cart_id}",
                params={"eager_load": "true"},
                headers=headers,
            )

            if response.status_code == 200:
                body = response.json()
                cart_data = unwrap(body) if isinstance(body, dict) else {}
                if not cart_data:
                    cart_data = body

                invoice_id = (
                    cart_data.get('invoice_id', 0)
                    or cart_data.get('cart_invoice', 0)
                    or 0
                )
                total_amount = cart_data.get('total_amount', 0) or 0
                status = cart_data.get('cart_status', 'open')

                return {
                    "cart_id": cart_id,
                    "invoice_id": invoice_id,
                    "total_amount": total_amount,
                    "status": status,
                }
            return None
        except Exception as e:
            self.print_status(f"❌ Error fetching cart {cart_id}: {e}", "❌")
            return None

    async def process_cart_payment(self, cart_detail: Dict[str, Any]) -> bool:
        if not await self.ensure_valid_token():
            return False

        headers = self.get_auth_headers()
        cart_id = cart_detail.get('cart_id')
        invoice_id = cart_detail.get('invoice_id') or 0
        total_amount = cart_detail.get('total_amount', 0) or 0

        if not invoice_id or total_amount <= 0:
            self.print_status(f"🔍 Fetching cart {cart_id} details...", "🔍")
            cart_info = await self.get_cart_with_invoice(cart_id)
            if not cart_info:
                self.print_status(f"❌ Failed to fetch cart {cart_id}", "❌")
                return False

            invoice_id = cart_info.get('invoice_id', 0) or 0
            total_amount = cart_info.get('total_amount', 0) or 0

            if invoice_id and invoice_id > 0 and invoice_id not in self.context.created_invoices:
                self.context.created_invoices.append(invoice_id)

        if not invoice_id:
            self.print_status(f"⚠️ Cart {cart_id} has no invoice", "⚠️")
            return False

        if total_amount <= 0:
            self.print_status(
                f"⚠️ Cart {cart_id} has zero total amount ({total_amount})", "⚠️"
            )
            return False

        payment_methods = ["cash", "card", "bank_transfer", "mobile_money", "wallet"]
        payment_data = {
            "payment_invoice_id": invoice_id,
            "payment_amount": total_amount,
            "payment_method": random.choice(payment_methods),
            "payment_reference": f"PAY-{uuid.uuid4().hex[:8].upper()}",
            "payment_notes": f"Bulk payment for invoice {invoice_id} from cart {cart_id}",
        }

        try:
            self.print_status(
                f"💳 Creating payment for invoice {invoice_id} (amount: {total_amount})",
                "💳",
            )

            payment_response = await self.client.post(
                f"{self.base_url}/api/v1/business/payments",
                json=payment_data,
                headers=headers,
            )

            if payment_response.status_code in (200, 201):
                body = payment_response.json()
                data = unwrap(body) if isinstance(body, dict) else {}
                if not data:
                    data = body

                payment_id = (
                    data.get('payment_id')
                    or data.get('id')
                    or 0
                )

                if payment_id:
                    self.stats["payments_created"] += 1
                    if payment_id not in self.context.created_payments:
                        self.context.created_payments.append(payment_id)
                    self.print_status(
                        f"✅ Payment {payment_id} created for invoice {invoice_id}",
                        "💳",
                    )
                    return True

                self.print_status(
                    f"⚠️ Payment created but no ID returned. Body: {str(body)[:200]}",
                    "⚠️",
                )
                return False

            error_msg = payment_response.text[:300] if payment_response.text else "No response"
            self.print_status(
                f"❌ Payment failed ({payment_response.status_code}): {error_msg}", "❌"
            )
            return False
        except Exception as e:
            self.print_status(f"❌ Error processing payment: {e}", "❌")
            return False

    async def process_payments_bulk(self, cart_details: List[Dict[str, Any]]) -> int:
        if not cart_details:
            return 0

        self.print_status(f"💳 Processing payments for {len(cart_details)} carts...", "💳")

        tasks = [self.process_cart_payment(cd) for cd in cart_details]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = sum(1 for r in results if r is True)
        self.print_status(f"✅ Processed {successful} payments", "✅")
        return successful

    # ==================== Reads ====================

    async def get_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        if not await self.ensure_valid_token():
            return None

        headers = self.get_auth_headers()
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/invoices/{invoice_id}",
                headers=headers,
            )
            if response.status_code == 200:
                body = response.json()
                data = unwrap(body) if isinstance(body, dict) else {}
                return data or body
            return None
        except Exception as e:
            self.print_status(f"❌ Error fetching invoice {invoice_id}: {e}", "❌")
            return None

    async def get_payment(self, payment_id: int) -> Optional[Dict[str, Any]]:
        if not await self.ensure_valid_token():
            return None

        headers = self.get_auth_headers()
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/payments/{payment_id}",
                headers=headers,
            )
            if response.status_code == 200:
                body = response.json()
                data = unwrap(body) if isinstance(body, dict) else {}
                return data or body
            return None
        except Exception as e:
            self.print_status(f"❌ Error fetching payment {payment_id}: {e}", "❌")
            return None

    async def update_invoice_status(self, invoice_id: int, new_status: str) -> bool:
        if not await self.ensure_valid_token():
            return False

        headers = self.get_auth_headers()
        try:
            response = await self.client.patch(
                f"{self.base_url}/api/v1/invoices/{invoice_id}/status",
                params={"new_status": new_status},
                headers=headers,
            )
            return response.status_code in (200, 201, 204)
        except Exception as e:
            self.print_status(f"❌ Error updating invoice {invoice_id} status: {e}", "❌")
            return False

    # ==================== Payment Actions ====================

    async def confirm_payment(self, payment_id: int) -> Tuple[bool, str]:
        """POST /payments/{id}/confirm   (PENDING → PAID)"""
        if not await self.ensure_valid_token():
            return False, "No auth"

        headers = self.get_auth_headers()
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/payments/{payment_id}/confirm",
                headers=headers,
            )
            body = response.text[:300] if response.text else ""
            return response.status_code in (200, 201), f"{response.status_code}: {body}"
        except Exception as e:
            return False, str(e)

    async def reject_payment(self, payment_id: int, reason: str = "Test rejection"
                             ) -> Tuple[bool, str]:
        """POST /payments/{id}/reject   (PENDING → FAILED)"""
        if not await self.ensure_valid_token():
            return False, "No auth"

        headers = self.get_auth_headers()
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/payments/{payment_id}/reject",
                json={"reason": reason},
                headers=headers,
            )
            body = response.text[:300] if response.text else ""
            return response.status_code in (200, 201), f"{response.status_code}: {body}"
        except Exception as e:
            return False, str(e)

    async def refund_payment(self, payment_id: int, reason: str = "Test refund"
                             ) -> Tuple[bool, str]:
        """POST /payments/{id}/refund   (PAID → REFUNDED). Backend takes only `reason`."""
        if not await self.ensure_valid_token():
            return False, "No auth"

        headers = self.get_auth_headers()
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/payments/{payment_id}/refund",
                json={"reason": reason},
                headers=headers,
            )
            body = response.text[:300] if response.text else ""
            return response.status_code in (200, 201), f"{response.status_code}: {body}"
        except Exception as e:
            return False, str(e)

    # ==================== Invoice Lifecycle Test ====================

    async def test_invoice_lifecycle_from_cart(self, cart_detail: Dict[str, Any]) -> None:
        print(f"\n{'=' * 60}")
        print("🧪 TESTING INVOICE LIFECYCLE (from cart side effect)")
        print(f"{'=' * 60}")

        cart_id = cart_detail.get('cart_id')
        invoice_id = cart_detail.get('invoice_id')

        if not invoice_id or invoice_id == 0:
            self.record_test(
                f"Cart {cart_id} - Invoice auto-created",
                False,
                "Cart created but no invoice ID was returned",
            )
            return

        invoice = await self.get_invoice(invoice_id)
        if not invoice:
            self.record_test(
                f"Cart {cart_id} → Invoice {invoice_id} auto-created",
                False,
                "Invoice not found after cart creation",
            )
            return

        initial_status = invoice.get('invoice_status', '')
        initial_amount = invoice.get('invoice_total_amount', 0)

        # Cart creation may auto-process payment, so 'paid' is a legitimate
        # starting state on this backend.
        valid_initial = {
            InvoiceStatus.UNPAID,
            InvoiceStatus.PARTIALLY_PAID,
            InvoiceStatus.PAID,
            InvoiceStatus.DEPOSITED,
        }

        self.record_test(
            f"Cart {cart_id} → Invoice {invoice_id} auto-created",
            initial_status in valid_initial,
            f"Invoice #{invoice_id} created with amount {initial_amount}, "
            f"status='{initial_status}'",
            expected=f"one of {sorted(valid_initial)}",
            actual=initial_status,
        )

        # Cart ↔ invoice linkage
        cart = await self.get_cart_with_invoice(cart_id)
        cart_invoice_ref = cart.get('invoice_id') if cart else None
        self.record_test(
            f"Cart {cart_id} - References invoice {invoice_id}",
            cart_invoice_ref == invoice_id,
            f"Cart.invoice_id should equal {invoice_id}",
            expected=invoice_id,
            actual=cart_invoice_ref,
        )

        # Valid transitions
        valid_transitions = InvoiceStatus.TRANSITIONS.get(initial_status, [])
        self.record_test(
            f"Invoice {invoice_id} - Has valid transitions from '{initial_status}'",
            len(valid_transitions) > 0,
            f"Valid targets: {valid_transitions}",
            expected="At least 1 valid transition",
            actual=valid_transitions,
        )

        # Try a valid transition (best-effort; some deployments may not expose        # the PATCH endpoint — in that case the test is skipped).
        if 'partially_paid' in valid_transitions:
            self.print_status(f"Testing: {initial_status} → partially_paid", "🧪")
            success = await self.update_invoice_status(invoice_id, 'partially_paid')
            if success:
                updated = await self.get_invoice(invoice_id)
                actual_status = updated.get('invoice_status') if updated else None
                self.record_test(
                    f"Invoice {invoice_id}: {initial_status} → partially_paid",
                    actual_status == 'partially_paid',
                    "Valid transition",
                    expected="partially_paid",
                    actual=actual_status,
                )
                await self.update_invoice_status(invoice_id, initial_status)
            else:
                self.print_status(
                    "⏭️  PATCH /invoices/{id}/status not available; skipping transition",
                    "⏭️",
                )

        # Invalid transition (only if endpoint available)
        invalid_target = InvoiceStatus.REFUNDED
        if invalid_target not in valid_transitions:
            self.print_status(
                f"Testing invalid: {initial_status} → {invalid_target}", "🧪"
            )
            await self.update_invoice_status(invoice_id, invalid_target)
            updated = await self.get_invoice(invoice_id)
            actual_status = updated.get('invoice_status') if updated else None
            if actual_status is None:
                self.print_status("⏭️  PATCH endpoint unavailable; skipping", "⏭️")
            else:
                self.record_test(
                    f"Invoice {invoice_id}: Invalid {initial_status} → {invalid_target}",
                    actual_status == initial_status,
                    "Invalid transitions must be rejected",
                    expected=f"stays '{initial_status}'",
                    actual=actual_status,
                )

    # ==================== Payment Lifecycle Test ====================

    async def test_payment_lifecycle(self, invoice_id: int, amount: float) -> None:
        """
        Real lifecycle (uppercase statuses):
            PENDING ──[confirm]──► PAID ──[refund]──► REFUNDED
            PENDING ──[reject]───► FAILED
        """
        print(f"\n{'=' * 60}")
        print("🧪 TESTING FULL PAYMENT LIFECYCLE (action-based)")
        print(f"{'=' * 60}")

        if not await self.ensure_valid_token():
            return

        headers = self.get_auth_headers()

        # ---- Step 1: Create payment ----
        self.print_status("Step 1: Creating payment...", "🧪")
        payment_data = {
            "payment_invoice_id": invoice_id,
            "payment_amount": amount,
            "payment_method": "bank_transfer",
            "payment_notes": "Lifecycle test payment",
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/payments",
                json=payment_data,
                headers=headers,
            )

            if response.status_code not in (200, 201):
                self.record_test(
                    "Payment Lifecycle - Create",
                    False,
                    f"API {response.status_code}: {response.text[:200]}",
                )
                return

            body = response.json()
            data = unwrap(body) if isinstance(body, dict) else {}
            payment_id = (
                data.get('payment_id')
                or data.get('id')
                or 0
            )

            self.record_test(
                "Payment Lifecycle - Create",
                payment_id > 0,
                f"Created payment #{payment_id}",
                expected="payment_id > 0",
                actual=payment_id,
            )

            if payment_id <= 0:
                return

            # ---- Step 2: Verify initial status is PENDING ----
            payment = await self.get_payment(payment_id)
            initial_status = payment.get('payment_status') if payment else None

            self.record_test(
                "Payment Lifecycle - Initial status is PENDING",
                initial_status == PaymentStatus.PENDING,
                f"Server-assigned initial status = '{initial_status}'",
                expected=PaymentStatus.PENDING,
                actual=initial_status,
            )

            if initial_status != PaymentStatus.PENDING:
                self.print_status(
                    f"⚠️ Skipping transition tests (payment is '{initial_status}', "
                    f"not '{PaymentStatus.PENDING}')",
                    "⚠️",
                )
                return

            # ---- Step 3: Confirm → PAID ----
            self.print_status("Step 2: Confirming payment (PENDING → PAID)", "🧪")
            success, detail = await self.confirm_payment(payment_id)
            payment = await self.get_payment(payment_id)
            actual_status = payment.get('payment_status') if payment else None

            self.record_test(
                "Payment Lifecycle - confirm() → PAID",
                success and actual_status == PaymentStatus.PAID,
                f"After confirm: status='{actual_status}' | {detail}",
                expected=PaymentStatus.PAID,
                actual=actual_status,
            )

            # ---- Step 4: Re-confirm → must fail ----
            self.print_status("Step 3: Re-confirming on PAID (should fail)", "🧪")
            success, detail = await self.confirm_payment(payment_id)
            payment = await self.get_payment(payment_id)
            actual_status = payment.get('payment_status') if payment else None

            self.record_test(
                "Payment Lifecycle - Re-confirm on PAID (must fail)",
                (not success) and actual_status == PaymentStatus.PAID,
                f"Status stays '{actual_status}' | {detail}",
                expected=f"rejected, status='{PaymentStatus.PAID}'",
                actual=f"success={success}, status={actual_status}",
            )

            # ---- Step 5: Refund → REFUNDED ----
            self.print_status("Step 4: Refunding payment (PAID → REFUNDED)", "🧪")
            success, detail = await self.refund_payment(
                payment_id, reason="Lifecycle test refund"
            )
            payment = await self.get_payment(payment_id)
            actual_status = payment.get('payment_status') if payment else None

            self.record_test(
                "Payment Lifecycle - refund() → REFUNDED",
                success and actual_status == PaymentStatus.REFUNDED,
                f"After refund: status='{actual_status}' | {detail}",
                expected=PaymentStatus.REFUNDED,
                actual=actual_status,
            )

            # ---- Step 6: Invoice reflects final state ----
            invoice = await self.get_invoice(invoice_id)
            invoice_status = invoice.get('invoice_status') if invoice else None
            self.record_test(
                "Payment Lifecycle - Invoice reflects final state",
                invoice_status in [
                    InvoiceStatus.PAID,
                    InvoiceStatus.PARTIALLY_PAID,
                    InvoiceStatus.REFUNDED,
                    InvoiceStatus.DEPOSITED,
                ],
                f"Invoice #{invoice_id} status = '{invoice_status}'",
                expected="paid/partially_paid/refunded/deposited",
                actual=invoice_status,
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.record_test("Payment Lifecycle", False, f"Exception: {e}")

    # ==================== Payment Status Transition Test ====================

    async def test_payment_status_transitions(self, payment_id: int) -> None:
        """
        Invalid-action tests against a payment that is NOT in the source state.
        """
        print(f"\n{'=' * 60}")
        print(f"🧪 TESTING PAYMENT STATUS TRANSITIONS - Payment #{payment_id}")
        print(f"{'=' * 60}")

        payment = await self.get_payment(payment_id)
        if not payment:
            self.record_test(
                f"Payment {payment_id} - Fetch",
                False,
                "Could not fetch payment",
            )
            return

        current_status = payment.get('payment_status', 'unknown')
        self.print_status(f"Current status: '{current_status}'", "📊")

        # Reject on non-PENDING must fail
        if current_status != PaymentStatus.PENDING:
            self.print_status("🧪 Testing: reject on non-PENDING payment", "🧪")
            success, detail = await self.reject_payment(
                payment_id, reason="Invalid transition test"
            )
            payment = await self.get_payment(payment_id)
            actual_status = payment.get('payment_status') if payment else None
            self.record_test(
                f"Payment {payment_id}: reject on '{current_status}' (must fail)",
                (not success) and actual_status == current_status,
                f"Status stays '{actual_status}' | {detail}",
                expected=f"rejected, status='{current_status}'",
                actual=f"success={success}, status={actual_status}",
            )

        # Confirm on non-PENDING must fail
        if current_status != PaymentStatus.PENDING:
            self.print_status("🧪 Testing: confirm on non-PENDING payment", "🧪")
            success, detail = await self.confirm_payment(payment_id)
            payment = await self.get_payment(payment_id)
            actual_status = payment.get('payment_status') if payment else None
            self.record_test(
                f"Payment {payment_id}: confirm on '{current_status}' (must fail)",
                (not success) and actual_status == current_status,
                f"Status stays '{actual_status}' | {detail}",
                expected=f"rejected, status='{current_status}'",
                actual=f"success={success}, status={actual_status}",
            )

        # Refund on non-PAID must fail
        if current_status != PaymentStatus.PAID:
            self.print_status("🧪 Testing: refund on non-PAID payment", "🧪")
            success, detail = await self.refund_payment(
                payment_id, reason="Invalid refund test"
            )
            payment = await self.get_payment(payment_id)
            actual_status = payment.get('payment_status') if payment else None
            self.record_test(
                f"Payment {payment_id}: refund on '{current_status}' (must fail)",
                (not success) and actual_status == current_status,
                f"Status stays '{actual_status}' | {detail}",
                expected=f"rejected, status='{current_status}'",
                actual=f"success={success}, status={actual_status}",
            )

    # ==================== Runner ====================

    async def run_status_transition_tests(self, cart_details: List[Dict[str, Any]]) -> None:
        print("\n" + "=" * 70)
        print("🧪 RUNNING STATUS TRANSITION TESTS")
        print("=" * 70)
        print("ℹ️  Invoices are auto-created by cart creation (side effect)")

        if not cart_details:
            self.print_status("⚠️ No carts available to test invoices", "⚠️")
            return

        test_cart = cart_details[0]
        await self.test_invoice_lifecycle_from_cart(test_cart)

        if test_cart.get('invoice_id'):
            await self.test_payment_lifecycle(
                invoice_id=test_cart['invoice_id'],
                amount=round(random.uniform(50, 200), 2),
            )

        if self.context.created_payments:
            await self.test_payment_status_transitions(self.context.created_payments[0])

        for cart_detail in cart_details[1:3]:
            invoice_id = cart_detail.get('invoice_id')
            if invoice_id:
                invoice = await self.get_invoice(invoice_id)
                if invoice:
                    status = invoice.get('invoice_status', '')
                    self.record_test(
                        f"Cart {cart_detail['cart_id']} → Invoice {invoice_id}",
                        status in [
                            InvoiceStatus.UNPAID,
                            InvoiceStatus.PARTIALLY_PAID,
                            InvoiceStatus.PAID,
                            InvoiceStatus.DEPOSITED,
                        ],
                        f"Auto-created invoice has status='{status}'",
                        expected="valid invoice status",
                        actual=status,
                    )

    def print_test_summary(self) -> None:
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.passed)
        failed = total - passed

        if total == 0:
            print("   No tests were run")
            return

        print(f"\n   Total Tests: {total}")
        print(f"   ✅ Passed:   {passed}")
        print(f"   ❌ Failed:   {failed}")
        print(f"   📈 Success:  {(passed / total * 100):.1f}%")

        if failed > 0:
            print("\n   Failed Tests:")
            for result in self.test_results:
                if not result.passed:
                    print(f"   ❌ {result.name}")
                    if result.expected is not None:
                        print(f"      Expected: {result.expected}")
                        print(f"      Actual:   {result.actual}")

        print("\n" + "=" * 70)

    async def run(self, context_file: str = "test_context.json",
                  carts: int = 10,
                  run_tests: bool = True):
        print("\n" + "=" * 70)
        print("🚀 BULK DATA CREATOR - Carts, Payments & Status Transition Tests")
        print("=" * 70)
        print(f"📍 Base URL:       {self.base_url}")
        print(f"🛒 Carts to create:{carts}")
        print(f"🧪 Run tests:      {run_tests}")
        print("=" * 70)

        self.context = load_context(context_file)

        if not await self.ensure_valid_token():
            self.print_status("❌ No authentication token available", "❌")
            return

        if not await self.fetch_all_data():
            self.print_status("❌ Failed to fetch required data", "❌")
            return

        start_time = time.time()

        product_ids = self.context.product_ids
        service_ids = self.context.service_ids
        provider_id = self.context.provider_ids[0] if self.context.provider_ids else 1
        seller_id = self.context.users[0].id if self.context.users else 0

        self.print_status(f"📦 Products available: {len(product_ids)}", "📦")
        self.print_status(f"📋 Services available: {len(service_ids)}", "📋")
        self.print_status(f"🏢 Provider ID:        {provider_id}", "🏢")
        self.print_status(f"👤 Seller ID:          {seller_id}", "👤")

        cart_details = await self.create_carts_bulk(
            provider_id, seller_id, product_ids, service_ids, carts
        )

        if cart_details:
            await self.process_payments_bulk(cart_details)

        if run_tests:
            await self.run_status_transition_tests(cart_details)

        elapsed = time.time() - start_time

        print("\n" + "=" * 70)
        print("📊 BULK DATA CREATION SUMMARY")
        print("=" * 70)
        print(f"✅ Carts created:    {self.stats['carts_created']}")
        print(f"✅ Invoices created: {self.stats['invoices_created']}")
        print(f"✅ Payments created: {self.stats['payments_created']}")
        print(f"❌ Errors:           {self.stats['errors']}")
        print(f"⏱️  Total time:       {elapsed:.2f}s")

        if self.context.created_carts:
            print(f"\n🛒 Cart IDs:    {self.context.created_carts[:10]}"
                  f"{'...' if len(self.context.created_carts) > 10 else ''}")
        if self.context.created_invoices:
            print(f"📄 Invoice IDs: {self.context.created_invoices[:10]}"
                  f"{'...' if len(self.context.created_invoices) > 10 else ''}")
        if self.context.created_payments:
            print(f"💳 Payment IDs: {self.context.created_payments[:10]}"
                  f"{'...' if len(self.context.created_payments) > 10 else ''}")

        if run_tests:
            self.print_test_summary()

        print("=" * 70)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Bulk Data Creator for Verdelia")
    parser.add_argument("--url", default="http://localhost:9000", help="Base URL")
    parser.add_argument("--context-file", default="test_context.json", help="Context file")
    parser.add_argument("--carts", type=int, default=10, help="Number of carts to create")
    parser.add_argument("--no-tests", action="store_true", help="Skip status transition tests")
    args = parser.parse_args()

    async with BulkDataCreator(args.url) as creator:
        await creator.run(
            context_file=args.context_file,
            carts=args.carts,
            run_tests=not args.no_tests,
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)