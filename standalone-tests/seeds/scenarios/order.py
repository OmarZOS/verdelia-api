# test_runner/scenarios/order.py
"""Order scenarios — create with items, delivery, optional payment,
and the two post-create phases the router exposes (pay,
confirm-inventory) plus the combined finalize.

Mirrors `CartScenario`:

  * every order must carry at least one ordered item (the router
    rejects an empty order),
  * `payment_method` is a *query parameter* on create, not part of
    the body — so the scenario passes it through `params=`,
  * order creation defers payment and inventory deduction to the
    `/pay` and `/confirm-inventory` endpoints; a "paid" order
    therefore has to call `/pay` explicitly,
  * `/finalize` is a convenience that runs both — the scenario
    exercises that path too.

Profiles (cycled in order so a run of count=20 has a predictable mix):
  * clean      — created, never paid, never confirmed
  * paid       — created, then `/pay`
  * confirmed  — created, paid, then `/confirm-inventory`
  * finalized  — created, then `/finalize` (payment + confirm in one call)

Delivery payloads use `Delivery_Info_API`, not `Delivery_API`. The
order router takes a `delivery_info` field whose only required
member is `destination_address: Location_API`. Do NOT send a bare
`Delivery_API` shape — that produces a 422 (`destination_address`
missing). Two different models; two different helpers.
"""

import asyncio
import random
from typing import Any, Dict, List, Optional

from scenarios.base import BaseScenario
from context import TestUser
from data import (
    extract_id,
    generate_delivery_info_data,
    generate_ordered_item_data,
    
    generate_placed_order_data,
    short,
)


class OrderScenario(BaseScenario):
    name = "orders"

    # How the mix of created orders should break down. Cycled per
    # order so a run with count=20 produces a predictable spread.
    _PROFILES = ("clean", "paid", "confirmed", "finalized")

    # ══════════════════════════════════════════════════════════════
    # Create
    # ══════════════════════════════════════════════════════════════

    async def create_orders(
        self,
        user: TestUser,
        supplier_ids: List[int],
        *,
        count: int = 10,
        product_pool: Optional[List[int]] = None,
    ) -> int:
        """Create orders against a rotating set of suppliers.

        Each order is built from the profile cycle — clean, paid,
        confirmed, finalized — so a batch exercises every path.

        `product_pool` is the ids the scenario can draw from when
        building ordered items.
        """
        if not supplier_ids:
            return 0

        print(f"\n📦 Creating {count} orders for {user.username}...")

        headers = self.get_auth_headers(user)
        if not headers:
            print("   ❌ No auth token")
            return 0

        product_pool = product_pool or [1]

        created = 0

        for i in range(count):
            profile = self._PROFILES[i % len(self._PROFILES)]
            supplier_id = random.choice(supplier_ids)

            # `payment_method` is a query param on the router, so it
            # lives outside the JSON body.
            payment_method = self._payment_method_for(profile)

            # Every other order carries a `delivery_info` block, so
            # the coverage is predictable even on short runs. A 40%
            # random gate can give zero delivery-bearing orders on
            # a `--profile smoke` run with only a few orders.
            delivery = (
                generate_delivery_info_data()
                if i % 2 == 0
                else None
            )

            ordered_items, submitted_order = (
                self._build_order_payload(
                    profile=profile,
                    provider_id=supplier_id,
                    user_id=user.id,
                    product_pool=product_pool,
                )
            )

            body = {
                "ordered_items": ordered_items,
                "submitted_order": submitted_order,
                "delivery_info": delivery,
            }

            try:
                response = await self.client.post(
                    f"{self.base_url}/api/v1/business/orders",
                    json=body,
                    params={"payment_method": payment_method},
                    headers=headers,
                )
            except Exception as e:
                print(f"   ❌ Order {i + 1} error: {e}")
                await asyncio.sleep(0.05)
                continue

            if response.status_code in (200, 201):
                response_body = response.json()
                order_id = self._extract_order_id(response_body)
                if order_id > 0:
                    self.context.created_orders.append(order_id)
                    self.stats["orders"] = self.stats.get("orders", 0) + 1
                    self.context.order_profiles[order_id] = profile
                    created += 1

                    # Post-create phases per profile.
                    if profile in ("paid", "confirmed"):
                        await self._pay_order(
                            user, order_id, headers, payment_method,
                        )
                    if profile == "confirmed":
                        await self._confirm_inventory(
                            user, order_id, headers,
                        )
                    if profile == "finalized":
                        await self._finalize_order(
                            user, order_id, headers, payment_method,
                        )

                    if created % 5 == 0:
                        print(
                            f"   … {created}/{count} orders created"
                        )
                else:
                    print(
                        f"   ⚠️ Could not extract order id: "
                        f"{short(response.text, 200)}"
                    )
            elif response.status_code in (402, 429):
                print(
                    f"   ℹ️ Order limit reached: "
                    f"{response.status_code}"
                )
                break
            elif response.status_code == 409:
                # Insufficient stock — a legitimate domain outcome
                # that the seeded product pool should mostly avoid.
                # Record it but keep going; other orders may succeed.
                self._record_failure(
                    f"Order {i + 1}/{count} (409)", response,
                )
            else:
                self._record_failure(
                    f"Order {i + 1}/{count}", response,
                )

            await asyncio.sleep(0.05)

        print(f"✅ Created {created} orders")
        return created

    # ══════════════════════════════════════════════════════════════
    # Payload construction
    # ══════════════════════════════════════════════════════════════

    def _build_order_payload(
        self,
        *,
        profile: str,
        provider_id: int,
        user_id: int,
        product_pool: List[int],
    ):
        """Compose the body for `POST /business/orders`.

        Returns `(ordered_items, submitted_order)`.

        Note: unlike the cart payload, there is no `cart_payment` /
        `cart_paid_money` intent block on the order. Payment intent
        is expressed by the *existence* of a `/pay` call after
        creation, and the `payment_method` query param on create.

        The delivery is assembled by the caller, not here, because
        it varies per iteration (see `create_orders`). Passing it in
        would tangle the profile logic with the coverage strategy.
        """
        product_id = random.choice(product_pool)
        quantity = random.randint(1, 5)

        item = generate_ordered_item_data(product_id, quantity)

        submitted_order = generate_placed_order_data(
            ordering_user_id=user_id,
            provider_id=provider_id,
        )

        return [item], submitted_order

    @staticmethod
    def _payment_method_for(profile: str) -> str:
        """Which `payment_method` to send for this profile.

        The value only matters for profiles that actually pay —
        clean orders never call `/pay`, so the value is inert.
        """
        if profile in ("paid", "confirmed", "finalized"):
            return "wallet"
        return "cash"

    # ══════════════════════════════════════════════════════════════
    # Post-create phases
    # ══════════════════════════════════════════════════════════════

    async def _pay_order(
        self,
        user: TestUser,
        order_id: int,
        headers: Dict[str, str],
        payment_method: str,
    ) -> None:
        """Call `POST /business/orders/{order_id}/pay`."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/orders/"
                f"{order_id}/pay",
                params={"payment_method": payment_method},
                headers=headers,
            )
            if response.status_code in (200, 201):
                self.stats["order_payments"] = (
                    self.stats.get("order_payments", 0) + 1
                )
            else:
                print(
                    f"   ℹ️ Pay for order {order_id}: "
                    f"{response.status_code} {short(response.text, 100)}"
                )
        except Exception as e:
            print(f"   ❌ Pay for order {order_id}: {e}")

    async def _confirm_inventory(
        self,
        user: TestUser,
        order_id: int,
        headers: Dict[str, str],
    ) -> None:
        """Call `POST /business/orders/{order_id}/confirm-inventory`."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/orders/"
                f"{order_id}/confirm-inventory",
                headers=headers,
            )
            if response.status_code in (200, 201):
                self.stats["order_inventory_confirmations"] = (
                    self.stats.get(
                        "order_inventory_confirmations", 0
                    ) + 1
                )
            else:
                print(
                    f"   ℹ️ Confirm inventory for order {order_id}: "
                    f"{response.status_code} {short(response.text, 100)}"
                )
        except Exception as e:
            print(
                f"   ❌ Confirm inventory for order {order_id}: {e}"
            )

    async def _finalize_order(
        self,
        user: TestUser,
        order_id: int,
        headers: Dict[str, str],
        payment_method: str,
    ) -> None:
        """Call `POST /business/orders/{order_id}/finalize`.

        This is the combined payment + inventory-confirm path. The
        scenario exercises it separately from `pay` + `confirm-inventory`
        so a regression in either style surfaces.
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/orders/"
                f"{order_id}/finalize",
                params={"payment_method": payment_method},
                headers=headers,
            )
            if response.status_code in (200, 201):
                self.stats["order_finalizations"] = (
                    self.stats.get("order_finalizations", 0) + 1
                )
            else:
                print(
                    f"   ℹ️ Finalize order {order_id}: "
                    f"{response.status_code} {short(response.text, 100)}"
                )
        except Exception as e:
            print(f"   ❌ Finalize order {order_id}: {e}")

    # ══════════════════════════════════════════════════════════════
    # Reads
    # ══════════════════════════════════════════════════════════════

    async def read_order(
        self, user: TestUser, order_id: int,
        *, include_items: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Fetch an order by id."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/orders/{order_id}",
                params={"include_items": include_items},
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                f"Get order {order_id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Get order {order_id}: {e}")
            return None

    async def read_order_items(
        self, user: TestUser, order_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch the items of an order."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/orders/"
                f"{order_id}/items",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                f"Get order items {order_id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Get order items {order_id}: {e}")
            return None

    async def read_user_orders(
        self,
        user: TestUser,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a page of orders for a user."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/orders/"
                f"user/{user.id}",
                params={"offset": offset, "limit": limit},
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                f"Get orders for user {user.id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Get orders for user {user.id}: {e}")
            return None

    async def read_order_inventory_status(
        self, user: TestUser, order_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch the remote stock status for every item in an order."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/orders/"
                f"{order_id}/inventory-status",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                f"Get inventory status {order_id}", response,
            )
            return None
        except Exception as e:
            print(
                f"   ❌ Get inventory status {order_id}: {e}"
            )
            return None

    # ══════════════════════════════════════════════════════════════
    # Writes
    # ══════════════════════════════════════════════════════════════

    async def update_order(
        self,
        user: TestUser,
        order_id: int,
        *,
        updated_items: List[Dict[str, Any]],
        updated_order: Dict[str, Any],
    ) -> bool:
        """Call `PUT /business/orders/{order_id}`."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.put(
                f"{self.base_url}/api/v1/business/orders/{order_id}",
                json={
                    "updated_items": updated_items,
                    "updated_order": updated_order,
                },
                headers=headers,
            )
            if response.status_code == 200:
                return True
            self._record_failure(
                f"Update order {order_id}", response,
            )
            return False
        except Exception as e:
            print(f"   ❌ Update order {order_id}: {e}")
            return False

    async def update_order_status(
        self,
        user: TestUser,
        order_id: int,
        new_status: str,
    ) -> bool:
        """Update an order's status via `PATCH /orders/{id}/status`."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.patch(
                f"{self.base_url}/api/v1/business/orders/"
                f"{order_id}/status",
                params={"status": new_status},
                headers=headers,
            )
            if response.status_code == 200:
                return True
            print(
                f"   ℹ️ Status update order {order_id} → "
                f"{new_status}: {response.status_code} "
                f"{short(response.text, 100)}"
            )
            return False
        except Exception as e:
            print(
                f"   ❌ Status update order {order_id} → "
                f"{new_status}: {e}"
            )
            return False

    async def delete_order(
        self,
        user: TestUser,
        order_id: int,
        *,
        force: bool = False,
    ) -> bool:
        """Delete an order."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/business/orders/{order_id}",
                params={"force_delete": force},
                headers=headers,
            )
            if response.status_code in (200, 204):
                if order_id in self.context.created_orders:
                    self.context.created_orders.remove(order_id)
                return True
            self._record_failure(
                f"Delete order {order_id}", response,
            )
            return False
        except Exception as e:
            print(f"   ❌ Delete order {order_id}: {e}")
            return False

    # ══════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _extract_order_id(body: Any) -> int:
        """Pull the order id out of the create response.

        The order router returns `{"order": {...}, "payment_id": ...,
        ...}` — the id lives at `order.id_placed_order`. Try that
        path first, then fall back to the generic walker.
        """
        if isinstance(body, dict):
            order = body.get("order")
            if isinstance(order, dict):
                for key in ("id_placed_order", "id", "order_id"):
                    value = order.get(key)
                    if value is not None:
                        try:
                            return int(value)
                        except (ValueError, TypeError):
                            pass
        return extract_id(body)