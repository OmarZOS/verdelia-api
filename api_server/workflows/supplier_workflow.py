# workflows/supplier_workflow.py
"""
Supplier and organisation workflow — orchestration layer.

Owns the sequencing that combines supplier/organisation persistence
with the usage system:

  * `create_supplier` checks `PROVIDER_OWNED` before persisting.
  * `create_organisation` checks `ORGANIZATION_OWNED` before
    persisting.

Both limits are domain-counted — the current count comes from
`SELECT COUNT(*)` against the supplier / organisation tables, not
from `subscription_usage`. `DomainLimitService` owns the check; the
workflow owns the sequencing.
"""

import logging
from typing import Optional

from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_402_PAYMENT_REQUIRED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_429_TOO_MANY_REQUESTS,
)
from core.models.api_models import (
    Location_API,
    ProductProvider_API,
    ProviderImage_API,
    ProviderOrganisation_API,
    OrganisationImage_API,
)
from core.models.app_models import ResourceCode
from core.models.models import ProductProvider, ProviderOrganisation

from services.domain_limit_service import DomainLimitService
from services.subscription_service import SubscriptionService
from services.supplier_service import OrganisationService, SupplierService

from core.logging_config import get_logger

logger = get_logger(__name__)


class SupplierWorkflow:
    """Orchestration around SupplierService and OrganisationService."""

    def __init__(
        self,
        supplier_service: Optional[SupplierService] = None,
        organisation_service: Optional[OrganisationService] = None,
        domain_limits: Optional[DomainLimitService] = None,
        subscription_service: Optional[SubscriptionService] = None,
    ):
        self.supplier_service = supplier_service or SupplierService()
        self.organisation_service = (
            organisation_service or OrganisationService()
        )
        self.domain_limits = domain_limits or DomainLimitService()
        self.subscription_service = (
            subscription_service or SubscriptionService()
        )

    # ==================== Supplier create ====================

    def create_supplier(
        self,
        provider: ProductProvider_API,
        location: Location_API,
        image: Optional[ProviderImage_API] = None,
        *,
        user_id: int,
        subscription_id: Optional[int] = None,
        existing_supplier_count: Optional[int] = None,
    ) -> ProductProvider:
        """Create a supplier, enforcing the plan's `provider_owned`
        limit before persisting.

        `user_id` is required. Every write that could increase a
        domain count goes through this method. Internal jobs that
        need to bypass metering must use `create_supplier_unmetered`
        below.
        """
        logger.info(
            f"create_supplier: start user_id={user_id} "
            f"name={provider.provider_name!r}"
        )

        subscription_id = self._resolve_subscription(
            user_id=user_id,
            subscription_id=subscription_id,
            operation="create_supplier",
        )

        if existing_supplier_count is None:
            existing_supplier_count = (
                self.supplier_service.count_suppliers_for_owner(user_id)
            )
            logger.info(
                f"create_supplier: counted existing={existing_supplier_count} "
                f"for user_id={user_id}"
            )

        result = self.domain_limits.check_with_count(
            subscription_id=subscription_id,
            resource=ResourceCode.PROVIDER_OWNED,
            current_count=existing_supplier_count,
            requested=1,
        )
        check = result.check
        logger.info(
            f"create_supplier: limit check "
            f"resource={check.resource.value} "
            f"current={check.current} requested={check.requested} "
            f"allowed={check.allowed} kind={check.limit.kind.value} "
            f"limit={check.limit.ceiling} remaining={check.remaining} "
            f"reason={check.reason!r}"
        )
        if not result.allowed:
            logger.warning(
                f"create_supplier: denying user_id={user_id} "
                f"subscription_id={subscription_id} "
                f"resource={check.resource.value} "
                f"current={check.current} limit={check.limit.ceiling} "
                f"reason={check.reason!r}"
            )
            raise self._denial_to_exception(check, user_id=user_id)

        logger.info(
            f"create_supplier: persisting user_id={user_id} "
            f"name={provider.provider_name!r}"
        )
        try:
            created = self.supplier_service.create_supplier(
                provider, location, image
            )
        except Exception as e:
            logger.error(
                f"create_supplier: persist failed user_id={user_id} "
                f"name={provider.provider_name!r}: {e}",
                exc_info=True,
            )
            raise

        logger.info(
            f"create_supplier: success user_id={user_id} "
            f"provider_id={getattr(created, 'id_provider', None)} "
            f"name={provider.provider_name!r}"
        )
        return created

    def create_supplier_unmetered(
        self,
        provider: "ProductProvider_API",
        location: Location_API,
        image: Optional[ProviderImage_API] = None,
    ) -> ProductProvider:
        """Create a supplier without any plan check.

        For seeders, migrations, and admin bulk imports. Anything
        reachable from an HTTP endpoint must go through
        `create_supplier` instead.
        """
        return self.supplier_service.create_supplier(
            provider, location, image
        )

    # ==================== Organisation create ====================

    def create_organisation(
        self,
        org: ProviderOrganisation_API,
        org_image: Optional[OrganisationImage_API] = None,
        *,
        user_id: int,
        subscription_id: Optional[int] = None,
        existing_organisation_count: Optional[int] = None,
    ) -> ProviderOrganisation:
        """Create an organisation, enforcing the plan's
        `organization_owned` limit before persisting."""
        logger.info(
            f"create_organisation: start user_id={user_id} "
            f"name={org.provider_organisation_name!r}"
        )

        subscription_id = self._resolve_subscription(
            user_id=user_id,
            subscription_id=subscription_id,
            operation="create_organisation",
        )

        if existing_organisation_count is None:
            existing_organisation_count = (
                self.organisation_service
                .count_organisations_for_owner(user_id)
            )
            logger.info(
                f"create_organisation: counted "
                f"existing={existing_organisation_count} "
                f"for user_id={user_id}"
            )

        result = self.domain_limits.check_with_count(
            subscription_id=subscription_id,
            resource=ResourceCode.ORGANIZATION_OWNED,
            current_count=existing_organisation_count,
            requested=1,
        )
        check = result.check
        logger.info(
            f"create_organisation: limit check "
            f"resource={check.resource.value} "
            f"current={check.current} requested={check.requested} "
            f"allowed={check.allowed} kind={check.limit.kind.value} "
            f"limit={check.limit.ceiling} remaining={check.remaining} "
            f"reason={check.reason!r}"
        )
        if not result.allowed:
            logger.warning(
                f"create_organisation: denying user_id={user_id} "
                f"subscription_id={subscription_id} "
                f"resource={check.resource.value} "
                f"current={check.current} limit={check.limit.ceiling} "
                f"reason={check.reason!r}"
            )
            raise self._denial_to_exception(check, user_id=user_id)

        logger.info(
            f"create_organisation: persisting user_id={user_id} "
            f"name={org.provider_organisation_name!r}"
        )
        try:
            created = self.organisation_service.create_organisation(
                org, org_image
            )
        except Exception as e:
            logger.error(
                f"create_organisation: persist failed user_id={user_id} "
                f"name={org.provider_organisation_name!r}: {e}",
                exc_info=True,
            )
            raise

        logger.info(
            f"create_organisation: success user_id={user_id} "
            f"org_id={getattr(created, 'id_provider_organisation', None)} "
            f"name={org.provider_organisation_name!r}"
        )
        return created

    def create_organisation_unmetered(
        self,
        org: ProviderOrganisation_API,
        org_image: Optional[OrganisationImage_API] = None,
    ) -> ProviderOrganisation:
        """Create an organisation without any plan check."""
        return self.organisation_service.create_organisation(org, org_image)

    # ==================== Internals ====================

    def _resolve_subscription(
        self,
        *,
        user_id: int,
        subscription_id: Optional[int],
        operation: str,
    ) -> int:
        """Return a subscription id for `user_id`, resolving it if not
        supplied. Raises 404 when the user has no subscription.
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
            f"{operation}: resolved subscription_id={sub.id_subscription} "
            f"plan_id={sub.subscription_plan_id} for user_id={user_id}"
        )
        return sub.id_subscription

    def _denial_to_exception(self, check, *, user_id: int) -> APIException:
        """Translate a failed `LimitCheck` into an API error.

        Mirrors the same method on `ProductWorkflow` and
        `UsageWorkflow`. Duplicated because the workflows are
        independent layers.
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
            f"Unhandled denial kind for user={user_id}: {check.reason}"
        )
        return APIException(
            status_code=HTTP_403_FORBIDDEN,
            error_code=ErrorCode.RESOURCE_LIMIT_EXCEEDED,
            details=details,
        )