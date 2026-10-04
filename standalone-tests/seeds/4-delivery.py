#!/usr/bin/env python3
"""
Delivery Router Test Runner — business ops with Delivery_API body.

Exercises the delivery router:

  Reads:
    GET  /delivery
    GET  /delivery/{id}
    GET  /delivery/{id}/next-states

  Ops (POST with optional Delivery_API body):
    POST /delivery/{id}/accept
    POST /delivery/{id}/confirm
    POST /delivery/{id}/ship
    POST /delivery/{id}/in-transit
    POST /delivery/{id}/out-for-delivery
    POST /delivery/{id}/deliver
    POST /delivery/{id}/cancel
    POST /delivery/{id}/fail
    POST /delivery/{id}/return
    POST /delivery/{id}/refund
    POST /delivery/{id}/tracking-pings
    POST /delivery/{id}/reroute
    POST /delivery/{id}/archive

Bodies are built from Delivery_API. Real fields patch the delivery;
signal fields (delivery_confirmed, proof_captured, ...) flow into the
policy. The runner sets the signals it wants to assert; the server
enforces the graph.

Outcomes:
  OK      → 2xx, transition accepted
  DENIED  → 409, policy said no (expected for illegal actions)
  FAILED  → anything else (5xx, transport, unexpected 4xx)

Run:
    python test_delivery_ops.py --provider 1 --limit 10 --probes
"""

import asyncio
import httpx
import json
import sys
import random
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import argparse


BASE = "/api/v1/business/delivery"
ADDRESSES = "/api/v1/addresses"


# ============================================================================
# Happy path
# ============================================================================
#
# Each step: (action, from_state, to_state, body_fields, signals)
# The runner only performs an action if the delivery's current status
# matches `from_state`. Otherwise the step is skipped for that delivery.

HAPPY_PATH: List[Tuple[str, str, str, Dict[str, Any], Dict[str, Any]]] = [
    # accept — optionally declare a package count at acceptance
    (
        "accept",
        "pending",
        "processing",
        {
            "delivery_package_count": 1,
        },
        {},
    ),
    # confirm — declare the real packing details here
    (
        "confirm",
        "processing",
        "confirmed",
        {
            "delivery_package_count": 3,
            "delivery_total_weight": 12.5,
            "delivery_cargo_dimensions": "30x20x15",
            "delivery_goods_description": "Test package",
        },
        {},
    ),
    # ship — assert the carrier accepted
    (
        "ship",
        "confirmed",
        "shipped",
        {
            "delivery_merchant_name": "ACME Logistics",
        },
        {
            "delivery_confirmed": True,
        },
    ),
    # in transit — assert the carrier ack
    (
        "in-transit",
        "shipped",
        "in_transit",
        {},
        {
            "in_transit_acknowledged": True,
        },
    ),
    # out for delivery — no signal needed
    (
        "out-for-delivery",
        "in_transit",
        "out_for_delivery",
        {},
        {},
    ),
    # delivered — assert proof captured
    (
        "deliver",
        "out_for_delivery",
        "delivered",
        {},
        {
            "proof_captured": True,
        },
    ),
]


# Deliberately-illegal probes. Each: (action, from_state, note)
DENIAL_PROBES = [
    ("confirm", "pending",
     "cannot confirm before accepting"),
    ("ship", "pending",
     "cannot ship before confirming"),
    ("deliver", "pending",
     "cannot deliver before out for delivery"),
    ("deliver", "confirmed",
     "cannot deliver before out for delivery"),
    ("ship", "processing",
     "cannot ship before confirming"),
]


TERMINAL_STATUSES = {"delivered", "cancelled", "returned", "refunded"}


# ============================================================================
# Location helper
# ============================================================================

class LocationGenerator:
    CITIES = [
        "Algiers", "Oran", "Constantine", "Annaba", "Blida",
        "Setif", "Tizi Ouzou", "Bejaia", "Batna", "Sidi Bel Abbes",
    ]
    STREETS = [
        "Main St", "Didouche Mourad", "1er Novembre",
        "Larbi Ben Mhidi", "Krim Belkacem", "Independance",
    ]
    COUNTRIES = ["DZ", "FR", "US", "CA", "DE", "GB"]

    @classmethod
    def _coords(cls, city: str) -> Tuple[float, float]:
        table = {
            "Algiers": (36.7538, 3.0588),
            "Oran": (35.6969, -0.6331),
            "Constantine": (36.3650, 6.6147),
            "Annaba": (36.9020, 7.7557),
            "Blida": (36.4700, 2.8277),
            "Setif": (36.1911, 5.4137),
            "Tizi Ouzou": (36.7111, 4.0458),
            "Bejaia": (36.7558, 5.0843),
            "Batna": (35.5550, 6.1741),
            "Sidi Bel Abbes": (35.1937, -0.6322),
        }
        return table.get(city, (36.7538, 3.0588))

    @classmethod
    def address(cls, name: Optional[str] = None) -> Dict[str, Any]:
        city = random.choice(cls.CITIES)
        lat, lon = cls._coords(city)
        lat += random.uniform(-0.02, 0.02)
        lon += random.uniform(-0.02, 0.02)
        street = f"{random.randint(1, 999)} {random.choice(cls.STREETS)}"
        return {
            "address_street": street[:200],
            "address_city": city,
            "address_postal_code": f"{random.randint(1000, 9999)}",
            "address_country": random.choice(cls.COUNTRIES),
            "location_latitude": round(lat, 6),
            "location_longitude": round(lon, 6),
            "location_name": name or random.choice(
                ["Home", "Office", "Clinic", "Shop"]
            ),
        }


# ============================================================================
# Outcomes
# ============================================================================

class Outcome:
    OK = "OK"
    DENIED = "DENIED"
    FAILED = "FAILED"


class CallRecord:
    __slots__ = (
        "endpoint", "method", "action", "delivery_id",
        "outcome", "status_code", "reason", "elapsed_ms",
    )

    def __init__(
        self,
        endpoint: str,
        method: str,
        action: Optional[str],
        delivery_id: Optional[int],
        outcome: str,
        status_code: int,
        reason: str = "",
        elapsed_ms: float = 0.0,
    ):
        self.endpoint = endpoint
        self.method = method
        self.action = action
        self.delivery_id = delivery_id
        self.outcome = outcome
        self.status_code = status_code
        self.reason = reason
        self.elapsed_ms = elapsed_ms


# ============================================================================
# Runner
# ============================================================================

class DeliveryOpsTestRunner:
    def __init__(self, base_url: str, context_file: str, provider_id: int):
        self.base_url = base_url
        self.context_file = context_file
        self.provider_id = provider_id
        self.client: Optional[httpx.AsyncClient] = None
        self.auth_token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.context_users: List[Dict[str, Any]] = []
        self.calls: List[CallRecord] = []

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0, verify=False, follow_redirects=False
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    # ── Logging ─────────────────────────────────────────────────────

    def log(self, msg: str, emoji: str = "ℹ️"):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {emoji} {msg}")

    # ── Auth ────────────────────────────────────────────────────────

    def headers(self) -> Dict[str, str]:
        return (
            {"Authorization": f"Bearer {self.auth_token}"}
            if self.auth_token
            else {}
        )

    def load_context(self) -> bool:
        p = Path(self.context_file)
        if not p.exists():
            self.log(f"Context file {p} not found", "❌")
            return False
        try:
            with open(p) as f:
                data = json.load(f)
            self.context_users = data.get("users", [])
            self.log(
                f"Loaded {len(self.context_users)} users from context", "📂"
            )
            return bool(self.context_users)
        except Exception as e:
            self.log(f"Error loading context: {e}", "❌")
            return False

    async def login(self, user_index: int = 0) -> bool:
        if user_index >= len(self.context_users):
            self.log(f"User index {user_index} out of range", "❌")
            return False
        user = self.context_users[user_index]
        username = user.get("username")
        password = user.get("password")
        self.log(f"Logging in as '{username}'", "🔐")

        try:
            r = await self.client.post(
                f"{self.base_url}/api/v1/authentication/token",
                json={
                    "app_user_name": username,
                    "app_user_password": password,
                },
            )
        except Exception as e:
            self.log(f"Login network error: {e}", "❌")
            return False

        if r.status_code != 200:
            self.log(
                f"Login failed: {r.status_code} {r.text[:200]}", "❌"
            )
            return False

        self.auth_token = r.json().get("access_token")
        self.user_id = user.get("id")
        self.log(f"Login ok as {username} (id={self.user_id})", "✅")
        return bool(self.auth_token)

    # ── Classification ──────────────────────────────────────────────

    def _classify(self, response: httpx.Response) -> Tuple[str, str]:
        if 200 <= response.status_code < 300:
            return Outcome.OK, ""

        reason = self._extract_reason(response)

        if response.status_code == 409:
            return Outcome.DENIED, reason or "transition not allowed"

        # Some backends still return 400 for policy denials — classify
        # those as DENIED too, when the reason names a state problem.
        if response.status_code == 400:
            lowered = (reason or "").lower()
            if (
                "not permitted" in lowered
                or "transition" in lowered
                or "cannot" in lowered
            ):
                return Outcome.DENIED, reason

        return Outcome.FAILED, reason or f"http {response.status_code}"

    @staticmethod
    def _extract_reason(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except Exception:
            return response.text[:200]

        detail = payload.get("detail")
        if isinstance(detail, dict):
            return (
                detail.get("reason")
                or detail.get("message")
                or json.dumps(detail)
            )
        if isinstance(detail, str):
            return detail
        return (
            payload.get("message")
            or payload.get("error")
            or response.text[:200]
        )

    # ── HTTP plumbing ───────────────────────────────────────────────

    async def call(
        self,
        method: str,
        path: str,
        *,
        action: Optional[str] = None,
        delivery_id: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[Any], str, str]:
        start = datetime.now()
        try:
            r = await self.client.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=body,
                headers=self.headers(),
            )
        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds() * 1000
            self.calls.append(CallRecord(
                path, method, action, delivery_id,
                Outcome.FAILED, 0, str(e), elapsed,
            ))
            return None, Outcome.FAILED, str(e)

        elapsed = (datetime.now() - start).total_seconds() * 1000
        outcome, reason = self._classify(r)
        self.calls.append(CallRecord(
            path, method, action, delivery_id,
            outcome, r.status_code, reason, elapsed,
        ))

        parsed: Optional[Any] = None
        if outcome == Outcome.OK:
            try:
                parsed = r.json()
            except Exception:
                parsed = None
        return parsed, outcome, reason

    # ── Reads ───────────────────────────────────────────────────────

    async def list_deliveries(
        self, limit: int = 20, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "provider_id": self.provider_id,
            "offset": 0,
            "limit": limit,
        }
        if status:
            params["status"] = status

        body, outcome, reason = await self.call(
            "GET", BASE,
            action="list",
            params=params,
        )
        self._report("GET /delivery", outcome, reason)
        if outcome != Outcome.OK or not body:
            return []
        if isinstance(body, list):
            return body
        if isinstance(body, dict):
            return body.get("data") or body.get("items") or []
        return []

    async def get_one(self, delivery_id: int) -> Optional[Dict[str, Any]]:
        body, outcome, reason = await self.call(
            "GET", f"{BASE}/{delivery_id}",
            action="get",
            delivery_id=delivery_id,
        )
        self._report(f"GET /delivery/{delivery_id}", outcome, reason)
        return body if outcome == Outcome.OK else None

    async def next_states(self, delivery_id: int) -> Optional[List[str]]:
        body, outcome, reason = await self.call(
            "GET", f"{BASE}/{delivery_id}/next-states",
            action="next-states",
            delivery_id=delivery_id,
        )
        self._report(
            f"GET /delivery/{delivery_id}/next-states", outcome, reason
        )
        if outcome == Outcome.OK and isinstance(body, dict):
            return list(body.get("next_states") or [])
        return None

    # ── Action ──────────────────────────────────────────────────────

    async def do_action(
        self,
        delivery_id: int,
        action: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str, Optional[Any]]:
        parsed, outcome, reason = await self.call(
            "POST", f"{BASE}/{delivery_id}/{action}",
            action=action,
            delivery_id=delivery_id,
            params=params,
            body=body,
        )
        self._report(
            f"POST /delivery/{delivery_id}/{action}", outcome, reason
        )
        return outcome, reason, parsed

    # ── Body builders ───────────────────────────────────────────────

    @staticmethod
    def _build_body(
        patch_fields: Dict[str, Any],
        signals: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Merge real patch fields and signal fields into one Delivery_API
        body. Returns None when there is nothing to send.
        """
        merged: Dict[str, Any] = {}
        merged.update(patch_fields or {})
        merged.update(signals or {})
        return merged or None

    # ── Address helper ──────────────────────────────────────────────

    async def create_address(
        self, label: str = "TrackingPoint"
    ) -> Optional[int]:
        addr = LocationGenerator.address(label)
        body, outcome, reason = await self.call(
            "POST", ADDRESSES,
            action="create-address",
            body=addr,
        )
        if outcome != Outcome.OK or not body:
            self._report("POST /addresses", outcome, reason)
            return None
        aid = (
            body.get("id_address")
            or body.get("address_id")
            or (body.get("data") or {}).get("id_address")
        )
        return int(aid) if aid else None

    # ── Scenarios ───────────────────────────────────────────────────

    async def test_reads(self) -> None:
        self.log("\n📖 READ endpoints", "📖")
        print("=" * 70)
        await self.list_deliveries(limit=5)

    async def test_next_states(self, delivery: Dict[str, Any]) -> None:
        delivery_id = delivery.get("id_delivery")
        states = await self.next_states(delivery_id)
        current = (delivery.get("delivery_status") or "").lower()
        if states is not None:
            self.log(
                f"Delivery {delivery_id} is '{current}', next: {states}",
                "🧭",
            )

    async def test_denial_probes(self, delivery: Dict[str, Any]) -> None:
        delivery_id = delivery.get("id_delivery")
        current = (delivery.get("delivery_status") or "").lower()

        applicable = [
            (a, note) for a, frm, note in DENIAL_PROBES if frm == current
        ]
        if not applicable:
            return

        self.log(
            f"🧪 Probing illegal actions on {delivery_id} "
            f"(current: {current})",
            "🧪",
        )
        for action, note in applicable:
            outcome, reason, _ = await self.do_action(delivery_id, action)
            if outcome == Outcome.DENIED:
                self.log(f"  ✅ Correctly denied: {note}", "✅")
            elif outcome == Outcome.OK:
                self.log(
                    f"  ⚠️  Policy ACCEPTED illegal '{action}': {note}",
                    "⚠️",
                )

    async def walk_happy_path(self, delivery: Dict[str, Any]) -> bool:
        delivery_id = delivery.get("id_delivery")
        current = (delivery.get("delivery_status") or "pending").lower()

        if current in TERMINAL_STATUSES:
            self.log(
                f"Skipping {delivery_id}: terminal '{current}'", "⏭️"
            )
            return False

        self.log(
            f"\n🔧 Walking delivery {delivery_id} "
            f"from '{current}' to 'delivered'",
            "🔧",
        )

        start_index = 0
        for i, (_a, before, _after, _p, _s) in enumerate(HAPPY_PATH):
            if before == current:
                start_index = i
                break
        else:
            self.log(
                f"  Delivery {delivery_id} is '{current}', not on the "
                f"happy path",
                "🛑",
            )
            return False

        for action, _before, expected, patch_fields, signals in \
                HAPPY_PATH[start_index:]:
            body = self._build_body(patch_fields, signals)
            outcome, reason, _ = await self.do_action(
                delivery_id, action, body=body
            )
            if outcome != Outcome.OK:
                self.log(
                    f"  Stopped at '{action}': {outcome} — {reason}",
                    "🛑",
                )
                return False

            refreshed = await self.get_one(delivery_id)
            if refreshed:
                got = (refreshed.get("delivery_status") or "").lower()
                if got != expected:
                    self.log(
                        f"  ⚠️  After '{action}', state is '{got}', "
                        f"expected '{expected}'",
                        "⚠️",
                    )
                    return False

            if expected != "delivered":
                addr_id = await self.create_address(f"tracking_{action}")
                if addr_id:
                    await self.do_action(
                        delivery_id, "tracking-pings",
                        params={"current_address_id": addr_id},
                    )

            await asyncio.sleep(0.15)

        return True

    async def test_cancel(self, delivery: Dict[str, Any]) -> bool:
        delivery_id = delivery.get("id_delivery")
        current = (delivery.get("delivery_status") or "").lower()

        if current in TERMINAL_STATUSES:
            return False

        self.log(
            f"\n🚫 Cancelling delivery {delivery_id} (from '{current}')",
            "🚫",
        )
        outcome, reason, _ = await self.do_action(
            delivery_id, "cancel",
            params={"reason": "test cancellation"},
        )
        return outcome == Outcome.OK

    async def test_reroute(self, delivery: Dict[str, Any]) -> bool:
        delivery_id = delivery.get("id_delivery")
        addr_id = await self.create_address("NewDestination")
        if not addr_id:
            return False
        outcome, reason, _ = await self.do_action(
            delivery_id, "reroute",
            params={"address_id": addr_id},
        )
        return outcome == Outcome.OK

    async def test_fail(self, delivery: Dict[str, Any]) -> bool:
        delivery_id = delivery.get("id_delivery")
        current = (delivery.get("delivery_status") or "").lower()

        if current not in {"processing", "in_transit", "out_for_delivery"}:
            return False

        self.log(f"\n💥 Reporting failure on {delivery_id}", "💥")
        outcome, reason, _ = await self.do_action(
            delivery_id, "fail",
            body={"failure_reported": True},
            params={"reason": "test failure"},
        )
        return outcome == Outcome.OK

    async def test_archive(self, delivery: Dict[str, Any]) -> bool:
        delivery_id = delivery.get("id_delivery")
        current = (delivery.get("delivery_status") or "").lower()

        self.log(
            f"\n🗄️  Archiving {delivery_id} (current: '{current}')", "🗄️"
        )
        outcome, reason, _ = await self.do_action(
            delivery_id, "archive"
        )
        return outcome == Outcome.OK

    # ── Reporting ───────────────────────────────────────────────────

    def _report(self, label: str, outcome: str, reason: str) -> None:
        emoji = {
            Outcome.OK: "✅",
            Outcome.DENIED: "🚫",
            Outcome.FAILED: "❌",
        }[outcome]
        suffix = f" — {reason}" if reason else ""
        print(f"   {emoji} {label}: {outcome}{suffix}")

    def print_summary(self) -> None:
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)

        by_outcome = {Outcome.OK: 0, Outcome.DENIED: 0, Outcome.FAILED: 0}
        by_action: Dict[str, Dict[str, int]] = {}

        for c in self.calls:
            by_outcome[c.outcome] = by_outcome.get(c.outcome, 0) + 1
            label = f"{c.method} {c.action or c.endpoint}"
            bucket = by_action.setdefault(
                label,
                {Outcome.OK: 0, Outcome.DENIED: 0, Outcome.FAILED: 0},
            )
            bucket[c.outcome] += 1

        print(f"   ✅ OK:     {by_outcome[Outcome.OK]}")
        print(f"   🚫 DENIED: {by_outcome[Outcome.DENIED]}")
        print(f"   ❌ FAILED: {by_outcome[Outcome.FAILED]}")

        print("\n   Per-action breakdown:")
        for label, counts in sorted(by_action.items()):
            print(
                f"     {label:<48} "
                f"OK={counts[Outcome.OK]:<3} "
                f"DENIED={counts[Outcome.DENIED]:<3} "
                f"FAILED={counts[Outcome.FAILED]}"
            )

        failures = [c for c in self.calls if c.outcome == Outcome.FAILED]
        if failures:
            print("\n   Failures:")
            for c in failures[:10]:
                print(
                    f"     {c.method} {c.endpoint} "
                    f"→ {c.status_code} {c.reason[:80]}"
                )
            if len(failures) > 10:
                print(f"     ... and {len(failures) - 10} more")

        denied = [c for c in self.calls if c.outcome == Outcome.DENIED]
        if denied:
            print("\n   Denials (policy rejections):")
            for c in denied[:10]:
                print(
                    f"     {c.action or c.endpoint} on "
                    f"delivery {c.delivery_id} → {c.reason[:80]}"
                )
            if len(denied) > 10:
                print(f"     ... and {len(denied) - 10} more")

        print("=" * 70)

    # ── Main run ────────────────────────────────────────────────────

    async def run(
        self,
        user_index: int,
        limit: int,
        do_probes: bool,
        do_cancel: bool,
        do_reroute: bool,
        do_fail: bool,
        do_archive: bool,
    ) -> None:
        print("\n" + "=" * 70)
        print("🚚 DELIVERY OPS TEST RUNNER")
        print("=" * 70)
        print(f"📍 Base URL:        {self.base_url}")
        print(f"🏢 Provider:        {self.provider_id}")
        print(f"📊 Limit:           {limit}")
        print(f"🧪 Denial probes:   {do_probes}")
        print(f"🚫 Cancel test:     {do_cancel}")
        print(f"📍 Reroute test:    {do_reroute}")
        print(f"💥 Fail test:       {do_fail}")
        print(f"🗄️  Archive test:    {do_archive}")
        print("=" * 70)

        if not self.load_context():
            return
        if not await self.login(user_index):
            return

        await self.test_reads()

        deliveries = await self.list_deliveries(limit=limit)
        if not deliveries:
            self.log("No deliveries to test against", "⚠️")
            self.print_summary()
            return

        self.log(f"Testing against {len(deliveries)} deliveries", "📦")
        print("=" * 70)

        completed: List[Dict[str, Any]] = []

        for d in deliveries[:limit]:
            delivery_id = d.get("id_delivery")
            current = (d.get("delivery_status") or "").lower()

            if current in TERMINAL_STATUSES:
                self.log(
                    f"Skipping {delivery_id} — terminal '{current}'", "⏭️"
                )
                if do_archive:
                    await self.test_archive(d)
                continue

            await self.test_next_states(d)

            if do_probes:
                await self.test_denial_probes(d)

            # decide flow: cancel, fail, or walk happy path
            cancelled = False
            failed = False

            if do_cancel and random.random() < 0.2:
                cancelled = await self.test_cancel(d)
            elif do_fail and current in {"in_transit", "out_for_delivery"} \
                    and random.random() < 0.15:
                # advance to a failable state first, then fail
                await self.walk_happy_path(d)
                refreshed = await self.get_one(delivery_id)
                if refreshed and (refreshed.get("delivery_status") or "") \
                        in {"in_transit", "out_for_delivery"}:
                    failed = await self.test_fail(refreshed)
            else:
                reached = await self.walk_happy_path(d)
                if reached:
                    refreshed = await self.get_one(delivery_id)
                    if refreshed:
                        completed.append(refreshed)
                continue

            refreshed = await self.get_one(delivery_id)
            if refreshed:
                completed.append(refreshed)

            if do_reroute and random.random() < 0.15:
                await self.test_reroute(d)

            await asyncio.sleep(0.2)

        if do_archive and completed:
            self.log("\n🗄️  ARCHIVE terminal deliveries", "🗄️")
            print("=" * 70)
            for d in completed[:5]:
                if (
                    d.get("delivery_status") or ""
                ).lower() in TERMINAL_STATUSES:
                    await self.test_archive(d)

        self.print_summary()


# ============================================================================
# Main
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Delivery router test runner — business ops"
    )
    parser.add_argument("--url", default="http://localhost:9000")
    parser.add_argument("--provider", type=int, default=1)
    parser.add_argument("--user-index", type=int, default=0)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--context-file", default="test_context.json")
    parser.add_argument("--probes", action="store_true",
                        help="Probe illegal actions and expect 409")
    parser.add_argument("--cancel", action="store_true",
                        help="Randomly cancel some deliveries")
    parser.add_argument("--reroute", action="store_true",
                        help="Randomly reroute some deliveries")
    parser.add_argument("--fail", action="store_true",
                        help="Randomly fail some in-flight deliveries")
    parser.add_argument("--archive", action="store_true",
                        help="Archive terminal deliveries")

    args = parser.parse_args()

    async with DeliveryOpsTestRunner(
        base_url=args.url,
        context_file=args.context_file,
        provider_id=args.provider,
    ) as runner:
        await runner.run(
            user_index=args.user_index,
            limit=args.limit,
            do_probes=args.probes,
            do_cancel=args.cancel,
            do_reroute=args.reroute,
            do_fail=args.fail,
            do_archive=args.archive,
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)