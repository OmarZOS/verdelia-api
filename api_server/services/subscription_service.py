# services/subscription_service.py (complete)
"""
Subscription service: CRUD for subscriptions and plans, plus object
building and business rules around expiry and quota.

The service does not touch the `AppUser` row. Linking a subscription
to a user is a two-step operation (create subscription, then point the
user at it) that belongs in `UserWorkflow` — the workflow is what has
both services in scope.
"""

import datetime
from typing import Optional, List, Dict, Any

from core.models.models import Subscription, Plan
from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_417_EXPECTATION_FAILED,
)
from repositories.subscription_repository import SubscriptionRepository
from core.logging_config import get_logger

logger = get_logger(__name__)


# Billing cycle → duration in days. Used to compute `subscription_expiry`
# from the plan's cycle when the caller doesn't supply an explicit date.
CYCLE_DURATIONS_DAYS: Dict[str, int] = {
    "monthly": 30,
    "semestrial": 180,
    "yearly": 365,
    # `lifetime` handled separately: expiry stays None.
}


class SubscriptionService:
    """Business logic for subscriptions and plans."""

    def __init__(self):
        self.subscription_repo = SubscriptionRepository()

    # ==================== Subscription reads ====================

    def get_subscription_by_id(
        self, subscription_id: int
    ) -> Optional[Subscription]:
        """Get a subscription by id, or None."""
        return self.subscription_repo.get_by_id(subscription_id)

    def get_subscription_for_user(
        self, user_id: int
    ) -> Optional[Subscription]:
        """Get the subscription a user points at, or None."""
        return self.subscription_repo.get_by_user_id(user_id)

    def get_subscriptions_for_plan(
        self, plan_id: int
    ) -> List[Subscription]:
        """Get all subscriptions on a plan."""
        return self.subscription_repo.get_by_plan_id(plan_id)

    def get_all_subscriptions(
        self, limit: int = 100, offset: int = 0
    ) -> List[Subscription]:
        """Get all subscriptions, paginated."""
        return self.subscription_repo.get_all(limit=limit, offset=offset)

    # ==================== Subscription writes ====================

    def create_subscription(
        self,
        *,
        plan_id: int,
        payment_id: Optional[int] = None,
        expiry: Optional[datetime.datetime] = None,
        quota: Optional[int] = None,
    ) -> Subscription:
        """Create a subscription row.

        `expiry` is computed from the plan's billing cycle when not
        supplied. `lifetime` plans get a null expiry. `quota` defaults
        to the plan's `subscription_quota` if the plan carries one —
        currently `Plan` has no quota column, so callers must supply
        it or accept the schema default of 0.

        Raises 404 when the plan doesn't exist.
        """
        plan = self.subscription_repo.get_plan_by_id(plan_id)
        if plan is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.PLAN_NOT_FOUND,
                details={"plan_id": plan_id},
            )

        if expiry is None:
            expiry = self._compute_expiry(plan)

        subscription = Subscription(
            subscription_plan_id=plan_id,
            subscription_payment_id=payment_id,
            subscription_expiry=expiry,
            subscription_quota=quota if quota is not None else 0,
        )

        try:
            return self.subscription_repo.create(subscription)
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.SUBSCRIPTION_CREATE_FAILED,
                details={"plan_id": plan_id, "error": str(e)},
            )

    def update_subscription(
        self,
        subscription_id: int,
        *,
        expiry: Optional[datetime.datetime] = None,
        quota: Optional[int] = None,
        plan_id: Optional[int] = None,
        payment_id: Optional[int] = None,
    ) -> Subscription:
        """Update fields on an existing subscription.

        Only the fields the caller supplies are changed. To clear the
        expiry (move to lifetime), pass `expiry=datetime.min` — see
        `set_expiry` for the intended API.
        """
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if subscription is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
                details={"subscription_id": subscription_id},
            )

        if plan_id is not None:
            plan = self.subscription_repo.get_plan_by_id(plan_id)
            if plan is None:
                raise APIException(
                    status_code=HTTP_404_NOT_FOUND,
                    error_code=ErrorCode.PLAN_NOT_FOUND,
                    details={"plan_id": plan_id},
                )
            subscription.subscription_plan_id = plan_id

        if payment_id is not None:
            subscription.subscription_payment_id = payment_id

        if expiry is not None:
            subscription.subscription_expiry = expiry

        if quota is not None:
            subscription.subscription_quota = quota

        try:
            return self.subscription_repo.update(subscription)
        except Exception as e:
            logger.error(
                f"Failed to update subscription {subscription_id}: {e}"
            )
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.SUBSCRIPTION_UPDATE_FAILED,
                details={
                    "subscription_id": subscription_id,
                    "error": str(e),
                },
            )

    def renew_subscription(
        self,
        subscription_id: int,
        additional_days: Optional[int] = None,
    ) -> Subscription:
        """Extend a subscription's expiry.

        When `additional_days` is not supplied, the plan's billing
        cycle determines the extension. Lifetime plans are left alone
        (expiry stays None).
        """
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if subscription is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
                details={"subscription_id": subscription_id},
            )

        plan = self.subscription_repo.get_plan_by_id(
            subscription.subscription_plan_id
        )
        if plan is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.PLAN_NOT_FOUND,
                details={"plan_id": subscription.subscription_plan_id},
            )

        # Lifetime plans never expire.
        if plan.billing_cycle == "lifetime":
            return subscription

        if additional_days is None:
            additional_days = CYCLE_DURATIONS_DAYS.get(plan.billing_cycle, 30)

        now = datetime.datetime.now()
        base = subscription.subscription_expiry or now
        # If already expired, extend from now rather than from the old
        # expiry so renewals never "catch up" an old date.
        if base < now:
            base = now

        subscription.subscription_expiry = base + datetime.timedelta(
            days=additional_days
        )

        try:
            return self.subscription_repo.update(subscription)
        except Exception as e:
            logger.error(
                f"Failed to renew subscription {subscription_id}: {e}"
            )
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.SUBSCRIPTION_UPDATE_FAILED,
                details={
                    "subscription_id": subscription_id,
                    "error": str(e),
                },
            )

    def delete_subscription(self, subscription_id: int) -> bool:
        """Delete a subscription row.

        Does not unlink the user — that's the workflow's job. The FK on
        `AppUser.app_user_subscription_ref` will block the delete if a
        user still points at this subscription.
        """
        subscription = self.subscription_repo.get_by_id(subscription_id)
        if subscription is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
                details={"subscription_id": subscription_id},
            )

        try:
            return self.subscription_repo.delete(subscription)
        except Exception as e:
            logger.error(
                f"Failed to delete subscription {subscription_id}: {e}"
            )
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.SUBSCRIPTION_DELETE_FAILED,
                details={
                    "subscription_id": subscription_id,
                    "error": str(e),
                },
            )

    # ==================== Business rules ====================

    def is_active(self, subscription: Subscription) -> bool:
        """Whether a subscription hasn't expired.

        A null expiry means "never expires" — lifetime plans. Anything
        with an expiry strictly after now is active.
        """
        if subscription is None:
            return False
        if subscription.subscription_expiry is None:
            return True
        return subscription.subscription_expiry > datetime.datetime.now()

    def is_active_for_user(self, user_id: int) -> bool:
        """Whether the user's current subscription is active."""
        subscription = self.get_subscription_for_user(user_id)
        return self.is_active(subscription)

    def days_remaining(
        self, subscription: Subscription
    ) -> Optional[int]:
        """Days until expiry, or None for lifetime plans.

        Returns 0 when already expired, never negative.
        """
        if subscription is None:
            return None
        if subscription.subscription_expiry is None:
            return None
        delta = subscription.subscription_expiry - datetime.datetime.now()
        return max(0, delta.days)

    # ==================== Object building ====================

    def build_subscription(
        self,
        *,
        plan_id: int,
        payment_id: Optional[int] = None,
        expiry: Optional[datetime.datetime] = None,
        quota: Optional[int] = None,
    ) -> Subscription:
        """Build a `Subscription` ORM object without persisting it.

        Useful when the caller wants to attach related objects before
        a single `create`. If you just want a row, use
        `create_subscription` — it does this and saves in one step.
        """
        plan = self.subscription_repo.get_plan_by_id(plan_id)
        if plan is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.PLAN_NOT_FOUND,
                details={"plan_id": plan_id},
            )

        if expiry is None:
            expiry = self._compute_expiry(plan)

        return Subscription(
            subscription_plan_id=plan_id,
            subscription_payment_id=payment_id,
            subscription_expiry=expiry,
            subscription_quota=quota if quota is not None else 0,
        )

    def build_plan(
        self,
        *,
        plan_name: str,
        plan_price: float,
        billing_cycle: str = "monthly",
        plan_type: str = "individual",
    ) -> Plan:
        """Build a `Plan` ORM object without persisting it.

        Validates the billing cycle and plan type against the schema's
        enums so callers get a clean 400 instead of a DB constraint
        violation.
        """
        self._validate_billing_cycle(billing_cycle)
        self._validate_plan_type(plan_type)

        if plan_price < 0:
            raise APIException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.INVALID_PLAN_PRICE,
                details={"plan_price": plan_price},
            )

        return Plan(
            plan_name=plan_name,
            plan_price=plan_price,
            billing_cycle=billing_cycle,
            plan_type=plan_type,
        )

    # ==================== Plan CRUD ====================

    def get_plan_by_id(self, plan_id: int) -> Optional[Plan]:
        return self.subscription_repo.get_plan_by_id(plan_id)

    def get_plan_by_name(self, plan_name: str) -> Optional[Plan]:
        return self.subscription_repo.get_plan_by_name(plan_name)

    def get_all_plans(
        self,
        plan_type: Optional[str] = None,
        billing_cycle: Optional[str] = None,
    ) -> List[Plan]:
        return self.subscription_repo.get_all_plans(
            plan_type=plan_type,
            billing_cycle=billing_cycle,
        )

    def create_plan(
        self,
        *,
        plan_name: str,
        plan_price: float,
        billing_cycle: str = "monthly",
        plan_type: str = "individual",
    ) -> Plan:
        """Create a plan row.

        Raises 409 if a plan with the same name already exists — the
        name is treated as the natural key for lookups.
        """
        if self.subscription_repo.get_plan_by_name(plan_name) is not None:
            raise APIException(
                status_code=HTTP_409_CONFLICT,
                error_code=ErrorCode.PLAN_ALREADY_EXISTS,
                details={"plan_name": plan_name},
            )

        plan = self.build_plan(
            plan_name=plan_name,
            plan_price=plan_price,
            billing_cycle=billing_cycle,
            plan_type=plan_type,
        )

        try:
            return self.subscription_repo.create_plan(plan)
        except Exception as e:
            logger.error(f"Failed to create plan '{plan_name}': {e}")
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.PLAN_CREATE_FAILED,
                details={"plan_name": plan_name, "error": str(e)},
            )

    def update_plan(
        self,
        plan_id: int,
        *,
        plan_name: Optional[str] = None,
        plan_price: Optional[float] = None,
        billing_cycle: Optional[str] = None,
        plan_type: Optional[str] = None,
    ) -> Plan:
        """Update fields on an existing plan."""
        plan = self.subscription_repo.get_plan_by_id(plan_id)
        if plan is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.PLAN_NOT_FOUND,
                details={"plan_id": plan_id},
            )

        if plan_name is not None:
            existing = self.subscription_repo.get_plan_by_name(plan_name)
            if existing is not None and existing.id_plan != plan_id:
                raise APIException(
                    status_code=HTTP_409_CONFLICT,
                    error_code=ErrorCode.PLAN_ALREADY_EXISTS,
                    details={"plan_name": plan_name},
                )
            plan.plan_name = plan_name

        if plan_price is not None:
            if plan_price < 0:
                raise APIException(
                    status_code=HTTP_400_BAD_REQUEST,
                    error_code=ErrorCode.INVALID_PLAN_PRICE,
                    details={"plan_price": plan_price},
                )
            plan.plan_price = plan_price

        if billing_cycle is not None:
            self._validate_billing_cycle(billing_cycle)
            plan.billing_cycle = billing_cycle

        if plan_type is not None:
            self._validate_plan_type(plan_type)
            plan.plan_type = plan_type

        try:
            return self.subscription_repo.update_plan(plan)
        except Exception as e:
            logger.error(f"Failed to update plan {plan_id}: {e}")
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.PLAN_UPDATE_FAILED,
                details={"plan_id": plan_id, "error": str(e)},
            )

    def delete_plan(self, plan_id: int) -> bool:
        """Delete a plan.

        Fails with a 409 when any subscription still references the
        plan — the FK is RESTRICT, and deleting a plan out from under
        an active subscription is not something we want to allow.
        """
        plan = self.subscription_repo.get_plan_by_id(plan_id)
        if plan is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.PLAN_NOT_FOUND,
                details={"plan_id": plan_id},
            )

        active_subs = self.subscription_repo.get_by_plan_id(plan_id)
        if active_subs:
            raise APIException(
                status_code=HTTP_409_CONFLICT,
                error_code=ErrorCode.PLAN_IN_USE,
                details={
                    "plan_id": plan_id,
                    "subscription_count": len(active_subs),
                },
            )

        try:
            return self.subscription_repo.delete_plan(plan)
        except Exception as e:
            logger.error(f"Failed to delete plan {plan_id}: {e}")
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.PLAN_DELETE_FAILED,
                details={"plan_id": plan_id, "error": str(e)},
            )

    # ==================== Internal helpers ====================

    def _compute_expiry(
        self, plan: Plan
    ) -> Optional[datetime.datetime]:
        """Compute a subscription's expiry from a plan's billing cycle.

        Returns None for lifetime plans, otherwise now + cycle duration.
        """
        if plan.billing_cycle == "lifetime":
            return None

        days = CYCLE_DURATIONS_DAYS.get(plan.billing_cycle)
        if days is None:
            # Unknown cycle — fail loudly rather than silently guessing.
            raise APIException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.INVALID_BILLING_CYCLE,
                details={"billing_cycle": plan.billing_cycle},
            )

        return datetime.datetime.now() + datetime.timedelta(days=days)

    def _validate_billing_cycle(self, cycle: str) -> None:
        if cycle not in ("monthly", "semestrial", "yearly", "lifetime"):
            raise APIException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.INVALID_BILLING_CYCLE,
                details={
                    "billing_cycle": cycle,
                    "allowed": [
                        "monthly",
                        "semestrial",
                        "yearly",
                        "lifetime",
                    ],
                },
            )

    def _validate_plan_type(self, plan_type: str) -> None:
        if plan_type not in ("individual", "organization"):
            raise APIException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.INVALID_PLAN_TYPE,
                details={
                    "plan_type": plan_type,
                    "allowed": ["individual", "organization"],
                },
            )