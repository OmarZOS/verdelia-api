# routers/business_routers/delivery_router.py
"""
Delivery router for managing deliveries, tracking, and bulk operations.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, Query, status, HTTPException
from typing import Optional, List
import logging

from core.models.api_models import Delivery_API, DeliveryUpdate_API, DeliveryStatus, Location_API
from core.response_models import ErrorResponseModel, get_crud_error_responses
from core.exceptions.specific.delivery_exceptions import (
    DeliveryNotFoundException,
    DeliveryCreationFailedException,
    DeliveryUpdateFailedException,
    DeliveryDeleteFailedException,
    DeliveryValidationFailedException,
    DeliveryCannotBeUpdatedException,
    DeliveryBulkUpdateFailedException,
    DeliveryBulkDeleteFailedException,
    DeliveryStatusInvalidException,
    AddressNotFoundException
)
from services.delivery_service import DeliveryService
from services.location_service import LocationService

from core.logging_config import get_logger

logger = get_logger(__name__)


address_router = APIRouter()


def get_delivery_service() -> DeliveryService:
    """Dependency to get DeliveryService instance"""
    return DeliveryService()


def get_location_service() -> LocationService:
    """Dependency to get LocationService instance"""
    return LocationService()


# ==================== Address Endpoints ====================

@address_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    summary="Create address",
    description="Create a new address",
    responses={
        201: {"description": "Address created successfully"},
        400: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False, include_409=True)
    }
)
def create_address(
    address_data: Location_API,
    location_service: LocationService = Depends(get_location_service)
):
    """
    Create a new address.
    """
    logger.info(f"Creating new address")
    
    try:
        # Create address using location service
        address = location_service.create_address_from_location(address_data)
        return {
            "id_address": address.id_address,
            "message": "Address created successfully"
        }
    except Exception as e:
        logger.error(f"Failed to create address: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create address: {str(e)}"
        )


@address_router.get(
    "/{address_id}",
    response_model=dict,
    summary="Get address by ID",
    description="Get address by ID",
    responses={
        200: {"description": "Address retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def get_address(
    address_id: int,
    location_service: LocationService = Depends(get_location_service)
):
    """
    Get address by ID.
    """
    logger.info(f"Fetching address with ID: {address_id}")
    
    try:
        address = location_service.get_address_by_id(address_id)
        if not address:
            raise AddressNotFoundException(address_id=address_id)
        
        return {
            "id_address": address.id_address,
            "address_street": address.address_street,
            "address_city": address.address_city,
            "address_postal_code": address.address_postal_code,
            "address_country": address.address_country,
            # "coordinates": address.location.position_wkt,
            # "location_longitude": address.location_longitude,
            # "location_name": address.location.location_name
        }
    except AddressNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to get address {address_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve address: {str(e)}"
        )


@address_router.put(
    "/{address_id}",
    response_model=dict,
    summary="Update address",
    description="Update an existing address",
    responses={
        200: {"description": "Address updated successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def update_address(
    address_id: int,
    address_data: Location_API,
    location_service: LocationService = Depends(get_location_service)
):
    """
    Update an existing address.
    """
    logger.info(f"Updating address with ID: {address_id}")
    
    try:
        address = location_service.update_address(address_id, address_data)
        if not address:
            raise AddressNotFoundException(address_id=address_id)
        
        return {
            "id_address": address.id_address,
            "message": "Address updated successfully"
        }
    except AddressNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to update address {address_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update address: {str(e)}"
        )


@address_router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete address",
    description="Delete an address",
    responses={
        204: {"description": "Address deleted successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def delete_address(
    address_id: int,
    location_service: LocationService = Depends(get_location_service)
):
    """
    Delete an address.
    """
    logger.info(f"Deleting address with ID: {address_id}")
    
    try:
        success = location_service.delete_address(address_id)
        if not success:
            raise AddressNotFoundException(address_id=address_id)
        return None  # 204 No Content
    except AddressNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete address {address_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete address: {str(e)}"
        )