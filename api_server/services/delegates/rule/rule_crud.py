"""
CRUD operations for management rules.
"""

import logging
from typing import Dict, Any

from core.exceptions.handler import ForbiddenException
from repositories.supplier_repository import OrganisationRepository, SupplierRepository
from core.models.api_models import ManagementRule_API
from core.models.models import ManagementRule, RoleInvitation
from core.exceptions.specific.staff_exceptions import (
    RuleNotFoundException,
    RuleInsertFailedException,
    RuleUpdateFailedException,
    RuleDeleteFailedException,
    StaffPermissionDeniedException
)
from repositories.management_rule_repository import ManagementRuleRepository
from .rule_validator import RuleValidator
from .rule_notification import RuleNotification
from .rule_helpers import RuleHelpers

from core.logging_config import get_logger

logger = get_logger(__name__)



class RuleCrud:
    """CRUD operations for management rules"""
    
    def __init__(self):
        self.rule_repo = ManagementRuleRepository()
        self.supplier_repo = SupplierRepository()
        self.org_repo = OrganisationRepository()
        self.validator = RuleValidator()
        self.notification = RuleNotification()
        self.helpers = RuleHelpers()
    
    def get_by_id(self, rule_id: int) -> ManagementRule:
        """
        Get management rule by ID.
        
        Args:
            rule_id: Rule ID to retrieve
            
        Returns:
            ManagementRule object
            
        Raises:
            RuleNotFoundException: If rule not found
        """
        rule = self.rule_repo.get_by_id(rule_id)
            
        if not rule:
            logger.warning(f"Rule not found with ID: {rule_id}")
            raise RuleNotFoundException(rule_id=rule_id)
        
        logger.debug(f"Retrieved rule with ID: {rule_id}")
        return rule
    
    def create(self, rule_data: ManagementRule_API) -> ManagementRule:
        """
        Create a new management rule.
        
        Args:
            rule_data: Rule data to create
            
        Returns:
            Created ManagementRule object
            
        Raises:
            RuleAlreadyExistsException: If rule already exists
            RuleInsertFailedException: If creation fails
        """
        logger.info(f"Creating new rule for user: {rule_data.rule_ref_user}, provider: {rule_data.rule_ref_provider}")
        
        # Validate
        self.validator.validate_rule_data(rule_data)
        user,provider,org = self.validator.validate_entities_exist(rule_data)
        self.validator.check_duplicate_rule(rule_data)
        
        # Build and create rule
        new_rule = self._build_rule_model(rule_data)
        
        try:
            final_rule = self.rule_repo.create(new_rule)
            logger.info(f"Rule created successfully with ID: {final_rule.id_management_rule}")
            

            destination_users = set()

            destination_users.add(user.id_app_user)
            destination_users.add(provider.product_provider_owner)
            destination_users.add(org.app_user_id)
            
            notification = self.notification.create_invitation_notification(final_rule, destination_users)
            
            self.rule_repo.create_invitation(
                RoleInvitation(
                    provider_id = provider.id_product_provider,
                    app_user_id = user.id_app_user,
                    notification_id = notification.id_notification,
                    organisation_id = final_rule.rule_ref_org,
                    rule_id = final_rule.id_management_rule,
                )
            )

            return final_rule
            
        except Exception as e:
            logger.error(f"Failed to create rule: {e}")
            raise RuleInsertFailedException(
                error=str(e),
                user_id=rule_data.rule_ref_user,
                provider_id=rule_data.rule_ref_provider,
                org_id=rule_data.rule_ref_org
            )
    
    def update(self, rule_data: ManagementRule_API) -> ManagementRule:
        """
        Update an existing management rule.
        
        Args:
            rule_data: Updated rule data
            
        Returns:
            Updated ManagementRule object
            
        Raises:
            RuleNotFoundException: If rule not found
            RuleUpdateFailedException: If update fails
        """
        logger.info(f"Updating rule with ID: {rule_data.id_management_rule}")
        
        # Validate
        self.validator.validate_rule_data(rule_data)
        user,provider,org = self.validator.validate_entities_exist(rule_data)
        
        destination_users = set()
        destination_users.add(user.id_app_user)
        destination_users.add(provider.product_provider_owner)
        destination_users.add(org.app_user_id)


        # Get existing rule
        existing_rule = self.get_by_id(rule_data.id_management_rule)
        
        # Track changes
        changes = []
        if existing_rule.management_rule_code != rule_data.management_rule_code:
            changes.append(f"code: {existing_rule.management_rule_code} -> {rule_data.management_rule_code}")
        if existing_rule.management_rule_status != rule_data.management_rule_status:
            changes.append(f"status: {existing_rule.management_rule_status} -> {rule_data.management_rule_status}")
        
        # Update fields
        existing_rule.management_rule_code = rule_data.management_rule_code
        existing_rule.management_rule_status = rule_data.management_rule_status
        existing_rule.management_rule_expiry = self.helpers.parse_expiry(rule_data.management_rule_expiry)
        
        try:
            final_rule = self.rule_repo.update(existing_rule)
            logger.info(f"Rule {rule_data.id_management_rule} updated successfully. Changes: {changes if changes else 'none'}")
            
            # Create notification
            self.notification.create_rule_update_notification(final_rule,destination_users)
            
            return final_rule
            
        except Exception as e:
            logger.error(f"Failed to update rule {rule_data.id_management_rule}: {e}")
            raise RuleUpdateFailedException(
                rule_id=rule_data.id_management_rule,
                error=str(e),
                fields_attempted=["management_rule_code", "management_rule_status", "management_rule_expiry"]
            )
    
    def delete(self, rule_id: int, force_delete: bool = False) -> Dict[str, Any]:
        """
        Delete a management rule.
        
        Args:
            rule_id: Rule ID to delete
            force_delete: Force delete even if rule is active
            
        Returns:
            Dictionary with success message
            
        Raises:
            RuleNotFoundException: If rule not found
            RuleDeleteFailedException: If deletion fails
        """
        logger.info(f"Deleting rule with ID: {rule_id} (force={force_delete})")
        
        rule = self.get_by_id(rule_id)

        for inv in rule.role_invitation:
            self.rule_repo.delete_invitation(inv)
        
        success = self.rule_repo.delete(rule)
        
        if not success:
            logger.error(f"Failed to delete rule {rule_id}")
            raise RuleDeleteFailedException(
                rule_id=rule_id,
                error="Repository returned False"
            )
        
        logger.info(f"Rule {rule_id} deleted successfully")
        return {
            "success": True,
            "message": "Rule deleted successfully",
            "rule_id": rule_id
        }
    
    def answer_invitation(self, rule_id: int, accept: bool,user_id:int) -> ManagementRule:
        """
        Respond to an invitation (accept or reject).
        
        Args:
            rule_id: Rule ID to respond to
            accept: True to accept, False to reject
            
        Returns:
            Updated ManagementRule object
            
        Raises:
            RuleNotFoundException: If rule not found
            InvitationAlreadyProcessedException: If already processed
            InvitationExpiredException: If invitation expired
            RuleUpdateFailedException: If update fails
        """
        action = "accept" if accept else "reject"
        logger.info(f"Processing invitation {action} for rule {rule_id}")
        
        # Get existing rule
        existing_rule = self.get_by_id(rule_id)

        if user_id != existing_rule.rule_ref_user:
            raise ForbiddenException()


        # Validate
        self.validator.check_invitation_expired(existing_rule)
        self.validator.check_invitation_already_processed(existing_rule)
        
        provider = self.supplier_repo.get_supplier_by_id(existing_rule.rule_ref_provider)
        org = self.org_repo.get_org_by_id(existing_rule.rule_ref_org)

        # Update status
        new_status = 'ACTIVE' if accept else 'REJECTED'
        new_inv_status = 'ACCEPTED' if accept else 'REJECTED'

        existing_rule.management_rule_status = new_status
        existing_rule.role_invitation[0].invitation_status = new_inv_status
        
        try:
            logger.info("*********************************************")
            logger.info("Updating invitation and rule")
            # self.rule_repo.update_invitation(existing_rule.role_invitation)
            final_rule = self.rule_repo.update(existing_rule)
            logger.info(f"Invitation {rule_id} {action}ed successfully")
            logger.info(f"Invitation {existing_rule.role_invitation[0].id_role_invitation} {existing_rule.role_invitation[0].invitation_status} successfully")
            
            

            destinations = set()
            destinations.add(provider.product_provider_owner)
            destinations.add(org.app_user_id)
            # Create notification
            self.notification.create_invitation_response_notification(final_rule, accept,destinations)
            
            return final_rule
            
        except Exception as e:
            logger.error(f"Failed to update rule {rule_id} for invitation response: {e}")
            raise RuleUpdateFailedException(
                rule_id=rule_id,
                error=str(e),
                fields_attempted=["management_rule_status"]
            )
    
    def _build_rule_model(self, rule_data: ManagementRule_API) -> ManagementRule:
        """
        Build ManagementRule model from API data.
        
        Args:
            rule_data: API rule data
            
        Returns:
            ManagementRule model instance
        """
        new_rule = ManagementRule(
            rule_ref_org=rule_data.rule_ref_org,
            rule_ref_provider=rule_data.rule_ref_provider,
            rule_ref_user=rule_data.rule_ref_user,
            management_rule_code=rule_data.management_rule_code,
            management_rule_status=rule_data.management_rule_status,
            management_rule_expiry=self.helpers.parse_expiry(rule_data.management_rule_expiry),
        )
        
        if rule_data.id_management_rule != 0:
            new_rule.id_management_rule = rule_data.id_management_rule
        
        return new_rule