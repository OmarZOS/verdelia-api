# routers/business_routers/service_router.py
"""
Service router for managing provided services, requirements, and staff assignments.
"""

from fastapi import APIRouter, Depends, Query, status
from typing import List, Optional
import logging

from services.helpers.auth.auth_dependencies import get_current_user_id
from core.models.api_models import (
    ProvidedService_API, 
    ServiceResourceRequirement_API, 
    ServiceStaffRequirement_API
)
from core.exceptions.specific.service_exceptions import (
    ServiceException,
    ServiceNotFoundException,
    ServiceCreationFailedException,
    ServiceUpdateFailedException,
    ServiceDeleteFailedException,
    ServiceCategoryNotFoundException,
    ServiceProviderNotFoundException,
    ServiceToggleStatusException,
    ServiceRequirementCreationException
)
from services.service_service import ServiceService

from core.logging_config import get_logger

logger = get_logger(__name__)

service_router = APIRouter()

def get_service_service() -> ServiceService:
    """Dependency to get ServiceService instance"""
    return ServiceService()


# ==================== Service Listing Endpoints ====================

@service_router.get(
    "/services",
    # response_model=List[ProvidedService_API],
    summary="Get services with filters",
    description="Retrieve services filtered by category, provider, or active status"
)
def get_services(
    category_id: int = Query(0, description="Filter by category ID"),
    provider_id: int = Query(0, description="Filter by provider ID"),
    active_only: bool = Query(False, description="Show only active services"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    service_service: ServiceService = Depends(get_service_service)
):
    """
    Get services with various filters.
    """
    logger.info(f"Fetching services with filters - category:{category_id}, provider:{provider_id}, active_only:{active_only}")
    
    try:
        if active_only:
            result = service_service.get_active_services(provider_id if provider_id > 0 else None)
        elif category_id > 0:
            result = service_service.get_services_by_category(category_id, offset, limit)
        elif provider_id > 0:
            result = service_service.get_services_by_provider(provider_id, offset, limit)
        else:
            result = service_service.get_services( offset, limit)
        
        logger.info(f"Found {len(result)} services")
        return result
        
    except (ServiceCategoryNotFoundException, ServiceProviderNotFoundException) as e:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch services: {e}")
        raise ServiceException(
            message="Failed to retrieve services",
            details={"error": str(e)}
        )


# ==================== Single Service Operations ====================

@service_router.get(
    "/services/categories",
    # response_model=ProvidedService_API,
    summary="Get service categories",
    description="Retrieve all service categories"
)
def get_service_categories(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    service_service: ServiceService = Depends(get_service_service)
):
    """
    Get service categories.
    """
    logger.info(f"Fetching service categories - offset:{offset}, limit:{limit}")
    
    try:
        categories = service_service.get_categories(offset, limit)
        logger.info(f"Found {len(categories)} service categories")
        return categories
        
    except Exception as e:
        logger.error(f"Failed to fetch service categories: {e}")
        raise ServiceException(
            message="Failed to retrieve service categories",
            details={"error": str(e)}
        )


@service_router.get(
    "/services/{service_id}",
    # response_model=ProvidedService_API,
    summary="Get service by ID",
    description="Retrieve a specific service by its ID"
)
def get_service(
    service_id: int,
    service_service: ServiceService = Depends(get_service_service)
):
    """
    Get service by ID.
    """
    logger.info(f"Fetching service with ID: {service_id}")
    
    try:
        service = service_service.get_service_by_id(service_id)
        if not service:
            raise ServiceNotFoundException(service_id=service_id)
        
        return service
        
    except ServiceNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch service {service_id}: {e}")
        raise ServiceNotFoundException(
            service_id=service_id,
            details={"error": str(e)}
        )



@service_router.post(
    "/services",
    status_code=status.HTTP_201_CREATED,
    # response_model=ProvidedService_API,
    summary="Create a new service",
    description="Creates a new service with resource and staff requirements"
)
def create_service(
    service: ProvidedService_API,
    requirements: List[ServiceResourceRequirement_API],
    staff_requirements: List[ServiceStaffRequirement_API],
    user_id: int = Depends(get_current_user_id),
    service_service: ServiceService = Depends(get_service_service)
):
    """
    Create a new service.
    """
    logger.info(f"Creating new service: {service.provided_service_name}")
    
    if not service.provided_service_name:
        raise ServiceCreationFailedException(
            error="Service name is required",
            service_name=service.provided_service_name,
            provider_id=service.provided_service_product_provider_id
        )
    
    try:
        created_service = service_service.create_service(
            service, requirements, staff_requirements
        )
        logger.info(f"Service created with ID: {getattr(created_service, 'provided_service_id', 'unknown')}")
        return created_service
        
    except (ServiceCreationFailedException, ServiceRequirementCreationException) as e:
        raise
    except Exception as e:
        logger.error(f"Failed to create service: {e}")
        raise ServiceCreationFailedException(
            error=str(e),
            service_name=service.provided_service_name,
            provider_id=service.provided_service_product_provider_id
        )


@service_router.put(
    "/services/{service_id}",
    # response_model=ProvidedService_API,
    summary="Update a service",
    description="Update an existing service's details"
)
def update_service(
    service_id: int,
    service: ProvidedService_API,
    user_id: int = Depends(get_current_user_id),
    service_service: ServiceService = Depends(get_service_service)
):
    """
    Update an existing service.
    """
    logger.info(f"Updating service with ID: {service_id}")
    
    try:
        existing_service = service_service.get_service_by_id(service_id)
        if not existing_service:
            raise ServiceNotFoundException(service_id=service_id)
        
        if hasattr(service, 'provided_service_id'):
            service.provided_service_id = service_id
        
        updated_service = service_service.update_service(service_id, service)
        logger.info(f"Service {service_id} updated successfully")
        return updated_service
        
    except (ServiceNotFoundException, ServiceUpdateFailedException):
        raise
    except Exception as e:
        logger.error(f"Failed to update service {service_id}: {e}")
        raise ServiceUpdateFailedException(
            service_id=service_id,
            error=str(e),
            fields_attempted=["service_details"]
        )


@service_router.patch(
    "/services/{service_id}/toggle",
    # response_model=ProvidedService_API,
    summary="Toggle service status",
    description="Activate or deactivate a service"
)
def toggle_service(
    service_id: int,
    is_active: bool = Query(..., description="True to activate, False to deactivate"),
    user_id: int = Depends(get_current_user_id),
    service_service: ServiceService = Depends(get_service_service)
):
    """
    Activate or deactivate a service.
    """
    action = "activate" if is_active else "deactivate"
    logger.info(f"Attempting to {action} service {service_id}")
    
    try:
        existing_service = service_service.get_service_by_id(service_id)
        if not existing_service:
            raise ServiceNotFoundException(service_id=service_id)
        
        current_status = getattr(existing_service, 'provided_service_is_active', False)
        if current_status == is_active:
            raise ServiceToggleStatusException(
                service_id=service_id,
                current_status=current_status,
                requested_status=is_active,
                error="Service already in requested state"
            )
        
        updated_service = service_service.toggle_service_status(service_id, is_active)
        logger.info(f"Service {service_id} {action}d successfully")
        return updated_service
        
    except (ServiceNotFoundException, ServiceToggleStatusException, ServiceUpdateFailedException):
        raise
    except Exception as e:
        logger.error(f"Failed to toggle service {service_id} status: {e}")
        raise ServiceToggleStatusException(
            service_id=service_id,
            requested_status=is_active,
            error=str(e)
        )


@service_router.delete(
    "/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a service",
    description=(
        "Deletes a service. When the service has requirements and "
        "`force_delete=false` (the default), the request is refused "
        "with 409. Pass `force_delete=true` to cascade the requirement "
        "deletions."
    ),
)
def delete_service(
    service_id: int,
    force_delete: bool = Query(
        False,
        description="Cascade delete requirements and refuse-if-in-use check",
    ),
    user_id: int = Depends(get_current_user_id),
    service_service: ServiceService = Depends(get_service_service),
):
    """
    Delete a service.

    Raises:
        ServiceNotFoundException: 404 if the service doesn't exist.
        ServiceDeleteFailedException: 409 if the service has
            dependencies or requirements and force_delete is false;
            500 if the delete fails for another reason.
    """
    logger.info(
        f"Deleting service with ID: {service_id} (force={force_delete})"
    )

    # The service layer owns the delete policy — existence check,
    # dependency check, requirement cascade, and the actual delete.
    # The router just forwards the call and translates exceptions to
    # HTTP responses.
    service_service.delete_service(service_id, force_delete=force_delete)
    logger.info(f"Service {service_id} deleted successfully")
    return None  # 204 No Content


# ==================== Additional Service Endpoints ====================

@service_router.get(
    "/services/category/{category_id}/roles",
    # response_model=List[ProvidedService_API],
    summary="Get roles by service category",
    description="Retrieve all roles in a specific service category"
)
def get_roles_by_service_category(
    category_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service_service: ServiceService = Depends(get_service_service)
):
    """
    Get all roles in a specific service category.
    """
    logger.info(f"Fetching roles for category {category_id}")
    
    try:
        roles = service_service.get_roles_by_service_category(category_id, offset, limit)
        return roles
        
    except ServiceCategoryNotFoundException as e:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch roles for category {category_id}: {e}")
        raise ServiceCategoryNotFoundException(
            category_id=category_id,
            details={"error": str(e)}
        )


@service_router.get(
    "/services/category/{category_id}",
    # response_model=List[ProvidedService_API],
    summary="Get services by category",
    description="Retrieve all services in a specific category"
)
def get_services_by_category(
    category_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service_service: ServiceService = Depends(get_service_service)
):
    """
    Get all services in a specific category.
    """
    logger.info(f"Fetching services for category {category_id}")
    
    try:
        services = service_service.get_services_by_category(category_id, offset, limit)
        return services
        
    except ServiceCategoryNotFoundException as e:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch services for category {category_id}: {e}")
        raise ServiceCategoryNotFoundException(
            category_id=category_id,
            details={"error": str(e)}
        )


@service_router.get(
    "/services/provider/{provider_id}",
    # response_model=List[ProvidedService_API],
    summary="Get services by provider",
    description="Retrieve all services offered by a specific provider"
)
def get_services_by_provider(
    provider_id: int,
    active_only: bool = Query(False, description="Show only active services"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service_service: ServiceService = Depends(get_service_service)
):
    """
    Get all services offered by a specific provider.
    """
    logger.info(f"Fetching services for provider {provider_id} (active_only={active_only})")
    
    try:
        if active_only:
            services = service_service.get_active_services(provider_id)
        else:
            services = service_service.get_services_by_provider(provider_id, offset, limit)
        
        return services
        
    except ServiceProviderNotFoundException as e:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch services for provider {provider_id}: {e}")
        raise ServiceProviderNotFoundException(
            provider_id=provider_id,
            details={"error": str(e)}
        )


@service_router.get(
    "/services/{service_id}/requirements",
    # response_model=List[ServiceResourceRequirement_API],
    summary="Get service requirements",
    description="Retrieve all resource requirements for a service"
)
def get_service_requirements(
    service_id: int,
    service_service: ServiceService = Depends(get_service_service)
):
    """
    Get all resource requirements for a service.
    """
    logger.info(f"Fetching requirements for service {service_id}")
    
    try:
        service = service_service.get_service_by_id(service_id)
        if not service:
            raise ServiceNotFoundException(service_id=service_id)
        
        requirements = service_service.get_service_requirements(service_id)
        return requirements
        
    except ServiceNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch requirements for service {service_id}: {e}")
        raise ServiceException(
            message="Failed to retrieve service requirements",
            details={"service_id": service_id, "error": str(e)}
        )


@service_router.get(
    "/services/{service_id}/staff-requirements",
    # response_model=List[ServiceStaffRequirement_API],
    summary="Get service staff requirements",
    description="Retrieve all staff requirements for a service"
)
def get_service_staff_requirements(
    service_id: int,
    service_service: ServiceService = Depends(get_service_service)
):
    """
    Get all staff requirements for a service.
    """
    logger.info(f"Fetching staff requirements for service {service_id}")
    
    try:
        service = service_service.get_service_by_id(service_id)
        if not service:
            raise ServiceNotFoundException(service_id=service_id)
        
        staff_requirements = service_service.get_service_staff_requirements(service_id)
        return staff_requirements
        
    except ServiceNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch staff requirements for service {service_id}: {e}")
        raise ServiceException(
            message="Failed to retrieve staff requirements",
            details={"service_id": service_id, "error": str(e)}
        )