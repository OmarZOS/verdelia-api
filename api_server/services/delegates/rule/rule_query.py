"""
Query operations for management rules.
"""

import logging
from typing import Optional, List

from core.exceptions.specific.staff_exceptions import (
    UserNotFoundExceptionForStaff,
    ProviderNotFoundExceptionForStaff
)
from repositories.user_repository import UserRepository
from repositories.supplier_repository import SupplierRepository
from repositories.management_rule_repository import ManagementRuleRepository

from core.logging_config import get_logger

logger = get_logger(__name__)



class RuleQuery:
    """Query operations for management rules"""
    
    def __init__(self):
        self.rule_repo = ManagementRuleRepository()
        self.user_repo = UserRepository()
        self.supplier_repo = SupplierRepository()
    
    def get_all(
        self,
        org_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        user_id: Optional[int] = None,
        rule_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100
    ) -> List:
        """
        Get all management rules with filters.
        
        Args:
            org_id: Filter by organisation ID
            supplier_id: Filter by supplier/provider ID
            user_id: Filter by user ID
            rule_id: Filter by rule ID
            offset: Pagination offset
            limit: Maximum number of records
            
        Returns:
            List of ManagementRule objects
        """
        logger.debug(f"Fetching rules - org:{org_id}, supplier:{supplier_id}, user:{user_id}, rule_id:{rule_id}, offset:{offset}, limit:{limit}")
        
        return self.rule_repo.get_all(
            org_id=org_id,
            supplier_id=supplier_id,
            user_id=user_id,
            rule_id=rule_id,
            offset=offset,
            limit=limit
        )
    
    def get_user_rules(self, user_id: int, status: Optional[str] = None) -> List:
        """
        Get all rules for a specific user.
        
        Args:
            user_id: User ID to fetch rules for
            status: Optional status filter
            
        Returns:
            List of ManagementRule objects
        """
        logger.debug(f"Fetching rules for user {user_id} (status={status})")
        
        # Validate user exists
        user = self.user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise UserNotFoundExceptionForStaff(user_id=user_id)
        
        if status:
            return self.rule_repo.get_by_user(user_id, status.upper())
        return self.rule_repo.get_by_user(user_id)
    
    def get_provider_staff(self, provider_id: int, active_only: bool = True) -> List:
        """
        Get all staff members for a provider.
        
        Args:
            provider_id: Provider ID to fetch staff for
            active_only: Return only active staff
            
        Returns:
            List of ManagementRule objects
        """
        logger.debug(f"Fetching staff for provider {provider_id} (active_only={active_only})")
        
        # Validate provider exists
        provider = self.supplier_repo.get_supplier_basic(provider_id)
        if not provider:
            logger.warning(f"Provider not found: {provider_id}")
            raise ProviderNotFoundExceptionForStaff(provider_id=provider_id)
        
        if active_only:
            return self.rule_repo.get_by_provider(provider_id, status='ACTIVE')
        return self.rule_repo.get_by_provider(provider_id)
    
    def get_pending_invitations(self, user_id: int) -> List:
        """
        Get pending invitations for a user.
        
        Args:
            user_id: User ID to fetch pending invitations for
            
        Returns:
            List of pending ManagementRule objects
        """
        logger.debug(f"Fetching pending invitations for user {user_id}")
        
        # Validate user exists
        user = self.user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"User not found: {user_id}")
            raise UserNotFoundExceptionForStaff(user_id=user_id)
        
        return self.rule_repo.get_by_user(user_id, status='PENDING')
    
    def get_user_active_rules(self, user_id: int) -> List:
        """
        Get active rules for a user.
        
        Args:
            user_id: User ID to fetch active rules for
            
        Returns:
            List of active ManagementRule objects
        """
        logger.debug(f"Fetching active rules for user {user_id}")
        return self.rule_repo.get_by_user(user_id, status='ACTIVE')
    
    def get_expiring_rules(self, days_threshold: int = 7) -> List:
        """
        Get rules that will expire soon.
        
        Args:
            days_threshold: Number of days before expiry to consider
            
        Returns:
            List of expiring ManagementRule objects
        """
        logger.debug(f"Fetching rules expiring within {days_threshold} days")
        return self.rule_repo.get_expiring_rules(days_threshold)
    
    def get_rule_by_user_and_provider(self, user_id: int, provider_id: int):
        """
        Get rule for a specific user and provider.
        
        Args:
            user_id: User ID
            provider_id: Provider ID
            
        Returns:
            ManagementRule object or None if not found
        """
        logger.debug(f"Fetching rule for user {user_id} and provider {provider_id}")
        result = self.rule_repo.get_by_user_and_provider(user_id, provider_id)
        if result and len(result) > 0:
            return result[0]
        return None