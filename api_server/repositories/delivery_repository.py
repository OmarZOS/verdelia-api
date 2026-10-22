# repositories/delivery_repository.py
from typing import Optional, List, Dict, Any
from core.models.models import AppUser, Delivery, Invoice, OrderedItem, PlacedOrder, Product
import storage.storage_broker as storage_broker

class DeliveryRepository:
    """Repository for Delivery-related database operations"""
    
    def get_by_id(self, delivery_id: int, eager_load: bool = True) -> Optional[Delivery]:
        """Get delivery by ID with optional eager loading"""
        if eager_load:
            records = storage_broker.get(
                Delivery,
                {Delivery.id_delivery: delivery_id},
                [],
                [

                {
                    Delivery.invoice:[{Invoice.placed_order:[{PlacedOrder.ordering_user:[{AppUser.app_user_person:[]}]},{PlacedOrder.ordered_item:[{OrderedItem.product:[Product.provider_id]}]}]}]},
                    Delivery.address,
                    # Delivery.person,
                    Delivery.delivery_provider,
                    Delivery.delivery_broker
                    # Delivery.cart,
                    # Delivery.placed_order,
                    # Delivery.delivery_provider,
                    # Delivery.delivery_broker
                ],
                offset=0,
                limit=1
            )
        else:
            records = storage_broker.get(
                Delivery,
                {Delivery.id_delivery: delivery_id},
                [],
                [],
                offset=0,
                limit=1
            )
        return records[0] if records else None
    
    def get_all(
        self,
        provider_id: int = 0,
        order_id: int = 0,
        broker_id: int = 0,
        offset: int = 0,
        limit: int = 100,
        eager_load: bool = True
    ) -> List[Delivery]:
        """Get all deliveries with filters"""
        conditions = {}
        
        if provider_id != 0:
            conditions[Delivery.delivery_provider_id] = provider_id
        if order_id != 0:
            conditions[Delivery.delivery_source_id] = order_id
            conditions[Delivery.delivery_source_type] = "placed_order"
        if broker_id != 0:
            conditions[Delivery.delivery_broker_id] = broker_id
        
        if eager_load:
            eager_load_depth = [
                # Delivery.cart,
                # Delivery.placed_order,
                Delivery.delivery_provider,
                Delivery.delivery_broker,
                Delivery.address
            ]
        else:
            eager_load_depth = []
        
        return storage_broker.get(
            Delivery,
            conditions,
            [],
            eager_load_depth,
            offset=offset,
            limit=limit
        )
    
    def get_by_status(self, status: str, limit: int = 100) -> List[Delivery]:
        """Get deliveries by status"""
        return storage_broker.get(
            Delivery,
            {Delivery.delivery_status: status},
            [],
            [Delivery.delivery_provider, Delivery.delivery_broker],
            limit=limit
        )
    
    def get_by_provider(self, provider_id: int, status: Optional[str] = None) -> List[Delivery]:
        """Get deliveries by provider with optional status filter"""
        conditions = {Delivery.delivery_provider_id: provider_id}
        if status:
            conditions[Delivery.delivery_status] = status
        
        return storage_broker.get(
            Delivery,
            conditions,
            [],
            [ Delivery.delivery_broker]
        )
    
    def get_by_recipient_person(self, person_id: int) -> List[Delivery]:
        """Get deliveries by recipient person"""
        return storage_broker.get(
            Delivery,
            {Delivery.recipient_person_id: person_id},
            [],
            [Delivery.delivery_provider, Delivery.delivery_broker]
        )
    
    def create(self, delivery: Delivery) -> Delivery:
        """Create a new delivery"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(delivery)
    
    def update(self, delivery: Delivery) -> Delivery:
        """Update an existing delivery"""
        from features.insertion import update_record_in_api
        return update_record_in_api(delivery)
    
    def delete(self, delivery: Delivery) -> bool:
        """Delete a delivery"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(delivery)
    
    def bulk_delete_by_criteria(
        self,
        provider_id: int = 0,
        order_id: int = 0,
        status: str = None
    ) -> int:
        """Delete multiple deliveries matching criteria"""
        from sqlalchemy.orm import Query
        from storage import storage_broker as sb
        
        try:
            query = sb.db_session.query(Delivery)
            
            if provider_id > 0:
                query = query.filter(Delivery.delivery_provider_id == provider_id)
            if status:
                query = query.filter(Delivery.delivery_status == status)
            else:
                # Only allow deletion of PENDING deliveries in bulk by default
                query = query.filter(Delivery.delivery_status == 'pending')
            
            deliveries_to_delete = query.all()
            deleted_count = 0
            
            for delivery in deliveries_to_delete:
                self.delete(delivery)
                deleted_count += 1
            
            return deleted_count
        except Exception as e:
            raise Exception(f"Failed to delete deliveries: {str(e)}")
    
    def count_by_status(self, status: str) -> int:
        """Count deliveries by status"""
        records = storage_broker.get(
            Delivery,
            {Delivery.delivery_status: status},
            [],
            [],
            limit=None
        )
        return len(records)
    
    def get_recent_deliveries(self, limit: int = 10) -> List[Delivery]:
        """Get most recent deliveries"""
        # This would typically order by created_at desc
        # Adjust based on your actual model
        return storage_broker.get(
            Delivery,
            {},
            [],
            [Delivery.delivery_provider, Delivery.delivery_broker],
            limit=limit
        )