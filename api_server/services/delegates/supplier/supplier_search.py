"""
Search operations for suppliers.
"""

import logging
from typing import List, Dict, Any

from repositories.supplier_repository import SupplierRepository

from core.logging_config import get_logger

logger = get_logger(__name__)


class SupplierSearch:
    """Search operations for suppliers"""
    
    def __init__(self):
        self.supplier_repo = SupplierRepository()
    
    def search_by_filter(
        self,
        longitude: float,
        latitude: float,
        distance_km: float,
        offset: int = 0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search suppliers by location.
        
        Args:
            longitude: Longitude coordinate
            latitude: Latitude coordinate
            distance_km: Search radius in kilometers
            offset: Pagination offset
            limit: Maximum number of records
            
        Returns:
            List of suppliers with distance information
        """
        logger.info(f"Searching suppliers near ({longitude}, {latitude}) within {distance_km}km")
        return self.supplier_repo.search_by_filter(
            (longitude, latitude), distance_km, offset, limit
        )