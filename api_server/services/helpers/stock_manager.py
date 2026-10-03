# services/stock_manager.py
"""
Stock Manager Service - Handles all product stock operations centrally.
This service manages stock validation, updates, rollbacks, and notifications.
"""

import logging
from typing import List, Tuple, Dict, Any, Optional, Callable
from dataclasses import dataclass
from decimal import Decimal

from core.exceptions.specific.product_exceptions import (
    ProductNotFoundException,
    ProductQuantityNotEnoughException
)
from core.models.models import Product, OrderedItem
from repositories.product_repository import ProductRepository
from communication.publisher import send_to_product_subscribers

from core.logging_config import get_logger

logger = get_logger(__name__)



@dataclass
class StockOperation:
    """Represents a stock operation on a product"""
    product: Product
    quantity: int
    operation_type: str  # 'decrease' or 'increase'
    original_quantity: int = 0
    
    def __post_init__(self):
        self.original_quantity = self.product.product_quantity
    
    @property
    def affected_quantity(self) -> int:
        return self.quantity
    
    @property
    def new_quantity(self) -> int:
        if self.operation_type == 'decrease':
            return self.original_quantity - self.quantity
        else:
            return self.original_quantity + self.quantity


class StockManager:
    """
    Centralized stock management service.
    Handles all product stock operations consistently across services.
    """
    
    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo
        self._operations_log: List[StockOperation] = []
    
    # ==================== Stock Validation ====================
    
    def validate_product_stock(
        self, 
        product_id: int, 
        requested_quantity: int
    ) -> Product:
        """
        Validate product stock and return product.
        
        Args:
            product_id: Product ID to validate
            requested_quantity: Requested quantity
            
        Returns:
            Product object
            
        Raises:
            ProductNotFoundException: If product not found
            ProductQuantityNotEnoughException: If insufficient stock
        """
        product = self.product_repo.get_product_by_id(product_id)
        if not product:
            logger.warning(f"Product not found with ID: {product_id}")
            raise ProductNotFoundException(product_id=product_id)
        
        if product.product_quantity < requested_quantity:
            logger.warning(
                f"Insufficient stock for product {product_id}. "
                f"Available: {product.product_quantity}, Requested: {requested_quantity}"
            )
            raise ProductQuantityNotEnoughException(
                product_id=product_id,
                available_quantity=product.product_quantity,
                requested_quantity=requested_quantity
            )
        
        return product
    
    def validate_multiple_products_stock(
        self,
        items: List[Tuple[int, int]]  # List of (product_id, quantity)
    ) -> List[Product]:
        """
        Validate stock for multiple products.
        
        Args:
            items: List of (product_id, requested_quantity) tuples
            
        Returns:
            List of validated Product objects
            
        Raises:
            ProductNotFoundException: If any product not found
            ProductQuantityNotEnoughException: If any product has insufficient stock
        """
        validated_products = []
        for product_id, quantity in items:
            product = self.validate_product_stock(product_id, quantity)
            validated_products.append(product)
        
        return validated_products
    
    # ==================== Stock Updates ====================
    
    def decrease_stock(
        self, 
        product: Product, 
        quantity: int,
        commit: bool = True
    ) -> StockOperation:
        """
        Decrease product stock.
        
        Args:
            product: Product to update
            quantity: Quantity to decrease
            commit: Whether to commit to database immediately
            
        Returns:
            StockOperation record
            
        Raises:
            ProductQuantityNotEnoughException: If insufficient stock
        """
        if quantity <= 0:
            logger.warning(f"Invalid quantity for stock decrease: {quantity}")
            return None
        
        if product.product_quantity < quantity:
            raise ProductQuantityNotEnoughException(
                product_id=product.id_product,
                available_quantity=product.product_quantity,
                requested_quantity=quantity
            )
        
        operation = StockOperation(product, quantity, 'decrease')
        product.product_quantity = operation.new_quantity
        
        if commit:
            self._commit_stock_update(product, operation)
        
        self._operations_log.append(operation)
        logger.debug(f"Decreased stock for product {product.id_product}: -{quantity} (new: {product.product_quantity})")
        
        return operation
    
    def increase_stock(
        self, 
        product: Product, 
        quantity: int,
        commit: bool = True
    ) -> StockOperation:
        """
        Increase product stock.
        
        Args:
            product: Product to update
            quantity: Quantity to increase
            commit: Whether to commit to database immediately
            
        Returns:
            StockOperation record
        """
        if quantity <= 0:
            logger.warning(f"Invalid quantity for stock increase: {quantity}")
            return None
        
        operation = StockOperation(product, quantity, 'increase')
        product.product_quantity = operation.new_quantity
        
        if commit:
            self._commit_stock_update(product, operation)
        
        self._operations_log.append(operation)
        logger.debug(f"Increased stock for product {product.id_product}: +{quantity} (new: {product.product_quantity})")
        
        return operation
    
    def batch_decrease_stock(
        self,
        products: List[Tuple[Product, int]],
        commit: bool = True
    ) -> List[StockOperation]:
        """
        Decrease stock for multiple products.
        
        Args:
            products: List of (product, quantity) tuples
            commit: Whether to commit to database immediately
            
        Returns:
            List of StockOperation records
        """
        operations = []
        for product, quantity in products:
            operation = self.decrease_stock(product, quantity, commit=False)
            operations.append(operation)
        
        if commit:
            self._commit_batch_updates(operations)
        
        return operations
    
    def batch_increase_stock(
        self,
        products: List[Tuple[Product, int]],
        commit: bool = True
    ) -> List[StockOperation]:
        """
        Increase stock for multiple products.
        
        Args:
            products: List of (product, quantity) tuples
            commit: Whether to commit to database immediately
            
        Returns:
            List of StockOperation records
        """
        operations = []
        for product, quantity in products:
            operation = self.increase_stock(product, quantity, commit=False)
            operations.append(operation)
        
        if commit:
            self._commit_batch_updates(operations)
        
        return operations
    
    def update_stock_from_ordered_items(
        self,
        items: List[OrderedItem],
        operation: str,  # 'decrease' or 'increase'
        commit: bool = True
    ) -> List[StockOperation]:
        """
        Update stock from a list of ordered items.
        
        Args:
            items: List of OrderedItem objects
            operation: 'decrease' or 'increase'
            commit: Whether to commit to database immediately
            
        Returns:
            List of StockOperation records
        """
        products = []
        for item in items:
            product = self.product_repo.get_product_by_id(item.ordered_product_id)
            if product:
                products.append((product, item.ordered_quantity))
        
        if operation == 'decrease':
            return self.batch_decrease_stock(products, commit)
        else:
            return self.batch_increase_stock(products, commit)
    
    # ==================== Stock Rollback ====================
    
    def rollback_last_operation(self) -> Optional[StockOperation]:
        """
        Rollback the last stock operation.
        
        Returns:
            The rolled back operation or None if no operations
        """
        if not self._operations_log:
            logger.warning("No operations to rollback")
            return None
        
        last_op = self._operations_log.pop()
        
        if last_op.operation_type == 'decrease':
            # Reverse: increase back
            last_op.product.product_quantity = last_op.original_quantity
            logger.info(f"Rolled back stock decrease for product {last_op.product.id_product}")
        else:
            # Reverse: decrease back
            last_op.product.product_quantity = last_op.original_quantity
            logger.info(f"Rolled back stock increase for product {last_op.product.id_product}")
        
        self._commit_stock_update(last_op.product, last_op, is_rollback=True)
        return last_op
    
    def rollback_all_operations(self) -> List[StockOperation]:
        """
        Rollback all stock operations in reverse order.
        
        Returns:
            List of rolled back operations
        """
        rolled_back = []
        while self._operations_log:
            op = self.rollback_last_operation()
            if op:
                rolled_back.append(op)
        
        logger.info(f"Rolled back {len(rolled_back)} stock operations")
        return rolled_back
    
    def rollback_to_checkpoint(self, checkpoint_size: int) -> List[StockOperation]:
        """
        Rollback operations to a specific checkpoint.
        
        Args:
            checkpoint_size: Number of operations to keep (0 = clear all)
            
        Returns:
            List of rolled back operations
        """
        rolled_back = []
        while len(self._operations_log) > checkpoint_size:
            op = self.rollback_last_operation()
            if op:
                rolled_back.append(op)
        
        return rolled_back
    
    # ==================== Private Methods ====================
    
    def _commit_stock_update(
        self, 
        product: Product, 
        operation: StockOperation,
        is_rollback: bool = False
    ) -> None:
        """
        Commit stock update to database and notify subscribers.
        """
        try:
            self.product_repo.update_product(product)
            self._notify_product_subscribers(product)
            
            action = "Rolled back" if is_rollback else "Applied"
            logger.debug(f"{action} stock {operation.operation_type} for product {product.id_product}")
            
        except Exception as e:
            logger.error(f"Failed to commit stock update: {e}")
            raise
    
    def _commit_batch_updates(self, operations: List[StockOperation]) -> None:
        """
        Commit multiple stock updates in batch.
        """
        for operation in operations:
            try:
                self.product_repo.update_product(operation.product)
                self._notify_product_subscribers(operation.product)
            except Exception as e:
                logger.error(f"Failed to commit batch stock update: {e}")
                # Rollback previous operations in this batch
                for prev_op in operations[:operations.index(operation)]:
                    self.rollback_last_operation()
                raise
        
        logger.debug(f"Committed {len(operations)} stock updates")
    
    def _notify_product_subscribers(self, product: Product) -> None:
        """
        Notify subscribers about product stock update.
        """
        try:
            send_to_product_subscribers(
                {'product_quantity': product.product_quantity},
                product.id_product
            )
        except Exception as e:
            # Log but don't fail the operation
            logger.warning(f"Failed to notify product subscribers for #{product.id_product}: {e}")
    
    # ==================== Utility Methods ====================
    
    def get_operations_log(self) -> List[StockOperation]:
        """Get the current operations log"""
        return self._operations_log.copy()
    
    def clear_log(self) -> None:
        """Clear the operations log"""
        self._operations_log.clear()
        logger.debug("Cleared stock operations log")
    
    def get_stock_summary(self) -> Dict[str, Any]:
        """Get summary of stock operations"""
        total_decreased = sum(
            op.quantity for op in self._operations_log 
            if op.operation_type == 'decrease'
        )
        total_increased = sum(
            op.quantity for op in self._operations_log 
            if op.operation_type == 'increase'
        )
        
        return {
            'total_operations': len(self._operations_log),
            'total_decreased': total_decreased,
            'total_increased': total_increased,
            'net_change': total_increased - total_decreased
        }
    
    def execute_with_rollback(
        self,
        callback: Callable[[], Any],
        commit_on_success: bool = True
    ) -> Any:
        """
        Execute a callback with automatic rollback on failure.
        
        Args:
            callback: Function to execute that performs stock operations
            commit_on_success: Whether to commit changes on success
            
        Returns:
            Result of the callback
        """
        checkpoint = len(self._operations_log)
        
        try:
            result = callback()
            
            if commit_on_success:
                # Keep all operations
                pass
            else:
                # Rollback to checkpoint
                self.rollback_to_checkpoint(checkpoint)
            
            return result
            
        except Exception as e:
            # Rollback all operations in this transaction
            self.rollback_to_checkpoint(checkpoint)
            logger.error(f"Transaction failed, rolled back: {e}")
            raise


# ==================== Context Manager for Stock Operations ====================

class StockTransaction:
    """
    Context manager for atomic stock operations.
    
    Usage:
        with StockTransaction(stock_manager) as tx:
            stock_manager.decrease_stock(product, 5)
            stock_manager.decrease_stock(product2, 3)
            # If exception occurs, all changes are rolled back
    """
    
    def __init__(self, stock_manager: StockManager):
        self.stock_manager = stock_manager
        self.checkpoint = 0
    
    def __enter__(self):
        self.checkpoint = len(self.stock_manager._operations_log)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Exception occurred - rollback
            self.stock_manager.rollback_to_checkpoint(self.checkpoint)
            logger.error(f"Stock transaction rolled back due to: {exc_val}")
        return False  # Don't suppress exception