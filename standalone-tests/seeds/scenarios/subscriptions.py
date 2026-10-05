# test_runner/scenarios/subscriptions.py
"""Subscription scenarios — plans, purchases, cancels, tiers."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from scenarios.base import BaseScenario
from context import TestUser
from data import (
    extract_id,
    generate_subscription_purchase_data,
    short,
    unwrap,
)


class SubscriptionsScenario(BaseScenario):
    name = "subscriptions"

    # ── Plans ──────────────────────────────────────────────────

    async def get_plans(
        self,
        user: Optional[TestUser] = None,
        plan_type: Optional[str] = None,
        billing_cycle: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if plan_type:
            params["plan_type"] = plan_type
        if billing_cycle:
            params["billing_cycle"] = billing_cycle

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/plans",
                params=params,
                headers=self.get_auth_headers(user) if user else {},
            )
            if response.status_code != 200:
                self._record_failure("List plans", response)
                return []

            payload = response.json()
            if isinstance(payload, list):
                return payload

            inner = (
                payload.get("data")
                if isinstance(payload, dict) else None
            )
            if isinstance(inner, list):
                return inner
            if isinstance(inner, dict):
                items = inner.get("items")
                if isinstance(items, list):
                    return items

            print(
                f"   ⚠️ /plans returned 200 but no list — "
                f"shape: {short(response.text, 200)}"
            )
            return []
        except Exception as e:
            print(f"   ❌ Error listing plans: {e}")
            return []

    async def get_plan_by_id(
        self, plan_id: int, user: Optional[TestUser] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/plans/{plan_id}",
                headers=self.get_auth_headers(user) if user else {},
            )
            if response.status_code == 200:
                return unwrap(response.json())
            self._record_failure(f"Get plan {plan_id}", response)
            return None
        except Exception as e:
            print(f"   ❌ Error fetching plan {plan_id}: {e}")
            return None

    # ── Purchases ──────────────────────────────────────────────

    async def initiate_subscription(
        self,
        user: TestUser,
        plan_id: int,
        *,
        payment_method: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        headers = self.get_auth_headers(user)
        if not headers:
            print("   ❌ No auth token")
            return None

        params = generate_subscription_purchase_data(
            plan_id,
            payment_method=payment_method,
            notes=notes,
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/app_user/{user.id}"
                f"/subscription/initiate",
                params=params,
                headers=headers,
            )
            if response.status_code in (200, 201):
                payload = unwrap(response.json()) or response.json()
                self._record_purchase(user, plan_id, payload)
                return payload

            self._record_failure(
                f"Purchase subscription user={user.id} "
                f"plan={plan_id}",
                response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None

    async def link_free_plan(
        self, user: TestUser, plan_id: int,
    ) -> Optional[Dict[str, Any]]:
        headers = self.get_auth_headers(user)
        if not headers:
            print("   ❌ No auth token")
            return None

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/app_user/{user.id}"
                f"/subscription/link-free",
                params={"plan_id": plan_id},
                headers=headers,
            )
            if response.status_code in (200, 201):
                payload = unwrap(response.json()) or response.json()
                self._record_purchase(user, plan_id, payload)
                return payload
            if response.status_code == 400:
                print(
                    f"   ℹ️ Link-free rejected for plan {plan_id} "
                    f"(expected if plan is paid)"
                )
                return None
            self._record_failure(
                f"Link free plan user={user.id} plan={plan_id}",
                response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None

    async def finalize_subscription(
        self, user: TestUser, payment_id: int,
    ) -> Optional[Dict[str, Any]]:
        headers = self.get_auth_headers(user)
        if not headers:
            return None

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/app_user/{user.id}"
                f"/subscription/finalize",
                params={"payment_id": payment_id},
                headers=headers,
            )
            if response.status_code in (200, 201):
                return unwrap(response.json()) or response.json()
            self._record_failure(
                f"Finalize user={user.id} payment={payment_id}",
                response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None

    # ── Reads ──────────────────────────────────────────────────

    async def get_user_subscription(
        self, user: TestUser,
    ) -> Optional[Dict[str, Any]]:
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/app_user/{user.id}"
                f"/subscription",
                headers=headers,
            )
            if response.status_code == 200:
                print(f"   ✅ User {user.id} has a subscription")
                return unwrap(response.json()) or response.json()
            if response.status_code == 404:
                print(
                    f"   ℹ️ User {user.id} has no subscription (404)"
                )
                return None
            self._record_failure(
                f"Get subscription for user {user.id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None

    async def check_subscription_status(
        self, user: TestUser,
    ) -> Optional[Dict[str, Any]]:
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/app_user/{user.id}"
                f"/subscription/status",
                headers=headers,
            )
            if response.status_code == 200:
                payload = response.json()
                active = (
                    payload.get("active")
                    if isinstance(payload, dict) else None
                )
                print(f"   ✅ User {user.id} active={active}")
                return payload
            self._record_failure(
                f"Check subscription status for user {user.id}",
                response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None

    async def cancel_subscription(
        self,
        user: TestUser,
        *,
        refund_payment_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        headers = self.get_auth_headers(user)
        params: Dict[str, Any] = {}
        if refund_payment_id is not None:
            params["refund_payment_id"] = refund_payment_id

        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/app_user/{user.id}"
                f"/subscription",
                params=params,
                headers=headers,
            )
            if response.status_code == 200:
                print(
                    f"   ✅ Cancelled subscription for user {user.id}"
                )
                return unwrap(response.json()) or response.json()
            if response.status_code == 404:
                print(
                    f"   ℹ️ No subscription to cancel for user "
                    f"{user.id}"
                )
                return None
            self._record_failure(
                f"Cancel subscription for user {user.id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None

    # ── Composite flows ────────────────────────────────────────

    async def run_flow(
        self, user: TestUser, plans: List[int],
    ) -> None:
        """Full lifecycle: list plans, purchase, read, link-free."""
        print(f"\n💳 Subscription flow for {user.username}...")

        all_plans = await self.get_plans(user)
        print(f"   ℹ️ Listed {len(all_plans)} plans")
        if all_plans:
            await self.get_plan_by_id(
                extract_id(all_plans[0]), user,
            )

        if not plans:
            print("   ⚠️ No plans to subscribe to")
            return

        paid_plan_id, free_plan_id = await self._pick_plans(plans, user)

        if free_plan_id is not None:
            await self.link_free_plan(user, free_plan_id)

        if paid_plan_id is not None:
            await self.initiate_subscription(
                user, paid_plan_id, payment_method="cash",
            )
            await self.get_user_subscription(user)
            await self.check_subscription_status(user)
            await self.link_free_plan(user, paid_plan_id)

    async def setup_tiered_users(
        self,
        users_scenario,
        plans: List[Dict[str, Any]],
    ) -> Dict[int, TestUser]:
        """Create one user per plan and attach that plan.

        Takes a `UsersScenario` for user creation + login. The
        subscription logic stays here.
        """
        print("\n🎫 Setting up one user per plan...")
        tiered: Dict[int, TestUser] = {}

        for plan in plans:
            plan_id = extract_id(plan)
            plan_name = plan.get("plan_name", f"plan_{plan_id}")
            price = float(plan.get("plan_price") or 0)

            user = await users_scenario.create_user(
                user_type="provider", extended=True,
            )
            if user is None:
                print(f"   ❌ Could not create user for {plan_name}")
                continue

            self.context.users.append(user)
            self.stats["users"] = self.stats.get("users", 0) + 1

            if not await users_scenario.login_user(user):
                print(f"   ❌ Could not log in user for {plan_name}")
                continue

            if price == 0:
                result = await self.link_free_plan(user, plan_id)
            else:
                result = await self.initiate_subscription(
                    user, plan_id, payment_method="cash",
                )

            if result is None:
                print(
                    f"   ⚠️ Tier {plan_name} (id={plan_id}, "
                    f"price={price}): user={user.id} created but "
                    f"subscription FAILED — not registered"
                )
                continue

            tiered[plan_id] = user
            print(
                f"   ✅ Tier {plan_name} (id={plan_id}, "
                f"price={price}): user={user.id}"
            )
        return tiered

    # ── Internal ───────────────────────────────────────────────

    def _record_purchase(
        self,
        user: TestUser,
        plan_id: int,
        payload: Dict[str, Any],
    ) -> None:
        subscription = (
            payload.get("subscription")
            if isinstance(payload, dict) else None
        )
        sub_id = 0
        if isinstance(subscription, dict):
            sub_id = extract_id(subscription)
        if sub_id > 0:
            self.context.created_subscriptions.append(sub_id)
            self.stats["subscriptions"] = (
                self.stats.get("subscriptions", 0) + 1
            )
            self.context.subscription_user_mapping.setdefault(
                user.id, []
            ).append(sub_id)

        payment = (
            payload.get("payment")
            if isinstance(payload, dict) else None
        )
        payment_id = extract_id(payment) if isinstance(payment, dict) else 0

        print(
            f"   ✅ Purchased subscription: user={user.id} "
            f"plan={plan_id} subscription={sub_id} "
            f"payment={payment_id}"
        )

    async def _pick_plans(
        self, plans: List[int], user: TestUser,
    ) -> tuple[Optional[int], Optional[int]]:
        paid_plan_id: Optional[int] = None
        free_plan_id: Optional[int] = None
        for pid in plans:
            plan = await self.get_plan_by_id(pid, user)
            if plan is None:
                continue
            price = plan.get("plan_price") or 0
            if price and float(price) > 0 and paid_plan_id is None:
                paid_plan_id = pid
            elif float(price or 0) == 0 and free_plan_id is None:
                free_plan_id = pid
        return paid_plan_id, free_plan_id