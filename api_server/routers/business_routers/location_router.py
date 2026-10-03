# routers/location_router.py
"""
Location router for managing locations and addresses.
"""

from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List, Dict, Any
import logging

from core.exceptions.specific.delivery_exceptions import AddressNotFoundException
from core.exceptions.handler import LocationDeleteFailedException, LocationNotFoundException
from core.models.api_models import Location_API, Delivery_API
from core.response_models import ErrorResponseModel, get_crud_error_responses
from services.location_service import LocationService

from core.logging_config import get_logger

logger = get_logger(__name__)


location_router = APIRouter()


def get_location_service() -> LocationService:
    """Dependency to get LocationService instance"""
    return LocationService()


# ==================== Location Endpoints ====================

@location_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    # response_model=Location_API,
    summary="Create location",
    description="Create a new location",
    responses={
        201: {"description": "Location created successfully"},
        400: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False, include_409=True)
    }
)
def create_location(
    location: Location_API,
    location_service: LocationService = Depends(get_location_service)
):
    """
    Create a new location.
    """
    logger.info(f"Creating new location with name: {location.location_name}")
    return location_service.create_location(location)


@location_router.get(
    "/{location_id}",
    # response_model=Location_API,
    summary="Get location",
    description="Get location by ID",
    responses={
        200: {"description": "Location retrieved successfully"},
        **get_crud_error_responses(include_404=True)
    }
)
def get_location(
    location_id: str,
    with_address: bool = Query(True, description="Include address details"),
    location_service: LocationService = Depends(get_location_service)
):
    """
    Get location by ID.
    """
    logger.info(f"Fetching location with ID: {location_id} (with_address={with_address})")
    
    if with_address:
        result = location_service.get_location_with_address(location_id)
    else:
        result = location_service.get_location_by_id(location_id, with_address=False)
    
    if not result:
        raise LocationNotFoundException(location_id=location_id)
    
    return result


@location_router.put(
    "/{location_id}",
    # response_model=Location_API,
    summary="Update location",
    description="Update an existing location",
    responses={
        200: {"description": "Location updated successfully"},
        400: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def update_location(
    location_id: str,
    location: Location_API,
    location_service: LocationService = Depends(get_location_service)
):
    """
    Update an existing location.
    """
    logger.info(f"Updating location with ID: {location_id}")
    return location_service.update_location(location_id, location)


@location_router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete location",
    description="Delete a location",
    responses={
        204: {"description": "Location deleted successfully"},
        400: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def delete_location(
    location_id: str,
    force_delete: bool = Query(False, description="Force delete even if location has references"),
    location_service: LocationService = Depends(get_location_service)
):
    """
    Delete a location.
    """
    logger.info(f"Deleting location with ID: {location_id} (force={force_delete})")
    
    success = location_service.delete_location(location_id, force_delete)
    if not success:
        raise LocationDeleteFailedException(
            location_id=location_id,
            error="Location not found or cannot be deleted"
        )
    
    return None  # 204 No Content


# ==================== Address Endpoints ====================

@location_router.post(
    "/address/from-delivery",
    status_code=status.HTTP_201_CREATED,
    # response_model=Address_API,
    summary="Create address from delivery",
    description="Create an address from delivery information",
    responses={
        201: {"description": "Address created successfully"},
        400: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False)
    }
)
def create_address_from_delivery(
    delivery: Delivery_API,
    location_service: LocationService = Depends(get_location_service)
):
    """
    Create an address from delivery information.
    """
    logger.info("Creating address from delivery information")
    
    address = location_service.build_address_from_delivery(delivery)
    result = location_service.address_repo.create_address(address)
    
    return result


@location_router.get(
    "/address/{address_id}",
    # response_model=Address_API,
    summary="Get address",
    description="Get address by ID",
    responses={
        200: {"description": "Address retrieved successfully"},
        **get_crud_error_responses(include_404=True)
    }
)
def get_address(
    address_id: str,
    location_service: LocationService = Depends(get_location_service)
):
    """
    Get address by ID.
    """
    logger.info(f"Fetching address with ID: {address_id}")
    
    result = location_service.get_address_by_id(address_id)
    if not result:
        raise AddressNotFoundException(address_id=address_id)
    
    return result


@location_router.put(
    "/address/{address_id}",
    # response_model=Address_API,
    summary="Update address",
    description="Update an address",
    responses={
        200: {"description": "Address updated successfully"},
        400: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def update_address(
    address_id: str,
    address_data: Dict[str, Any],
    location_service: LocationService = Depends(get_location_service)
):
    """
    Update an address.
    """
    logger.info(f"Updating address with ID: {address_id}")
    return location_service.update_address(address_id, address_data)