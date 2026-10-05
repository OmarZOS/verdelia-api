# routers/business_routers/staff_router.py
"""
Staff router for managing staff assignments (management rules).
"""

from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List
import logging

from workflows.team_workflow import TeamWorkflow
from services.helpers.auth.auth_dependencies import get_current_user_id
from core.models.api_models import ManagementRule_API
from core.response_models import ErrorResponseModel, get_crud_error_responses
from core.exceptions.specific.staff_exceptions import (
    StaffException,
    RuleNotFoundException,
    RuleAlreadyExistsException,
    RuleInsertFailedException,
    RuleUpdateFailedException,
    RuleDeleteFailedException,
    RuleInvalidStatusException,
    InvitationAlreadyProcessedException,
    OrganisationNotFoundExceptionForStaff
)
from services.management_rule_service import ManagementRuleService

from core.logging_config import get_logger
logger = get_logger(__name__)


staff_router = APIRouter()

def get_team_workflow() -> TeamWorkflow:
    return TeamWorkflow()

def get_management_rule_service() -> ManagementRuleService:
    """Dependency to get ManagementRuleService instance"""
    return ManagementRuleService()


# ==================== Staff Listing Endpoints ====================

@staff_router.get(
    "/staff",
    # response_model=List[ManagementRule_API],
    summary="Get staff members",
    description="Fetch staff members with pagination and filters",
    responses={
        # 200: {"description": "Staff members retrieved successfully"},
        **get_crud_error_responses(include_404=True)
    }
)
def get_staff(
    org_id: Optional[int] = Query(
        default=None,
        description="Filter by organisation ID",
        ge=0
    ),
    provider_id: Optional[int] = Query(
        default=None,
        description="Filter by provider ID",
        ge=0
    ),
    user_id: Optional[int] = Query(
        default=None,
        description="Filter by user ID",
        ge=0
    ),
    rule_id: Optional[int] = Query(
        default=None,
        description="Filter by specific rule ID",
        ge=0
    ),
    status: Optional[str] = Query(
        default=None,
        description="Filter by status (ACTIVE, PENDING, REJECTED, EXPIRED)",
        pattern="^(ACTIVE|PENDING|REJECTED|EXPIRED)$"
    ),
    offset: int = Query(
        default=0,
        description="Pagination offset",
        ge=0
    ),
    limit: int = Query(
        default=50,
        description="Maximum number of records to return (max 100)",
        ge=1,
        le=100
    ),
    rule_service: ManagementRuleService = Depends(get_management_rule_service)
):
    """
    Fetch staff members with pagination and filters.
    
    - **org_id**: Organisation ID filter
    - **provider_id**: Provider ID filter
    - **user_id**: User ID filter
    - **rule_id**: Specific rule ID filter
    - **status**: Filter by status (ACTIVE, PENDING, REJECTED, EXPIRED)
    - **offset**: Pagination offset
    - **limit**: Pagination limit (max 100)
    """
    logger.info(
        f"Fetching staff - org_id:{org_id}, provider_id:{provider_id}, "
        f"user_id:{user_id}, rule_id:{rule_id}, status:{status}, "
        f"offset:{offset}, limit:{limit}"
    )
    
    # Get staff members
    staff_members = rule_service.get_all_rules(
        org_id=org_id,
        supplier_id=provider_id,
        user_id=user_id,
        rule_id=rule_id,
        offset=offset,
        limit=limit
    )
    
    # Filter by status if provided
    if status and staff_members:
        staff_members = [
            member for member in staff_members 
            if getattr(member, 'management_rule_status', None) == status
        ]
    
    return staff_members



@staff_router.get(
    "/staff/user/{user_id}",
    # response_model=List[ManagementRule_API],
    summary="Get user staff assignments",
    description="Get all staff assignments for a specific user",
    responses={
        200: {"description": "User staff assignments retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def get_user_staff(
    user_id: int,
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, PENDING, REJECTED, EXPIRED)"),
    rule_service: ManagementRuleService = Depends(get_management_rule_service)
):
    """
    Get all staff assignments for a specific user.
    """
    logger.info(f"Fetching staff assignments for user {user_id} (status={status})")
    
    if status:
        return rule_service.get_user_rules(user_id, status.upper())
    return rule_service.get_user_rules(user_id)


@staff_router.get(
    "/staff/provider/{provider_id}",
    # response_model=List[ManagementRule_API],
    summary="Get provider staff",
    description="Get all staff members for a provider",
    responses={
        200: {"description": "Provider staff retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def get_provider_staff(
    provider_id: int,
    active_only: bool = Query(True, description="Return only active staff"),
    rule_service: ManagementRuleService = Depends(get_management_rule_service)
):
    """
    Get all staff members for a provider.
    """
    logger.info(f"Fetching staff for provider {provider_id} (active_only={active_only})")
    return rule_service.get_provider_staff(provider_id, active_only)


@staff_router.get(
    "/staff/pending/{user_id}",
    # response_model=List[ManagementRule_API],
    summary="Get pending invitations",
    description="Get all pending invitations for a user",
    responses={
        200: {"description": "Pending invitations retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def get_pending_invitations(
    user_id: int,
    rule_service: ManagementRuleService = Depends(get_management_rule_service)
):
    """
    Get all pending invitations for a user.
    """
    logger.info(f"Fetching pending invitations for user {user_id}")
    return rule_service.get_pending_invitations(user_id)


# ==================== Staff CRUD Operations ====================

@staff_router.post(
    "/staff",
    status_code=status.HTTP_201_CREATED,
    summary="Create staff assignment",
    description="Insert a new staff member (create a management rule)",
    responses={
        201: {"description": "Staff assignment created successfully"},
        400: {"model": ErrorResponseModel},
        402: {
            "description": (
                "Payment required — the caller's plan does not allow "
                "team members"
            ),
            "model": ErrorResponseModel,
        },
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
        429: {
            "description": "Plan limit exceeded — team is full",
            "model": ErrorResponseModel,
        },
        **get_crud_error_responses(include_404=False, include_409=True),
    },
)
def insert_staff_details(
    rule: ManagementRule_API,
    user_id: int = Depends(get_current_user_id),
    workflow: TeamWorkflow = Depends(get_team_workflow),
):
    """Insert a new staff member (create a management rule).

    Enforces the plan's `team_members` limit, scoped to the rule's
    organisation. A rule created without `rule_ref_org` is not
    metered — it's not a team member.
    """
    logger.info(
        f"Creating new staff assignment for user: {rule.rule_ref_user} "
        f"(invited by user_id={user_id})"
    )
    return workflow.create_rule(rule, user_id=user_id)



@staff_router.put(
    "/staff/{staff_id}",
    # response_model=ManagementRule_API,
    summary="Update staff assignment",
    description="Update staff details",
    responses={
        200: {"description": "Staff assignment updated successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def update_staff_details(
    staff_id: int,
    staff: ManagementRule_API,
    rule_service: ManagementRuleService = Depends(get_management_rule_service)
):
    """
    Update staff details.
    """
    logger.info(f"Updating staff assignment with ID: {staff_id}")
    staff.id_management_rule = staff_id
    return rule_service.update_rule(staff)


@staff_router.put(
    "/staff/answer/{staff_id}",
    # response_model=ManagementRule_API,
    summary="Answer staff invitation",
    description="Answer a staff invitation (accept or reject)",
    responses={
        # 200: {"description": "Invitation answered successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def answer_staff_invitation(
    staff_id: int,
    accept: bool = Query(..., description="Accept (true) or reject (false) invitation"),
    user_id: int = Depends(get_current_user_id),
    rule_service: ManagementRuleService = Depends(get_management_rule_service)
):
    """
    Answer a staff invitation (accept or reject).
    """
    action = "accept" if accept else "reject"
    logger.info(f"Processing invitation {action} for staff assignment {staff_id}")
    return rule_service.answer_invitation(staff_id, accept,user_id)


@staff_router.delete(
    "/staff/delete/{staff_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete staff assignment",
    description="Delete a staff member by ID",
    responses={
        204: {"description": "Staff assignment deleted successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True)
    }
)
def delete_staff_by_id(
    staff_id: int,
    force_delete: bool = Query(False, description="Force delete even if assignment is active"),
    rule_service: ManagementRuleService = Depends(get_management_rule_service)
):
    """
    Delete a staff member by ID.
    """
    logger.info(f"Deleting staff assignment with ID: {staff_id} (force={force_delete})")
    rule_service.delete_rule(staff_id)
    return None  # 204 No Content