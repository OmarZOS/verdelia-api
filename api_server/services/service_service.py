# services/service_service.py

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from repositories.service_repository import ServiceRepository
from core.models.api_models import (
    ProvidedService_API,
    ServiceResourceRequirement_API,
    ServiceStaffRequirement_API,
)
from core.exceptions.specific.service_exceptions import (
    ServiceNotFoundException,
    ServiceCreationFailedException,
    ServiceUpdateFailedException,
    ServiceDeleteFailedException,
    ServiceCategoryNotFoundException,
    ServiceProviderNotFoundException,
    ServiceToggleStatusException,
)
from core.messages import *
from core.models.models import (
    ProvidedService,
    ProvidedServiceCategory,
    ServiceResourceRequirement,
    ServiceStaffRequirement,
    StaffRole,
)
from repositories.supplier_repository import SupplierRepository

from core.logging_config import get_logger

logger = get_logger(__name__)


class ServiceService:
    """Service for service-related business logic."""

    def __init__(self):
        self.service_repo = ServiceRepository()
        self.provider_repo = SupplierRepository()

    # ==================== Private Helper Methods ====================

    def _build_service_model(
        self, api_service: ProvidedService_API,
    ) -> ProvidedService:
        """
        Build a `ProvidedService` model from the API payload.

        Column names come from `core.models.models.ProvidedService`:

            provided_service_name
            provided_service_description
            category_id                       ← not provided_service_category_id
            provider_id                       ← not provided_service_product_provider_id
            base_price                        ← not provided_service_base_price
            unit_price                        ← not provided_service_final_price
            provided_service_actual_duration
            provided_service_is_active
            provided_service_pricing_config
            vat_rate
        """
        service = ProvidedService(
            provided_service_name=api_service.provided_service_name,
            provided_service_description=api_service.provided_service_description,
            category_id=api_service.category_id,
            provider_id=api_service.provided_service_product_provider_id,
            base_price=api_service.provided_service_base_price,
            unit_price=api_service.provided_service_final_price,
            provided_service_actual_duration=api_service.provided_service_actual_duration,
            provided_service_is_active=api_service.provided_service_is_active,
            provided_service_pricing_config=api_service.provided_service_pricing_config,
        )

        if api_service.provided_service_id and api_service.provided_service_id != 0:
            service.idprovided_service = api_service.provided_service_id

        return service

    def _build_resource_requirement(
        self,
        api_req: ServiceResourceRequirement_API,
        *,
        service_id: int,
    ) -> ServiceResourceRequirement:
        """
        Build a `ServiceResourceRequirement` bound to `service_id`.

        `service_id` is required and always wins over whatever
        `api_req.resource_requirement_service_id` contains. That's
        deliberate: on the create path the service row doesn't exist
        yet, so the API payload can't carry the id; the caller passes
        it in after persisting the service. On an update path (if
        this ever grows one), the requirement belongs to the service
        being updated, not whatever the client claims.

        Column names:

            service_id
            service_resource_requirement_name
            service_resource_requirement_type
            service_resource_requirement_quantity
            unit_price                       ← not service_resource_requirement_cost_per_unit
            service_resource_requirement_is_consumable
            service_resource_requirement_notes
            product_id                       ← not service_resource_requirement_product_ref
        """
        return ServiceResourceRequirement(
            service_id=service_id,
            service_resource_requirement_name=api_req.resource_requirement_name,
            service_resource_requirement_type=api_req.resource_requirement_type,
            service_resource_requirement_quantity=api_req.resource_requirement_quantity,
            unit_price=api_req.resource_requirement_cost_per_unit,
            service_resource_requirement_is_consumable=api_req.resource_requirement_is_consumable,
            service_resource_requirement_notes=api_req.resource_requirement_notes,
            product_id=api_req.resource_requirement_product_ref,
        )

    def _build_staff_requirement(
        self,
        api_req: ServiceStaffRequirement_API,
        *,
        service_id: int,
    ) -> ServiceStaffRequirement:
        """
        Build a `ServiceStaffRequirement` bound to `service_id`.

        `service_id` is required and always wins over whatever
        `api_req.service_staff_requirement_service_id` contains, for
        the same reason as `_build_resource_requirement`.

        Column names:

            service_staff_requirement_service_id
            service_staff_requirement_role_id    ← not service_staff_requirement_role
            service_staff_requirement_min_count
            service_staff_requirement_max_count
            service_staff_requirement_hourly_rate
            service_staff_requirement_allocated_hours
            service_staff_requirement_notes
        """
        return ServiceStaffRequirement(
            service_staff_requirement_service_id=service_id,
            service_staff_requirement_role_id=api_req.service_staff_requirement_role,
            service_staff_requirement_min_count=api_req.service_staff_requirement_min_count,
            service_staff_requirement_max_count=api_req.service_staff_requirement_max_count,
            service_staff_requirement_hourly_rate=api_req.service_staff_requirement_hourly_rate,
            service_staff_requirement_allocated_hours=api_req.service_staff_requirement_allocated_hours,
            service_staff_requirement_notes=api_req.service_staff_requirement_notes,
        )

    def _validate_provider_exists(self, provider_id: int) -> bool:
        provider = self.provider_repo.get_supplier_by_id(provider_id)
        if not provider:
            logger.warning("Provider not found with ID: %s", provider_id)
            raise ServiceProviderNotFoundException(provider_id=provider_id)
        return True

    def _validate_category_exists(self, category_id: int) -> bool:
        category = self.service_repo.get_category_by_id(category_id)
        if not category:
            logger.warning("Category not found with ID: %s", category_id)
            raise ServiceCategoryNotFoundException(category_id=category_id)
        return True

    def _check_service_dependencies(self, service_id: int) -> bool:
        if self.service_repo.get_package_items_by_service(service_id):
            return True
        if self.service_repo.get_cart_items_by_service(service_id):
            return True
        return False

    # ==================== Service Retrieval Methods ====================

    def get_service_by_id(self, service_id: int) -> ProvidedService:
        service = self.service_repo.get_service_by_id(service_id)
        if not service:
            logger.warning("Service not found with ID: %s", service_id)
            raise ServiceNotFoundException(service_id=service_id)
        logger.debug("Retrieved service with ID: %s", service_id)
        return service

    def get_services_by_category(
        self, category_id: int, offset: int = 0, limit: int = 100,
    ) -> List[ProvidedService]:
        self._validate_category_exists(category_id)
        return self.service_repo.get_services_by_category(
            category_id, offset, limit,
        )

    def get_services_by_provider(
        self, provider_id: int, offset: int = 0, limit: int = 100,
    ) -> List[ProvidedService]:
        self._validate_provider_exists(provider_id)
        return self.service_repo.get_services_by_provider(
            provider_id, offset, limit,
        )

    def get_services(
        self, offset: int = 0, limit: int = 100,
    ) -> List[ProvidedService]:
        return self.service_repo.get_services(offset, limit)

    def get_active_services(
        self, provider_id: Optional[int] = None,
    ) -> List[ProvidedService]:
        if provider_id:
            self._validate_provider_exists(provider_id)
        return self.service_repo.get_active_services(provider_id)

    def get_service_requirements(
        self, service_id: int,
    ) -> List[ServiceResourceRequirement]:
        self.get_service_by_id(service_id)
        return self.service_repo.get_service_resource_requirements(service_id)

    def get_service_staff_requirements(
        self, service_id: int,
    ) -> List[ServiceStaffRequirement]:
        self.get_service_by_id(service_id)
        return self.service_repo.get_service_staff_requirements(service_id)

    def get_categories(
        self, offset: int = 0, limit: int = 100,
    ) -> List[ProvidedServiceCategory]:
        return self.service_repo.get_categories(offset, limit)

    def get_roles_by_service_category(
        self, category_id: int, offset: int = 0, limit: int = 100,
    ) -> List[StaffRole]:
        return self.service_repo.get_roles_by_service_category(
            category_id, offset, limit,
        )

    # ==================== Service Creation Methods ====================

    def create_service(
        self,
        service_data: ProvidedService_API,
        requirements: List[ServiceResourceRequirement_API],
        staff_requirements: List[ServiceStaffRequirement_API],
    ) -> ProvidedService:
        """
        Create a new service with its requirements.

        Transaction strategy: the repos own their own session. If a
        requirement fails to persist, the caller (this method) deletes
        the freshly-created service row so the DB doesn't accumulate
        orphans. This is best-effort — a crash between the two steps
        leaves an orphan, and a periodic sweeper should reconcile
        services with no requirements.
        """
        logger.info(
            "Creating new service: %s", service_data.provided_service_name,
        )

        if service_data.category_id:
            self._validate_category_exists(service_data.category_id)
        if service_data.provided_service_product_provider_id:
            self._validate_provider_exists(
                service_data.provided_service_product_provider_id,
            )

        service = self._build_service_model(service_data)

        service_created: Optional[ProvidedService] = None
        try:
            service_created = self.service_repo.create_service(service)
            service_id = service_created.idprovided_service
            logger.info("Service created with ID: %s", service_id)

            created_requirements: List[ServiceResourceRequirement] = []
            for req_data in requirements:
                req = self._build_resource_requirement(
                    req_data, service_id=service_id,
                )
                created_req = self.service_repo.create_resource_requirement(req)
                created_requirements.append(created_req)
                logger.debug(
                    "Created resource requirement: %s",
                    created_req.id_service_resource_requirement,
                )

            created_staff: List[ServiceStaffRequirement] = []
            for req_data in staff_requirements:
                req = self._build_staff_requirement(
                    req_data, service_id=service_id,
                )
                created_req = self.service_repo.create_staff_requirement(req)
                created_staff.append(created_req)
                logger.debug(
                    "Created staff requirement: %s",
                    created_req.id_service_staff_requirement,
                )

            # Attach to the in-memory object for the response serializer.
            # Note: the relationship on ProvidedService is
            # `service_resource_requirement` (not `service_staff_requirement`)
            # for resource requirements.
            # service_created.service_resource_requirement = created_requirements
            # service_created.service_staff_requirement = created_staff

            logger.info(
                "Service created successfully with %d resource and "
                "%d staff requirements",
                len(created_requirements), len(created_staff),
            )
            return service_created

        except Exception as e:
            logger.error("Failed to create service with requirements: %s", e)

            # Best-effort cleanup of the orphaned service row.
            if service_created is not None:
                try:
                    self.service_repo.delete_service(service_created)
                    logger.info(
                        "Rolled back orphaned service %s",
                        service_created.idprovided_service,
                    )
                except Exception:
                    logger.exception(
                        "Failed to roll back orphaned service %s",
                        service_created.idprovided_service,
                    )

            raise ServiceCreationFailedException(
                error=str(e),
                service_name=service_data.provided_service_name,
                provider_id=service_data.provided_service_product_provider_id,
            )

    # ==================== Service Update Methods ====================

    def update_service(
        self, service_id: int, service_data: ProvidedService_API,
    ) -> ProvidedService:
        logger.info("Updating service with ID: %s", service_id)

        service = self.get_service_by_id(service_id)
        changed_fields = service_data.model_fields_set

        if (
            "category_id" in changed_fields
            and service_data.category_id != service.category_id
            and service_data.category_id
        ):
            self._validate_category_exists(service_data.category_id)

        if (
            "provided_service_product_provider_id" in changed_fields
            and service_data.provided_service_product_provider_id
            != service.provider_id
        ):
            self._validate_provider_exists(
                service_data.provided_service_product_provider_id,
            )

        # Only apply fields the caller supplied. The model-level rename
        # for provider_id is handled here — the API field stays
        # `provided_service_product_provider_id`, the column is `provider_id`.
        field_map = {
            "provided_service_product_provider_id": "provider_id",
            "provided_service_name": "provided_service_name",
            "provided_service_description": "provided_service_description",
            "category_id": "category_id",
            "provided_service_base_price": "base_price",
            "provided_service_final_price": "unit_price",
            "provided_service_actual_duration": "provided_service_actual_duration",
            "provided_service_is_active": "provided_service_is_active",
            "provided_service_pricing_config": "provided_service_pricing_config",
        }

        for api_name, column_name in field_map.items():
            if api_name in changed_fields:
                setattr(service, column_name, getattr(service_data, api_name))

        try:
            updated_service = self.service_repo.update_service(service)
            logger.info("Service %s updated successfully", service_id)
            return updated_service
        except Exception as e:
            logger.error("Failed to update service %s: %s", service_id, e)
            raise ServiceUpdateFailedException(
                service_id=service_id, error=str(e),
            )

    def toggle_service_status(
        self, service_id: int, is_active: bool,
    ) -> ProvidedService:
        action = "activate" if is_active else "deactivate"
        logger.info("Attempting to %s service %s", action, service_id)

        service = self.get_service_by_id(service_id)

        current_status = service.provided_service_is_active
        if current_status == is_active:
            raise ServiceToggleStatusException(
                service_id=service_id,
                current_status=current_status,
                requested_status=is_active,
                error=(
                    f"Service already {'active' if is_active else 'inactive'}"
                ),
            )

        service.provided_service_is_active = is_active

        try:
            updated_service = self.service_repo.update_service(service)
            logger.info("Service %s %sd successfully", service_id, action)
            return updated_service
        except Exception as e:
            logger.error("Failed to %s service %s: %s", action, service_id, e)
            raise ServiceToggleStatusException(
                service_id=service_id,
                requested_status=is_active,
                error=str(e),
            )

    # ==================== Service Deletion Methods ====================

    def delete_service(
        self, service_id: int, force_delete: bool = False,
    ) -> Dict[str, Any]:
        """
        Delete a service and its requirements.

        `force_delete=False` (the default) refuses to delete a service
        that still has package, cart, or order dependencies. It also
        refuses when the service still has requirements attached unless
        the caller passes `force_delete=True`.

        `force_delete=True` skips the dependency checks and cascades
        through the requirements.
        """
        logger.info(
            "Deleting service with ID: %s (force=%s)",
            service_id, force_delete,
        )

        service = self.get_service_by_id(service_id)

        requirements = self.service_repo.get_service_resource_requirements(service_id)
        staff_requirements = self.service_repo.get_service_staff_requirements(service_id)

        has_requirements = len(requirements) > 0
        has_staff_requirements = len(staff_requirements) > 0

        if not force_delete:
            if self._check_service_dependencies(service_id):
                logger.warning(
                    "Refusing delete of service %s: has dependencies "
                    "(packages, carts, or orders)",
                    service_id,
                )
                raise ServiceDeleteFailedException(
                    service_id=service_id,
                    has_dependencies=True,
                    error="Service has existing dependencies (orders, carts)",
                )

            if has_requirements or has_staff_requirements:
                logger.warning(
                    "Refusing delete of service %s: has %d resource and "
                    "%d staff requirements. Retry with force_delete=true "
                    "to cascade.",
                    service_id, len(requirements), len(staff_requirements),
                )
                raise ServiceDeleteFailedException(
                    service_id=service_id,
                    error=(
                        "Service has associated requirements. "
                        "Use force_delete=true to delete."
                    ),
                )

        if has_requirements:
            for req in requirements:
                logger.info(
                    "Deleting resource requirement %s for service %s",
                    req.id_service_resource_requirement, service_id,
                )
                if not self.service_repo.delete_service_resource_requirements(req):
                    raise ServiceDeleteFailedException(
                        service_id=service_id,
                        error=(
                            f"Failed to delete resource requirement "
                            f"{req.id_service_resource_requirement}"
                        ),
                    )

        if has_staff_requirements:
            for req in staff_requirements:
                logger.info(
                    "Deleting staff requirement %s for service %s",
                    req.id_service_staff_requirement, service_id,
                )
                if not self.service_repo.delete_service_staff_requirements(req):
                    raise ServiceDeleteFailedException(
                        service_id=service_id,
                        error=(
                            f"Failed to delete staff requirement "
                            f"{req.id_service_staff_requirement}"
                        ),
                    )

        try:
            success = self.service_repo.delete_service(service)
            if not success:
                raise ServiceDeleteFailedException(
                    service_id=service_id,
                    error="Repository returned False",
                )
            logger.info("Service %s deleted successfully", service_id)
            return {
                "message": f"Service {service_id} deleted successfully",
                "service_id": service_id,
            }
        except ServiceDeleteFailedException:
            raise
        except Exception as e:
            logger.error("Failed to delete service %s: %s", service_id, e)
            raise ServiceDeleteFailedException(
                service_id=service_id, error=str(e),
            )

    # ==================== Counts ====================

    def count_services_for_provider(self, provider_id: int) -> int:
        return self.service_repo.count_services_by_provider(provider_id)