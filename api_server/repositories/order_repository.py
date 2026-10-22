# repositories/order_repository.py
from typing import Optional, List, Dict, Any
from core.models.models import PlacedOrder, OrderedItem, Product, AppUser, Person
import storage.storage_broker as storage_broker

class OrderRepository:
    """Repository for Order-related database operations"""
    
    def get_order_by_id(self, order_id: int, with_items: bool = True) -> Optional[PlacedOrder]:
        """Get order by ID with optional items loading"""
        if with_items:
            records = storage_broker.get(
                PlacedOrder,
                {PlacedOrder.id_placed_order: order_id},
                [],
                [PlacedOrder.ordered_item]
            )
        else:
            records = storage_broker.get(
                PlacedOrder,
                {PlacedOrder.id_placed_order: order_id},
                [],
                [],
                None
            )
        return records[0] if records else None
    
    def get_order_basic(self, order_id: int) -> Optional[PlacedOrder]:
        """Get order with only basic info (no eager loading)"""
        records = storage_broker.get(
            PlacedOrder,
            {PlacedOrder.id_placed_order: order_id},
            [],
            [],
            None
        )
        return records[0] if records else None
    
    def get_user_orders(self, user_id: int, offset: int = 0, limit: int = 100) -> List[PlacedOrder]:
        """Get all orders for a user"""
        return storage_broker.get(
            PlacedOrder,
            {PlacedOrder.ordering_user_id: user_id},
            [OrderedItem],
            None,
            offset=offset,
            limit=limit
        )
    
    def get_order_items(self, order_id: int) -> List[OrderedItem]:
        """Get all items for an order"""
        return storage_broker.get(
            OrderedItem,
            {OrderedItem.order_id: order_id},
            [],
            [OrderedItem.product],
            None
        )
    
    def get_order_item_by_id(self, item_id: int) -> Optional[OrderedItem]:
        """Get order item by ID"""
        records = storage_broker.get(
            OrderedItem,
            {OrderedItem.id_ordered_item: item_id},
            [],
            []
        )
        return records[0] if records else None
    
    def get_orders_by_provider_products(
        self,
        provider_id: int,
        offset: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """Get orders containing products from a specific provider"""
        conditions = {Product.provider_id: provider_id}
        
        return storage_broker.get(
            Product,
            conditions,
            [OrderedItem],
            [{
                Product.ordered_item: [{
                    OrderedItem.order: [{
                        PlacedOrder.ordering_user: [{
                            AppUser.app_user_person: [Person.person_details]
                        }]
                    }]
                }]
            }],
            offset=offset,
            limit=limit
        )
    
    def create_order(self, order: PlacedOrder) -> PlacedOrder:
        """Create a new order"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(order)
    
    def update_order(self, order: PlacedOrder) -> PlacedOrder:
        """Update an existing order"""
        from features.insertion import update_record_in_api
        return update_record_in_api(order)
    
    
    def delete_order_item(self, item: OrderedItem) -> bool:
        """Delete an order item"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(item)
        
    def delete_order(self, order: PlacedOrder) -> bool:
        """Delete an order"""
        from features.insertion import delete_record_from_api
        for item in order.ordered_item:
            self.delete_order_item(item)
        return delete_record_from_api(order)
    
    def create_order_item(self, item: OrderedItem) -> OrderedItem:
        """Create an order item"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(item)
    
    def get_order_status_stats(self, user_id: Optional[int] = None) -> Dict[str, int]:
        """Get order statistics by status"""
        conditions = {}
        if user_id:
            conditions[PlacedOrder.ordering_user_id] = user_id
        
        orders = storage_broker.get(PlacedOrder, conditions, [], [])
        
        stats = {}
        for order in orders:
            status = order.order_state or 'UNKNOWN'
            stats[status] = stats.get(status, 0) + 1
        
        return stats

# repositories/order_item_repository.py
from typing import Optional, List
from core.models.models import OrderedItem
import storage.storage_broker as storage_broker

class OrderItemRepository:
    """Repository for OrderItem-related database operations"""
    
    def get_by_id(self, item_id: int) -> Optional[OrderedItem]:
        """Get order item by ID"""
        records = storage_broker.get(
            OrderedItem,
            {OrderedItem.id_ordered_item: item_id},
            [],
            []
        )
        return records[0] if records else None
    
    def get_by_order(self, order_id: int) -> List[OrderedItem]:
        """Get all items for an order"""
        return storage_broker.get(
            OrderedItem,
            {OrderedItem.order_id: order_id},
            [],
            [OrderedItem.product]
        )
    
    def get_by_product(self, product_id: int) -> List[OrderedItem]:
        """Get all order items for a product"""
        return storage_broker.get(
            OrderedItem,
            {OrderedItem.product_id: product_id},
            [],
            [OrderedItem.order]
        )
    
    def create(self, item: OrderedItem) -> OrderedItem:
        """Create an order item"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(item)
    
    def update(self, item: OrderedItem) -> OrderedItem:
        """Update an order item"""
        from features.insertion import update_record_in_api
        return update_record_in_api(item)
    
    def delete(self, item: OrderedItem) -> bool:
        """Delete an order item"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(item)
    
    def bulk_delete_by_order(self, order_id: int) -> int:
        """Delete all items for an order"""
        items = self.get_by_order(order_id)
        deleted_count = 0
        for item in items:
            if self.delete(item):
                deleted_count += 1
        return deleted_count