"""
Management rule service for handling staff assignments, invitations, and notifications.
"""

import logging
from typing import Optional, List, Dict, Any

from services.delegates.rule.rule_crud import RuleCrud
from services.delegates.rule.rule_query import RuleQuery
from core.models.api_models import ManagementRule_API
from core.models.models import ManagementRule

# Import components

from core.logging_config import get_logger

logger = get_logger(__name__)



class ManagementRuleService:
    """Service for management rule/staff operations"""
    
    def __init__(self):
        self.crud = RuleCrud()
        self.query = RuleQuery()
    
    # ==================== CRUD Operations ====================
    
    def get_rule_by_id(self, rule_id: int) -> ManagementRule:
        """Get management rule by ID."""
        return self.crud.get_by_id(rule_id)
    
    def create_rule(self, rule_data: ManagementRule_API) -> ManagementRule:
        """Create a new management rule."""
        return self.crud.create(rule_data)
    
    def update_rule(self, rule_data: ManagementRule_API) -> ManagementRule:
        """Update an existing management rule."""
        return self.crud.update(rule_data)
    
    def delete_rule(self, rule_id: int, force_delete: bool = False) -> Dict[str, Any]:
        """Delete a management rule."""
        return self.crud.delete(rule_id, force_delete)
    
    def answer_invitation(self, rule_id: int, accept: bool,user_id:int) -> ManagementRule:
        """Respond to an invitation (accept or reject)."""
        return self.crud.answer_invitation(rule_id, accept,user_id)
    
    # ==================== Query Operations ====================
    
    def get_all_rules(
        self,
        org_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        user_id: Optional[int] = None,
        rule_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100
    ) -> List[ManagementRule]:
        """Get all management rules with filters."""
        return self.query.get_all(org_id, supplier_id, user_id, rule_id, offset, limit)
    
    def get_user_rules(self, user_id: int, status: Optional[str] = None) -> List[ManagementRule]:
        """Get all rules for a specific user."""
        return self.query.get_user_rules(user_id, status)
    
    def get_provider_staff(self, provider_id: int, active_only: bool = True) -> List[ManagementRule]:
        """Get all staff members for a provider."""
        return self.query.get_provider_staff(provider_id, active_only)
    
    def get_pending_invitations(self, user_id: int) -> List[ManagementRule]:
        """Get pending invitations for a user."""
        return self.query.get_pending_invitations(user_id)
    
    def get_user_active_rules(self, user_id: int) -> List[ManagementRule]:
        """Get active rules for a user."""
        return self.query.get_user_active_rules(user_id)
    
    def get_expiring_rules(self, days_threshold: int = 7) -> List[ManagementRule]:
        """Get rules that will expire soon."""
        return self.query.get_expiring_rules(days_threshold)
    
    def get_rule_by_user_and_provider(self, user_id: int, provider_id: int) -> Optional[ManagementRule]:
        """Get rule for a specific user and provider."""
        return self.query.get_rule_by_user_and_provider(user_id, provider_id)