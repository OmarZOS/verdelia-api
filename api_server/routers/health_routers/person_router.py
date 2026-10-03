# routers/person_router.py
"""
Person router for managing person records, blood types, and person details.
"""

from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List
import logging

from core.responses.person_responses import BloodTypeResponseModel, PersonResponseModel
from core.models.api_models import Person_API, Location_API
from core.response_models import (
    SuccessResponseModel,
    ErrorResponseModel,
    get_crud_error_responses
)
from services.person_service import PersonService

from core.logging_config import get_logger

logger = get_logger(__name__)


person_router = APIRouter(
    # tags=["People"],
    # prefix="/people/api/v1/people"
)


def get_person_service() -> PersonService:
    """Dependency to get PersonService instance"""
    return PersonService()





# ==================== Person Endpoints ====================

@person_router.get(
    "/people/{person_id}",
    response_model=SuccessResponseModel[PersonResponseModel],
    summary="Get person by ID",
    description="Retrieve a person by their ID",
    responses={
        200: {
            "description": "Person retrieved successfully",
            "model": SuccessResponseModel[PersonResponseModel]
        },
        **get_crud_error_responses(include_404=True)
    }
)
def get_person(
    person_id: str,
    full: bool = Query(False, description="Include all related data (blood type, location, etc.)"),
    person_service: PersonService = Depends(get_person_service)
):
    """
    Get person by ID.
    
    - **person_id**: Person ID to fetch (path parameter)
    - **full**: Include all related data (blood type, location, etc.)
    """
    logger.info(f"Fetching person with ID: {person_id} (full={full})")
    
    result = person_service.get_person_by_id(person_id, full)
    
    return SuccessResponseModel(
        success=True,
        data=result,
        message=f"Person {person_id} retrieved successfully",
        details={"full_data": full}
    )


@person_router.post(
    "/people",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponseModel[PersonResponseModel],
    summary="Create or update person",
    description="Create a new person or update an existing one",
    responses={
        201: {
            "description": "Person created/updated successfully",
            "model": SuccessResponseModel[PersonResponseModel]
        },
        400: {
            "description": "Bad Request - Invalid data",
            "model": ErrorResponseModel
        },
        404: {
            "description": "Blood type not found",
            "model": ErrorResponseModel
        },
        409: {
            "description": "Conflict - Duplicate person",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=True, include_409=True)
    }
)
def create_or_update_person(
    person: Person_API,
    location: Location_API,
    person_service: PersonService = Depends(get_person_service)
):
    """
    Create or update a person.
    
    - **person**: Person details (request body)
    - **location**: Location details (request body)
    """
    logger.info(f"Creating/updating person: {person.person_first_name} {person.person_last_name}")
    
    result = person_service.refresh_or_insert_person(person, location)
    
    person_id = getattr(result, 'id_person', None)
    
    return SuccessResponseModel(
        success=True,
        message="Person saved successfully",
        data=result,
        details={
            "person_id": person_id,
            "full_name": f"{person.person_first_name} {person.person_last_name}",
            "action": "created" if person.id_person == 0 else "updated"
        }
    )


@person_router.delete(
    "/people/{person_id}",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponseModel,
    summary="Delete person",
    description="Delete a person by ID",
    responses={
        200: {
            "description": "Person deleted successfully",
            "model": SuccessResponseModel
        },
        400: {
            "description": "Bad Request - Cannot delete person with dependencies",
            "model": ErrorResponseModel
        },
        **get_crud_error_responses(include_404=True)
    }
)
def delete_person(
    person_id: str,
    force_delete: bool = Query(False, description="Force delete even if person has dependencies"),
    person_service: PersonService = Depends(get_person_service)
):
    """
    Delete a person.
    
    - **person_id**: Person ID to delete (path parameter)
    - **force_delete**: Force delete even if person has dependencies (query parameter)
    """
    logger.info(f"Deleting person with ID: {person_id} (force={force_delete})")
    
    result = person_service.delete_person(person_id)
    
    return SuccessResponseModel(
        success=True,
        message=f"Person {person_id} deleted successfully",
        data=result,
        details={"force_deleted": force_delete}
    )


# ==================== Blood Type Endpoints ====================

@person_router.get(
    "/people/blood-types/all",
    response_model=SuccessResponseModel[List[BloodTypeResponseModel]],
    summary="Get all blood types",
    description="Retrieve all available blood types",
    responses={
        200: {
            "description": "Blood types retrieved successfully",
            "model": SuccessResponseModel[List[BloodTypeResponseModel]]
        },
        **get_crud_error_responses(include_404=False)
    }
)
def get_blood_types(
    person_service: PersonService = Depends(get_person_service)
):
    """
    Get all blood types.
    """
    logger.info("Fetching all blood types")
    
    result = person_service.get_all_blood_types()
    
    return SuccessResponseModel(
        success=True,
        data=result,
        message=f"Found {len(result) if isinstance(result, list) else 0} blood types",
        details={"total_count": len(result) if isinstance(result, list) else 0}
    )


@person_router.get(
    "/people/blood-type/{blood_type_id}",
    response_model=SuccessResponseModel[BloodTypeResponseModel],
    summary="Get blood type by ID",
    description="Retrieve a specific blood type by its ID",
    responses={
        200: {
            "description": "Blood type retrieved successfully",
            "model": SuccessResponseModel[BloodTypeResponseModel]
        },
        **get_crud_error_responses(include_404=True)
    }
)
def get_blood_type(
    blood_type_id: str,
    person_service: PersonService = Depends(get_person_service)
):
    """
    Get blood type by ID.
    
    - **blood_type_id**: Blood type ID to fetch (path parameter)
    """
    logger.info(f"Fetching blood type with ID: {blood_type_id}")
    
    result = person_service.get_blood_type_by_id(blood_type_id)
    
    return SuccessResponseModel(
        success=True,
        data=result,
        message=f"Blood type {blood_type_id} retrieved successfully"
    )


# ================= Additional Person Endpoints =================

@person_router.get(
    "/people",
    response_model=SuccessResponseModel[List[PersonResponseModel]],
    summary="Get all persons",
    description="Retrieve all persons with pagination",
    responses={
        200: {
            "description": "Persons retrieved successfully",
            "model": SuccessResponseModel[List[PersonResponseModel]]
        },
        **get_crud_error_responses(include_404=False)
    }
)
def get_all_persons(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return (max 1000)"),
    person_service: PersonService = Depends(get_person_service)
):
    """
    Get all persons with pagination.
    
    - **offset**: Pagination offset (query parameter)
    - **limit**: Number of records to return (query parameter, max 1000)
    """
    logger.info(f"Fetching all persons (offset={offset}, limit={limit})")
    
    # This method would need to be implemented in the service
    result = person_service.get_all_persons(offset, limit)
    
    return SuccessResponseModel(
        success=True,
        data=result,
        message=f"Found {len(result) if isinstance(result, list) else 0} persons",
        details={
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": len(result) if isinstance(result, list) else 0
            }
        }
    )


@person_router.get(
    "/people/search/name",
    response_model=SuccessResponseModel[List[PersonResponseModel]],
    summary="Search persons by name",
    description="Search for persons by first name or last name",
    responses={
        200: {
            "description": "Persons found successfully",
            "model": SuccessResponseModel[List[PersonResponseModel]]
        },
        **get_crud_error_responses(include_404=False)
    }
)
def search_persons_by_name(
    first_name: Optional[str] = Query(None, description="First name to search"),
    last_name: Optional[str] = Query(None, description="Last name to search"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    person_service: PersonService = Depends(get_person_service)
):
    """
    Search for persons by first name or last name.
    
    - **first_name**: First name to search (query parameter)
    - **last_name**: Last name to search (query parameter)
    - **limit**: Maximum number of results (query parameter, max 100)
    """
    logger.info(f"Searching persons - first_name:{first_name}, last_name:{last_name}, limit:{limit}")
    
    result = person_service.search_persons(first_name, last_name, limit)
    
    return SuccessResponseModel(
        success=True,
        data=result,
        message=f"Found {len(result) if isinstance(result, list) else 0} persons matching the search",
        details={
            "search_criteria": {
                "first_name": first_name,
                "last_name": last_name
            },
            "limit": limit,
            "total_found": len(result) if isinstance(result, list) else 0
        }
    )