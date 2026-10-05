# services/domain_limit_service.py
"""
Checks limits for resources whose current count comes from a domain
table rather than from `subscription_usage`.

Five resources go through this service:

    organization_owned        SELECT COUNT(*) FROM provider_organisation
    provider_owned            SELECT COUNT(*) FROM product_provider
    team_members              SELECT COUNT(*) FROM management_rule
    products_per_provider     SELECT COUNT(*) FROM product
    services_per_provider     SELECT COUNT(*) FROM provided_service

The counting is delegated to per-resource callables registered at
construction time. The service itself doesn't query domain tables —
the wiring layer supplies one `CounterFn` per resource.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from core.models.app_models import (
    CountingStrategy,
    Limit,
    LimitCheck,
    ResourceCode,
    check_limit,
    resolve_limits,
)
from repositories.subscription_repository import SubscriptionRepository


# A counter takes a scope and returns the current count for its
# resource. The scope is a user id for user-scoped resources and a
# provider/org id for provider/org-scoped ones.
CounterFn = Callable[[int], int]


_DOMAIN_RESOURCES = frozenset(
    r for r in ResourceCode
    if r.counting is CountingStrategy.DOMAIN
)


@dataclass(frozen=True)
class DomainCheckResult:
    """Outcome of a domain-counted check."""

    check: LimitCheck
    subscription_id: int
    plan_id: int

    @property
    def allowed(self) -> bool:
        return self.check.allowed


class DomainLimitService:
    """Checks domain-counted resources against plan limits.

    Counting is delegated to per-resource callables. The service
    itself only knows the plan limits and how to compare a count
    against them.
    """

    def __init__(
        self,
        subscription_repo: Optional[SubscriptionRepository] = None,
        counters: Optional[dict[ResourceCode, CounterFn]] = None,
    ) -> None:
        self._subs = subscription_repo or SubscriptionRepository()
        self._counters: dict[ResourceCode, CounterFn] = counters or {}

    # ==================== Registration ====================

    def register_counter(
        self,
        resource: ResourceCode,
        counter: CounterFn,
    ) -> None:
        """Register a counting callable for a resource."""
        self._assert_handled(resource)
        self._counters[resource] = counter

    # ==================== Public API ====================

    def count(self, resource: ResourceCode, scope: int) -> int:
        """Current count for `resource` at the given scope.

        Raises ValueError when no counter is registered — a missing
        counter is a wiring bug, not a runtime condition.
        """
        self._assert_handled(resource)
        counter = self._counters.get(resource)
        if counter is None:
            raise ValueError(
                f"No counter registered for {resource.value!r}. "
                f"Register one with `register_counter()` at wiring time."
            )
        return counter(scope)

    def has_counter(self, resource: ResourceCode) -> bool:
        """Whether a counter is registered for this resource."""
        return resource in self._counters

    def check(
        self,
        subscription_id: int,
        resource: ResourceCode,
        scope: int,
        requested: int = 1,
    ) -> DomainCheckResult:
        """Count the resource at `scope`, then check the plan."""
        current = self.count(resource, scope)
        return self.check_with_count(
            subscription_id, resource, current, requested
        )

    def check_with_count(
        self,
        subscription_id: int,
        resource: ResourceCode,
        current_count: int,
        requested: int = 1,
    ) -> DomainCheckResult:
        """Check an already-computed count against the plan."""
        self._assert_handled(resource)

        plan_id = self._plan_id(subscription_id)
        plan = self._subs.get_plan_by_id(plan_id)
        if plan is None:
            raise LookupError(
                f"Plan {plan_id} not found for subscription "
                f"{subscription_id}"
            )

        limits = resolve_limits(plan)
        check = check_limit(limits, resource, current_count, requested)

        return DomainCheckResult(
            check=check,
            subscription_id=subscription_id,
            plan_id=plan_id,
        )

    def ceiling(
        self,
        subscription_id: int,
        resource: ResourceCode,
    ) -> Optional[int]:
        """The plan's ceiling for `resource`, or None when unlimited
        or negotiated."""
        self._assert_handled(resource)
        plan_id = self._plan_id(subscription_id)
        plan = self._subs.get_plan_by_id(plan_id)
        if plan is None:
            return None
        limits = resolve_limits(plan)
        limit = limits.get(resource)
        return limit.ceiling if limit is not None else None

    # ==================== Internals ====================

    def _assert_handled(self, resource: ResourceCode) -> None:
        if resource not in _DOMAIN_RESOURCES:
            raise ValueError(
                f"{resource.value!r} is not a domain-counted resource. "
                f"This service handles only: "
                f"{sorted(r.value for r in _DOMAIN_RESOURCES)}. "
                f"Period-counted resources go through UsageService; "
                f"flags are read from the plan_limit row directly."
            )

    def _plan_id(self, subscription_id: int) -> int:
        sub = self._subs.get_by_id(subscription_id)
        if sub is None:
            raise LookupError(
                f"No subscription with id {subscription_id}"
            )
        return sub.subscription_plan_id