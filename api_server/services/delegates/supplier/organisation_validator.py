"""
Validation logic for organisation operations.
"""

import logging
from typing import Optional

from core.exceptions.specific.supplier_exceptions import (
    OrganisationNotFoundException,
    OrganisationNameAlreadyUsedException
)
from repositories.supplier_repository import OrganisationRepository

from core.logging_config import get_logger

logger = get_logger(__name__)



class OrganisationValidator:
    """Validator for organisation operations"""
    
    def __init__(self):
        self.org_repo = OrganisationRepository()
    
    def validate_org_exists(self, org_id: str) -> None:
        """
        Validate that organisation exists.
        
        Args:
            org_id: Organisation ID to validate
            
        Raises:
            OrganisationNotFoundException: If organisation not found
        """
        org = self.org_repo.get_org_by_id(org_id)
        if not org:
            logger.warning(f"Organisation not found with ID: {org_id}")
            raise OrganisationNotFoundException(org_id=org_id)
        return org
    
    def validate_org_name_unique(self, org_name: str, exclude_org_id: Optional[str] = None) -> None:
        """
        Validate that organisation name is unique.
        
        Args:
            org_name: Organisation name to check
            exclude_org_id: Organisation ID to exclude from check (for updates)
            
        Raises:
            OrganisationNameAlreadyUsedException: If name is taken
        """
        existing = self.org_repo.get_org_by_name(org_name)
        if existing and (not exclude_org_id or existing.id_provider_organisation != int(exclude_org_id)):
            logger.warning(f"Organisation name already exists: {org_name}")
            raise OrganisationNameAlreadyUsedException(org_name=org_name)
    
    def validate_ownership(self, organisation, user_id: int) -> None:
        """
        Validate that user owns the organisation.
        
        Args:
            organisation: Organisation to check ownership for
            user_id: User ID to validate
            
        Raises:
            OrganisationUpdateFailedException: If ownership validation fails
        """
        from core.exceptions.specific.supplier_exceptions import OrganisationUpdateFailedException
        
        if user_id != organisation.app_user_id:
            logger.warning(f"User ID mismatch for organisation {organisation.id_provider_organisation}")
            raise OrganisationUpdateFailedException(
                org_id=organisation.id_provider_organisation,
                error="User ID mismatch"
            )