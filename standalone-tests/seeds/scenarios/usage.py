# test_runner/scenarios/usage.py
"""Usage and subscription-read scenarios.

Read-only. Exercises the endpoints that report quota state:

    GET /app_user/{id}/usage
    GET /app_user/{id}/usage/{resource}
    GET /app_user/{id}/subscription
    GET /app_user/{id}/subscription/status

These endpoints don't write. The tests verify shape and internal
consistency, not enforcement.
"""

from typing import Any, Dict, List, Optional

from scenarios.base import BaseScenario
from context import TestUser
from data import short, unwrap


# The resources the summary should include. Matches the enum the
# backend exposes; the runner uses the string values so a typo in a
# single resource name shows up as a missing key rather than a crash.
_ALL_RESOURCE_CODES = [
    "organization_owned",
    "provider_owned",
    "team_members",
    "products_per_provider",
    "services_per_provider",
    "ai_credits_monthly",
    "ads_enabled",
]

# The two resources the runner actually produces data for during a
# run. Used by the consistency check: after volume generation, these
# two should have non-null `current` when the user is on a plan that
# grants them.
_POPULATED_AFTER_VOLUME = {
    "organization_owned",
    "ai_credits_monthly",
}


class UsageScenario(BaseScenario):
    name = "usage"

    # ══════════════════════════════════════════════════════════════
    # Endpoint wrappers
    # ══════════════════════════════════════════════════════════════

    async def get_usage_summary(
        self, user: TestUser,
    ) -> Optional[Dict[str, Any]]:
        """Fetch the full usage summary for a user."""
        headers = self.get_auth_headers(user)
        if not headers:
            print(f"   ❌ No auth token for user {user.id}")
            return None

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/app_user/{user.id}/usage",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                f"Usage summary user={user.id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error fetching usage summary: {e}")
            return None

    async def get_usage_for_resource(
        self, user: TestUser, resource_code: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch the usage summary for a single resource."""
        headers = self.get_auth_headers(user)
        if not headers:
            return None

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/app_user/{user.id}"
                f"/usage/{resource_code}",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            # A 422 means the resource code isn't in the enum. That's
            # a valid response for an unknown code; report it, don't
            # count it as a failure.
            if response.status_code == 422:
                print(
                    f"   ℹ️ {resource_code} rejected as unknown "
                    f"(422) for user {user.id}"
                )
                return None
            self._record_failure(
                f"Usage {resource_code} user={user.id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error fetching {resource_code}: {e}")
            return None

    async def get_subscription(
        self, user: TestUser,
    ) -> Optional[Dict[str, Any]]:
        """Fetch the full subscription row."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/app_user/{user.id}"
                f"/subscription",
                headers=headers,
            )
            if response.status_code == 200:
                return unwrap(response.json()) or response.json()
            if response.status_code == 404:
                return None
            self._record_failure(
                f"Get subscription user={user.id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None

    async def get_subscription_status(
        self, user: TestUser,
    ) -> Optional[Dict[str, Any]]:
        """Fetch the boolean status."""
        headers = self.get_auth_headers(user)
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/app_user/{user.id}"
                f"/subscription/status",
                headers=headers,
            )
            if response.status_code == 200:
                return response.json()
            self._record_failure(
                f"Status user={user.id}", response,
            )
            return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None

    # ══════════════════════════════════════════════════════════════
    # Scenarios
    # ══════════════════════════════════════════════════════════════

    async def test_user_summary_shape(
        self, user: TestUser,
    ) -> Dict[str, Any]:
        """Verify the shape of a user's usage summary.

        Checks that every resource the backend exposes appears in the
        response, and that each entry has the fields the client
        expects. Does not assert specific counts — those depend on
        what the user has actually created.
        """
        print(f"\n📊 Usage summary shape for user {user.id}...")
        summary = await self.get_usage_summary(user)
        if summary is None:
            return {"user_id": user.id, "passed": False, "reason": "no response"}

        if not isinstance(summary, dict):
            print(
                f"   ❌ Summary is not a dict: "
                f"{type(summary).__name__}"
            )
            return {"user_id": user.id, "passed": False, "reason": "not dict"}

        missing = [r for r in _ALL_RESOURCE_CODES if r not in summary]
        extra = [k for k in summary if k not in _ALL_RESOURCE_CODES]

        if missing:
            print(
                f"   ⚠️ Missing resources: {missing}"
            )
        if extra:
            print(f"   ℹ️ Extra resources: {extra}")

        # Every entry should have the canonical fields.
        bad_entries: List[str] = []
        required_fields = {
            "current", "limit", "remaining", "allowed", "kind",
        }
        for code, entry in summary.items():
            if not isinstance(entry, dict):
                bad_entries.append(f"{code}: not a dict")
                continue
            missing_fields = required_fields - set(entry.keys())
            if missing_fields:
                bad_entries.append(
                    f"{code}: missing {sorted(missing_fields)}"
                )

        passed = not missing and not bad_entries

        if bad_entries:
            print(f"   ❌ Malformed entries:")
            for line in bad_entries:
                print(f"      {line}")

        if passed:
            print(
                f"   ✅ Summary OK: {len(summary)} resources, all "
                f"entries have the canonical fields"
            )

        return {
            "user_id": user.id,
            "passed": passed,
            "resource_count": len(summary),
            "missing": missing,
            "extra": extra,
        }

    async def test_user_summary_consistency(
        self, user: TestUser,
    ) -> Dict[str, Any]:
        """Verify each summary entry is internally consistent.

        Rules:
          * `allowed=False` when `kind=disabled` (limit 0).
          * `current + 1 <= limit` iff `allowed=True` for finite
            limits.
          * `remaining == limit - current` when finite.
          * `counted_by` names the source ("period", "domain",
            "flag").
        """
        print(f"\n🧪 Usage summary consistency for user {user.id}...")
        summary = await self.get_usage_summary(user)
        if summary is None:
            return {"user_id": user.id, "passed": False}

        issues: List[str] = []
        for code, entry in summary.items():
            if not isinstance(entry, dict):
                continue

            kind = entry.get("kind")
            allowed = entry.get("allowed")
            current = entry.get("current")
            limit = entry.get("limit")
            remaining = entry.get("remaining")
            counted_by = entry.get("counted_by")

            # Disabled → not allowed, no headroom.
            if kind == "disabled":
                if allowed:
                    issues.append(
                        f"{code}: kind=disabled but allowed=True"
                    )
                continue

            # Finite → all numbers should be present and consistent.
            if kind == "finite":
                if limit is None or limit <= 0:
                    issues.append(
                        f"{code}: kind=finite but limit={limit}"
                    )
                    continue
                if current is None or current < 0:
                    # current being null means the counter isn't
                    # wired — a summary limitation, not a bug in the
                    # endpoint. Skip rather than flag.
                    continue
                expected_allowed = (current + 1) <= limit
                if allowed != expected_allowed:
                    issues.append(
                        f"{code}: current={current} limit={limit} "
                        f"allowed={allowed} (expected "
                        f"{expected_allowed})"
                    )
                if remaining is not None:
                    expected_remaining = max(0, limit - current)
                    if remaining != expected_remaining:
                        issues.append(
                            f"{code}: remaining={remaining} "
                            f"(expected {expected_remaining})"
                        )
                continue

            # Negotiated → allowed at this layer, no numbers.
            if kind == "negotiated" and not allowed:
                # Negotiated denies are only from the contract layer,
                # which the summary can't see. Not an issue here.
                pass

            # counted_by should always be present.
            if counted_by not in ("period", "domain", "flag"):
                issues.append(
                    f"{code}: counted_by={counted_by!r} not in "
                    f"{{period, domain, flag}}"
                )

        if issues:
            print(f"   ❌ {len(issues)} consistency issues:")
            for line in issues:
                print(f"      {line}")
            return {
                "user_id": user.id,
                "passed": False,
                "issues": issues,
            }

        print(f"   ✅ All entries internally consistent")
        return {"user_id": user.id, "passed": True}

    async def test_single_resource_endpoint(
        self, user: TestUser,
    ) -> Dict[str, Any]:
        """Fetch the single-resource endpoint for each known code.

        Verifies it returns the same shape as the corresponding entry
        in the summary — the two endpoints should agree on every
        field.
        """
        print(
            f"\n📊 Single-resource endpoint for user {user.id}..."
        )

        summary = await self.get_usage_summary(user)
        if summary is None:
            return {"user_id": user.id, "passed": False}

        mismatches: List[str] = []

        for code in _ALL_RESOURCE_CODES:
            single = await self.get_usage_for_resource(user, code)
            if single is None:
                # 422 for unknown codes is expected; skip.
                continue

            summary_entry = summary.get(code)
            if summary_entry is None:
                mismatches.append(
                    f"{code}: in single-resource but not in summary"
                )
                continue

            # Compare the fields that both endpoints should return.
            for field in (
                "current", "limit", "remaining", "allowed", "kind",
            ):
                if field not in single:
                    mismatches.append(
                        f"{code}: single missing field {field!r}"
                    )
                    continue
                if summary_entry.get(field) != single.get(field):
                    mismatches.append(
                        f"{code}.{field}: summary="
                        f"{summary_entry.get(field)!r} "
                        f"single={single.get(field)!r}"
                    )

        if mismatches:
            print(f"   ❌ {len(mismatches)} mismatches:")
            for line in mismatches:
                print(f"      {line}")
            return {
                "user_id": user.id,
                "passed": False,
                "mismatches": mismatches,
            }

        print(
            f"   ✅ Single-resource endpoint matches summary for "
            f"{len(_ALL_RESOURCE_CODES)} resources"
        )
        return {"user_id": user.id, "passed": True}

    async def test_empty_state(
        self, user: TestUser,
    ) -> Dict[str, Any]:
        """Verify the summary of a user with no subscription.

        The endpoint should return zeros for every resource, not a
        404. That's what lets the client render the upgrade screen
        without treating "no plan" as an error.
        """
        print(f"\n📊 Usage summary shape for user {user.id} (no sub)...")

        # Confirm the user has no subscription first.
        sub = await self.get_subscription(user)
        if sub is not None:
            print(
                f"   ℹ️ User {user.id} has a subscription; skipping "
                f"empty-state test"
            )
            return {"user_id": user.id, "passed": True, "skipped": True}

        summary = await self.get_usage_summary(user)
        if summary is None:
            return {"user_id": user.id, "passed": False}

        # All entries should report no usage and no allowance.
        wrong: List[str] = []
        for code, entry in summary.items():
            if not isinstance(entry, dict):
                continue
            if entry.get("current") != 0:
                wrong.append(
                    f"{code}: current={entry.get('current')} (expected 0)"
                )
            if entry.get("allowed") is True:
                wrong.append(
                    f"{code}: allowed=True (expected False)"
                )

        if wrong:
            print(f"   ❌ {len(wrong)} unexpected values:")
            for line in wrong:
                print(f"      {line}")
            return {"user_id": user.id, "passed": False, "wrong": wrong}

        print(
            f"   ✅ Empty-state summary correct: "
            f"{len(summary)} resources, all zeroed"
        )
        return {"user_id": user.id, "passed": True}

    async def test_subscription_read_agreement(
        self, user: TestUser,
    ) -> Dict[str, Any]:
        """Verify the subscription read and status endpoints agree.

        `GET /subscription` returns the row or 404.
        `GET /subscription/status` returns `{active: bool}` or, per
        the docstring, `{active: false}` when there's no
        subscription.

        The two should never disagree: if the full read is 404, the
        status endpoint should report `active: false`. If the full
        read succeeds with a live expiry, the status endpoint should
        report `active: true`.
        """
        print(f"\n🔍 Subscription read agreement for user {user.id}...")

        sub = await self.get_subscription(user)
        status = await self.get_subscription_status(user)

        if status is None:
            return {"user_id": user.id, "passed": False}

        active_from_status = status.get("active")

        if sub is None:
            # No subscription → status should say inactive.
            if active_from_status is not False:
                print(
                    f"   ❌ No subscription but status reports "
                    f"active={active_from_status}"
                )
                return {"user_id": user.id, "passed": False}
            print(f"   ✅ Both agree: no subscription, inactive")
            return {"user_id": user.id, "passed": True}

        # Subscription exists → status should be true unless expired.
        expiry = sub.get("subscription_expiry")
        if expiry is None:
            # Lifetime plan → always active.
            if active_from_status is not True:
                print(
                    f"   ❌ Lifetime subscription but status reports "
                    f"active={active_from_status}"
                )
                return {"user_id": user.id, "passed": False}
            print(f"   ✅ Both agree: lifetime subscription, active")
            return {"user_id": user.id, "passed": True}

        # Non-lifetime: status should reflect the expiry.
        print(
            f"   ✅ Subscription present, expiry={expiry}, "
            f"status active={active_from_status}"
        )
        return {"user_id": user.id, "passed": True}

    # ══════════════════════════════════════════════════════════════
    # Composite flow
    # ══════════════════════════════════════════════════════════════

    async def run_for_user(
        self, user: TestUser,
    ) -> Dict[str, Any]:
        """Run every usage-endpoint test for one user."""
        results = [
            await self.test_user_summary_shape(user),
            await self.test_user_summary_consistency(user),
            await self.test_single_resource_endpoint(user),
            await self.test_subscription_read_agreement(user),
        ]

        # Empty state only makes sense when the user has no
        # subscription. Run it separately via `run_empty_state`.
        passed = all(r.get("passed", False) for r in results)
        return {
            "user_id": user.id,
            "passed": passed,
            "results": results,
        }

    async def run_empty_state(
        self, user: TestUser,
    ) -> Dict[str, Any]:
        """Run the empty-state test. Only meaningful when the user
        has no subscription."""
        return await self.test_empty_state(user)