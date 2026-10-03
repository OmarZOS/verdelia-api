"""
Image handling for organisations.
"""

import logging
from typing import Optional

from core.models.api_models import OrganisationImage_API
from core.models.models import OrganisationImage
from core.exceptions.specific.supplier_exceptions import (
    ImageInsertFailedException,
    ImageUpdateFailedException
)
from repositories.supplier_repository import OrganisationRepository

from core.logging_config import get_logger

logger = get_logger(__name__)



class OrganisationImageHandler:
    """Image handler for organisations"""
    
    def __init__(self):
        self.org_repo = OrganisationRepository()
    
    def handle_image(self, organisation, image: Optional[OrganisationImage_API]) -> None:
        """
        Handle organisation image creation or update.
        
        Args:
            organisation: Organisation model instance
            image: Image API data
            
        Raises:
            ImageInsertFailedException: If image creation fails
            ImageUpdateFailedException: If image update fails
        """
        if not image or not image.org_image_url:
            return
        
        if image.id_org_image == 0:
            self._create_image(organisation, image)
        else:
            self._update_image(image)
    
    def _create_image(self, organisation, image: OrganisationImage_API) -> None:
        """
        Create a new organisation image.
        
        Args:
            organisation: Organisation model instance
            image: Image API data
            
        Raises:
            ImageInsertFailedException: If creation fails
        """
        new_image = OrganisationImage(org_image_url=image.org_image_url)
        new_image.org_ref_id = organisation.id_provider_organisation
        try:
            self.org_repo.create_org_image(new_image)
            logger.info(f"Created organisation image for organisation {organisation.id_provider_organisation}")
        except Exception as e:
            logger.error(f"Failed to create organisation image: {e}")
            raise ImageInsertFailedException(
                error=str(e),
                details={"organisation_id": organisation.id_provider_organisation}
            )
    
    def _update_image(self, image: OrganisationImage_API) -> None:
        """
        Update an existing organisation image.
        
        Args:
            image: Image API data
            
        Raises:
            ImageUpdateFailedException: If update fails
        """
        existing_image = self.org_repo.get_org_image_by_id(image.id_org_image)
        if existing_image:
            existing_image.org_image_url = image.org_image_url
            try:
                self.org_repo.update_org_image(existing_image)
                logger.info(f"Updated organisation image with ID: {image.id_org_image}")
            except Exception as e:
                logger.error(f"Failed to update organisation image: {e}")
                raise ImageUpdateFailedException(
                    image_id=image.id_org_image,
                    error=str(e)
                )
    
    def delete_images(self, org_id: str) -> int:
        """
        Delete all images for an organisation.
        
        Args:
            org_id: Organisation ID
            
        Returns:
            Number of images deleted
        """
        images = self.org_repo.get_org_images(org_id)
        for img in images:
            self.org_repo.delete_org_image(img)
        logger.info(f"Deleted {len(images)} associated images for organisation {org_id}")
        return len(images)