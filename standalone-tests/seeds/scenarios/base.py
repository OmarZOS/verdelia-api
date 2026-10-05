# test_runner/base.py
"""Shared base for scenario modules.

Every scenario is a thin wrapper around an HTTP surface. They all
need the same three things: an authenticated client, the shared
context, and a way to log failures. That lives here.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from context import TestContext, TestUser
from data import short


class BaseScenario:
    """Base class for one-router scenario modules.

    Subclasses are constructed with a shared client + context and
    expose methods that mirror the router's endpoints. They do not
    own the client — the runner creates it once and passes it in.
    """

    # Override in subclasses — used by the runner for logging.
    name: str = "unnamed"

    def __init__(
        self,
        client: httpx.AsyncClient,
        context: TestContext,
        stats: Dict[str, int],
        base_url: str,
    ) -> None:
        self.client = client
        self.context = context
        self.stats = stats
        self.base_url = base_url

    # ── Auth ───────────────────────────────────────────────────

    def get_auth_headers(self, user: TestUser) -> Dict[str, str]:
        return (
            {"Authorization": f"Bearer {user.access_token}"}
            if user.access_token else {}
        )

    # ── Failure recording ──────────────────────────────────────

    def _record_failure(
        self, label: str, response: httpx.Response,
    ) -> None:
        self.stats["failures"] = self.stats.get("failures", 0) + 1
        print(
            f"   ❌ {label}: HTTP {response.status_code} — "
            f"{short(response.text)}"
        )

    # ── Bounded creation loop ──────────────────────────────────

    async def probe_limit_boundary(
        self,
        user: TestUser,
        resource_name: str,
        create_fn,
        *,
        max_attempts: int = 50,
    ) -> Dict[str, Any]:
        """Create resources until the plan refuses, then once more.

        `create_fn` is an async callable that returns the raw HTTP
        response. Stops on the first non-2xx status, or at
        `max_attempts` (to bound the run on unlimited plans).
        """
        print(
            f"\n🔬 Probing {resource_name} limit for user {user.id}..."
        )
        created = 0
        attempts = 0
        first_denial: Optional[httpx.Response] = None

        while attempts < max_attempts:
            attempts += 1
            response = await create_fn()
            if response is None:
                break

            if response.status_code in (200, 201):
                created += 1
                if created % 10 == 0:
                    print(f"   … {created} created")
                continue

            first_denial = response
            break

        status = first_denial.status_code if first_denial else None
        print(
            f"   📊 {resource_name}: {created} created, "
            f"stopped at attempt {attempts} "
            f"(denial status={status or 'none'})"
        )
        return {
            "resource": resource_name,
            "user_id": user.id,
            "created": created,
            "attempts": attempts,
            "denial_status": status,
            "denial_body": (
                short(first_denial.text) if first_denial else None
            ),
        }