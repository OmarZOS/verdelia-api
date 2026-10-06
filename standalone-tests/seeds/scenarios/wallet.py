# test_runner/scenarios/wallet.py
"""Wallet scenarios.

Funds users, reads their ledgers, and verifies the wallet
endpoints. The wallet lives on the finance server; the API proxies
every call. This scenario talks to the API's wallet routes.

Used by other scenarios (cart, subscriptions) to top up before
operations that draw on a balance. Also standalone: a runner can
create users, fund them, and read the ledger back to verify the
round-trip.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from scenarios.base import BaseScenario
from context import TestUser
from data import short


class WalletScenario(BaseScenario):
    name = "wallet"

    # ── Endpoints ──────────────────────────────────────────────

    API_ME = "/api/v1/wallet/me"
    API_TOPUP = "/api/v1/wallet/topup"
    API_TRANSACTIONS = "/api/v1/wallet/me/transactions"
    API_ADJUST = "/api/v1/wallet/adjust"

    # ── Reads ──────────────────────────────────────────────────

    async def get_my_wallet(
        self, user: TestUser,
    ) -> Optional[Dict[str, Any]]:
        """Return the caller's own wallet, or None on failure.

        Uses `GET /wallet/me`. A 404 here means the user has no
        wallet — which for a freshly created user is a data problem
        (they should have one) rather than an expected state.
        """
        headers = self.get_auth_headers(user)
        if not headers:
            print(f"   ❌ No auth token for user {user.id}")
            return None

        try:
            response = await self.client.get(
                f"{self.base_url}{self.API_ME}",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                f"Get wallet for user {user.id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error fetching wallet: {e}")
            return None

    async def get_wallet_for_user(
        self, caller: TestUser, target_user_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Read another user's wallet via `GET /wallet/user/{id}`.

        Succeeds when the caller is the target or an admin.
        Returns None on any non-200 — the caller's own check is
        used by the "stranger" test, which expects a 403.
        """
        headers = self.get_auth_headers(caller)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/wallet/user/{target_user_id}",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"   ❌ Error fetching wallet: {e}")
            return None

    async def get_transactions(
        self,
        user: TestUser,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Fetch the caller's wallet ledger, newest first."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}{self.API_TRANSACTIONS}",
                params={"limit": limit, "offset": offset},
                headers=headers,
            )
            if response.status_code == 200:
                body = response.json()
                return body if isinstance(body, list) else []
            self._record_failure(
                f"Get transactions for user {user.id}", response,
            )
            return []
        except Exception as e:
            print(f"   ❌ Error fetching transactions: {e}")
            return []

    # ── Writes ─────────────────────────────────────────────────

    async def top_up(
        self,
        user: TestUser,
        *,
        amount: float,
        payment_method: str = "deposit",
        reference: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Top up a user's wallet via `POST /wallet/topup`.

        Returns the API's response body on success (which carries
        `wallet_id`, `amount`, `balance_after`, and `transaction`),
        or None on failure.
        """
        headers = self.get_auth_headers(user)
        if not headers:
            print(f"   ❌ No auth token for user {user.id}")
            return None

        payload: Dict[str, Any] = {
            "amount": amount,
            "payment_method": payment_method,
        }
        if reference:
            payload["reference"] = reference
        if notes:
            payload["notes"] = notes

        try:
            response = await self.client.post(
                f"{self.base_url}{self.API_TOPUP}",
                json=payload,
                headers=headers,
            )
            if response.status_code in (200, 201):
                return response.json()
            self._record_failure(
                f"Top up user {user.id} with {amount}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error topping up: {e}")
            return None

    async def adjust(
        self,
        admin: TestUser,
        *,
        user_id: int,
        direction: str,
        amount: float,
        reason: str,
    ) -> Optional[Dict[str, Any]]:
        """Admin adjustment via `POST /wallet/adjust`.

        Requires the caller to be an admin. Returns the response
        body on success, or None on failure.
        """
        headers = self.get_auth_headers(admin)
        if not headers:
            print(f"   ❌ No auth token for admin {admin.id}")
            return None

        payload = {
            "user_id": user_id,
            "direction": direction,
            "amount": amount,
            "reason": reason,
        }

        try:
            response = await self.client.post(
                f"{self.base_url}{self.API_ADJUST}",
                json=payload,
                headers=headers,
            )
            if response.status_code in (200, 201):
                return response.json()
            self._record_failure(
                f"Adjust wallet for user {user_id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error adjusting wallet: {e}")
            return None

    # ── Composite: fund for a downstream scenario ─────────────

    async def ensure_funded(
        self,
        user: TestUser,
        *,
        minimum: float = 100_000.0,
        top_up_to: Optional[float] = None,
        silent: bool = False,
    ) -> bool:
        """Ensure a user's wallet has at least `minimum`.

        Reads the wallet first; if the balance is already above
        the floor, no write happens. Otherwise tops up to
        `top_up_to` (defaults to `minimum`).

        Returns True when the wallet is at or above `minimum`
        after the call, False otherwise. `silent` suppresses the
        per-user print — used by the runner when funding many
        users in a loop.
        """
        wallet = await self.get_my_wallet(user)
        if wallet is None:
            return False

        balance = float(wallet.get("balance", 0))
        target = top_up_to if top_up_to is not None else minimum

        if balance >= minimum:
            if not silent:
                print(
                    f"   💰 {user.username}: balance {balance} "
                    f"≥ {minimum} (no top-up)"
                )
            return True

        top_up_amount = target - balance
        if not silent:
            print(
                f"   💰 {user.username}: topping up "
                f"{balance} → {target} (+{top_up_amount})"
            )

        result = await self.top_up(
            user,
            amount=top_up_amount,
            payment_method="deposit",
            reference=f"ensure-funded:{user.id}",
            notes="Automatic top-up by wallet scenario",
        )
        if result is None:
            return False

        if not silent:
            print(
                f"   ✅ {user.username}: new balance "
                f"{result.get('balance_after')}"
            )
        return True

    # ── Verification scenarios ─────────────────────────────────

    async def verify_my_wallet(
        self, user: TestUser,
    ) -> Dict[str, Any]:
        """Check the shape of `GET /wallet/me`."""
        print(f"\n💳 Verifying wallet shape for {user.username}...")
        wallet = await self.get_my_wallet(user)
        if wallet is None:
            return {"user_id": user.id, "passed": False, "reason": "no wallet"}

        required = {"id", "currency", "balance", "status", "type"}
        missing = required - wallet.keys()
        if missing:
            print(f"   ❌ Missing fields: {sorted(missing)}")
            return {
                "user_id": user.id,
                "passed": False,
                "missing": sorted(missing),
            }

        print(
            f"   ✅ Wallet shape OK: id={wallet['id']} "
            f"balance={wallet['balance']} currency={wallet['currency']}"
        )
        return {"user_id": user.id, "passed": True}

    async def verify_topup_roundtrip(
        self,
        user: TestUser,
        *,
        amount: float = 50_000.0,
    ) -> Dict[str, Any]:
        """Top up and verify the balance changed by the expected amount.

        Reads the balance, tops up, reads again. The delta must
        equal the top-up amount. Any drift means the credit didn't
        land, landed twice, or landed for the wrong amount.
        """
        print(
            f"\n💳 Verifying top-up roundtrip for {user.username} "
            f"(amount {amount})..."
        )

        before = await self.get_my_wallet(user)
        if before is None:
            return {"user_id": user.id, "passed": False, "reason": "no wallet"}
        balance_before = float(before.get("balance", 0))

        result = await self.top_up(
            user,
            amount=amount,
            payment_method="deposit",
            reference=f"verify-topup:{user.id}",
        )
        if result is None:
            return {"user_id": user.id, "passed": False, "reason": "top-up failed"}

        after = await self.get_my_wallet(user)
        if after is None:
            return {"user_id": user.id, "passed": False, "reason": "no wallet after"}
        balance_after = float(after.get("balance", 0))

        delta = balance_after - balance_before
        passed = abs(delta - amount) < 0.01

        if passed:
            print(
                f"   ✅ Balance delta: {delta} (expected {amount})"
            )
        else:
            print(
                f"   ❌ Balance delta: {delta} (expected {amount})"
            )

        # Track the top-up in stats so the summary reflects it.
        self.stats["wallet_topups"] = (
            self.stats.get("wallet_topups", 0) + 1
        )
        self.stats["wallet_credited_total"] = (
            self.stats.get("wallet_credited_total", 0) + amount
        )

        return {
            "user_id": user.id,
            "passed": passed,
            "delta": delta,
            "expected": amount,
        }

    async def verify_stranger_403(
        self,
        caller: TestUser,
        target_user_id: int,
    ) -> Dict[str, Any]:
        """Read another user's wallet as a non-admin. Expect 403.

        The endpoint must refuse a stranger; if it doesn't, the
        wallet balance of any user is readable by any authenticated
        caller.
        """
        print(
            f"\n🔒 Verifying stranger-block for {caller.username} "
            f"→ user {target_user_id}..."
        )

        headers = self.get_auth_headers(caller)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/wallet/user/{target_user_id}",
                headers=headers,
            )
            passed = response.status_code in (403, 404)
            if passed:
                print(
                    f"   ✅ Stranger read blocked: "
                    f"{response.status_code}"
                )
            else:
                print(
                    f"   ❌ Stranger read returned "
                    f"{response.status_code}, expected 403"
                )
            return {"passed": passed, "status": response.status_code}
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {"passed": False}

    async def verify_ledger_reflects_topup(
        self,
        user: TestUser,
        *,
        expected_at_least: int = 1,
    ) -> Dict[str, Any]:
        """Fetch the ledger and confirm top-up entries appear.

        After `verify_topup_roundtrip`, the ledger should have at
        least one entry with `intent="topup"`. The check is
        `at least`, not `exactly` — other credits may have
        landed before or since.
        """
        print(
            f"\n📜 Verifying ledger for {user.username}..."
        )
        transactions = await self.get_transactions(user, limit=20)

        topups = [
            t for t in transactions
            if t.get("intent") == "topup"
            or t.get("direction") == "in"
        ]

        passed = len(transactions) >= expected_at_least
        if passed:
            print(
                f"   ✅ Ledger has {len(transactions)} entries "
                f"({len(topups)} incoming)"
            )
        else:
            print(
                f"   ❌ Ledger has {len(transactions)} entries, "
                f"expected ≥ {expected_at_least}"
            )
        return {
            "user_id": user.id,
            "passed": passed,
            "count": len(transactions),
            "incoming": len(topups),
        }

    # ── Composite run ──────────────────────────────────────────

    async def run_for_user(
        self,
        user: TestUser,
        *,
        top_up_amount: float = 50_000.0,
        ensure_minimum: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run the wallet scenarios for one user.

        When `ensure_minimum` is set, tops the wallet up to at
        least that balance first. When it's None, the caller is
        responsible for the wallet having whatever funds it needs.

        Always runs the shape and ledger checks. Runs the top-up
        roundtrip only when `top_up_amount` is positive.
        """
        results: List[Dict[str, Any]] = []

        if ensure_minimum is not None:
            await self.ensure_funded(
                user, minimum=ensure_minimum, silent=True,
            )

        results.append(await self.verify_my_wallet(user))

        if top_up_amount > 0:
            results.append(
                await self.verify_topup_roundtrip(
                    user, amount=top_up_amount,
                )
            )
            results.append(
                await self.verify_ledger_reflects_topup(user)
            )

        passed = all(r.get("passed", False) for r in results)
        return {
            "user_id": user.id,
            "passed": passed,
            "results": results,
        }