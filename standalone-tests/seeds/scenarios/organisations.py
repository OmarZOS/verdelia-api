# test_runner/scenarios/organisations.py
"""Organisation scenarios — create, list, probe limit."""

import asyncio
import random
from typing import Any, Dict, List

from scenarios.base import BaseScenario
from context import TestUser
from data import extract_id, generate_organisation_data, short


class OrganisationsScenario(BaseScenario):
    name = "organisations"

    async def create_organisations(
        self, user: TestUser, count: int = 3,
    ) -> List[int]:
        print(
            f"\n🏢 Creating {count} organisations for {user.username}..."
        )
        headers = self.get_auth_headers(user)
        if not headers:
            print("   ❌ No auth token")
            return []

        org_ids: List[int] = []
        for i in range(count):
            with_naming = random.random() < 0.85
            data = generate_organisation_data(with_naming=with_naming)

            try:
                response = await self.client.post(
                    f"{self.base_url}/api/v1/organisations",
                    json={"organisation": data},
                    headers=headers,
                )
                if response.status_code in (200, 201):
                    org_id = extract_id(response.json())
                    if org_id > 0:
                        org_ids.append(org_id)
                        self.context.created_organisations.append(org_id)
                        self.stats["organisations"] = (
                            self.stats.get("organisations", 0) + 1
                        )
                        kind = (
                            "trilingual" if with_naming else "flat-only"
                        )
                        print(
                            f"   ✅ Organisation {i + 1} "
                            f"({kind}): {org_id}"
                        )
                    else:
                        print(
                            f"   ⚠️ Could not extract org id: "
                            f"{short(response.text, 200)}"
                        )
                elif response.status_code in (402, 429):
                    print(
                        f"   ℹ️ Organisation limit reached: "
                        f"{response.status_code}"
                    )
                    break
                else:
                    self._record_failure(
                        f"Organisation {i + 1}", response
                    )
            except Exception as e:
                print(f"   ❌ Error: {e}")
            await asyncio.sleep(0.1)

        if org_ids:
            self.context.user_org_mapping[user.id] = org_ids

        print(f"✅ Created {len(org_ids)} organisations")
        return org_ids

    async def probe_user(
        self, plan_id: int, user: TestUser,
    ) -> Dict[str, Any]:
        """Probe the organisation limit for one tiered user."""
        headers = self.get_auth_headers(user)
        if not headers:
            return {}

        async def _create(h: Dict[str, str] = headers):
            data = generate_organisation_data()
            return await self.client.post(
                f"{self.base_url}/api/v1/organisations",
                json={"organisation": data},
                headers=h,
            )

        return await self.probe_limit_boundary(
            user,
            f"organisations (plan {plan_id})",
            _create,
            max_attempts=20,
        )