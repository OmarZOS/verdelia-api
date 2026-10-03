"""
Validation logic for management rules.
"""

import logging
from typing import Optional

from core.models.api_models import ManagementRule_API
from core.exceptions.specific.staff_exceptions import (
    RuleInvalidStatusException,
    InvalidRuleCodeException,
    UserNotFoundExceptionForStaff,
    ProviderNotFoundExceptionForStaff,
    OrganisationNotFoundExceptionForStaff,
    RuleAlreadyExistsException,
    InvitationExpiredException,
    InvitationAlreadyProcessedException
)
from repositories.user_repository import UserRepository
from repositories.supplier_repository import OrganisationRepository, SupplierRepository
from repositories.management_rule_repository import ManagementRuleRepository

from core.logging_config import get_logger

logger = get_logger(__name__)



class RuleValidator:
    """Validator for management rule operations"""
    
    VALID_STATUSES = ["PENDING", "ACTIVE", "REJECTED", "EXPIRED", "INACTIVE"]
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.supplier_repo = SupplierRepository()
        self.org_repo = OrganisationRepository()
        self.rule_repo = ManagementRuleRepository()
    
    def validate_rule_data(self, rule_data: ManagementRule_API) -> None:
        """
        Validate rule data before creation/update.
        
        Args:
            rule_data: Rule data to validate
            
        Raises:
            InvalidRuleCodeException: If rule code is invalid
            RuleInvalidStatusException: If status is invalid
        """
        # Validate status
        if rule_data.management_rule_status not in self.VALID_STATUSES:
            logger.warning(f"Invalid rule status: {rule_data.management_rule_status}")
            raise RuleInvalidStatusException(
                requested_status=rule_data.management_rule_status,
                allowed_statuses=self.VALID_STATUSES
            )
    
    def validate_entities_exist(self, rule_data: ManagementRule_API) -> None:
        """
        Validate that all referenced entities exist.
        
        Args:
            rule_data: Rule data containing entity references
            
        Raises:
            UserNotFoundExceptionForStaff: If user not found
            ProviderNotFoundExceptionForStaff: If provider not found
            OrganisationNotFoundExceptionForStaff: If organisation not found
        """
        # Validate user (if provided)
        if rule_data.rule_ref_user:
            user = self.user_repo.get_by_id(rule_data.rule_ref_user)
            if not user:
                logger.warning(f"User not found: {rule_data.rule_ref_user}")
                raise UserNotFoundExceptionForStaff(user_id=rule_data.rule_ref_user)
        
        # Validate provider (if provided)
        if rule_data.rule_ref_provider:
            provider = self.supplier_repo.get_supplier_basic(rule_data.rule_ref_provider)
            if not provider:
                logger.warning(f"Provider not found: {rule_data.rule_ref_provider}")
                raise ProviderNotFoundExceptionForStaff(provider_id=rule_data.rule_ref_provider)
        
        # Validate organisation (if provided)
        if rule_data.rule_ref_org:
            org = self.org_repo.get_org_by_id(rule_data.rule_ref_org)
            if not org:
                logger.warning(f"Organisation not found: {rule_data.rule_ref_org}")
                raise OrganisationNotFoundExceptionForStaff(org_id=rule_data.rule_ref_org)
        return user,provider,org
    
    def check_duplicate_rule(self, rule_data: ManagementRule_API) -> None:
        """
        Check if a rule already exists for the same user and provider.
        
        Args:
            rule_data: Rule data to check
            
        Raises:
            RuleAlreadyExistsException: If duplicate rule found
        """
        existings = self.rule_repo.get_by_user_and_provider(
            rule_data.rule_ref_user,
            rule_data.rule_ref_provider
        )
        if existings and len(existings) > 0:
            logger.warning(f"Duplicate rule found for user {rule_data.rule_ref_user} and provider {rule_data.rule_ref_provider}")
            raise RuleAlreadyExistsException(
                user_id=rule_data.rule_ref_user,
                provider_id=rule_data.rule_ref_provider,
                rule_id=existings[0].id_management_rule
            )
    
    def check_invitation_expired(self, rule) -> None:
        """
        Check if an invitation has expired.
        
        Args:
            rule: Rule to check
            
        Raises:
            InvitationExpiredException: If invitation has expired
        """
        from datetime import datetime
        
        if rule.management_rule_expiry and rule.management_rule_expiry < datetime.now():
            logger.warning(f"Invitation {rule.id_management_rule} has expired")
            raise InvitationExpiredException(
                rule_id=rule.id_management_rule,
                expiry_date=rule.management_rule_expiry.isoformat()
            )
    
    def check_invitation_already_processed(self, rule) -> None:
        """
        Check if an invitation has already been processed.
        
        Args:
            rule: Rule to check
            
        Raises:
            InvitationAlreadyProcessedException: If already processed
        """
        if rule.management_rule_status in ['ACTIVE', 'REJECTED']:
            logger.warning(f"Invitation {rule.id_management_rule} already {rule.management_rule_status.lower()}")
            raise InvitationAlreadyProcessedException(
                rule_id=rule.id_management_rule,
                current_status=rule.management_rule_status
            )