# routers/supplier_router.py
"""
Supplier and Organisation router for managing suppliers, organisations, and their relationships.
"""

from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List
import logging

from services.helpers.auth.auth_dependencies import get_current_user_id
from core.exceptions.specific.supplier_exceptions import SupplierNotFoundException
from core.models.api_models import (
    Location_API, ProductProvider_API, ProviderImage_API,
    ProviderOrganisation_API, OrganisationImage_API
)
from core.response_models import (
    ErrorResponseModel,
    get_crud_error_responses
)
from core.models.models import ProductProvider, ProviderOrganisation
from services.supplier_service import SupplierService
from services.supplier_service import OrganisationService

from core.logging_config import get_logger

logger = get_logger(__name__)


supplier_router = APIRouter()


def get_supplier_service() -> SupplierService:
    return SupplierService()


def get_organisation_service() -> OrganisationService:
    return OrganisationService()


# ==================== Supplier Endpoints ====================

@supplier_router.get(
    "/suppliers",
    # # response_model=List[ProductProvider_API],
    summary="Get all suppliers",
    description="Retrieve all suppliers with pagination and filters",
    responses={
        # 200: {
        #     "description": "Suppliers retrieved successfully"
        # },
        **get_crud_error_responses(include_404=False)
    }
)
def get_all_suppliers(
    owner_id: int = Query(0, description="Filter by owner ID"),
    org_id: int = Query(0, description="Filter by organisation ID"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return (max 100)"),
    supplier_service: SupplierService = Depends(get_supplier_service)
):
    """
    Get all suppliers with pagination and filters.
    """
    logger.info(f"Fetching suppliers - owner_id:{owner_id}, org_id:{org_id}, offset:{offset}, limit:{limit}")
    return supplier_service.get_all_suppliers(owner_id, org_id, offset, limit)


@supplier_router.get(
    "/supplier-types",
    # # response_model=List[dict],
    summary="Get supplier types",
    description="Get all supplier types",
    responses={
        200: {
            "description": "Supplier types retrieved successfully"
        },
        **get_crud_error_responses(include_404=False)
    }
)
def get_supplier_types(
    supplier_service: SupplierService = Depends(get_supplier_service)
):
    """
    Get all supplier types.
    """
    logger.info("Fetching supplier types")
    return supplier_service.get_supplier_types()


@supplier_router.get(
    "/suppliers/search/location",
    # response_model=List[dict],
    summary="Search suppliers by location",
    description="Search suppliers by geographic location within a radius",
    responses={
        200: {
            "description": "Suppliers found successfully"
        },
        400: {
            "description": "Bad Request - Invalid coordinates",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=False)
    }
)
def search_suppliers_by_location(
    longitude: float = Query(..., description="Longitude coordinate", ge=-180, le=180),
    latitude: float = Query(..., description="Latitude coordinate", ge=-90, le=90),
    distance_km: float = Query(10, description="Search radius in kilometers", ge=1, le=500),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return (max 100)"),
    supplier_service: SupplierService = Depends(get_supplier_service)
):
    """
    Search suppliers by geographic location.
    """
    logger.info(f"Searching suppliers near ({longitude}, {latitude}) within {distance_km}km")
    return supplier_service.search_suppliers_by_location(
        longitude, latitude, distance_km, offset, limit
    )


@supplier_router.get(
    "/suppliers/{provider_id}",
    # response_model=ProductProvider_API,
    summary="Get supplier by ID",
    description="Retrieve a specific supplier by its ID",
    responses={
        200: {
            "description": "Supplier retrieved successfully"
        },
        **get_crud_error_responses(include_404=True)
    }
)

def get_supplier(
    provider_id: str,
    full: bool = Query(True, description="Include all related data (products, images, etc.)"),
    supplier_service: SupplierService = Depends(get_supplier_service)
):
    """
    Get supplier by ID.
    """
    logger.info(f"Fetching supplier with ID: {provider_id} (full={full})")
    return supplier_service.get_supplier_by_id(provider_id, full)


@supplier_router.post(
    "/suppliers/ids",
    status_code=status.HTTP_201_CREATED,
    # response_model=ProductProvider_API,
    summary="Get suppliers by IDs",
    description="Retrieve multiple suppliers by their IDs",
    responses={
        201: {
            "description": "Supplier created successfully"
        },
        400: {
            "description": "Bad Request - Invalid data",
            "model": ErrorResponseModel
        },
        409: {
            "description": "Conflict - Supplier already exists",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=False, include_409=True)
    }
)
def get_supplier_by_ids(
    provider_ids: List[str] = Query(..., description="List of supplier IDs to retrieve"),
    full: bool = Query(True, description="Include all related data (products, images, etc.)"),
    supplier_service: SupplierService = Depends(get_supplier_service)
):
    """
    Get suppliers by a list of IDs.
    """
    logger.info(f"Fetching suppliers with IDs: {provider_ids} (full={full})")
    return supplier_service.get_suppliers_by_ids(provider_ids, full)


@supplier_router.post(
    "/suppliers",
    status_code=status.HTTP_201_CREATED,
    # response_model=ProductProvider_API,
    summary="Create a new supplier",
    description="Create a new supplier with location and optional image",
    responses={
        201: {
            "description": "Supplier created successfully"
        },
        400: {
            "description": "Bad Request - Invalid data",
            "model": ErrorResponseModel
        },
        409: {
            "description": "Conflict - Supplier already exists",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=False, include_409=True)
    }
)
def create_supplier(
    provider: ProductProvider_API,
    location: Location_API,
    image: Optional[ProviderImage_API] = None,
    user_id: int = Depends(get_current_user_id),
    supplier_service: SupplierService = Depends(get_supplier_service)
):
    """
    Create a new supplier.
    """
    provider.id_provider_owner = user_id
    logger.info(f"Creating new supplier: {provider.provider_name}")
    return supplier_service.create_supplier(provider, location, image)


@supplier_router.put(
    "/suppliers/{provider_id}",
    # response_model=ProductProvider_API,
    summary="Update a supplier",
    description="Update an existing supplier's details",
    responses={
        200: {
            "description": "Supplier updated successfully"
        },
        **get_crud_error_responses(include_404=True)
    }
)
def update_supplier(
    provider_id: str,
    provider: ProductProvider_API,
    image: Optional[ProviderImage_API] = None,
    location: Optional[Location_API] = None,
    user_id: int = Depends(get_current_user_id),
    supplier_service: SupplierService = Depends(get_supplier_service)
):
    """
    Update an existing supplier.
    """
    logger.info(f"Updating supplier with ID: {provider_id}")
    provider.id_product_provider = provider_id
    return supplier_service.update_supplier(provider, image, location,user_id)


@supplier_router.delete(
    "/suppliers/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a supplier",
    description="Delete a supplier by ID",
    responses={
        204: {
            "description": "Supplier deleted successfully"
        },
        400: {
            "description": "Bad Request - Cannot delete supplier with dependencies",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=True)
    }
)
def delete_supplier(
    provider_id: str,
    force_delete: bool = Query(False, description="Force delete even if supplier has products"),
    user_id: int = Depends(get_current_user_id),
    supplier_service: SupplierService = Depends(get_supplier_service)
):
    """
    Delete a supplier.
    """
    logger.info(f"Deleting supplier with ID: {provider_id} (force={force_delete})")
    supplier_service.delete_supplier(provider_id,user_id)
    return None  # 204 No Content


# ==================== Organisation Endpoints ====================

@supplier_router.get(
    "/organisations",
    # response_model=List[ProviderOrganisation_API],
    summary="Get all organisations",
    description="Get all organisations with pagination",
    responses={
        200: {
            "description": "Organisations retrieved successfully"
        },
        **get_crud_error_responses(include_404=False)
    }
)
def get_all_organisations(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Number of records to return (max 500)"),
    organisation_service: OrganisationService = Depends(get_organisation_service)
):
    """
    Get all organisations with pagination.
    """
    logger.info(f"Fetching all organisations (offset={offset}, limit={limit})")
    return organisation_service.get_all_orgs(offset, limit)


@supplier_router.get(
    "/organisations/{org_id}",
    # response_model=ProviderOrganisation_API,
    summary="Get organisation by ID",
    description="Retrieve a specific organisation by its ID",
    responses={
        200: {
            "description": "Organisation retrieved successfully"
        },
        **get_crud_error_responses(include_404=True)
    }
)
def get_organisation(
    org_id: str,
    organisation_service: OrganisationService = Depends(get_organisation_service)
):
    """
    Get organisation by ID.
    """
    logger.info(f"Fetching organisation with ID: {org_id}")
    return organisation_service.get_org_by_id(org_id)


@supplier_router.post(
    "/organisations",
    status_code=status.HTTP_201_CREATED,
    # response_model=ProviderOrganisation_API,
    summary="Create a new organisation",
    description="Create a new organisation with optional image",
    responses={
        201: {
            "description": "Organisation created successfully"
        },
        400: {
            "description": "Bad Request - Invalid data",
            "model": ErrorResponseModel
        },
        409: {
            "description": "Conflict - Organisation already exists",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=False, include_409=True)
    }
)
def create_organisation(
    organisation: ProviderOrganisation_API,
    org_image: Optional[OrganisationImage_API] = None,
    user_id: int = Depends(get_current_user_id),
    organisation_service: OrganisationService = Depends(get_organisation_service)
):
    """
    Create a new organisation.
    """
    logger.info(f"Creating new organisation: {organisation.provider_organisation_name}")
    organisation.app_user_id = user_id
    return organisation_service.create_organisation(organisation, org_image)


@supplier_router.put(
    "/organisations/{org_id}",
    # response_model=ProviderOrganisation_API,
    summary="Update an organisation",
    description="Update an existing organisation's details",
    responses={
        200: {
            "description": "Organisation updated successfully"
        },
        **get_crud_error_responses(include_404=True)
    }
)
def update_organisation(
    org_id: str,
    organisation: ProviderOrganisation_API,
    org_image: Optional[OrganisationImage_API] = None,
    user_id: int = Depends(get_current_user_id),
    organisation_service: OrganisationService = Depends(get_organisation_service)
):
    """
    Update an existing organisation.
    """
    logger.info(f"Updating organisation with ID: {org_id}")
    organisation.id_provider_organisation = org_id
    organisation.app_user_id = user_id

    return organisation_service.update_organisation(organisation, org_image)


@supplier_router.delete(
    "/organisations/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an organisation",
    description="Delete an organisation by ID",
    responses={
        204: {
            "description": "Organisation deleted successfully"
        },
        400: {
            "description": "Bad Request - Cannot delete organisation with dependencies",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=True)
    }
)
def delete_organisation(
    org_id: str,
    force_delete: bool = Query(False, description="Force delete even if organisation has suppliers"),
    user_id: int = Depends(get_current_user_id),
    organisation_service: OrganisationService = Depends(get_organisation_service)
):
    """
    Delete an organisation.
    """
    logger.info(f"Deleting organisation with ID: {org_id} (force={force_delete})")
    organisation_service.delete_organisation(org_id,user_id)
    return None  # 204 No Content