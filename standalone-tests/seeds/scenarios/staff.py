# test_runner/scenarios/staff.py
"""Staff scenarios — create management rules."""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List

from scenarios.base import BaseScenario
from context import TestUser


class StaffScenario(BaseScenario):
    name = "staff"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._used_assignments: set[str] = set()

    async def create_staff_rules(
        self,
        owner: TestUser,
        supplier_ids: List[int],
        target_users: List[TestUser],
        rules_per_supplier: int = 2,
    ) -> int:
        if not supplier_ids or not target_users:
            return 0
        print("\n👥 Creating staff rules...")

        headers = self.get_auth_headers(owner)
        if not headers:
            print("   ❌ No auth token")
            return 0

        org_ids = self.context.user_org_mapping.get(owner.id, [])
        if not org_ids:
            print("   ⚠️ No organisation found")
            return 0

        rule_codes = [27, 45, 60, 12, 33, 78, 91, 56, 23, 67]
        statuses = ["ACTIVE", "PENDING", "REJECTED"]

        total = 0
        for supplier_id in supplier_ids:
            for target in target_users[:rules_per_supplier]:
                if supplier_id in self.context.user_supplier_mapping.get(
                    target.id, []
                ):
                    continue

                key = f"{target.id}_{supplier_id}"
                if key in self._used_assignments:
                    continue

                data = {
                    "rule_ref_org": org_ids[0],
                    "rule_ref_provider": supplier_id,
                    "rule_ref_user": target.id,
                    "management_rule_code": random.choice(rule_codes),
                    "management_rule_status": random.choice(statuses),
                    "management_rule_expiry": (
                        datetime.now()
                        + timedelta(days=random.randint(7, 90))
                    ).isoformat(),
                    "management_rule_notes": (
                        f"Staff rule for supplier {supplier_id}"
                    ),
                }

                try:
                    response = await self.client.post(
                        f"{self.base_url}/api/v1/staff",
                        json=data,
                        headers=headers,
                    )
                    if response.status_code == 201:
                        self.context.created_staff_rules.append(1)
                        self._used_assignments.add(key)
                        self.stats["staff_rules"] = (
                            self.stats.get("staff_rules", 0) + 1
                        )
                        total += 1
                        print(
                            f"   ✅ Rule: User {target.id} → "
                            f"Supplier {supplier_id}"
                        )
                    elif response.status_code in (402, 429):
                        print(
                            f"   ℹ️ Team-member limit reached: "
                            f"{response.status_code}"
                        )
                        break
                    else:
                        self._record_failure(
                            f"Rule user {target.id} → "
                            f"supplier {supplier_id}",
                            response,
                        )
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                await asyncio.sleep(0.1)

        print(f"✅ Created {total} staff rules")
        return total

    @property
    def used_assignments(self) -> set[str]:
        return self._used_assignments