# workflows/service_workflow.py
"""
Service workflow — orchestration layer.

Owns the sequencing that combines service persistence with the
usage system:

  * `create_service` checks `SERVICES_PER_PROVIDER` before
    persisting. The limit is domain-counted — the current count
    comes from `SELECT COUNT(*)` against the `provided_service`
    table, scoped to the provider the service belongs to.

Everything else (reads, updates, toggles) goes directly through
`ServiceService` — they don't change the domain count.
"""

import logging
from typing import List, Optional

from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_402_PAYMENT_REQUIRED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_429_TOO_MANY_REQUESTS,
)
from core.models.api_models import (
    ProvidedService_API,
    ServiceResourceRequirement_API,
    ServiceStaffRequirement_API,
)
from core.models.app_models import ResourceCode
from core.models.models import ProvidedService

from services.domain_limit_service import DomainLimitService
from services.service_service import ServiceService
from services.subscription_service import SubscriptionService

from core.logging_config import get_logger

logger = get_logger(__name__)


class ServiceWorkflow:
    """Orchestration around ServiceService."""

    def __init__(
        self,
        service: Optional[ServiceService] = None,
        domain_limits: Optional[DomainLimitService] = None,
        subscription_service: Optional[SubscriptionService] = None,
    ):
        self.service = service or ServiceService()
        self.domain_limits = domain_limits or DomainLimitService()
        self.subscription_service = (
            subscription_service or SubscriptionService()
        )

    # ==================== Create with metering ====================

    def create_service(
        self,
        service_data: ProvidedService_API,
        requirements: List[ServiceResourceRequirement_API],
        staff_requirements: List[ServiceStaffRequirement_API],
        *,
        user_id: int,
        subscription_id: Optional[int] = None,
        existing_service_count: Optional[int] = None,
    ) -> ProvidedService:
        """Create a service, enforcing the plan's
        `services_per_provider` limit before persisting.

        `user_id` is required. Internal jobs that need to bypass
        metering must use `create_service_unmetered` below.

        The count is scoped to the provider the service belongs to.
        A user with three providers has three independent ceilings,
        not one.
        """
        provider_id = service_data.provided_service_product_provider_id
        logger.info(
            f"create_service: start user_id={user_id} "
            f"provider_id={provider_id} "
            f"name={service_data.provided_service_name!r}"
        )

        # ── Resolve subscription ───────────────────────────────
        subscription_id = self._resolve_subscription(
            user_id=user_id,
            subscription_id=subscription_id,
            operation="create_service",
        )

        # ── Require a target provider ──────────────────────────
        if provider_id is None:
            logger.error(
                f"create_service: missing "
                f"provided_service_product_provider_id for "
                f"user_id={user_id}"
            )
            raise ValueError(
                "create_service requires "
                "provided_service_product_provider_id to enforce the "
                "per-provider quota."
            )

        # ── Domain limit check ─────────────────────────────────
        if existing_service_count is None:
            existing_service_count = (
                self.service.count_services_for_provider(provider_id)
            )
            logger.info(
                f"create_service: counted existing="
                f"{existing_service_count} for provider_id={provider_id}"
            )
        else:
            logger.info(
                f"create_service: using supplied existing_service_count="
                f"{existing_service_count} for provider_id={provider_id}"
            )

        result = self.domain_limits.check_with_count(
            subscription_id=subscription_id,
            resource=ResourceCode.SERVICES_PER_PROVIDER,
            current_count=existing_service_count,
            requested=1,
        )

        check = result.check
        logger.info(
            f"create_service: limit check "
            f"resource={check.resource.value} "
            f"current={check.current} requested={check.requested} "
            f"allowed={check.allowed} kind={check.limit.kind.value} "
            f"limit={check.limit.ceiling} remaining={check.remaining} "
            f"reason={check.reason!r}"
        )
        if not result.allowed:
            logger.warning(
                f"create_service: denying user_id={user_id} "
                f"subscription_id={subscription_id} "
                f"provider_id={provider_id} "
                f"resource={check.resource.value} "
                f"current={check.current} "
                f"limit={check.limit.ceiling} "
                f"reason={check.reason!r}"
            )
            raise self._denial_to_exception(check, user_id=user_id)

        # ── Persist ────────────────────────────────────────────
        logger.info(
            f"create_service: persisting user_id={user_id} "
            f"provider_id={provider_id} "
            f"name={service_data.provided_service_name!r}"
        )
        try:
            created = self.service.create_service(
                service_data, requirements, staff_requirements
            )
        except Exception as e:
            logger.error(
                f"create_service: persist failed user_id={user_id} "
                f"provider_id={provider_id} "
                f"name={service_data.provided_service_name!r}: {e}",
                exc_info=True,
            )
            raise

        logger.info(
            f"create_service: success user_id={user_id} "
            f"provider_id={provider_id} "
            f"service_id="
            f"{getattr(created, 'provided_service_id', None)} "
            f"name={service_data.provided_service_name!r}"
        )
        return created

    def create_service_unmetered(
        self,
        service_data: ProvidedService_API,
        requirements: List[ServiceResourceRequirement_API],
        staff_requirements: List[ServiceStaffRequirement_API],
    ) -> ProvidedService:
        """Create a service without any plan check.

        For seeders, migrations, and admin bulk imports. Anything
        reachable from an HTTP endpoint must go through
        `create_service` instead.
        """
        return self.service.create_service(
            service_data, requirements, staff_requirements
        )

    # ==================== Internals ====================

    def _resolve_subscription(
        self,
        *,
        user_id: int,
        subscription_id: Optional[int],
        operation: str,
    ) -> int:
        """Return a subscription id for `user_id`, resolving it if
        not supplied. Raises 404 when the user has no subscription.
        """
        if subscription_id is not None:
            logger.info(
                f"{operation}: using supplied subscription_id="
                f"{subscription_id} for user_id={user_id}"
            )
            return subscription_id

        sub = self.subscription_service.get_subscription_for_user(user_id)
        if sub is None:
            logger.warning(
                f"{operation}: refusing user_id={user_id} — no "
                f"subscription on file"
            )
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
                details={"user_id": user_id},
            )
        logger.info(
            f"{operation}: resolved subscription_id="
            f"{sub.id_subscription} plan_id={sub.subscription_plan_id} "
            f"for user_id={user_id}"
        )
        return sub.id_subscription

    def _denial_to_exception(self, check, *, user_id: int) -> APIException:
        """Translate a failed `LimitCheck` into an API error.

        Mirrors `UsageWorkflow._denial_to_exception`,
        `ProductWorkflow._denial_to_exception`, and
        `SupplierWorkflow._denial_to_exception`. Duplicated because
        the workflows are independent layers.
        """
        details = {
            "resource": check.resource.value,
            "current": check.current,
            "requested": check.requested,
            "reason": check.reason,
        }

        if check.limit.is_disabled:
            return APIException(
                status_code=HTTP_402_PAYMENT_REQUIRED,
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
            f"Unhandled denial kind for user={user_id}: "
            f"{check.reason}"
        )
        return APIException(
            status_code=HTTP_403_FORBIDDEN,
            error_code=ErrorCode.RESOURCE_LIMIT_EXCEEDED,
            details=details,
        )