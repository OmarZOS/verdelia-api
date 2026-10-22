# test_runner/scenarios/delivery.py
"""Delivery scenarios — drive the delivery state machine.

The delivery router has no create endpoint: deliveries are produced
as a side effect of cart and order creation. This scenario therefore
operates on deliveries that *already exist*, produced earlier in the
run by `CartScenario` and `OrderScenario`.

The policy (`policies/delivery_policy.py`) gates most transitions on
*signal predicates* — fields the caller has to assert, defaulting to
False. Without those fields set on the request body, the transition
is denied with a 409. This scenario therefore sends the correct
signal for each step.

Signals used, one per transition that requires one:

  confirmed → shipped          : delivery_confirmed
  shipped   → in_transit       : in_transit_acknowledged
  out_for_delivery → delivered : proof_captured
  *         → failed           : incident_reported
  delivered/failed → returned  : return_confirmed
  delivered → refunded         : refund_completed

Transitions without a signal predicate (pending→processing,
processing→confirmed, in_transit→out_for_delivery, the →cancelled
edges) are gated by structural predicates only and need no body.

Profiles (cycled in order):

  * happy      — accept → confirm → ship → in-transit →
                 out-for-delivery → deliver → archive
  * cancelled  — accept → cancel
  * failed     — accept → confirm → ship → fail
  * returned   — full happy chain to delivered, then return, archive
  * refunded   — full happy chain to delivered, then refund, archive

`happy` and `returned`/`refunded` share the same initial chain;
they differ only in what happens at the terminal state.

Fetching:
  Deliveries are looked up by **provider id**, not by user. A
  delivery's `delivery_provider_id` is the supplier, not the buyer,
  so provider is the correct filter axis. The list endpoint refuses
  an unfiltered query, so `fetch_deliveries` requires at least one
  of `provider_ids` or `statuses`.
"""

import asyncio
import random
from typing import Any, Dict, List, Optional

from scenarios.base import BaseScenario
from context import TestUser
from data import short


class DeliveryScenario(BaseScenario):
    name = "deliveries"

    # Which terminal fate each delivery is driven to. Cycled per
    # delivery so a run with count=20 produces a predictable mix.
    _PROFILES = ("happy", "cancelled", "failed", "returned", "refunded")

    # The ordered chain of transitions for the happy path. Each
    # element is (endpoint_suffix, signal_field_or_None).
    #
    # When `signal_field` is set, the POST body carries
    # `{signal_field: True}` so the policy's signal predicate fires.
    # When it's None, the transition is gated by structural
    # predicates only and a body is unnecessary.
    _HAPPY_CHAIN = (
        ("accept", None),
        ("confirm", None),
        ("ship", "delivery_confirmed"),
        ("in-transit", "in_transit_acknowledged"),
        ("out-for-delivery", None),
        ("deliver", "proof_captured"),
    )

    # ══════════════════════════════════════════════════════════════
    # Bulk fetch — by provider, not by user
    # ══════════════════════════════════════════════════════════════

    async def fetch_deliveries(
        self,
        caller: TestUser,
        *,
        provider_ids: Optional[List[int]] = None,
        statuses: Optional[List[str]] = None,
        limit: int = 500,
    ) -> List[int]:
        """Fetch delivery ids from the delivery list endpoint.

        Called after cart and order flows have run, to collect the
        deliveries those flows produced. Returns a flat list of
        delivery ids.

        `caller` supplies the auth token for the request. It is
        NOT a filter — the query is scoped by `provider_ids`, not
        by user. A delivery's `delivery_provider_id` is the
        supplier that owns the goods, not the buyer who ordered
        them.

        `provider_ids` filters to deliveries for the given
        providers. The router requires at least one filter on the
        list endpoint, so a caller that passes neither
        `provider_ids` nor `statuses` gets an empty list back with
        a warning rather than a 400.

        Filters by provider because the runner creates deliveries
        under several providers (suppliers[:3]) and a bare list
        without any filter is refused by the router.
        """
        headers = self.get_auth_headers(caller)

        collected: List[int] = []
        seen: set = set()

        # The router requires at least one filter. If the caller
        # gave none, we cannot query at all — the endpoint will 400.
        if not provider_ids and not statuses:
            print(
                "   ⚠️ fetch_deliveries called with no filters; "
                "nothing to query."
            )
            return []

        # Query per provider (or once, if statuses were given) and
        # deduplicate by delivery id.
        query_filters: List[Dict[str, Any]] = []
        if provider_ids:
            for pid in provider_ids:
                query_filters.append({"provider_id": pid})
        else:
            query_filters.append({})

        for base in query_filters:
            if statuses:
                # The list endpoint takes a single status, not a
                # list. Query once per status and merge.
                for status_value in statuses:
                    params: Dict[str, Any] = dict(base)
                    params["limit"] = limit
                    params["offset"] = 0
                    params["status"] = status_value
                    await self._fetch_one_page(
                        headers, params, collected, seen,
                    )
            else:
                params = dict(base)
                params["limit"] = limit
                params["offset"] = 0
                await self._fetch_one_page(
                    headers, params, collected, seen,
                )

        print(
            f"   🚚 Fetched {len(collected)} delivery ids "
            f"(provider_ids={provider_ids})"
        )
        return collected

    async def _fetch_one_page(
        self,
        headers: Dict[str, str],
        params: Dict[str, Any],
        collected: List[int],
        seen: set,
    ) -> None:
        """Fetch one page of deliveries and append ids to `collected`.

        Silent on failure — a single bad query should not abort the
        whole fetch. Logs at info level so the reason is visible.
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/delivery",
                params=params,
                headers=headers,
            )
            if response.status_code != 200:
                print(
                    f"   ℹ️ delivery list {params} → "
                    f"{response.status_code} {short(response.text, 100)}"
                )
                return
            rows = self._extract_rows(response.json())
            for row in rows:
                did = self._extract_delivery_id(row)
                if did is not None and did not in seen:
                    seen.add(did)
                    collected.append(did)
        except Exception as e:
            print(f"   ❌ delivery list {params}: {e}")

    @staticmethod
    def _extract_rows(body: Any) -> List[Dict[str, Any]]:
        """Normalize the delivery list response into a list of dicts.

        The router's list endpoint may return:
          * a bare list
          * {"data": [...]}
          * {"deliveries": [...]}
          * {"items": [...]}
          * {"results": [...]}

        Accept all of them; unknown shapes yield an empty list.
        """
        if isinstance(body, list):
            return [r for r in body if isinstance(r, dict)]
        if isinstance(body, dict):
            for key in ("data", "deliveries", "items", "results"):
                value = body.get(key)
                if isinstance(value, list):
                    return [r for r in value if isinstance(r, dict)]
            # Some endpoints nest: {"data": {"deliveries": [...]}}
            data = body.get("data")
            if isinstance(data, dict):
                for key in ("deliveries", "items", "results"):
                    value = data.get(key)
                    if isinstance(value, list):
                        return [r for r in value if isinstance(r, dict)]
        return []

    @staticmethod
    def _extract_delivery_id(row: Dict[str, Any]) -> Optional[int]:
        """Pull the delivery id out of one row."""
        for key in ("id_delivery", "id", "delivery_id"):
            value = row.get(key)
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    continue
        return None

    # ══════════════════════════════════════════════════════════════
    # Entry point
    # ══════════════════════════════════════════════════════════════

    async def run_delivery_flow(
        self,
        user: TestUser,
        delivery_ids: List[int],
        *,
        count: Optional[int] = None,
    ) -> int:
        """Drive deliveries through the state machine.

        `delivery_ids` are the deliveries to act on. If `count` is
        given, only the first `count` are processed; otherwise all
        are. Returns the number of deliveries that reached a
        terminal state.

        Deliveries are expected to come from the cart or order
        scenarios. If the list is empty, the scenario prints a
        warning and returns 0 — it does not fabricate ids.
        """
        if not delivery_ids:
            print(
                "\n🚚 No deliveries to exercise. The cart and order "
                "scenarios populate `context.created_deliveries`; run "
                "them first."
            )
            return 0

        if count is not None:
            delivery_ids = delivery_ids[:count]

        print(
            f"\n🚚 Exercising {len(delivery_ids)} deliveries for "
            f"{user.username}..."
        )

        headers = self.get_auth_headers(user)
        if not headers:
            print("   ❌ No auth token")
            return 0

        completed = 0

        for i, delivery_id in enumerate(delivery_ids):
            profile = self._PROFILES[i % len(self._PROFILES)]

            try:
                reached_terminal = await self._drive_delivery(
                    user, delivery_id, profile, headers,
                )
                if reached_terminal:
                    self.stats["deliveries_terminal"] = (
                        self.stats.get("deliveries_terminal", 0) + 1
                    )
                    completed += 1

                # Record the terminal state for downstream tests.
                self.context.delivery_profiles[delivery_id] = profile

                if (i + 1) % 5 == 0:
                    print(
                        f"   … {i + 1}/{len(delivery_ids)} deliveries "
                        f"exercised"
                    )

            except Exception as e:
                print(f"   ❌ Delivery {delivery_id}: {e}")

            await asyncio.sleep(0.05)

        print(f"✅ {completed} deliveries reached a terminal state")
        return completed

    # ══════════════════════════════════════════════════════════════
    # Per-delivery driver
    # ══════════════════════════════════════════════════════════════

    async def _drive_delivery(
        self,
        user: TestUser,
        delivery_id: int,
        profile: str,
        headers: Dict[str, str],
    ) -> bool:
        """Run one delivery through its profile's lifecycle. ..."""
        # Ensure the delivery has a package count. `processing →
        # confirmed` requires `delivery_package_count > 0`, and the
        # cart/order flows may not have set it. This call is
        # idempotent — the workflow patches, doesn't replace.
        await self._update_details(user, delivery_id, headers)

        # These two are optional / exercisable-where-valid, so keep
        # them randomized. They don't gate any transition.
        if random.random() < 0.3:
            await self._record_tracking_ping(
                user, delivery_id, headers,
            )
        if random.random() < 0.2:
            await self._reroute(user, delivery_id, headers)


        # ── Profile-specific chains ──
        if profile == "happy":
            if not await self._run_happy_chain(
                user, delivery_id, headers,
            ):
                return False
            await self._archive(user, delivery_id, headers)
            return True

        if profile == "cancelled":
            if not await self._run_step(
                user, delivery_id, "accept", headers,
            ):
                return False
            if not await self._run_step(
                user, delivery_id, "cancel", headers,
            ):
                return False
            await self._archive(user, delivery_id, headers)
            return True

        if profile == "failed":
            # accept → confirm → ship → fail
            #
            # `ship` requires `delivery_confirmed`;
            # `fail` requires `incident_reported`. Both are signal
            # predicates; without the body fields the policy denies
            # the transition with a 409.
            if not await self._run_step(
                user, delivery_id, "accept", headers,
            ):
                return False
            if not await self._run_step(
                user, delivery_id, "confirm", headers,
            ):
                return False
            if not await self._run_step(
                user, delivery_id, "ship", headers,
                signal="delivery_confirmed",
            ):
                return False
            if not await self._run_step(
                user, delivery_id, "fail", headers,
                signal="incident_reported",
            ):
                return False
            await self._archive(user, delivery_id, headers)
            return True

        if profile == "returned":
            if not await self._run_happy_chain(
                user, delivery_id, headers,
            ):
                return False
            if not await self._run_step(
                user, delivery_id, "return", headers,
                signal="return_confirmed",
            ):
                return False
            await self._archive(user, delivery_id, headers)
            return True

        if profile == "refunded":
            if not await self._run_happy_chain(
                user, delivery_id, headers,
            ):
                return False
            if not await self._run_step(
                user, delivery_id, "refund", headers,
                signal="refund_completed",
            ):
                return False
            await self._archive(user, delivery_id, headers)
            return True

        print(f"   ⚠️ Unknown delivery profile: {profile}")
        return False

    async def _run_happy_chain(
        self,
        user: TestUser,
        delivery_id: int,
        headers: Dict[str, str],
    ) -> bool:
        """Walk the six-step happy path. Returns False on first failure."""
        for suffix, signal in self._HAPPY_CHAIN:
            if not await self._run_step(
                user, delivery_id, suffix, headers, signal=signal,
            ):
                return False
        return True

    # ══════════════════════════════════════════════════════════════
    # Individual transitions
    # ══════════════════════════════════════════════════════════════

    async def _run_step(
        self,
        user: TestUser,
        delivery_id: int,
        suffix: str,
        headers: Dict[str, str],
        *,
        signal: Optional[str] = None,
    ) -> bool:
        """Call one transition endpoint.

        `suffix` is the last path segment: 'accept', 'confirm',
        'ship', 'in-transit', 'out-for-delivery', 'deliver',
        'cancel', 'fail', 'return', 'refund'.

        `signal` names the `Delivery_API` field the policy requires
        for this transition, if any. When set, the POST body carries
        `{signal: True}` so the policy's signal predicate fires.
        Without it the policy defaults the field to False and denies
        the transition with a 409.

        Returns True on 200, False otherwise (with a short log line).
        """
        body = {signal: True} if signal else None

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}/{suffix}",
                json=body,
                headers=headers,
            )
            if response.status_code == 200:
                self.stats["delivery_transitions"] = (
                    self.stats.get("delivery_transitions", 0) + 1
                )
                return True
            # 409 is expected when the state machine refuses the
            # move — that's a real signal, not a runner bug, so log
            # it at info level rather than as a failure.
            if response.status_code == 409:
                print(
                    f"   ℹ️ {suffix} on delivery {delivery_id} "
                    f"refused: {short(response.text, 120)}"
                )
                return False
            self._record_failure(
                f"{suffix} on delivery {delivery_id}", response,
            )
            return False
        except Exception as e:
            print(
                f"   ❌ {suffix} on delivery {delivery_id}: {e}"
            )
            return False

    # ══════════════════════════════════════════════════════════════
    # Metadata writes
    # ══════════════════════════════════════════════════════════════

    async def _update_details(
        self,
        user: TestUser,
        delivery_id: int,
        headers: Dict[str, str],
    ) -> None:
        """POST /{id}/details — metadata-only write.

        Sends only the mutable descriptive fields. Status is
        rejected by this endpoint; it has its own transition routes.
        Fields not sent retain their current value because the
        workflow patches, not replaces.
        """
        try:
            body = {
                "delivery_special_instructions": "Leave at the door",
                "delivery_package_count": random.randint(1, 5),
                "delivery_goods_description": "Test goods",
            }
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}/details",
                json=body,
                headers=headers,
            )
            if response.status_code == 200:
                self.stats["delivery_detail_updates"] = (
                    self.stats.get("delivery_detail_updates", 0) + 1
                )
            elif response.status_code == 409:
                # Not editable in the current state — legitimate.
                pass
            else:
                print(
                    f"   ℹ️ details on delivery {delivery_id}: "
                    f"{response.status_code} {short(response.text, 100)}"
                )
        except Exception as e:
            print(
                f"   ❌ details on delivery {delivery_id}: {e}"
            )

    async def _record_tracking_ping(
        self,
        user: TestUser,
        delivery_id: int,
        headers: Dict[str, str],
    ) -> None:
        """POST /{id}/tracking-pings?current_address_id=..."""
        try:
            # The router requires a real address id. If the context
            # doesn't track any, skip the call — a fabricated id
            # will be rejected by the workflow and produce noise.
            address_id = self._pick_address_id()
            if address_id is None:
                return

            response = await self.client.post(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}/tracking-pings",
                params={"current_address_id": address_id},
                headers=headers,
            )
            if response.status_code == 200:
                self.stats["delivery_tracking_pings"] = (
                    self.stats.get("delivery_tracking_pings", 0) + 1
                )
            else:
                print(
                    f"   ℹ️ tracking-ping on delivery {delivery_id}: "
                    f"{response.status_code} {short(response.text, 100)}"
                )
        except Exception as e:
            print(
                f"   ❌ tracking-ping on delivery {delivery_id}: {e}"
            )

    async def _reroute(
        self,
        user: TestUser,
        delivery_id: int,
        headers: Dict[str, str],
    ) -> None:
        """POST /{id}/reroute?address_id=..."""
        try:
            address_id = self._pick_address_id()
            if address_id is None:
                return

            response = await self.client.post(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}/reroute",
                params={"address_id": address_id},
                headers=headers,
            )
            if response.status_code == 200:
                self.stats["delivery_reroutes"] = (
                    self.stats.get("delivery_reroutes", 0) + 1
                )
            else:
                print(
                    f"   ℹ️ reroute on delivery {delivery_id}: "
                    f"{response.status_code} {short(response.text, 100)}"
                )
        except Exception as e:
            print(f"   ❌ reroute on delivery {delivery_id}: {e}")

    async def _archive(
        self,
        user: TestUser,
        delivery_id: int,
        headers: Dict[str, str],
    ) -> None:
        """POST /{id}/archive — only valid on terminal deliveries."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}/archive",
                headers=headers,
            )
            if response.status_code == 200:
                self.stats["delivery_archives"] = (
                    self.stats.get("delivery_archives", 0) + 1
                )
            else:
                # 409 here means the delivery wasn't terminal when
                # archive was called — a legitimate domain refusal
                # given the profiles above only archive after a
                # terminal state.
                print(
                    f"   ℹ️ archive on delivery {delivery_id}: "
                    f"{response.status_code} {short(response.text, 100)}"
                )
        except Exception as e:
            print(f"   ❌ archive on delivery {delivery_id}: {e}")

    # ══════════════════════════════════════════════════════════════
    # Reads
    # ══════════════════════════════════════════════════════════════

    async def read_delivery(
        self, user: TestUser, delivery_id: int,
    ) -> Optional[Dict[str, Any]]:
        """GET /{id}"""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                f"Get delivery {delivery_id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Get delivery {delivery_id}: {e}")
            return None

    async def read_next_states(
        self, user: TestUser, delivery_id: int,
    ) -> Optional[Dict[str, Any]]:
        """GET /{id}/next-states"""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}/next-states",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                f"Get next-states {delivery_id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Get next-states {delivery_id}: {e}")
            return None

    async def list_deliveries(
        self,
        user: TestUser,
        *,
        provider_id: int = 0,
        source_type: Optional[str] = None,
        source_id: int = 0,
        delivery_status: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Optional[Dict[str, Any]]:
        """GET "" — requires at least one filter.

        `user` supplies the auth token. `provider_id` and the other
        kwargs are the actual filters.
        """
        headers = self.get_auth_headers(user)

        params: Dict[str, Any] = {
            "provider_id": provider_id,
            "source_id": source_id,
            "offset": offset,
            "limit": limit,
        }
        if source_type:
            params["source_type"] = source_type
        if delivery_status:
            params["status"] = delivery_status

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/delivery",
                params=params,
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                "List deliveries", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ List deliveries: {e}")
            return None

    # ══════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════

    def _pick_address_id(self) -> Optional[int]:
        """Pick a real address id from the context, or None.

        The router requires a real address id for `/tracking-pings`
        and `/reroute`. The runner does not currently track address
        ids in its context, so this returns None until that changes —
        and callers skip the call rather than fabricating an id.

        To enable these endpoints, add `context.created_addresses`
        (a list of ints) populated by whoever creates addresses
        during a run, then return `random.choice(...)` here.
        """
        addresses = getattr(self.context, "created_addresses", None)
        if not addresses:
            return None
        return random.choice(addresses)