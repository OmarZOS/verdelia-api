# services/service_service.py - Fixed version

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from repositories.service_repository import ServiceRepository
from core.models.api_models import ProvidedService_API, ServiceResourceRequirement_API, ServiceStaffRequirement_API
from core.exceptions.specific.service_exceptions import (
    ServiceException,
    ServiceNotFoundException,
    ServiceCreationFailedException,
    ServiceUpdateFailedException,
    ServiceDeleteFailedException,
    ServiceCategoryNotFoundException,
    ServiceProviderNotFoundException,
    ServiceToggleStatusException,
    ServiceRequirementCreationException,
    ServiceRequirementNotFoundException,
    ServiceStaffRequirementNotFoundException
)
from core.messages import *
from core.models.models import ProvidedService, ProvidedServiceCategory, ServiceResourceRequirement, ServiceStaffRequirement, StaffRole
from repositories.supplier_repository import SupplierRepository
from storage.storage_broker import session_scope

from core.logging_config import get_logger

logger = get_logger(__name__)



class ServiceService:
    """Service for service-related business logic"""
    
    def __init__(self):
        self.service_repo = ServiceRepository()
        self.provider_repo = SupplierRepository()
    
    # ==================== Private Helper Methods ====================
    
    def _build_service_model(self, api_service: ProvidedService_API) -> ProvidedService:
        """
        Build service model from API data.
        
        Args:
            api_service: API service data
            
        Returns:
            ProvidedService model instance
        """
        service = ProvidedService(
            provided_service_name=api_service.provided_service_name,
            provided_service_description=api_service.provided_service_description,
            provided_service_category_id=api_service.provided_service_category_id,
            provided_service_product_provider_id=api_service.provided_service_product_provider_id,
            provided_service_base_price=api_service.provided_service_base_price,
            provided_service_final_price=api_service.provided_service_final_price,
            provided_service_actual_duration=api_service.provided_service_actual_duration,
            provided_service_is_active=api_service.provided_service_is_active,
            provided_service_pricing_config=api_service.provided_service_pricing_config,
        )
        
        if api_service.provided_service_id and api_service.provided_service_id != 0:
            service.provided_service_id = api_service.provided_service_id
        
        return service
    
    def _build_resource_requirement(self, api_req: ServiceResourceRequirement_API) -> ServiceResourceRequirement:
        """Build resource requirement from API data."""
        req = ServiceResourceRequirement(
            service_resource_requirement_service_id=api_req.resource_requirement_service_id,
            service_resource_requirement_name=api_req.resource_requirement_name,
            service_resource_requirement_type=api_req.resource_requirement_type,
            service_resource_requirement_quantity=api_req.resource_requirement_quantity,
            service_resource_requirement_cost_per_unit=api_req.resource_requirement_cost_per_unit,
            service_resource_requirement_is_consumable=api_req.resource_requirement_is_consumable,
            service_resource_requirement_notes=api_req.resource_requirement_notes,
            service_resource_requirement_product_ref=api_req.resource_requirement_product_ref,
        )
        
        # If there's an ID, set it (for updates)
        if hasattr(api_req, 'resource_requirement_id') and api_req.resource_requirement_id and api_req.resource_requirement_id != 0:
            req.service_resource_requirement_id = api_req.resource_requirement_id
    
        return req

    def _build_staff_requirement(self, api_req: ServiceStaffRequirement_API) -> ServiceStaffRequirement:
        """Build staff requirement from API data."""
        req = ServiceStaffRequirement(
            service_staff_requirement_service_id=api_req.service_staff_requirement_service_id,
            service_staff_requirement_role=api_req.service_staff_requirement_role,
            service_staff_requirement_min_count=api_req.service_staff_requirement_min_count,
            service_staff_requirement_max_count=api_req.service_staff_requirement_max_count,
            service_staff_requirement_hourly_rate=api_req.service_staff_requirement_hourly_rate,
            service_staff_requirement_allocated_hours=api_req.service_staff_requirement_allocated_hours,
            service_staff_requirement_notes=api_req.service_staff_requirement_notes,
        )
        
        if hasattr(api_req, 'service_staff_requirement_id') and api_req.service_staff_requirement_id and api_req.service_staff_requirement_id != 0:
            req.service_staff_requirement_id = api_req.service_staff_requirement_id
        
        return req
    
    def _build_staff_requirement(self, api_req: ServiceStaffRequirement_API) -> ServiceStaffRequirement:
        """Build staff requirement from API data."""
        req = ServiceStaffRequirement(
            service_staff_requirement_service_id=api_req.service_staff_requirement_service_id,
            service_staff_requirement_role=api_req.service_staff_requirement_role,  # Now integer
            service_staff_requirement_min_count=api_req.service_staff_requirement_min_count,
            service_staff_requirement_max_count=api_req.service_staff_requirement_max_count,
            service_staff_requirement_hourly_rate=api_req.service_staff_requirement_hourly_rate,
            service_staff_requirement_allocated_hours=api_req.service_staff_requirement_allocated_hours,
            service_staff_requirement_notes=api_req.service_staff_requirement_notes,
        )
        
        if hasattr(api_req, 'service_staff_requirement_id') and api_req.service_staff_requirement_id and api_req.service_staff_requirement_id != 0:
            req.service_staff_requirement_id = api_req.service_staff_requirement_id
        
        return req

    
    def _validate_provider_exists(self, provider_id: int) -> bool:
        """Validate that a provider exists."""
        provider = self.provider_repo.get_supplier_by_id(provider_id)
        if not provider:
            logger.warning(f"Provider not found with ID: {provider_id}")
            raise ServiceProviderNotFoundException(provider_id=provider_id)
        return True
    
    def _validate_category_exists(self, category_id: int) -> bool:
        """Validate that a category exists."""
        category = self.service_repo.get_category_by_id(category_id)
        if not category:
            logger.warning(f"Category not found with ID: {category_id}")
            raise ServiceCategoryNotFoundException(category_id=category_id)
        return True
    
    def _check_service_dependencies(self, service_id: int) -> bool:
        """Check if service has dependencies."""
        package_items = self.service_repo.get_package_items_by_service(service_id)
        if package_items:
            return True
        
        cart_items = self.service_repo.get_cart_items_by_service(service_id)
        if cart_items:
            return True
        
        return False
    
    # ==================== Service Retrieval Methods ====================
    
    def get_service_by_id(self, service_id: int) -> ProvidedService:
        """Get service by ID."""
        service = self.service_repo.get_service_by_id(service_id)
        if not service:
            logger.warning(f"Service not found with ID: {service_id}")
            raise ServiceNotFoundException(service_id=service_id)
        
        logger.debug(f"Retrieved service with ID: {service_id}")
        return service
    
    def get_services_by_category(self, category_id: int, offset: int = 0, limit: int = 100) -> List[ProvidedService]:
        """Get services by category."""
        self._validate_category_exists(category_id)
        return self.service_repo.get_services_by_category(category_id, offset, limit)
    
    def get_services_by_provider(self, provider_id: int, offset: int = 0, limit: int = 100) -> List[ProvidedService]:
        """Get services by provider."""
        self._validate_provider_exists(provider_id)
        return self.service_repo.get_services_by_provider(provider_id, offset, limit)
    
    def get_services(self, offset: int = 0, limit: int = 100) -> List[ProvidedService]:
        """Get all services."""
        return self.service_repo.get_services(offset, limit)
    
    def get_active_services(self, provider_id: Optional[int] = None) -> List[ProvidedService]:
        """Get active services."""
        if provider_id:
            self._validate_provider_exists(provider_id)
        return self.service_repo.get_active_services(provider_id)
    
    def get_service_requirements(self, service_id: int) -> List[ServiceResourceRequirement]:
        """Get resource requirements for a service."""
        self.get_service_by_id(service_id)
        return self.service_repo.get_service_resource_requirements(service_id)
    
    def get_service_staff_requirements(self, service_id: int) -> List[ServiceStaffRequirement]:
        """Get staff requirements for a service."""
        self.get_service_by_id(service_id)
        return self.service_repo.get_service_staff_requirements(service_id)

    def get_categories(self, offset: int = 0, limit: int = 100) -> List[ProvidedServiceCategory]:
        """Get all service categories."""
        return self.service_repo.get_categories(offset, limit)

    def get_roles_by_service_category(self, category_id: int, offset: int = 0, limit: int = 100) -> List[StaffRole]:
        """Get roles by service category."""
        return self.service_repo.get_roles_by_service_category(category_id, offset, limit)

    # ==================== Service Creation Methods ====================
    
    def create_service(
        self,
        service_data: ProvidedService_API,
        requirements: List[ServiceResourceRequirement_API],
        staff_requirements: List[ServiceStaffRequirement_API]
    ) -> ProvidedService:
        """
        Create a new service with requirements.
        
        The key fix: Requirements are saved in a session-aware way.
        """
        logger.info(f"Creating new service: {service_data.provided_service_name}")
        
        # Validate category
        if service_data.provided_service_category_id:
            self._validate_category_exists(service_data.provided_service_category_id)
        
        # Validate provider
        if service_data.provided_service_product_provider_id:
            self._validate_provider_exists(service_data.provided_service_product_provider_id)
        
        # Build service
        service = self._build_service_model(service_data)
        
        # Use session_scope to handle the transaction
        with session_scope() as session:
            try:
                # Save service first to get ID
                service_created = self.service_repo.create_service(service)
                service_id = service_created.provided_service_id
                logger.info(f"Service created with ID: {service_id}")
                
                # Create resource requirements
                created_requirements = []
                for req_data in requirements:
                    req = self._build_resource_requirement(req_data)
                    req.service_resource_requirement_service_id = service_id
                    created_req = self.service_repo.create_resource_requirement(req)
                    created_requirements.append(created_req)
                    logger.debug(f"Created resource requirement: {created_req.service_resource_requirement_id}")
                
                # Create staff requirements
                created_staff = []
                for req_data in staff_requirements:
                    req = self._build_staff_requirement(req_data)
                    req.service_staff_requirement_service_id = service_id
                    created_req = self.service_repo.create_staff_requirement(req)
                    created_staff.append(created_req)
                    logger.debug(f"Created staff requirement: {created_req.service_staff_requirement_id}")
                
                # Attach requirements to service for response
                service_created.resource_requirements = created_requirements
                service_created.staff_requirements = created_staff
                
                logger.info(f"Service created successfully with {len(created_requirements)} resource and {len(created_staff)} staff requirements")
                return service_created
                
            except Exception as e:
                logger.error(f"Failed to create service with requirements: {e}")
                raise ServiceCreationFailedException(
                    error=str(e),
                    service_name=service_data.provided_service_name,
                    provider_id=service_data.provided_service_product_provider_id
                )
    
    # ==================== Service Update Methods ====================
    
    def update_service(self, service_id: int, service_data: ProvidedService_API) -> ProvidedService:
        """Update an existing service."""
        logger.info(f"Updating service with ID: {service_id}")
        
        # Validate service exists
        service = self.get_service_by_id(service_id)
        changed_fields = service_data.model_fields_set
        
        # Validate category if changed
        if (
            "provided_service_category_id" in changed_fields
            and service_data.provided_service_category_id != service.provided_service_category_id
            and service_data.provided_service_category_id
        ):
            self._validate_category_exists(service_data.provided_service_category_id)
        
        # Validate provider if changed
        if (
            "provided_service_product_provider_id" in changed_fields
            and service_data.provided_service_product_provider_id != service.provided_service_product_provider_id
        ):
            self._validate_provider_exists(service_data.provided_service_product_provider_id)
        
        # Only apply fields supplied by the caller; model defaults must not erase stored data.
        updatable_fields = {
            "provided_service_product_provider_id",
            "provided_service_name",
            "provided_service_description",
            "provided_service_category_id",
            "provided_service_base_price",
            "provided_service_final_price",
            "provided_service_actual_duration",
            "provided_service_is_active",
            "provided_service_pricing_config",
        }
        for field_name in changed_fields & updatable_fields:
            setattr(service, field_name, getattr(service_data, field_name))
        
        try:
            updated_service = self.service_repo.update_service(service)
            logger.info(f"Service {service_id} updated successfully")
            return updated_service
        except Exception as e:
            logger.error(f"Failed to update service {service_id}: {e}")
            raise ServiceUpdateFailedException(
                service_id=service_id,
                error=str(e)
            )
    
    def toggle_service_status(self, service_id: int, is_active: bool) -> ProvidedService:
        """Activate or deactivate a service."""
        action = "activate" if is_active else "deactivate"
        logger.info(f"Attempting to {action} service {service_id}")
        
        service = self.get_service_by_id(service_id)
        
        current_status = service.provided_service_is_active
        if current_status == is_active:
            raise ServiceToggleStatusException(
                service_id=service_id,
                current_status=current_status,
                requested_status=is_active,
                error=f"Service already {'active' if is_active else 'inactive'}"
            )
        
        service.provided_service_is_active = is_active
        
        try:
            updated_service = self.service_repo.update_service(service)
            logger.info(f"Service {service_id} {action}d successfully")
            return updated_service
        except Exception as e:
            logger.error(f"Failed to {action} service {service_id}: {e}")
            raise ServiceToggleStatusException(
                service_id=service_id,
                requested_status=is_active,
                error=str(e)
            )
    
    # ==================== Service Deletion Methods ====================
    
    def delete_service(self, service_id: int, force_delete: bool = False) -> Dict[str, Any]:
        """Delete a service and all associated requirements."""
        logger.info(f"Deleting service with ID: {service_id} (force={force_delete})")
        
        # Validate service exists
        service = self.get_service_by_id(service_id)
        
        requirements = self.service_repo.get_service_resource_requirements(service_id)
        staff_requirements = self.service_repo.get_service_staff_requirements(service_id)

        has_requirements = len(requirements) > 0
        has_staff_requirements = len(staff_requirements) > 0
        
        if not force_delete:
            has_dependencies = self._check_service_dependencies(service_id)
            
            if has_dependencies:
                raise ServiceDeleteFailedException(
                    service_id=service_id,
                    has_dependencies=True,
                    error="Service has existing dependencies (orders, carts)"
                )
            
            if has_requirements or has_staff_requirements:
                raise ServiceDeleteFailedException(
                    service_id=service_id,
                    error="Service has associated requirements. Use force_delete=true to delete."
                )
        
        # Delete resource requirements
        if has_requirements:
            for req in requirements:
                self.service_repo.delete_service_resource_requirements(req)
            logger.debug(f"Deleted resource requirements for service {service_id}")
        
        # Delete staff requirements
        if has_staff_requirements:
            for req in staff_requirements:
                self.service_repo.delete_service_staff_requirements(req)
            logger.debug(f"Deleted staff requirements for service {service_id}")
        
        # Delete service
        try:
            success = self.service_repo.delete_service(service)
            if not success:
                raise ServiceDeleteFailedException(
                    service_id=service_id,
                    error="Repository returned False"
                )
            
            logger.info(f"Service {service_id} deleted successfully")
            return {
                "message": f"Service {service_id} deleted successfully",
                "service_id": service_id
            }
            
        except Exception as e:
            logger.error(f"Failed to delete service {service_id}: {e}")
            raise ServiceDeleteFailedException(
                service_id=service_id,
                error=str(e)
            )