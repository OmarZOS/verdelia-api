from typing import Optional, List
from core.models.models import Iproduct
import storage.storage_broker as storage_broker

class IProductRepository:
    """Repository for AI-generated product data"""
    
    def get_by_id(self, iproduct_id: int) -> Optional[Iproduct]:
        """Get IProduct by ID"""
        records = storage_broker.get(Iproduct, {Iproduct.id_iproduct: iproduct_id},None,[Iproduct.naming_contribution])
        return records[0] if records else None
    
    def get_by_barcode(self, barcode: str) -> Optional[List[Iproduct]]:
        """Get IProduct by barcode"""
        records = storage_broker.get(Iproduct, {Iproduct.barcode: barcode},None,[Iproduct.naming_contribution])
        return records if records else None
    
    def create(self, iproduct: Iproduct) -> Iproduct:
        """Create a new IProduct"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(iproduct)
    
    def update(self, iproduct: Iproduct) -> Iproduct:
        """Update an existing IProduct"""
        from features.insertion import update_record_in_api
        return update_record_in_api(iproduct)
    
    def delete(self, iproduct_id: int) -> bool:
        """Delete an IProduct"""
        from features.insertion import delete_record_from_api
        iproduct = self.get_by_id(iproduct_id)
        if iproduct:
            return delete_record_from_api(iproduct)
        return False