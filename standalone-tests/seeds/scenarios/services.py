# test_runner/scenarios/services.py
"""Service scenarios — create with requirements + staff reqs."""

import asyncio
import random
from typing import List

from scenarios.base import BaseScenario
from context import TestUser
from data import (
    extract_id,
    generate_service_request,
    short,
)


class ServicesScenario(BaseScenario):
    name = "services"

    async def create_services(
        self,
        user: TestUser,
        supplier_ids: List[int],
        count_per_supplier: int = 5,
    ) -> int:
        if not supplier_ids:
            return 0
        print(f"\n🛠️ Creating services for {user.username}...")

        headers = self.get_auth_headers(user)
        if not headers:
            print("   ❌ No auth token")
            return 0

        total = len(supplier_ids) * count_per_supplier
        count = 0

        for sup_id in supplier_ids:
            for i in range(count_per_supplier):
                payload = generate_service_request(
                    provider_id=sup_id,
                    category_id=random.choice([1, 2, 3, 4, 5]),
                    product_ids=self.context.created_products,
                )
                try:
                    response = await self.client.post(
                        f"{self.base_url}/api/v1/business/services",
                        json=payload,
                        headers=headers,
                    )
                    if response.status_code in (200, 201):
                        sid = extract_id(response.json())
                        if sid > 0:
                            self.context.created_services.append(sid)
                            self.stats["services"] = (
                                self.stats.get("services", 0) + 1
                            )
                            count += 1
                            if count % 25 == 0:
                                print(
                                    f"   … {count}/{total} created"
                                )
                        else:
                            print(
                                f"   ⚠️ Could not extract service id: "
                                f"{short(response.text, 200)}"
                            )
                    elif response.status_code in (402, 429):
                        print(
                            f"   ℹ️ Service limit reached for "
                            f"supplier {sup_id}: "
                            f"{response.status_code}"
                        )
                        break
                    else:
                        self._record_failure(
                            f"Service {count + 1}/{total}", response
                        )
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                await asyncio.sleep(0.05)

        print(f"✅ Created {count} services")
        return count

    async def validate_endpoint(
        self,
        user: TestUser,
        *,
        provider_id: int,
        category_id: int,
    ) -> None:
        """Exercise the endpoint's validation paths."""
        print(f"\n🔍 Validating service endpoint for {user.username}...")
        headers = self.get_auth_headers(user)
        if not headers:
            return

        # Invalid provider.
        payload = generate_service_request(
            provider_id=99999,
            category_id=category_id,
            product_ids=self.context.created_products or [1],
        )
        response = await self.client.post(
            f"{self.base_url}/api/v1/business/services",
            json=payload,
            headers=headers,
        )
        print(
            f"   invalid_provider → {response.status_code} "
            f"(expect 400/404/422)"
        )

        # Invalid category.
        payload = generate_service_request(
            provider_id=provider_id,
            category_id=99999,
            product_ids=self.context.created_products or [1],
        )
        response = await self.client.post(
            f"{self.base_url}/api/v1/business/services",
            json=payload,
            headers=headers,
        )
        print(
            f"   invalid_category → {response.status_code} "
            f"(expect 400/404/422)"
        )

        # Fetch non-existent service.
        response = await self.client.get(
            f"{self.base_url}/api/v1/business/services/999999",
            headers=headers,
        )
        print(
            f"   get_missing → {response.status_code} (expect 404)"
        )