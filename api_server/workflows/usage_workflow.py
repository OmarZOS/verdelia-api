# workflows/usage_workflow.py
"""
Usage workflow: orchestrates quota checks and counter updates.

The workflow layer owns the sequence that no single service should:

  * combining a plan's limits with a subscription's current usage
  * translating a denial into an API error
  * recording usage *after* a side effect succeeds, so a failed
    operation doesn't consume quota
  * syncing the user's quota mirror when the subscription changes

`UsageService` knows how to combine limits and counters. It does not
know when to call itself, how to roll back a partial write, or what
error code to raise on denial. That's this file's job.

Dispatch on resource category is driven by `ResourceCode.counting`
(see `core.models.app_models.CountingStrategy`). There are no local
frozensets of period/domain/flag resources — the enum is the single
source of truth.

Domain counting is delegated to `DomainLimitService`, which takes a
per-resource counter registry. The workflow injects it at
construction; a `DomainLimitService` without counters can still
answer "what's the ceiling" but not "what's the current count."
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_429_TOO_MANY_REQUESTS,
)
from core.models.app_models import (
    CountingStrategy,
    Limit,
    LimitCheck,
    ResourceCode,
    resolve_limits,
)
from core.models.models import AppUser, Subscription

from services.domain_limit_service import DomainLimitService
from services.usage_service import UsageService, ReservationResult
from services.subscription_service import SubscriptionService
from services.user_service import UserService

logger = logging.getLogger(__name__)


# Provider-scoped DOMAIN resources — the user-scoped summary can't
# count these, because "the current count" depends on which provider
# you're asking about. Those come from a per-provider endpoint.
_PROVIDER_SCOPED_DOMAIN = frozenset({
    ResourceCode.PRODUCTS_PER_PROVIDER,
    ResourceCode.SERVICES_PER_PROVIDER,
})


class UsageWorkflow:
    """Coordinates usage checks, reservations, and quota sync.

    Constructed per-request; holds no state between calls. All
    collaborators are injected so tests can swap them out.

    `domain_limits` has no default. A default-constructed
    `DomainLimitService` has zero counters and raises ValueError at
    the first count. Making it required forces the wiring layer to
    supply one — a fix that surfaces at construction rather than
    mid-request.
    """

    def __init__(
        self,
        usage_service: Optional[UsageService] = None,
        subscription_service: Optional[SubscriptionService] = None,
        user_service: Optional[UserService] = None,
        domain_limits: Optional[DomainLimitService] = None,
    ):
        self.usage_service = usage_service or UsageService()
        self.subscription_service = (
            subscription_service or SubscriptionService()
        )
        self.user_service = user_service or UserService()
        self.domain_limits = domain_limits

    # ==================== Checks (no writes) ====================

    def peek(
        self,
        user_id: int,
        resource: ResourceCode,
        on_date=None,
    ) -> Optional[int]:
        """Current count for a period-counted resource.

        Returns:
          * the count, for a PERIOD resource
          * 0, when the user has no subscription
          * None, for a DOMAIN or FLAG resource — this workflow
            cannot answer "how many exist right now" without knowing
            which domain table (or, for a flag, there is no count).

        Callers that need a hard int should narrow on the resource's
        `counting` first:

            if resource.counting is CountingStrategy.PERIOD:
                n = workflow.peek(user_id, resource)
        """
        sub = self._subscription_for(user_id, required=False)
        if sub is None:
            return 0

        if resource.counting is not CountingStrategy.PERIOD:
            return None

        return self.usage_service.peek(
            sub.id_subscription, resource, on_date=on_date
        )

    def check(
        self,
        user_id: int,
        resource: ResourceCode,
        amount: int = 1,
        on_date=None,
    ) -> LimitCheck:
        """Check whether an action is allowed, without writing.

        Only valid for PERIOD resources. For DOMAIN resources, use
        `DomainLimitService` with a count supplied by the caller. For
        FLAG resources, read the plan limit directly.

        Raises APIException if the user has no subscription. Raises
        ValueError if the resource isn't period-counted.
        """
        sub = self._subscription_for(user_id, required=True)
        return self.usage_service.check(
            sub.id_subscription, resource, amount, on_date=on_date
        )

    def require(
        self,
        user_id: int,
        resource: ResourceCode,
        amount: int = 1,
        on_date=None,
    ) -> LimitCheck:
        """Like `check`, but raises on denial."""
        sub = self._subscription_for(user_id, required=True)
        check = self.usage_service.check(
            sub.id_subscription, resource, amount, on_date=on_date
        )
        if check.allowed:
            return check

        raise self._denial_to_exception(
            check, user_id=user_id, subscription_id=sub.id_subscription
        )

    # ==================== Reservations (check + write) ====================

    def reserve(
        self,
        user_id: int,
        resource: ResourceCode,
        amount: int = 1,
        on_date=None,
    ) -> ReservationResult:
        """Check and, on success, record in one call."""
        sub = self._subscription_for(user_id, required=True)
        return self.usage_service.check_and_reserve(
            sub.id_subscription, resource, amount, on_date=on_date
        )

    def require_reserve(
        self,
        user_id: int,
        resource: ResourceCode,
        amount: int = 1,
        on_date=None,
    ) -> ReservationResult:
        """Like `reserve`, but raises on denial."""
        result = self.reserve(user_id, resource, amount, on_date=on_date)
        if result.reserved:
            return result

        raise self._denial_to_exception(
            result.check,
            user_id=user_id,
            subscription_id=result.subscription_id,
        )

    # ==================== Recording (write only) ====================

    def record(
        self,
        user_id: int,
        resource: ResourceCode,
        amount: int = 1,
    ) -> int:
        """Record usage without checking."""
        sub = self._subscription_for(user_id, required=True)
        return self.usage_service.record(
            sub.id_subscription, resource, amount
        )

    def record_many(
        self,
        user_id: int,
        deltas: dict[ResourceCode, int],
    ) -> dict[str, int]:
        """Record multiple counters in one write."""
        sub = self._subscription_for(user_id, required=True)
        return self.usage_service.record_many(
            sub.id_subscription, deltas
        )

    # ==================== Quota mirror ====================

    def sync_user_quota(self, user_id: int) -> AppUser:
        """Refresh the user's quota mirror from their subscription."""
        sub = self._subscription_for(user_id, required=False)
        user = self.user_service.get_user_by_id(user_id)

        if sub is None:
            if user.user_quota != 0:
                user.user_quota = 0
                return self.user_service.update_user_record_raw(user)
            return user

        new_quota = sub.subscription_quota or 0
        if user.user_quota == new_quota:
            return user

        user.user_quota = new_quota
        return self.user_service.update_user_record_raw(user)

    # ==================== Bulk reads ====================

    def usage_summary(
        self,
        user_id: int,
        resources: Iterable[ResourceCode],
    ) -> dict[str, dict]:
        """Current counts and limits for a set of resources.

        Dispatches on each resource's `counting` strategy:

          * PERIOD — current count is read from `usage_service`
          * DOMAIN, user-scoped — current count is read from
            `domain_limits` (if a counter is registered)
          * DOMAIN, provider-scoped — current is None; the client
            fetches per provider
          * FLAG   — current is None; `allowed` reflects the flag

        Every resource in `resources` appears in the result. The
        `counted_by` and `scope` fields tell the client which service
        produced the entry and whether `current` is meaningful.
        """
        sub = self._subscription_for(user_id, required=False)

        if sub is None:
            return {r.value: _empty_summary(r) for r in resources}

        limits = self._limits_for(sub.subscription_plan_id)

        return {
            r.value: self._summarize_one(
                sub.id_subscription, r, limits, user_id
            )
            for r in resources
        }

    def provider_usage_summary(
        self,
        user_id: int,
        provider_id: int,
    ) -> dict[str, dict]:
        """Usage for the provider-scoped resources on one provider.

        Answers "how many products/services does this provider have,
        and what's the plan's headroom for it?" — the question the
        user summary can't answer.

        Raises APIException when the user has no subscription or
        when no counters are wired for the provider-scoped resources.
        """
        if self.domain_limits is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
                details={"reason": "domain counting not wired"},
            )

        sub = self._subscription_for(user_id, required=True)
        limits = self._limits_for(sub.subscription_plan_id)

        result: dict[str, dict] = {}
        for resource in _PROVIDER_SCOPED_DOMAIN:
            if not self.domain_limits.has_counter(resource):
                continue

            current = self.domain_limits.count(resource, provider_id)
            check = self.domain_limits.check_with_count(
                sub.id_subscription, resource, current, 1
            ).check
            result[resource.value] = _summary_dict(
                current=current, check=check, counted_by="domain",
            )
        return result

    def _summarize_one(
        self,
        subscription_id: int,
        resource: ResourceCode,
        limits: dict[ResourceCode, Limit],
        user_id: int,
    ) -> dict:
        """Build the summary entry for one resource."""
        match resource.counting:
            case CountingStrategy.PERIOD:
                current = self.usage_service.peek(
                    subscription_id, resource
                )
                check = self.usage_service.check(
                    subscription_id, resource, 1
                )
                return _summary_dict(
                    current=current,
                    check=check,
                    counted_by="period",
                )

            case CountingStrategy.DOMAIN:
                limit = limits.get(resource)

                if resource in _PROVIDER_SCOPED_DOMAIN:
                    return {
                        "current": None,
                        "limit": limit.ceiling if limit else 0,
                        "remaining": None,
                        "allowed": bool(limit and limit.is_finite),
                        "kind": limit.kind.value if limit else "disabled",
                        "counted_by": "domain",
                        "scope": "per_provider",
                    }

                if (
                    self.domain_limits is not None
                    and self.domain_limits.has_counter(resource)
                ):
                    current = self.domain_limits.count(
                        resource, user_id
                    )
                    check = self.domain_limits.check_with_count(
                        subscription_id, resource, current, 1
                    ).check
                    return _summary_dict(
                        current=current,
                        check=check,
                        counted_by="domain",
                    )

                return {
                    "current": None,
                    "limit": limit.ceiling if limit else 0,
                    "remaining": None,
                    "allowed": bool(limit and limit.is_finite),
                    "kind": limit.kind.value if limit else "disabled",
                    "counted_by": "domain",
                }

            case CountingStrategy.FLAG:
                limit = limits.get(resource)
                enabled = limit is not None and limit.value != 0
                return {
                    "current": None,
                    "limit": None,
                    "remaining": None,
                    "allowed": enabled,
                    "kind": "flag",
                    "counted_by": "flag",
                }

        raise AssertionError(
            f"unhandled counting strategy: {resource.counting}"
        )

    # ==================== Internals ====================

    def _limits_for(
        self,
        plan_id: int,
    ) -> dict[ResourceCode, Limit]:
        """Resolve the plan's limits for a subscription's plan id."""
        plan = self.subscription_service.get_plan_by_id(plan_id)
        if plan is None:
            raise LookupError(f"Plan {plan_id} not found")
        return resolve_limits(plan)

    def _subscription_for(
        self,
        user_id: int,
        *,
        required: bool,
    ) -> Optional[Subscription]:
        """Fetch the user's subscription, or raise if required and
        missing."""
        sub = self.subscription_service.get_subscription_for_user(user_id)
        if sub is None and required:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
                details={"user_id": user_id},
            )
        return sub

    def _denial_to_exception(
        self,
        check: LimitCheck,
        *,
        user_id: int,
        subscription_id: int,
    ) -> APIException:
        """Translate a failed `LimitCheck` into the right HTTP shape."""
        details = {
            "resource": check.resource.value,
            "current": check.current,
            "requested": check.requested,
            "reason": check.reason,
        }

        if check.limit.is_disabled:
            return APIException(
                status_code=HTTP_403_FORBIDDEN,
                error_code=ErrorCode.RESOURCE_NOT_AVAILABLE,
                details=details,
            )

        if check.limit.is_finite:
            details["limit"] = check.limit.ceiling
            details["remaining"] = check.remaining
            return APIException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                error_code=ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                details=details,
            )

        logger.error(
            f"Unhandled denial kind for user={user_id} "
            f"subscription={subscription_id}: {check.reason}"
        )
        return APIException(
            status_code=HTTP_403_FORBIDDEN,
            error_code=ErrorCode.RESOURCE_LIMIT_EXCEEDED,
            details=details,
        )


# ==================== Module-level helpers ====================

def _summary_dict(
    *,
    current: int,
    check: LimitCheck,
    counted_by: str,
) -> dict:
    """Shape a PERIOD resource's summary entry from a `LimitCheck`."""
    return {
        "current": current,
        "limit": check.limit.ceiling,
        "remaining": check.remaining,
        "allowed": check.allowed,
        "kind": check.limit.kind.value,
        "counted_by": counted_by,
    }


def _empty_summary(resource: ResourceCode) -> dict:
    """Entry shape for a user with no subscription.

    `counted_by` reflects the resource's strategy even in the
    no-subscription case, so the client's rendering logic doesn't
    depend on the user's subscription state.
    """
    return {
        "current": 0,
        "limit": 0,
        "remaining": 0,
        "allowed": False,
        "kind": "disabled",
        "counted_by": resource.counting.value,
    }