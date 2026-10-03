"""
Validation logic for supplier operations.
"""

import logging
from typing import Optional

from core.exceptions.specific.supplier_exceptions import (
    SupplierTypeNotFoundException,
    SupplierNotFoundException
)
from repositories.supplier_repository import SupplierRepository

from core.logging_config import get_logger

logger = get_logger(__name__)



class SupplierValidator:
    """Validator for supplier operations"""
    
    def __init__(self):
        self.supplier_repo = SupplierRepository()
    
    def validate_supplier_type(self, supplier_type_id: int) -> None:
        """
        Validate that supplier type exists.
        
        Args:
            supplier_type_id: Supplier type ID to validate
            
        Raises:
            SupplierTypeNotFoundException: If supplier type not found
        """
        supplier_type = self.supplier_repo.get_supplier_type_by_id(supplier_type_id)
        if not supplier_type:
            logger.warning(f"Supplier type not found with ID: {supplier_type_id}")
            raise SupplierTypeNotFoundException(supplier_type_id=supplier_type_id)
        return supplier_type
    
    def validate_supplier_exists(self, supplier_id: str, full: bool = True) -> None:
        """
        Validate that supplier exists.
        
        Args:
            supplier_id: Supplier ID to validate
            full: Whether to load all related data eagerly
            
        Raises:
            SupplierNotFoundException: If supplier not found
        """
        supplier = self.supplier_repo.get_supplier_by_id(supplier_id, eager_load=full)
        if not supplier:
            logger.warning(f"Supplier not found with ID: {supplier_id}")
            raise SupplierNotFoundException(supplier_id=supplier_id)
        return supplier
    
    def validate_ownership(self, supplier, user_id: int) -> None:
        """
        Validate that user owns the supplier.
        
        Args:
            supplier: Supplier to check ownership for
            user_id: User ID to validate
            
        Raises:
            SupplierUpdateFailedException: If ownership validation fails
        """
        from core.exceptions.specific.supplier_exceptions import SupplierUpdateFailedException
        
        if user_id != supplier.product_provider_owner:
            logger.warning(f"User ID mismatch for supplier {supplier.id_product_provider}")
            raise SupplierUpdateFailedException(
                supplier_id=supplier.id_product_provider,
                error="User ID mismatch"
            )