# test_runner/scenarios/users.py
"""User management scenarios — create, login, list."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from scenarios.base import BaseScenario
from context import TestUser
from data import (
    generate_location_data,
    generate_person_data,
    generate_user_data,
    extract_id,
    short,
)


class UsersScenario(BaseScenario):
    name = "users"

    async def create_user(
        self,
        user_type: Optional[str] = None,
        extended: bool = False,
    ) -> Optional[TestUser]:
        user_data = generate_user_data(user_type)
        person_data = generate_person_data(extended)
        location_data = generate_location_data(extended)

        payload = {
            "user": user_data,
            "person": person_data,
            "location": location_data,
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/app_user",
                json=payload,
            )
            if response.status_code in (200, 201):
                user_id = extract_id(response.json())
                if user_id > 0:
                    user = TestUser(
                        id=user_id,
                        username=user_data["app_user_name"],
                        email=user_data["app_user_email"],
                        password=user_data["app_user_password"],
                        user_data=user_data,
                        person_data=person_data,
                        location_data=location_data,
                    )
                    self._assign_roles(user)
                    self.context.user_roles[user_id] = user.roles
                    return user
                print(
                    f"   ⚠️ Could not extract user id from: "
                    f"{short(response.text, 200)}"
                )
            else:
                self._record_failure("Create user", response)
            return None
        except Exception as e:
            print(f"   ❌ Exception creating user: {e}")
            return None

    @staticmethod
    def _assign_roles(user: TestUser) -> None:
        t = user.user_data.get("app_user_type", "guest")
        role_map = {
            "provider": ["provider", "business_owner"],
            "customer": ["customer", "consumer"],
            "patient": ["patient"],
            "admin": ["admin", "super_user"],
            "guest": ["guest"],
        }
        user.roles = role_map.get(t, ["guest"])

    async def create_users(self, count: int = 10) -> List[TestUser]:
        print(f"\n👥 Creating {count} users...")
        created: List[TestUser] = []
        user_types = ["provider", "customer", "patient", "guest"]

        for i in range(count):
            user_type = user_types[i % len(user_types)]
            extended = i % 2 == 0
            print(
                f"  [{i + 1}/{count}] Creating {user_type} user"
                f"{' (extended)' if extended else ''}..."
            )
            user = await self.create_user(user_type, extended)
            if user:
                self.context.users.append(user)
                created.append(user)
                self.stats["users"] = self.stats.get("users", 0) + 1
                print(
                    f"   ✅ User {i + 1}: {user.username} "
                    f"(ID: {user.id}, Roles: {', '.join(user.roles)})"
                )
            else:
                print(f"   ❌ Failed to create user {i + 1}")
            await asyncio.sleep(0.1)

        print(f"\n✅ Created {len(created)}/{count} users")
        return created

    async def login_user(self, user: TestUser) -> bool:
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/authentication/token",
                json={
                    "app_user_name": user.username,
                    "app_user_password": user.password,
                },
            )
            if response.status_code == 200:
                result = response.json()
                token = result.get("access_token")
                if token:
                    user.access_token = token
                    user.refresh_token = result.get("refresh_token")
                    user.token_expires_at = (
                        datetime.now() + timedelta(hours=1)
                    )
                    return True
            return False
        except Exception:
            return False

    async def login_users(self) -> int:
        print("\n🔐 Logging in users...")
        success = 0
        for user in self.context.users:
            if await self.login_user(user):
                success += 1
                print(f"   ✅ {user.username}")
            else:
                print(f"   ❌ {user.username}")
        print(f"✅ Logged in {success}/{len(self.context.users)} users")
        return success