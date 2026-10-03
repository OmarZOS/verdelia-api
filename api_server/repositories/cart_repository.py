# repositories/cart_repository.py - Fixed version

from typing import Optional, List, Dict, Any, Tuple
from core.models.models import *
import storage.storage_broker as storage_broker
from sqlalchemy.orm import joinedload, sessionmaker, Session
from sqlalchemy import select, delete
import logging

from core.logging_config import get_logger

logger = get_logger(__name__)



class CartRepository:
    """Repository for Cart-related database operations"""
    
    def get_cart_by_id(self, cart_id: int, eager_load: bool = True) -> Optional[Cart]:
        """Get cart by ID with optional eager loading"""
        if eager_load:
            eager_fields = [
                Cart.invoice,
                Cart.ordered_item,
                Cart.ordered_service,
                Cart.app_user_,
                Cart.app_user,
                Cart.cart_product_provider,
                Cart.person
            ]
        else:
            eager_fields = []
        
        records = storage_broker.get(
            Cart,
            {Cart.cart_id: cart_id},
            [],
            eager_fields
        )
        return records[0] if records else None

    def list_carts(self, 
                provider_id: int = 0,
                seller_id: int = 0,
                buyer_id: int = 0,
                status: str = None,
                offset: int = 0, 
                limit: int = 100) -> Tuple[List[Cart], int]:
        """List carts with multiple filter options."""
        conditions = {}
        
        if provider_id > 0:
            conditions[Cart.cart_product_provider_id] = provider_id
        if seller_id > 0:
            conditions[Cart.cart_selling_user] = seller_id
        if buyer_id > 0:
            conditions[Cart.cart_client_user] = buyer_id
        if status:
            conditions[Cart.cart_status] = status
        
        total = storage_broker.count(Cart, conditions, [])
        carts = storage_broker.get(
            Cart,
            conditions,
            [],
            [Cart.invoice, Cart.ordered_item, Cart.ordered_service],
            offset=offset,
            limit=limit
        )
        
        return carts, total
    
    def get_carts_by_provider(self, provider_id: int, offset: int = 0, limit: int = 100) -> List[Cart]:
        """Get carts by provider ID"""
        return storage_broker.get(
            Cart,
            {Cart.cart_product_provider_id: provider_id},
            [],
            [Cart.invoice],
            offset=offset,
            limit=limit
        )
    
    def get_carts_by_seller(self, seller_id: int, offset: int = 0, limit: int = 100) -> List[Cart]:
        """Get carts by seller user ID"""
        return storage_broker.get(
            Cart,
            {Cart.cart_selling_user: seller_id},
            [],
            [Cart.invoice],
            offset=offset,
            limit=limit
        )
    
    def get_carts_by_buyer(self, buyer_id: int, offset: int = 0, limit: int = 100) -> List[Cart]:
        """Get carts by buyer/client user ID"""
        return storage_broker.get(
            Cart,
            {Cart.cart_client_user: buyer_id},
            [],
            [Cart.invoice],
            offset=offset,
            limit=limit
        )
    
    def get_carts_by_status(self, status: str, offset: int = 0, limit: int = 100) -> List[Cart]:
        """Get carts by status"""
        return storage_broker.get(
            Cart,
            {Cart.cart_status: status},
            [],
            [Cart.invoice],
            offset=offset,
            limit=limit
        )
    
    def delete_cart_sync(self, cart: Cart) -> bool:
        """Synchronously delete a cart and all related records."""
        try:
            with storage_broker.session_scope() as session:
                # Merge cart into session to get a bound instance
                cart_merged = session.merge(cart)
                
                # Get all related ordered items
                ordered_items = session.query(OrderedItem).filter(
                    OrderedItem.ordered_item_cart_ref == cart_merged.cart_id
                ).all()
                
                # Delete ordered items first
                for item in ordered_items:
                    session.delete(item)
                session.flush()
                
                # Get all related ordered services
                ordered_services = session.query(OrderedService).filter(
                    OrderedService.ordered_service_cart_id == cart_merged.cart_id
                ).all()
                
                # Delete ordered services
                for service in ordered_services:
                    session.delete(service)
                session.flush()
                
                # Now delete the cart
                session.delete(cart_merged)
                session.flush()
                
                logger.info(f"Cart {cart.cart_id} deleted synchronously with all related records")
                return True
        except Exception as e:
            logger.error(f"Failed to delete cart {cart.cart_id}: {e}")
            return False

    def delete_cart_by_id_sync(self, cart_id: int) -> bool:
        """Delete a cart by ID synchronously."""
        try:
            with storage_broker.session_scope() as session:
                # Get cart with relations
                cart = session.query(Cart).filter(Cart.cart_id == cart_id).first()
                if not cart:
                    logger.warning(f"Cart {cart_id} not found for deletion")
                    return False
                
                # Delete ordered items
                session.query(OrderedItem).filter(
                    OrderedItem.ordered_item_cart_ref == cart_id
                ).delete(synchronize_session=False)
                
                # Delete ordered services
                session.query(OrderedService).filter(
                    OrderedService.ordered_service_cart_id == cart_id
                ).delete(synchronize_session=False)
                
                # Delete the cart
                session.delete(cart)
                session.flush()
                
                logger.info(f"Cart {cart_id} deleted by ID synchronously")
                return True
        except Exception as e:
            logger.error(f"Failed to delete cart {cart_id}: {e}")
            return False

    def delete_ordered_service(self, service: OrderedService) -> bool:
        """Delete an ordered service."""
        try:
            with storage_broker.session_scope() as session:
                service_merged = session.merge(service)
                session.delete(service_merged)
                session.flush()
                return True
        except Exception as e:
            logger.error(f"Failed to delete ordered service: {e}")
            return False
    
    def delete_ordered_items_by_cart(self, cart_id: int) -> bool:
        """Delete all ordered items for a cart."""
        try:
            with storage_broker.session_scope() as session:
                session.query(OrderedItem).filter(
                    OrderedItem.ordered_item_cart_ref == cart_id
                ).delete(synchronize_session=False)
                session.flush()
                return True
        except Exception as e:
            logger.error(f"Failed to delete ordered items for cart {cart_id}: {e}")
            return False
    
    def delete_ordered_services_by_cart(self, cart_id: int) -> bool:
        """Delete all ordered services for a cart."""
        try:
            with storage_broker.session_scope() as session:
                session.query(OrderedService).filter(
                    OrderedService.ordered_service_cart_id == cart_id
                ).delete(synchronize_session=False)
                session.flush()
                return True
        except Exception as e:
            logger.error(f"Failed to delete ordered services for cart {cart_id}: {e}")
            return False
    
    def create_cart(self, cart: Cart) -> Cart:
        """Create a new cart"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(cart)
    
    def update_cart(self, cart: Cart) -> Cart:
        """Update an existing cart"""
        from features.insertion import update_record_in_api
        return update_record_in_api(cart)
    
    def create_ordered_service(self, service: OrderedService) -> OrderedService:
        """Create an ordered service"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(service)
    

