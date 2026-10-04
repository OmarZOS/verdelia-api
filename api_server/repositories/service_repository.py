
from typing import Optional, List, Dict, Any, Tuple
from core.models.models import *
import storage.storage_broker as storage_broker
from sqlalchemy.orm import joinedload, sessionmaker, Session
from sqlalchemy import select, delete
import logging

logger = logging.getLogger(__name__)



class ServiceRepository:
    """Repository for Service-related database operations"""
    
    def get_service_by_id(self, service_id: int, eager_load: bool = True) -> Optional[ProvidedService]:
        """Get service by ID"""
        eager_fields = []
        if eager_load:
            eager_fields =[
                {ProvidedService.service_staff_requirement: [{ServiceStaffRequirement.staff_role : [{StaffRole.naming_contribution:[]}]}]},
                ProvidedService.service_resource_requirement,
            ]
        
        records = storage_broker.get(
            ProvidedService,
            {ProvidedService.provided_service_id: service_id},
            [],
            eager_fields
        )
        return records[0] if records else None

    def get_services_by_ids(self, service_ids: List[int], eager_load: bool = True) -> List[ProvidedService]:
        """
        Get services by list of IDs with optional eager loading.
        
        Args:
            service_ids: List of service IDs to fetch
            eager_load: Whether to eager load related relationships
            
        Returns:
            List of ProvidedService objects
        """
        if not service_ids:
            return []
        
        # Build eager fields
        eager_fields = [ProvidedService.service_resource_requirement]
        if eager_load:
            eager_fields = [
                {ProvidedService.service_staff_requirement: [StaffRole.naming_contribution]},
                ProvidedService.provided_service_category,
                ProvidedService.provided_service_product_provider,
                ProvidedService.ordered_service,
                ProvidedService.service_package_item,
                ProvidedService.service_contribution
            ]
        
        # Build condition for IN clause
        condition = {ProvidedService.provided_service_id: service_ids}
        
        # Execute query
        records = storage_broker.get(
            ProvidedService,
            condition,
            [],
            eager_fields
        )
        
        return records
    
    def get_services_by_category(self, category_id: int, offset: int = 0, limit: int = 100) -> List[ProvidedService]:
        """Get services by category"""
        return storage_broker.get(
            ProvidedService,
            {ProvidedService.provided_service_category_id: category_id},
            [],
            [],
            offset=offset,
            limit=limit
        )
    
    def get_services_by_category(self, category_id: int, offset: int = 0, limit: int = 100) -> List[ProvidedService]:
        """Get services by category"""
        return storage_broker.get(
            ProvidedService,
            {ProvidedService.provided_service_category_id: category_id},
            [],
            None,
            offset,
            limit
        )

    def get_categories(self, offset: int = 0, limit: int = 100) -> Optional[ProvidedServiceCategory]:
            """Get service category by ID"""
            data = storage_broker.get(
                ProvidedServiceCategory,
                {},
                [],
                [ProvidedServiceCategory.naming_contribution],
                offset,
                limit
            )
            return data if data else None
    
    def get_category_by_id(self, category_id: int) -> Optional[ProvidedServiceCategory]:
        """Get service category by ID"""
        data = storage_broker.get(
            ProvidedServiceCategory,
            {ProvidedServiceCategory.provided_service_category_id: category_id},
            [],
            None,
            0,
            1
        )
        return data[0] if data else None

    def get_roles_by_service_category(self, category_id: int, offset: int = 0, limit: int = 100) -> List[StaffRole]:
            """Get roles by service category"""
            return storage_broker.get(
                StaffRole,
                {StaffRole.staff_role_service_category_ref: category_id},
                [],
                [StaffRole.naming_contribution],
                offset,
                limit
            )
    
    def get_services_by_provider(self, provider_id: int, offset: int = 0, limit: int = 100) -> List[ProvidedService]:
        """Get services by provider"""
        return storage_broker.get(
            ProvidedService,
            {ProvidedService.provided_service_product_provider_id: provider_id},
            [],
            None,
            offset,
            limit
        )
    
    def get_services(self, offset: int = 0, limit: int = 100) -> List[ProvidedService]:
        """Get all services"""
        return storage_broker.get(
            ProvidedService,
            {},
            [],
            None,
            offset,
            limit
        )
    
    def get_package_items_by_service(self, service_id: int) -> List[ServicePackageItem]:
        """Get package items by service ID"""
        return storage_broker.get(
            ServicePackageItem,
            {ServicePackageItem.service_package_item_service_id: service_id},
            [],
            None,
            0,
            10
        )
    
    def get_cart_items_by_service(self, service_id: int) -> List[OrderedService]:
        """Get ordered services by service ID"""
        return storage_broker.get(
            OrderedService,
            {OrderedService.ordered_service_service_id: service_id},
            [],
            None,
            0,
            10
        )
    
    def get_active_services(self, provider_id: Optional[int] = None) -> List[ProvidedService]:
        """Get active services"""
        conditions = {ProvidedService.provided_service_is_active: True}
        if provider_id:
            conditions[ProvidedService.provided_service_product_provider_id] = provider_id
        
        return storage_broker.get(ProvidedService, conditions, [], None)
    
    def create_service(self, service: ProvidedService) -> ProvidedService:
        """Create a new service"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(service)
    
    def update_service(self, service: ProvidedService) -> ProvidedService:
        """Update an existing service"""
        from features.insertion import update_record_in_api
        return update_record_in_api(service)
    
    def delete_service_resource_requirements(self, requirement: ServiceResourceRequirement) -> bool:
        """Delete a service resource requirement"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(requirement)
    
    def delete_service_staff_requirements(self, requirement: ServiceStaffRequirement) -> bool:
        """Delete a service staff requirement"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(requirement)
    
    def delete_service(self, service: ProvidedService) -> bool:
        """Delete a service"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(service)
    
    def get_service_resource_requirements(self, service_id: int) -> List[ServiceResourceRequirement]:
        """Get resource requirements for a service"""
        return storage_broker.get(
            ServiceResourceRequirement,
            {ServiceResourceRequirement.service_resource_requirement_service_id: service_id},
            [],
            None
        )
    
    def get_service_staff_requirements(self, service_id: int) -> List[ServiceStaffRequirement]:
        """Get staff requirements for a service"""
        return storage_broker.get(
            ServiceStaffRequirement,
            {ServiceStaffRequirement.service_staff_requirement_service_id: service_id},
            [],
            None
        )
    
    def create_resource_requirement(self, requirement: ServiceResourceRequirement) -> ServiceResourceRequirement:
        """Create a new resource requirement."""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(requirement)

    def create_staff_requirement(self, requirement: ServiceStaffRequirement) -> ServiceStaffRequirement:
        """Create a new staff requirement."""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(requirement)

    def get_resource_requirement_by_id(self, requirement_id: int) -> Optional[ServiceResourceRequirement]:
        """Get a resource requirement by ID."""
        records = storage_broker.get(
            ServiceResourceRequirement,
            {ServiceResourceRequirement.service_resource_requirement_id: requirement_id},
            [],
            None
        )
        return records[0] if records else None

    def get_staff_requirement_by_id(self, requirement_id: int) -> Optional[ServiceStaffRequirement]:
        """Get a staff requirement by ID."""
        records = storage_broker.get(
            ServiceStaffRequirement,
            {ServiceStaffRequirement.service_staff_requirement_id: requirement_id},
            [],
            None
        )
        return records[0] if records else None

    def delete_resource_requirement(self, requirement_id: int) -> bool:
        """Delete a resource requirement by ID."""
        from features.insertion import delete_record_from_api
        requirement = self.get_resource_requirement_by_id(requirement_id)
        if requirement:
            return delete_record_from_api(requirement)
        return False

    def delete_staff_requirement(self, requirement_id: int) -> bool:
        """Delete a staff requirement by ID."""
        from features.insertion import delete_record_from_api
        requirement = self.get_staff_requirement_by_id(requirement_id)
        if requirement:
            return delete_record_from_api(requirement)
        return False
