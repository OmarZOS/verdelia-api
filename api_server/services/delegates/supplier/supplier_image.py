"""
Image handling for suppliers.
"""

import logging
from typing import Optional

from core.models.api_models import ProviderImage_API
from core.models.models import ProviderImage
from core.exceptions.specific.supplier_exceptions import (
    ImageInsertFailedException,
    ImageUpdateFailedException
)
from repositories.supplier_repository import SupplierRepository

from core.logging_config import get_logger

logger = get_logger(__name__)



class SupplierImageHandler:
    """Image handler for suppliers"""
    
    def __init__(self):
        self.supplier_repo = SupplierRepository()
    
    def handle_image(self, supplier, image: Optional[ProviderImage_API]) -> None:
        """
        Handle supplier image creation or update.
        
        Args:
            supplier: Supplier model instance
            image: Image API data
            
        Raises:
            ImageInsertFailedException: If image creation fails
            ImageUpdateFailedException: If image update fails
        """
        if not image or not image.provider_image_url:
            return
        
        if image.id_provider_image == 0:
            self._create_image(supplier, image)
        else:
            self._update_image(image)
    
    def _create_image(self, supplier, image: ProviderImage_API) -> None:
        """
        Create a new supplier image.
        
        Args:
            supplier: Supplier model instance
            image: Image API data
            
        Raises:
            ImageInsertFailedException: If creation fails
        """
        new_image = ProviderImage(provider_image_url=image.provider_image_url)
        new_image.provider_ref = supplier
        try:
            self.supplier_repo.create_supplier_image(new_image)
            logger.info(f"Created supplier image for supplier {supplier.id_product_provider}")
        except Exception as e:
            logger.error(f"Failed to create supplier image: {e}")
            raise ImageInsertFailedException(
                error=str(e),
                details={"supplier_id": supplier.id_product_provider}
            )
    
    def _update_image(self, image: ProviderImage_API) -> None:
        """
        Update an existing supplier image.
        
        Args:
            image: Image API data
            
        Raises:
            ImageUpdateFailedException: If update fails
        """
        existing_image = self.supplier_repo.get_supplier_image_by_id(image.id_provider_image)
        if existing_image:
            existing_image.provider_image_url = image.provider_image_url
            try:
                self.supplier_repo.update_supplier_image(existing_image)
                logger.info(f"Updated supplier image with ID: {image.id_provider_image}")
            except Exception as e:
                logger.error(f"Failed to update supplier image: {e}")
                raise ImageUpdateFailedException(
                    image_id=image.id_provider_image,
                    error=str(e)
                )
    
    def delete_images(self, supplier_id: str) -> int:
        """
        Delete all images for a supplier.
        
        Args:
            supplier_id: Supplier ID
            
        Returns:
            Number of images deleted
        """
        images = self.supplier_repo.get_supplier_images(supplier_id)
        for img in images:
            self.supplier_repo.delete_supplier_image(img)
        logger.info(f"Deleted {len(images)} associated images for supplier {supplier_id}")
        return len(images)