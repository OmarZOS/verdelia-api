# test_runner/scenarios/suppliers.py
"""Supplier scenarios — create under an organisation."""

import asyncio
import random
from typing import List

from scenarios.base import BaseScenario
from context import TestUser
from data import (
    extract_id,
    generate_location_data,
    generate_supplier_data,
    short,
)


class SuppliersScenario(BaseScenario):
    name = "suppliers"

    async def create_suppliers(
        self,
        user: TestUser,
        org_ids: List[int],
        count_per_org: int = 3,
    ) -> List[int]:
        if not org_ids:
            return []
        print(f"\n🏥 Creating suppliers for {user.username}...")

        headers = self.get_auth_headers(user)
        if not headers:
            print("   ❌ No auth token")
            return []

        supplier_ids: List[int] = []
        total = len(org_ids) * count_per_org
        count = 0

        for org_id in org_ids:
            for i in range(count_per_org):
                with_naming = random.random() < 0.85
                sup_data = generate_supplier_data(
                    org_id, user.id, with_naming=with_naming,
                )
                loc_data = generate_location_data(extended=True)

                try:
                    response = await self.client.post(
                        f"{self.base_url}/api/v1/suppliers",
                        json={"provider": sup_data, "location": loc_data},
                        headers=headers,
                    )
                    if response.status_code in (200, 201):
                        sup_id = extract_id(response.json())
                        if sup_id > 0:
                            supplier_ids.append(sup_id)
                            self.context.created_suppliers.append(sup_id)
                            self.stats["suppliers"] = (
                                self.stats.get("suppliers", 0) + 1
                            )
                            count += 1
                            kind = (
                                "trilingual" if with_naming
                                else "flat-only"
                            )
                            print(
                                f"   ✅ Supplier {count}/{total} "
                                f"({kind}): {sup_id}"
                            )
                        else:
                            print(
                                f"   ⚠️ Could not extract supplier id: "
                                f"{short(response.text, 200)}"
                            )
                    elif response.status_code in (402, 429):
                        print(
                            f"   ℹ️ Supplier limit reached: "
                            f"{response.status_code}"
                        )
                        break
                    else:
                        self._record_failure(
                            f"Supplier {count + 1}/{total}", response
                        )
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                await asyncio.sleep(0.1)

        if supplier_ids:
            self.context.user_supplier_mapping[user.id] = supplier_ids

        print(f"✅ Created {len(supplier_ids)} suppliers")
        return supplier_ids