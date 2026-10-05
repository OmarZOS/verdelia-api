# test_runner/scenarios/products.py
"""Product scenarios — create with image + iproduct payload."""

import asyncio
from typing import List

from scenarios.base import BaseScenario
from context import TestUser
from data import (
    extract_id,
    generate_iproduct_data,
    generate_product_data,
    generate_product_image_data,
    short,
)


class ProductsScenario(BaseScenario):
    name = "products"

    async def create_products(
        self,
        user: TestUser,
        supplier_ids: List[int],
        count_per_supplier: int = 5,
    ) -> int:
        if not supplier_ids:
            return 0
        print(f"\n📦 Creating products for {user.username}...")

        headers = self.get_auth_headers(user)
        if not headers:
            print("   ❌ No auth token")
            return 0

        total = len(supplier_ids) * count_per_supplier
        count = 0

        for sup_id in supplier_ids:
            for i in range(count_per_supplier):
                prod_data = generate_product_data(sup_id, user.id)
                img_data = generate_product_image_data()
                iprod_data = generate_iproduct_data()
                try:
                    response = await self.client.post(
                        f"{self.base_url}/api/v1/products",
                        json={
                            "product": prod_data,
                            "image": img_data,
                            "iproduct": iprod_data,
                        },
                        headers=headers,
                    )
                    if response.status_code in (200, 201):
                        prod_id = extract_id(response.json())
                        if prod_id > 0:
                            self.context.created_products.append(prod_id)
                            self.stats["products"] = (
                                self.stats.get("products", 0) + 1
                            )
                            count += 1
                            if count % 25 == 0:
                                print(
                                    f"   … {count}/{total} created"
                                )
                        else:
                            print(
                                f"   ⚠️ Could not extract product id: "
                                f"{short(response.text, 200)}"
                            )
                    elif response.status_code in (402, 429):
                        print(
                            f"   ℹ️ Product limit reached for "
                            f"supplier {sup_id}: "
                            f"{response.status_code}"
                        )
                        break
                    else:
                        self._record_failure(
                            f"Product {count + 1}/{total}", response
                        )
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                await asyncio.sleep(0.05)

        print(f"✅ Created {count} products")
        return count