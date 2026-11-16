# test_runner/scenarios/cart.py
"""Cart scenarios — create with items, services, delivery, and
optional payment.

Mirrors `ProductsScenario`: loops over a target count, records ids,
tracks stats, honors metering denials. Cart-specific work:

  * every cart must carry at least one ordered item or service
    (the endpoint rejects an empty cart),
  * the `cart` payload can declare a payment intent — `cart_payment`
    or `cart_deposit` plus a nonzero `cart_paid_money` and a
    `cart_payment_method`,
  * after creation, a cart can be paid and finalized in two extra
    calls.

The scenario exercises all three: clean carts, paid carts, and
finalized carts.

Address handling
----------------
The runner does not create addresses. The server's cart workflow
does it, by resolving the `delivery.destination_address` payload
through `LocationService.create_address_from_location`. The cart
create response should carry the resulting `delivery` row with a
populated `address_id`; that id is what the delivery scenario needs
for `has_recipient` to pass.

If the response does not carry an address id, the runner logs a
warning rather than inventing one — a delivery with no address can
never leave `pending`, and that failure should be visible in one
line, not as a 409 six steps later.
"""

import asyncio
import random
from typing import Any, Dict, List, Optional

from scenarios.base import BaseScenario
from context import TestUser
from data import (
    extract_id,
    generate_delivery_data,
    generate_ordered_item_data,
    generate_ordered_service_data,
    generate_person_data,
    generate_cart_data,
    short,
)


class CartScenario(BaseScenario):

    name = "carts"

    # How the mix of created carts should break down. The scenario
    # picks one of these per cart, in order, so a run with count=20
    # produces a predictable mix.
    _PROFILES = ("clean", "paid", "deposit", "finalized")

    async def create_carts(
        self,
        user: TestUser,
        supplier_ids: List[int],
        *,
        count: int = 10,
        product_pool: Optional[List[int]] = None,
        service_pool: Optional[List[int]] = None,
    ) -> int:
        if not supplier_ids:
            return 0

        print(f"\n🛒 Creating {count} carts for {user.username}...")

        headers = self.get_auth_headers(user)
        if not headers:
            print("   ❌ No auth token")
            return 0

        product_pool = product_pool or [1]
        service_pool = service_pool or [1]

        created = 0
        delivery_attempts = 0
        delivery_addresses_recorded = 0

        for i in range(count):
            profile = self._PROFILES[i % len(self._PROFILES)]
            supplier_id = random.choice(supplier_ids)

            # Decide whether this cart carries a delivery. If so,
            # build the delivery payload with a location sub-object
            # the server can turn into an address. The runner never
            # creates the address itself.
            delivery_payload: Optional[Dict[str, Any]] = None
            if random.random() < 0.4:
                delivery_attempts += 1
                delivery_payload = generate_delivery_data(
                    provider_id=supplier_id,
                )

            payload = self._build_cart_payload(
                profile=profile,
                provider_id=supplier_id,
                seller_user_id=user.id,
                buyer_user_id=user.id,
                product_pool=product_pool,
                service_pool=service_pool,
                delivery_payload=delivery_payload,
            )

            try:
                response = await self.client.post(
                    f"{self.base_url}/api/v1/business/carts",
                    json=payload,
                    headers=headers,
                )
            except Exception as e:
                print(f"   ❌ Cart {i + 1} error: {e}")
                await asyncio.sleep(0.05)
                continue

            if response.status_code in (200, 201):
                body = response.json()
                cart_id = self._extract_cart_id(body)
                if cart_id > 0:
                    self.context.created_carts.append(cart_id)
                    self.stats["carts"] = self.stats.get("carts", 0) + 1
                    created += 1

                    self.context.cart_profiles[cart_id] = profile

                    # ── Record the delivery + its address if present.
                    # The cart response is the *only* reliable source
                    # of address ids; the runner never creates
                    # addresses itself.
                    if delivery_payload is not None:
                        if self._record_delivery_from_response(body):
                            delivery_addresses_recorded += 1

                    if profile in ("paid", "finalized"):
                        await self._pay_cart(user, cart_id, headers)
                    if profile == "finalized":
                        await self._confirm_inventory(
                            user, cart_id, headers,
                        )

                    if created % 5 == 0:
                        print(f"   … {created}/{count} carts created")
                else:
                    print(
                        f"   ⚠️ Could not extract cart id: "
                        f"{short(response.text, 200)}"
                    )
            elif response.status_code in (402, 429):
                print(
                    f"   ℹ️ Cart limit reached: {response.status_code}"
                )
                break
            else:
                self._record_failure(
                    f"Cart {i + 1}/{count}", response,
                )

            await asyncio.sleep(0.05)

        # One-line summary that makes the address situation visible
        # without requiring a second run to diagnose.
        if delivery_attempts > 0:
            if delivery_addresses_recorded == 0:
                print(
                    "   ⚠️ None of the cart responses carried a "
                    "delivery address id. Deliveries created this "
                    "run cannot leave `pending` (has_recipient will "
                    "refuse). Check that the cart workflow resolves "
                    "`delivery.destination_address` into an address "
                    "and echoes `delivery.address_id` in the "
                    "response."
                )
            elif delivery_addresses_recorded < delivery_attempts:
                print(
                    f"   ℹ️ {delivery_addresses_recorded}/"
                    f"{delivery_attempts} carts with delivery "
                    f"returned a resolvable address"
                )

        print(f"✅ Created {created} carts")
        return created

    # ══════════════════════════════════════════════════════════════
    # Payload construction
    # ══════════════════════════════════════════════════════════════

    def _build_cart_payload(
        self,
        *,
        profile: str,
        provider_id: int,
        seller_user_id: int,
        buyer_user_id: int,
        product_pool: List[int],
        service_pool: List[int],
        delivery_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compose the body for `POST /business/carts` for one profile.

        Profiles:
          * clean      — no payment intent; paid_money = 0
          * paid       — cart_payment = true, paid_money > 0,
                         method = "wallet"
          * deposit    — cart_deposit = true, paid_money < total,
                         method = "wallet"
          * finalized  — same as paid, and the scenario also calls
                         `confirm-inventory` after creation
        """
        product_id = random.choice(product_pool)
        quantity = random.randint(1, 5)

        item = generate_ordered_item_data(product_id, quantity)
        services = []
        if profile in ("paid", "finalized") and random.random() < 0.5:
            services.append(
                generate_ordered_service_data(
                    random.choice(service_pool), quantity=1,
                )
            )

        total = self._estimate_total(item, services)

        cart_data = generate_cart_data(
            status="open",
            total_amount=total,
        )

        if profile == "clean":
            pass
        elif profile == "paid":
            cart_data["cart_payment"] = True
            cart_data["cart_paid_money"] = total
            cart_data["cart_payment_method"] = "wallet"
        elif profile == "deposit":
            deposit = round(total * 0.3, 2)
            cart_data["cart_deposit"] = True
            cart_data["cart_paid_money"] = deposit
            cart_data["cart_payment_method"] = "wallet"
        elif profile == "finalized":
            cart_data["cart_payment"] = True
            cart_data["cart_paid_money"] = total
            cart_data["cart_payment_method"] = "wallet"

        payload: Dict[str, Any] = {
            "provider_id": provider_id,
            "seller_user_id": seller_user_id,
            "buyer_user_id": buyer_user_id,
            "cart": cart_data,
            "ordered_items": [item],
            "ordered_services": services,
        }

        # Some carts carry a client (the person the delivery is for)
        # to exercise the person-attach path.
        if random.random() < 0.3:
            payload["client"] = generate_person_data(extended=False)

        # Use the pre-built delivery payload when supplied. The
        # payload carries a `destination_address` location sub-object
        # that the server's cart workflow resolves into a real
        # `address_id` on the delivery row.
        if delivery_payload is not None:
            payload["delivery"] = delivery_payload

        return payload

    # ══════════════════════════════════════════════════════════════
    # Response extraction — the only source of address ids
    # ══════════════════════════════════════════════════════════════

    def _record_delivery_from_response(self, body: Any) -> bool:
        """Extract the delivery from a cart-create response and record
        its id + address id in the context.

        Returns True if an address id was recorded — the caller uses
        this to distinguish "server resolved the address" from
        "server returned a delivery with no address".

        Handles the common envelope shapes:
          * {"data": {"delivery": {...}}}
          * {"delivery": {...}}
          * {"data": {"cart": {"delivery": {...}}}}
        """
        delivery = self._find_delivery(body)
        if delivery is None:
            return False

        delivery_id = self._extract_delivery_id_from_row(delivery)
        if delivery_id > 0 and delivery_id not in self.context.created_deliveries:
            self.context.created_deliveries.append(delivery_id)

        address_id = self._extract_address_id_from_row(delivery)
        if address_id is not None and address_id > 0:
            if address_id not in self.context.created_addresses:
                self.context.created_addresses.append(address_id)
            return True

        # Delivery exists but has no address — log once per
        # occurrence so a broken server-side resolution is visible.
        print(
            f"   ⚠️ delivery {delivery_id or '?'} from cart "
            f"response has no address_id — has_recipient will "
            f"refuse `pending → processing` for this delivery"
        )
        return False

    @staticmethod
    def _find_delivery(body: Any) -> Optional[Dict[str, Any]]:
        """Locate the delivery dict inside a cart-create response."""
        if not isinstance(body, dict):
            return None

        # Try top level, then `data`, then `data.cart`.
        candidates: List[Any] = [
            body.get("delivery"),
            (body.get("data") or {}).get("delivery")
            if isinstance(body.get("data"), dict) else None,
            ((body.get("data") or {}).get("cart") or {}).get("delivery")
            if isinstance(body.get("data"), dict)
            and isinstance(body.get("data", {}).get("cart"), dict)
            else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, dict):
                return candidate
        return None

    @staticmethod
    def _extract_delivery_id_from_row(
        delivery: Dict[str, Any],
    ) -> int:
        for key in ("id_delivery", "delivery_id", "id"):
            value = delivery.get(key)
            if value:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    continue
        return 0

    @staticmethod
    def _extract_address_id_from_row(
        delivery: Dict[str, Any],
    ) -> Optional[int]:
        for key in (
            "address_id",
            "delivery_address_id",
            "delivery_address",
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
    def _estimate_total(
        item: Dict[str, Any],
        services: List[Dict[str, Any]],
    ) -> float:
        """Rough total for the client-side payload.

        The server recomputes the real total from the product and
        service tables. This figure only feeds the `cart_payment` /
        `cart_deposit` intent — the amount the client *intends* to
        pay now.
        """
        unit = float(item.get("unit_price", 0) or 0)
        qty = int(item.get("ordered_quantity", 1) or 1)
        total = unit * qty
        for s in services:
            total += float(
                s.get("ordered_service_total_price", 0) or 0
            )
        return round(total, 2)

    # ══════════════════════════════════════════════════════════════
    # Post-create phases
    # ══════════════════════════════════════════════════════════════

    async def _pay_cart(
        self,
        user: TestUser,
        cart_id: int,
        headers: Dict[str, str],
    ) -> None:
        """Call `POST /business/carts/{cart_id}/pay`."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/carts/{cart_id}/pay",
                params={"payment_method": "wallet"},
                headers=headers,
            )
            if response.status_code in (200, 201):
                self.stats["cart_payments"] = (
                    self.stats.get("cart_payments", 0) + 1
                )
            else:
                print(
                    f"   ℹ️ Pay for cart {cart_id}: "
                    f"{response.status_code} {short(response.text, 100)}"
                )
        except Exception as e:
            print(f"   ❌ Pay for cart {cart_id}: {e}")

    async def _confirm_inventory(
        self,
        user: TestUser,
        cart_id: int,
        headers: Dict[str, str],
    ) -> None:
        """Call `POST /business/carts/{cart_id}/confirm-inventory`."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/business/carts/"
                f"{cart_id}/confirm-inventory",
                headers=headers,
            )
            if response.status_code in (200, 201):
                self.stats["cart_inventory_confirmations"] = (
                    self.stats.get("cart_inventory_confirmations", 0) + 1
                )
            else:
                print(
                    f"   ℹ️ Confirm inventory for cart {cart_id}: "
                    f"{response.status_code} {short(response.text, 100)}"
                )
        except Exception as e:
            print(
                f"   ❌ Confirm inventory for cart {cart_id}: {e}"
            )

    # ══════════════════════════════════════════════════════════════
    # Reads
    # ══════════════════════════════════════════════════════════════

    async def read_cart(
        self, user: TestUser, cart_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a cart by id."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/carts/{cart_id}",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                f"Get cart {cart_id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Get cart {cart_id}: {e}")
            return None

    async def read_cart_summary(
        self, user: TestUser, cart_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Fetch the summary of a cart — totals and counts."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/business/carts/{cart_id}/summary",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                f"Get cart summary {cart_id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Get cart summary {cart_id}: {e}")
            return None

    async def update_cart_status(
        self,
        user: TestUser,
        cart_id: int,
        new_status: str,
    ) -> bool:
        """Update a cart's status via the policy-gated endpoint."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.patch(
                f"{self.base_url}/api/v1/business/carts/{cart_id}/status",
                params={"status": new_status},
                headers=headers,
            )
            if response.status_code == 200:
                return True
            print(
                f"   ℹ️ Status update cart {cart_id} → "
                f"{new_status}: {response.status_code} "
                f"{short(response.text, 100)}"
            )
            return False
        except Exception as e:
            print(
                f"   ❌ Status update cart {cart_id} → "
                f"{new_status}: {e}"
            )
            return False

    async def delete_cart(
        self,
        user: TestUser,
        cart_id: int,
        *,
        force: bool = False,
    ) -> bool:
        """Delete a cart."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/business/carts/{cart_id}",
                params={"force_delete": force},
                headers=headers,
            )
            if response.status_code in (200, 204):
                if cart_id in self.context.created_carts:
                    self.context.created_carts.remove(cart_id)
                return True
            self._record_failure(
                f"Delete cart {cart_id}", response,
            )
            return False
        except Exception as e:
            print(f"   ❌ Delete cart {cart_id}: {e}")
            return False

    # ══════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _extract_cart_id(body: Any) -> int:
        """Pull the cart id out of the create response.

        The endpoint wraps the id in `data.cart_id`, so the generic
        `extract_id` (which walks known wrapper keys) may miss it.
        Try the known path first, then fall back.
        """
        if isinstance(body, dict):
            data = body.get("data")
            if isinstance(data, dict):
                cart_id = data.get("cart_id")
                if cart_id is not None:
                    try:
                        return int(cart_id)
                    except (ValueError, TypeError):
                        pass
        return extract_id(body)