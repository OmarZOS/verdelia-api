# services/usage_service.py
"""
Combines a subscription's plan limits with its periodic usage.

Only handles resources whose count lives in `subscription_usage`
**and** which have a corresponding `ResourceCode` member. Today that
is exactly one resource: `AI_CREDITS_MONTHLY` (column
`ai_credits_used`).

Resources handled elsewhere:

  * domain-counted — `ORGANIZATION_OWNED`, `PROVIDER_OWNED`,
    `TEAM_MEMBERS`, `PRODUCTS_PER_PROVIDER`,
    `SERVICES_PER_PROVIDER`. Counted from their domain tables at
    check time, not from `subscription_usage`.
  * flag — `ADS_ENABLED`. Read from the `plan_limit` row directly.

Metrics without a plan limit — `ai_product_searches`,
`ai_auto_fills`, `products_created` — are written through
`UsageRepository` directly, not through this service. They become
plan-checked the day they gain a `ResourceCode` and an entry in
`_RESOURCE_TO_COLUMN`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from core.models.app_models import (
    DISABLED,
    Limit,
    LimitCheck,
    ResourceCode,
    check_limit,
    resolve_limits,
)
from repositories.subscription_repository import SubscriptionRepository
from repositories.usage_repository import (
    COUNTER_COLUMNS,
    UsageRepository,
)


# ResourceCode → usage counter column.
#
# The only place these two vocabularies meet. Every value here must
# be a member of `COUNTER_COLUMNS`. The assertion below enforces it
# at import time, so a mismatch fails loudly instead of silently
# counting zero — the failure mode that hid the previous mismatch.
_RESOURCE_TO_COLUMN: dict[ResourceCode, str] = {
    ResourceCode.AI_CREDITS_MONTHLY: "ai_credits_used",
}

# Import-time guard. If a resource is added here without adding the
# column to the repository, the module fails to import rather than
# running with a silent zero.
_drift = set(_RESOURCE_TO_COLUMN.values()) - COUNTER_COLUMNS
if _drift:
    raise ImportError(
        f"_RESOURCE_TO_COLUMN references columns not in "
        f"COUNTER_COLUMNS: {sorted(_drift)}. Update the repository's "
        f"COUNTER_COLUMNS or fix the map."
    )


@dataclass(frozen=True)
class ReservationResult:
    """Outcome of `check_and_reserve`.

    `check` is the raw `LimitCheck` — allowed, reason, remaining.
    `reserved` is True only when the check passed *and* the counter
    was incremented. On denial, `reserved` is False and no write
    occurred.
    """

    check: LimitCheck
    reserved: bool
    subscription_id: int
    plan_id: int
    period_start: Optional[date]


class UsageService:
    """Period-counted usage checks and reservations.

    All public methods take primitives and return either primitives
    or a frozen dataclass. No ORM objects cross this boundary.
    """

    def __init__(
        self,
        usage_repo: Optional[UsageRepository]=None,
        subscription_repo: Optional[SubscriptionRepository]=None,
    ) -> None:
        self._usage = usage_repo or UsageRepository()
        self._subs = subscription_repo or SubscriptionRepository()

    # ==================== Public API ====================

    def peek(
        self,
        subscription_id: int,
        resource: ResourceCode,
        on_date: Optional[date] = None,
    ) -> int:
        """Current count for `resource` this period.

        Returns 0 when no usage row exists yet. Does not write.

        Raises ValueError for resources that aren't period-counted.
        """
        column = self._column_for(resource)
        row = self._usage.get_current(subscription_id, on_date=on_date)
        return _count(row, column)

    def check(
        self,
        subscription_id: int,
        resource: ResourceCode,
        amount: int = 1,
        on_date: Optional[date] = None,
    ) -> LimitCheck:
        """Check whether `amount` more of `resource` is allowed.

        Does not write. Use `check_and_reserve` when you want the
        check and the increment to happen together.
        """
        column = self._column_for(resource)
        plan_id = self._plan_id(subscription_id)
        limits, current = self._limits_and_count(
            subscription_id, plan_id, column, on_date
        )
        return check_limit(limits, resource, current, amount)

    def check_and_reserve(
        self,
        subscription_id: int,
        resource: ResourceCode,
        amount: int = 1,
        on_date: Optional[date] = None,
    ) -> ReservationResult:
        """Check the limit and, on success, increment the counter.

        On denial: nothing is written, `reserved` is False, `check`
        carries the reason.

        On success: the counter is incremented by `amount`,
        `reserved` is True, `check.allowed` is True.

        The check and the increment are not atomic. Two concurrent
        callers can both see "1 of 2 used" and both succeed, leaving
        the counter at 3. That is acceptable for this workload: the
        cost of strict serialization (`SELECT … FOR UPDATE`) is
        higher than the cost of occasionally exceeding a quota by
        the race delta, and the counter resets next period anyway.
        """
        column = self._column_for(resource)
        plan_id = self._plan_id(subscription_id)
        limits, current = self._limits_and_count(
            subscription_id, plan_id, column, on_date
        )
        check = check_limit(limits, resource, current, amount)

        if not check.allowed:
            return ReservationResult(
                check=check,
                reserved=False,
                subscription_id=subscription_id,
                plan_id=plan_id,
                period_start=on_date or date.today(),
            )

        updated = self._usage.increment(
            subscription_id,
            column=column,
            amount=amount,
        )

        return ReservationResult(
            check=check,
            reserved=True,
            subscription_id=subscription_id,
            plan_id=plan_id,
            period_start=updated.get("period_start"),
        )

    def record(
        self,
        subscription_id: int,
        resource: ResourceCode,
        amount: int = 1,
    ) -> int:
        """Increment the counter without checking.

        For callers who already passed a `check` and want to record
        the outcome separately. Returns the new counter value.

        Prefer `check_and_reserve` when you control both call sites.
        This method exists for paths that check early (validation)
        and record late (after a successful side effect), where
        collapsing the two would either double-check or write before
        the side effect succeeds.
        """
        column = self._column_for(resource)
        updated = self._usage.increment(
            subscription_id,
            column=column,
            amount=amount,
        )
        return _count(updated, column)

    def record_many(
        self,
        subscription_id: int,
        deltas: dict[ResourceCode, int],
    ) -> dict[str, int]:
        """Record multiple counters in one write.

        `deltas` maps ResourceCode → amount. Unknown resources raise
        ValueError. Returns the updated counter values keyed by
        column name.
        """
        if not deltas:
            return {}

        columns: dict[str, int] = {}
        for resource, amount in deltas.items():
            columns[self._column_for(resource)] = amount

        updated = self._usage.increment_many(
            subscription_id,
            deltas=columns,
        )
        return {c: _count(updated, c) for c in columns}

    # ==================== Internals ====================

    def _column_for(self, resource: ResourceCode) -> str:
        """Map a resource to its counter column.

        Raises ValueError for resources that aren't period-counted.
        The message names where the resource *is* handled, so a
        misuse tells the caller where to go instead.
        """
        column = _RESOURCE_TO_COLUMN.get(resource)
        if column is None:
            raise ValueError(
                f"{resource.value!r} is not a period-counted resource. "
                f"This service handles only: "
                f"{sorted(r.value for r in _RESOURCE_TO_COLUMN)}. "
                f"Domain-counted resources are checked from their "
                f"domain tables; flags like ads_enabled are read from "
                f"the plan_limit row."
            )
        return column

    def _plan_id(self, subscription_id: int) -> int:
        sub = self._subs.get_by_id(subscription_id)
        if sub is None:
            raise LookupError(
                f"No subscription with id {subscription_id}"
            )
        return sub.subscription_plan_id

    def _limits_and_count(
        self,
        subscription_id: int,
        plan_id: int,
        column: str,
        on_date: Optional[date],
    ) -> tuple[dict[ResourceCode, Limit], int]:
        """Fetch the plan's resolved limits and the current counter.

        Bundled because both are needed together by `check` and
        `check_and_reserve`, and fetching them separately would let
        the caller forget one.

        `plan_id` is passed in rather than resolved here so callers
        that already have it don't trigger a second
        `SubscriptionRepository.get_by_id`.
        """
        plan = self._subs.get_plan_by_id(plan_id)
        if plan is None:
            raise LookupError(
                f"Plan {plan_id} not found for subscription "
                f"{subscription_id}"
            )

        limits = resolve_limits(plan)

        row = self._usage.get_current(subscription_id, on_date=on_date)
        current = _count(row, column)

        return limits, current

        # ==================== User-scoped API ====================

    def check_for_user(
        self,
        user_id: int,
        resource: ResourceCode,
        amount: int = 1,
        on_date: Optional[date] = None,
    ) -> LimitCheck:
        """Check whether a user can consume `amount` more.

        Resolves the user's subscription, then delegates to `check`.
        Unlike `check`, which takes a subscription id, this variant
        takes a user id and handles the "user has no subscription"
        case as a denial rather than a lookup failure.

        A user with no subscription gets a `LimitCheck` with
        `allowed=False`, `reason="no subscription"`. That keeps the
        caller's shape uniform — every call returns a `LimitCheck`,
        and denial is expressed through `allowed`, not exceptions.
        """
        sub_id = self._subscription_id_for_user(user_id)
        if sub_id is None:
            return LimitCheck(
                allowed=False,
                resource=resource,
                limit=Limit(resource=resource, value=DISABLED),
                current=0,
                requested=amount,
                reason="no subscription on file",
            )

        return self.check(sub_id, resource, amount, on_date=on_date)

    def add_for_user(
        self,
        user_id: int,
        resource: ResourceCode,
        amount: int = 1,
    ) -> int:
        """Record consumption of `amount` for a user.

        Equivalent to `record(user.subscription_id, resource,
        amount)` but keyed by user id. Returns the new counter value.

        Use after a `check_for_user` that passed, or after a
        `require_for_user` (see below) that didn't raise. If you want
        check-and-record in one call, use `reserve_for_user`.
        """
        column = self._column_for(resource)
        updated = self._usage.add_for_user(user_id, column, amount)
        return _count(updated, column)

    def reduce_for_user(
        self,
        user_id: int,
        resource: ResourceCode,
        amount: int = 1,
    ) -> int:
        """Refund `amount` of a user's consumption.

        Used when a reserved operation failed and the credit should
        be returned. Clamps at zero — reducing past zero is a no-op.

        Returns the resulting counter value.
        """
        column = self._column_for(resource)
        updated = self._usage.reduce_for_user(user_id, column, amount)
        return _count(updated, column)

    def check_and_reserve_for_user(
        self,
        user_id: int,
        resource: ResourceCode,
        amount: int = 1,
        on_date: Optional[date] = None,
    ) -> ReservationResult:
        """Check and, on success, record. Keyed by user id.

        On denial: `reserved=False`, no write.
        On success: `reserved=True`, counter incremented.

        Use this when the work the reservation is for cannot fail
        after the reservation is taken. When the work *can* fail,
        use `check_for_user` + `add_for_user` on success +
        `reduce_for_user` on failure.
        """
        sub_id = self._subscription_id_for_user(user_id)
        if sub_id is None:
            return ReservationResult(
                check=LimitCheck(
                    allowed=False,
                    resource=resource,
                    limit=Limit(resource=resource, value=DISABLED),
                    current=0,
                    requested=amount,
                    reason="no subscription on file",
                ),
                reserved=False,
                subscription_id=0,
                plan_id=0,
                period_start=on_date or date.today(),
            )

        return self.check_and_reserve(
            sub_id, resource, amount, on_date=on_date
        )

    # ==================== Internals ====================

    def _subscription_id_for_user(self, user_id: int) -> Optional[int]:
        """Resolve a user's subscription id via the usage repository.

        Delegates to the repository rather than touching `AppUser`
        directly — the repository owns the ORM read.
        """
        return self._usage._subscription_id_for_user(user_id)


# ==================== Helpers ====================

def _count(row: Optional[dict], column: str) -> int:
    """Read a counter from a usage row dict.

    Tolerates a missing row (returns 0) and a missing column on the
    row (returns 0). The repository is supposed to guarantee both,
    but a `None` here would crash the request path, and returning 0
    is the safe default for "no usage yet".
    """
    if row is None:
        return 0
    return row.get(column, 0) or 0