# routers/business_operation_router.py
"""
Business operation router for retrieving business operation data.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from typing import Dict, Optional, List, Any
import logging

from core.response_models import ErrorResponseModel, get_crud_error_responses
from core.exceptions.specific.business_exceptions import (
    BusinessOperationNotFoundException,
    BusinessOperationServiceException
)
from services.business_operation_service import BusinessOperationService

from core.logging_config import get_logger

logger = get_logger(__name__)


business_operation_router = APIRouter()


def get_business_operation_service() -> BusinessOperationService:
    """Dependency to get BusinessOperationService instance"""
    return BusinessOperationService()


# ==================== Response Model ====================



@business_operation_router.get(
    "/operations",
    summary="Get business operations",
    description="Get business operations with filters and aggregate statistics",
    responses={
        200: {"description": "Business operations retrieved successfully"},
        400: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=False, include_403=False)
    }
)
def get_business_operations(
    supplier_id: int = Query(0, description="Filter by supplier ID"),
    client_id: int = Query(0, description="Filter by client ID"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return (max 1000)"),
    date_from: Optional[datetime] = Query(None, description="Inclusive lower bound on created_at"),
    date_to: Optional[datetime] = Query(None, description="Inclusive upper bound on created_at"),
    include_stats: bool = Query(True, description="Include aggregate statistics"),
    operation_service: BusinessOperationService = Depends(get_business_operation_service),
):
    """
    Get business operations with filters and aggregate statistics.

    Response shape:
      - operations: list of per-operation dicts
      - stats:      totals, ratios, distributions by status/source/supplier/client/day
      - pagination: offset, limit, returned, total_in_window
      - window:     normalised date range applied
    """
    logger.info(
        f"Fetching business operations - supplier:{supplier_id}, client:{client_id}, "
        f"date_from:{date_from}, date_to:{date_to}, offset:{offset}, limit:{limit}, "
        f"include_stats:{include_stats}"
    )

    if date_from and date_to and date_from > date_to:
        raise BusinessOperationServiceException(
            message="Invalid time window",
            details={"error": "date_from must be <= date_to"},
        )

    try:
        return operation_service.get_operations(
            supplier_id=supplier_id if supplier_id > 0 else 0,
            client_id=client_id if client_id > 0 else 0,
            offset=offset,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
            include_stats=include_stats,
        )
    except Exception as e:
        logger.error(f"Failed to fetch business operations: {e}")
        raise BusinessOperationServiceException(
            message="Failed to retrieve business operations",
            details={"error": str(e)},
        )