# test_runner/scenarios/delivery.py
"""Delivery scenarios — drive the verification-based state machine.

The delivery router has no create endpoint: deliveries are produced
as a side effect of cart and order creation. This scenario therefore
operates on deliveries that *already exist*.

There are no caller-asserted booleans. Each transition is gated by
state the workflow reads from the delivery row and from related
rows (carrier assignment, tracking address, refund payment). The
scenario *records* that state via the evidence endpoints, then calls
the transition. The transition succeeds or fails based on what the
row says, not on what the caller claimed.

Evidence endpoints used, by transition:

  confirmed → shipped              : PATCH carrier via /details
  shipped → in_transit             : move tracking off destination
  in_transit → out_for_delivery    : tracking still off destination
  out_for_delivery → delivered     : move tracking onto destination
  delivered → refunded             : POST /refund-payment

Profiles (cycled in order):

  * happy      — accept → confirm → ship → in-transit →
                 out-for-delivery → deliver → archive
  * cancelled  — accept → cancel
  * failed     — accept → confirm → ship → fail
  * returned   — full happy chain to delivered, then return, archive
  * refunded   — full happy chain to delivered, then refund, archive
"""

import asyncio
import random
from typing import Any, Dict, List, Optional

from scenarios.base import BaseScenario
from context import TestUser
from data import short


class DeliveryScenario(BaseScenario):
    name = "deliveries"

    _PROFILES = ("happy", "cancelled", "failed", "returned", "refunded")

    # The ordered chain of transitions for the happy path.
    #
    # No signals — every transition is enabled by evidence the
    # runner records *before* calling the endpoint. The chain is
    # decomposed into `_run_happy_chain`, which interleaves the
    # evidence-recording calls with the transitions.
    _HAPPY_CHAIN = (
        "accept",
        "confirm",
        "ship",
        "in-transit",
        "out-for-delivery",
        "deliver",
    )

    # ══════════════════════════════════════════════════════════════
    # Bulk fetch (unchanged)
    # ══════════════════════════════════════════════════════════════

    async def fetch_deliveries(
        self,
        caller: TestUser,
        *,
        provider_ids: Optional[List[int]] = None,
        statuses: Optional[List[str]] = None,
        limit: int = 500,
    ) -> List[int]:
        headers = self.get_auth_headers(caller)
        collected: List[int] = []
        seen: set = set()

        if not provider_ids and not statuses:
            print(
                "   ⚠️ fetch_deliveries called with no filters; "
                "nothing to query."
            )
            return []

        query_filters: List[Dict[str, Any]] = []
        if provider_ids:
            for pid in provider_ids:
                query_filters.append({"provider_id": pid})
        else:
            query_filters.append({})

        for base in query_filters:
            if statuses:
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
        if isinstance(body, list):
            return [r for r in body if isinstance(r, dict)]
        if isinstance(body, dict):
            for key in ("data", "deliveries", "items", "results"):
                value = body.get(key)
                if isinstance(value, list):
                    return [r for r in value if isinstance(r, dict)]
            data = body.get("data")
            if isinstance(data, dict):
                for key in ("deliveries", "items", "results"):
                    value = data.get(key)
                    if isinstance(value, list):
                        return [r for r in value if isinstance(r, dict)]
        return []

    @staticmethod
    def _extract_delivery_id(row: Dict[str, Any]) -> Optional[int]:
        for key in ("id_delivery", "id", "delivery_id"):
            value = row.get(key)
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    continue
        return None

    # ══════════════════════════════════════════════════════════════
    # Entry point (unchanged signature)
    # ══════════════════════════════════════════════════════════════

    async def run_delivery_flow(
        self,
        user: TestUser,
        delivery_ids: List[int],
        *,
        count: Optional[int] = None,
    ) -> int:
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
        """Run one delivery through its profile's lifecycle.

        The sequence is *state-driven*: before every gated
        transition, the runner records the evidence the policy will
        read.
        """
        # ── Phase 0: read the delivery's current shape.
        # `carrying_user_id` and the destination address id are what
        # the policy reads, so we need both before we can build a
        # working chain.
        delivery = await self.read_delivery(user, delivery_id)
        if delivery is None:
            return False

        destination_address_id = self._extract_address_id(delivery)
        current_address_id = self._extract_current_address_id(delivery)

        # ── Phase 1: complete the "packed" fields.
        # `processing → confirmed` needs packages + weight + method.
        # The cart/order flows may not have set all three, so we
        # patch them now.
        await self._complete_packed_fields(
            user, delivery_id, headers,
        )

        # ── Phase 2: assign a carrier.
        # `confirmed → shipped` requires a non-null carrying_user_id.
        # This is not a boolean — it writes the column.
        await self._assign_carrier(user, delivery_id, headers)

        # ── Phase 3: profile-specific chains ──
        if profile == "happy":
            if not await self._run_happy_chain(
                user, delivery_id, headers,
                destination_address_id=destination_address_id,
                current_address_id=current_address_id,
            ):
                return False
            await self._archive(user, delivery_id, headers)
            return True

        if profile == "cancelled":
            # Cancellable-window predicate only; no evidence needed.
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
            # accept → confirm → ship → fail.
            # `fail` needs `has_carrier and has_tracking_started` —
            # both are already satisfied by phase 2 and by the fact
            # that the delivery was created with an address. If the
            # delivery has no current address id yet, move the
            # tracking off destination first.
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
            ):
                return False
            if current_address_id is None:
                await self._move_tracking_off_destination(
                    user, delivery_id, headers,
                    destination_address_id=destination_address_id,
                )
            if not await self._run_step(
                user, delivery_id, "fail", headers,
            ):
                return False
            await self._archive(user, delivery_id, headers)
            return True

        if profile == "returned":
            if not await self._run_happy_chain(
                user, delivery_id, headers,
                destination_address_id=destination_address_id,
                current_address_id=current_address_id,
            ):
                return False
            # `delivered → returned` requires tracking to be off
            # destination (return_received predicate).
            await self._move_tracking_off_destination(
                user, delivery_id, headers,
                destination_address_id=destination_address_id,
            )
            if not await self._run_step(
                user, delivery_id, "return", headers,
            ):
                return False
            await self._archive(user, delivery_id, headers)
            return True

        if profile == "refunded":
            if not await self._run_happy_chain(
                user, delivery_id, headers,
                destination_address_id=destination_address_id,
                current_address_id=current_address_id,
            ):
                return False
            # `delivered → refunded` requires a completed refund
            # payment on the linked invoice.
            await self._record_refund(
                user, delivery_id, headers,
            )
            if not await self._run_step(
                user, delivery_id, "refund", headers,
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
        *,
        destination_address_id: Optional[int],
        current_address_id: Optional[int],
    ) -> bool:
        """Walk the happy path, recording evidence between steps.

        The chain is:

          accept → confirm → ship → in-transit →
          out-for-delivery → deliver

        Evidence interleaved:

          before in-transit : move tracking OFF destination
          before deliver    : move tracking ONTO destination

        Without these moves, the policy predicates for
        `shipped → in_transit`, `in_transit → out_for_delivery`,
        and `out_for_delivery → delivered` will all return 409.
        """
        # accept (structural only)
        if not await self._run_step(
            user, delivery_id, "accept", headers,
        ):
            return False

        # confirm (structural: packages + weight + method)
        if not await self._run_step(
            user, delivery_id, "confirm", headers,
        ):
            return False

        # ship (needs carrier — already set in phase 2)
        if not await self._run_step(
            user, delivery_id, "ship", headers,
        ):
            return False

        # Before in-transit: tracking must be OFF destination.
        # If the delivery was created with a current_address_id
        # equal to the destination, we need to move it. If it's
        # already off destination, leave it alone.
        if (
            destination_address_id is not None
            and current_address_id == destination_address_id
        ):
            await self._move_tracking_off_destination(
                user, delivery_id, headers,
                destination_address_id=destination_address_id,
            )

        # in-transit
        if not await self._run_step(
            user, delivery_id, "in-transit", headers,
        ):
            return False

        # out-for-delivery
        if not await self._run_step(
            user, delivery_id, "out-for-delivery", headers,
        ):
            return False

        # Before deliver: tracking must be ON destination.
        if destination_address_id is not None:
            await self._move_tracking_onto_destination(
                user, delivery_id, headers,
                destination_address_id=destination_address_id,
            )

        # deliver
        if not await self._run_step(
            user, delivery_id, "deliver", headers,
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
    ) -> bool:
        """Call one transition endpoint.

        No signal argument — the policy decides based on the row's
        state, which the runner moved via the evidence helpers
        before this call.
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}/{suffix}",
                json=None,
                headers=headers,
            )
            if response.status_code == 200:
                self.stats["delivery_transitions"] = (
                    self.stats.get("delivery_transitions", 0) + 1
                )
                return True
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
    # Evidence recording
    # ══════════════════════════════════════════════════════════════

    async def _complete_packed_fields(
        self, user: TestUser, delivery_id: int, headers: Dict[str, str],
    ) -> None:
        body = {
            "delivery_package_count": random.randint(1, 3),
            "delivery_total_weight": round(random.uniform(1.0, 5.0), 2),
            "delivery_shipping_method": "standard",
            "delivery_goods_description": "Test goods",
            "delivery_special_instructions": "Leave at the door",
        }
        dest = self._pick_address_id()
        if dest is not None:
            body["delivery_address_id"] = dest
        try:
            body = {
                "delivery_package_count": random.randint(1, 3),
                "delivery_total_weight": round(
                    random.uniform(0.5, 5.0), 2,
                ),
                "delivery_shipping_method": "standard",
                "delivery_goods_description": "Test goods",
                "delivery_special_instructions": "Leave at the door",
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
                # Not editable in this state — legitimate.
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

    async def _assign_carrier(
        self,
        user: TestUser,
        delivery_id: int,
        headers: Dict[str, str],
    ) -> None:
        """Assign a carrier. Enables `confirmed → shipped`.

        The carrier id is the caller's own user id — the calling user
        becomes the carrying user. This is what the policy reads as
        `has_carrier(d)`: `carrying_user_id > 0`.

        If the delivery already has a carrier, this is skipped.
        """
        try:
            # Read current state first — skip if already assigned.
            current = await self.read_delivery(user, delivery_id)
            if current is not None:
                existing_carrier = (
                    self._extract_carrying_user_id(current)
                )
                if existing_carrier is not None and existing_carrier > 0:
                    return
        except Exception:
            pass

        try:
            body = {"carrying_user_id": int(user.id)}
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}/details",
                json=body,
                headers=headers,
            )
            if response.status_code == 200:
                self.stats["delivery_carrier_assignments"] = (
                    self.stats.get("delivery_carrier_assignments", 0) + 1
                )
            else:
                print(
                    f"   ℹ️ carrier assignment on delivery "
                    f"{delivery_id}: {response.status_code} "
                    f"{short(response.text, 100)}"
                )
        except Exception as e:
            print(
                f"   ❌ carrier assignment on delivery {delivery_id}: {e}"
            )

    async def _move_tracking_off_destination(
        self,
        user: TestUser,
        delivery_id: int,
        headers: Dict[str, str],
        *,
        destination_address_id: Optional[int],
    ) -> None:
        """Move tracking to an address that isn't the destination.

        Enables `shipped → in_transit` and (via the moving-address
        predicate) `delivered/failed → returned`.

        Uses any existing address id in the context that is NOT
        equal to the destination. If none is available, this is a
        no-op and the caller will see a 409 on the transition — which
        is the correct signal to add address tracking to the runner.
        """
        try:
            candidate = self._pick_address_id_excluding(
                destination_address_id,
            )
            if candidate is None:
                print(
                    f"   ℹ️ no non-destination address available for "
                    f"tracking-ping on delivery {delivery_id}"
                )
                return

            response = await self.client.post(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}/tracking-pings",
                params={"current_address_id": candidate},
                headers=headers,
            )
            if response.status_code == 200:
                self.stats["delivery_tracking_pings"] = (
                    self.stats.get("delivery_tracking_pings", 0) + 1
                )
            else:
                print(
                    f"   ℹ️ tracking-ping(off) on delivery "
                    f"{delivery_id}: {response.status_code} "
                    f"{short(response.text, 100)}"
                )
        except Exception as e:
            print(
                f"   ❌ tracking-ping(off) on delivery "
                f"{delivery_id}: {e}"
            )

    async def _move_tracking_onto_destination(
        self,
        user: TestUser,
        delivery_id: int,
        headers: Dict[str, str],
        *,
        destination_address_id: Optional[int],
    ) -> None:
        """Move tracking to the destination address.

        Enables `out_for_delivery → delivered`.
        """
        if destination_address_id is None:
            print(
                f"   ℹ️ no destination address on delivery "
                f"{delivery_id}; skipping on-destination ping"
            )
            return

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}/tracking-pings",
                params={"current_address_id": destination_address_id},
                headers=headers,
            )
            if response.status_code == 200:
                self.stats["delivery_tracking_pings"] = (
                    self.stats.get("delivery_tracking_pings", 0) + 1
                )
            else:
                print(
                    f"   ℹ️ tracking-ping(on) on delivery "
                    f"{delivery_id}: {response.status_code} "
                    f"{short(response.text, 100)}"
                )
        except Exception as e:
            print(
                f"   ❌ tracking-ping(on) on delivery "
                f"{delivery_id}: {e}"
            )

    async def _record_refund(
        self,
        user: TestUser,
        delivery_id: int,
        headers: Dict[str, str],
    ) -> None:
        """Record a completed refund on the linked invoice.

        Enables `delivered → refunded`. Requires the delivery to
        have a `delivery_invoice_ref` (cart/order flows set this).
        """
        try:
            body = {
                "amount": round(random.uniform(50.0, 500.0), 2),
                "reference": f"REF-{delivery_id}-TEST",
            }
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}/refund-payment",
                json=body,
                headers=headers,
            )
            if response.status_code == 200:
                self.stats["delivery_refunds"] = (
                    self.stats.get("delivery_refunds", 0) + 1
                )
            else:
                print(
                    f"   ℹ️ refund-payment on delivery {delivery_id}: "
                    f"{response.status_code} {short(response.text, 100)}"
                )
        except Exception as e:
            print(
                f"   ❌ refund-payment on delivery {delivery_id}: {e}"
            )

    # ══════════════════════════════════════════════════════════════
    # Non-status writes
    # ══════════════════════════════════════════════════════════════

    async def _reroute(
        self,
        user: TestUser,
        delivery_id: int,
        headers: Dict[str, str],
    ) -> None:
        """POST /{id}/reroute?address_id=...

        Optional — does not gate any transition. Kept for coverage.
        """
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
                print(
                    f"   ℹ️ archive on delivery {delivery_id}: "
                    f"{response.status_code} {short(response.text, 100)}"
                )
        except Exception as e:
            print(f"   ❌ archive on delivery {delivery_id}: {e}")

    # ══════════════════════════════════════════════════════════════
    # Reads (unchanged)
    # ══════════════════════════════════════════════════════════════

    async def read_delivery(
        self, user: TestUser, delivery_id: int,
    ) -> Optional[Dict[str, Any]]:
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/delivery/"
                f"{delivery_id}",
                headers=headers,
            )
            if response.status_code == 200:
                body = response.json()
                # Unwrap `{"data": {...}}` so callers see the row
                # directly regardless of envelope shape.
                if isinstance(body, dict) and isinstance(
                    body.get("data"), dict,
                ):
                    return body["data"]
                return body
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

    # ══════════════════════════════════════════════════════════════
    # Row readers (small helpers for extracting columns)
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _extract_address_id(
        delivery: Dict[str, Any],
    ) -> Optional[int]:
        for key in (
            "address_id", "delivery_address_id", "delivery_address",
        ):
            value = delivery.get(key)
            if isinstance(value, dict):
                value = value.get("id_address") or value.get("id")
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def _extract_current_address_id(
        delivery: Dict[str, Any],
    ) -> Optional[int]:
        for key in (
            "current_address_id",
            "delivery_current_address_id",
            "delivery_current_address",
        ):
            value = delivery.get(key)
            if isinstance(value, dict):
                value = value.get("id_address") or value.get("id")
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def _extract_carrying_user_id(
        delivery: Dict[str, Any],
    ) -> Optional[int]:
        value = delivery.get("carrying_user_id")
        if isinstance(value, dict):
            value = value.get("id_app_user") or value.get("id")
        if value is not None:
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
        return None

    # ══════════════════════════════════════════════════════════════
    # Address picking
    # ══════════════════════════════════════════════════════════════

    def _pick_address_id(self) -> Optional[int]:
        addresses = getattr(self.context, "created_addresses", None)
        if not addresses:
            return None
        return random.choice(addresses)

    def _pick_address_id_excluding(
        self, excluded: Optional[int],
    ) -> Optional[int]:
        """Pick an address id that isn't `excluded`.

        Falls back to any address if the only ones available are the
        excluded one — better to emit a 409 the caller can see than
        to silently skip.
        """
        addresses = getattr(self.context, "created_addresses", None)
        if not addresses:
            return None
        candidates = [a for a in addresses if a != excluded]
        if candidates:
            return random.choice(candidates)
        # Only the excluded address exists; return it so the failure
        # is visible as a 409 rather than a silent skip.
        return random.choice(addresses)