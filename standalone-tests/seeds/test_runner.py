# test_runner/runner.py
"""The test runner itself — orchestration only.

Scenarios live in `test_runner/scenarios/`. This file owns the HTTP
client and the top-level sequence. Everything else is delegated.
"""

import httpx
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from context import VolumeProfile, TestContext, TestUser
from data import extract_id, short
from scenarios import (
    OrganisationsScenario,
    ProductsScenario,
    ServicesScenario,
    StaffScenario,
    UsageScenario,
    SubscriptionsScenario,
    SuppliersScenario,
    UsersScenario,
)


class TestRunner:
    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url
        self.client: Optional[httpx.AsyncClient] = None
        self.context = TestContext()
        self.stats: Dict[str, int] = {
            "users": 0,
            "organisations": 0,
            "suppliers": 0,
            "products": 0,
            "services": 0,
            "staff_rules": 0,
            "subscriptions": 0,
            "failures": 0,
        }

        # Scenarios are constructed in __aenter__ once the client
        # exists. Until then they're None.
        self.users: Optional[UsersScenario] = None
        self.organisations: Optional[OrganisationsScenario] = None
        self.suppliers: Optional[SuppliersScenario] = None
        self.products: Optional[ProductsScenario] = None
        self.services: Optional[ServicesScenario] = None
        self.staff: Optional[StaffScenario] = None
        self.subscriptions: Optional[SubscriptionsScenario] = None
        self.usage: Optional[UsageScenario] = None


    async def __aenter__(self):
        limits = httpx.Limits(
            max_keepalive_connections=20, max_connections=40,
        )
        timeout = httpx.Timeout(30.0, connect=5.0)
        self.client = httpx.AsyncClient(
            timeout=timeout, verify=False, limits=limits,
        )

        def _make(cls):
            return cls(
                client=self.client,
                context=self.context,
                stats=self.stats,
                base_url=self.base_url,
            )

        self.users = _make(UsersScenario)
        self.organisations = _make(OrganisationsScenario)
        self.suppliers = _make(SuppliersScenario)
        self.products = _make(ProductsScenario)
        self.services = _make(ServicesScenario)
        self.staff = _make(StaffScenario)
        self.subscriptions = _make(SubscriptionsScenario)
        self.usage = _make(UsageScenario)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    # ══════════════════════════════════════════════════════════════
    # Orchestration
    # ══════════════════════════════════════════════════════════════

    async def run(
        self,
        profile: VolumeProfile,
        skip_users: bool = False,
        skip_login: bool = False,
        skip_subscriptions: bool = False,
        skip_boundary: bool = False,
        context_file: str = "test_context.json",
    ) -> None:
        self._print_header(profile)

        if Path(context_file).exists() and not skip_users:
            self.context.load(context_file)

        if not skip_users and not self.context.users:
            await self.users.create_users(profile.users)
        else:
            print(
                f"\n📋 Using {len(self.context.users)} existing users"
            )

        if not self.context.users:
            print("\n❌ No users available.")
            return

        if not skip_login:
            await self.users.login_users()

        authenticated = [u for u in self.context.users if u.access_token]
        if not authenticated:
            print("\n⚠️ No authenticated users.")
            return

        primary = authenticated[0]
        print(
            f"\n👤 Primary user: {primary.username} "
            f"(ID: {primary.id})"
        )

        # ── Subscriptions ──────────────────────────────────────
        plans: List[Dict[str, Any]] = []
        tiered: Dict[int, TestUser] = {}

        if not skip_subscriptions:
            plans = await self.subscriptions.get_plans(primary)
            print(f"\n💳 Found {len(plans)} plans")

            if not plans:
                print(
                    "   ⚠️ No plans seeded. Run:\n"
                    "      python -m storage.seed --plans-only"
                )
            else:
                plan_ids = [
                    extract_id(p) for p in plans if extract_id(p) > 0
                ]
                await self.subscriptions.run_flow(primary, plan_ids)
                tiered = await self.subscriptions.setup_tiered_users(
                    self.users, plans,
                )

        # ── Boundary probes ────────────────────────────────────
        if not skip_boundary and tiered:
            print("\n" + "=" * 60)
            print("🔬 Metering boundary scenarios")
            print("=" * 60)
            for plan_id, u in tiered.items():
                await self.organisations.probe_user(plan_id, u)

        # ── Volume generation ──────────────────────────────────
        volume_user = self._pick_volume_user(primary, tiered)
        if volume_user.id != primary.id:
            print(
                f"\n📌 Using paid-tier user {volume_user.id} for "
                f"volume generation (primary is on Free)"
            )

        print("\n" + "=" * 60)
        print("🧪 Generating volume")
        print("=" * 60)

        orgs = await self.organisations.create_organisations(
            volume_user, count=profile.orgs_per_user,
        )
        suppliers = await self.suppliers.create_suppliers(
            volume_user, orgs,
            count_per_org=profile.suppliers_per_org,
        )
        await self.products.create_products(
            volume_user, suppliers,
            count_per_supplier=profile.products_per_supplier,
        )
        await self.services.create_services(
            volume_user, suppliers,
            count_per_supplier=profile.services_per_supplier,
        )

        if suppliers:
            await self.staff.create_staff_rules(
                volume_user, suppliers,
                authenticated[1:6],
                rules_per_supplier=profile.staff_rules_per_supplier,
            )

        for u in authenticated[1:6]:
            small_orgs = await self.organisations.create_organisations(
                u, count=1,
            )
            await self.suppliers.create_suppliers(
                u, small_orgs, count_per_org=2,
            )



        # ── Usage endpoint tests ───────────────────────────────
        print("\n" + "=" * 60)
        print("📊 Usage endpoint tests")
        print("=" * 60)

        # Test the volume user (has a paid plan and generated data).
        await self.usage.run_for_user(volume_user)

        # Test each tiered user. Each is on a different plan, so
        # the summary should reflect that plan's limits.
        for plan_id, tiered_user in tiered.items():
            await self.usage.run_for_user(tiered_user)

        # Empty state: a user with no subscription.
        no_sub_user = next(
            (u for u in authenticated if not u.access_token is None and
             u.id != volume_user.id and
             u.id not in {tu.id for tu in tiered.values()}),
            None,
        )
        if no_sub_user is not None:
            # The runner gave every tier user a subscription. Pick
            # a user the runner didn't touch.
            await self.usage.run_empty_state(no_sub_user)
            
            

        self.context.save(context_file)
        self.print_summary()

    # ══════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════

    def _pick_volume_user(
        self, primary: TestUser, tiered: Dict[int, TestUser],
    ) -> TestUser:
        """Prefer a paid-tier user for volume generation.

        The primary user can end up on Free (if the paid purchase
        failed, or if the free-link overwrote it). Free denies every
        metered resource, so volume generation produces nothing.
        """
        if not tiered:
            return primary
        for plan_id, u in tiered.items():
            if plan_id != 1:  # not Free
                return u
        return primary

    def _print_header(self, profile: VolumeProfile) -> None:
        print("\n" + "=" * 60)
        print(f"🚀 VERDELIA API TEST RUNNER — {profile.name.upper()}")
        print("=" * 60)
        print(f"📍 URL: {self.base_url}")
        print(f"🕐 Started: {datetime.now().strftime('%H:%M:%S')}")
        print(
            f"📊 Profile: users={profile.users} "
            f"orgs={profile.orgs_per_user} "
            f"suppliers={profile.suppliers_per_org} "
            f"products={profile.products_per_supplier} "
            f"services={profile.services_per_supplier}"
        )
        print("=" * 60)

    def print_summary(self) -> None:
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print("\n📈 Generated Data:")
        print(f"   👤 Users: {self.stats['users']}")
        print(
            f"   🔐 Authenticated: "
            f"{len([u for u in self.context.users if u.access_token])}"
        )
        print(f"   📋 Subscriptions: {self.stats['subscriptions']}")
        print(f"   🏢 Organisations: {self.stats['organisations']}")
        print(f"   🏥 Suppliers: {self.stats['suppliers']}")
        print(f"   📦 Products: {self.stats['products']}")
        print(f"   🛠️ Services: {self.stats['services']}")
        print(f"   👥 Staff Rules: {self.stats['staff_rules']}")
        print(f"   ❌ Failures: {self.stats['failures']}")

        print("\n📊 Distribution:")
        print(f"   Users with Orgs: {len(self.context.user_org_mapping)}")
        print(
            f"   Users with Suppliers: "
            f"{len(self.context.user_supplier_mapping)}"
        )
        print(
            f"   Users with Subscriptions: "
            f"{len(self.context.subscription_user_mapping)}"
        )
        if self.staff:
            print(
                f"   Staff Assignments: "
                f"{len(self.staff.used_assignments)}"
            )

        if self.context.user_roles:
            role_counts: Dict[str, int] = {}
            for roles in self.context.user_roles.values():
                for role in roles:
                    role_counts[role] = role_counts.get(role, 0) + 1
            print("\n👤 Role Distribution:")
            for role, count in sorted(
                role_counts.items(), key=lambda x: x[1], reverse=True,
            ):
                print(f"   {role}: {count}")

        print("\n" + "=" * 60)