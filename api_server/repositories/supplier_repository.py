# repositories/supplier_repository.py
from typing import Optional, List, Dict, Any, Tuple
from core.models.models import (
    ProductProvider, ProductProviderType, ProviderDetails, 
    ProviderImage, ProviderOrganisation, OrganisationImage
)
from core.models.persistent_models import Location
from core.models.models import Address
import storage.storage_broker as storage_broker
from sqlalchemy import func
from geoalchemy2.elements import WKTElement

class SupplierRepository:
    """Repository for Supplier/Provider-related database operations"""
    
    def get_supplier_by_id(self, provider_id: str, eager_load: bool = True) -> Optional[ProductProvider]:
        """Get supplier by ID with optional eager loading"""
        if eager_load:
            records = storage_broker.get(
                ProductProvider,
                {ProductProvider.id_product_provider: provider_id},
                None,
                [
                    {ProductProvider.product_provider_location: [
                        Location.position_wkt, Location.location_name, 
                        Location.id_location, Location.location_address
                    ]},
                    ProductProvider.product_provider_type,
                    {ProductProvider.product_provider_details:[{ProviderDetails.naming_contribution:[]}]},
                    {ProductProvider.product_provider_org : [{ProviderOrganisation.naming_contribution:[]}]},
                    ProductProvider.provider_image,
                    ProductProvider.provider_reaction,
                    ProductProvider.management_rule
                ]
            )
        else:
            records = storage_broker.get(
                ProductProvider,
                {ProductProvider.id_product_provider: provider_id},
                None,
                []
            )
        return records[0] if records else None

    def get_suppliers_by_ids(self, provider_ids: List[str], eager_load: bool = True) -> List[ProductProvider]:
        """Get suppliers by IDs with optional eager loading"""
        
        # Clean and validate input
        if not provider_ids:
            return []
        
        # Remove duplicates and None values
        provider_ids = list(set([pid for pid in provider_ids if pid is not None]))
        
        if not provider_ids:
            return []
        
        # Convert to integers
        int_ids = []
        for pid in provider_ids:
            try:
                int_ids.append(int(pid))
            except (ValueError, TypeError):
                continue
        
        if not int_ids:
            return []
        
        int_ids = list(set(int_ids))
        
        # Build conditions as a list for get_records_by_filter
        conditions = [
            ProductProvider.id_product_provider.in_(int_ids)
        ]
        
        # Build eager loading
        if eager_load:
            eager_load_depth = [
                {ProductProvider.product_provider_location: [
                    Location.position_wkt, 
                    Location.location_name, 
                    Location.id_location, 
                    Location.location_address
                ]},
                ProductProvider.product_provider_type,
                {ProductProvider.product_provider_details:[{ProviderDetails.naming_contribution:[]}]},
                {ProductProvider.product_provider_org : [{ProviderOrganisation.naming_contribution:[]}]},
                ProductProvider.provider_image,
                ProductProvider.provider_reaction,
                ProductProvider.management_rule
            ]
        else:
            eager_load_depth = None
        
        # ✅ Use get_records_by_filter
        records = storage_broker.search_by_filter(
            table=ProductProvider,
            conditions=conditions,           # List of conditions
            eager_load_depth=eager_load_depth,
            offset=0,
            limit=len(int_ids)
        )
        
        return records if records else []
    
    def get_supplier_basic(self, provider_id: str) -> Optional[ProductProvider]:
        """Get supplier with only basic info (no eager loading)"""
        records = storage_broker.get(
            ProductProvider,
            {ProductProvider.id_product_provider: provider_id},
            None,
            [
                ProductProvider.product_provider_location,
                {ProductProvider.product_provider_details:[{ProviderDetails.naming_contribution:[]}]},
                ProductProvider.management_rule
            ]
        )
        return records[0] if records else None
    
    def get_all_suppliers(
        self,
        owner_id: int = 0,
        org_id: int = 0,
        offset: int = 0,
        limit: int = 10,
        
    ) -> List[ProductProvider]:
        """Get all suppliers with filters"""
        conditions = {}
        if owner_id != 0:
            conditions[ProductProvider.product_provider_owner] = owner_id
        if org_id != 0:
            conditions[ProductProvider.product_provider_org_id] = org_id
        
        return storage_broker.get(
            ProductProvider,
            conditions=conditions,
            join_tables=[],
            eager_load_depth=[
                {
                    ProductProvider.product_provider_location: [
                        Location.id_location,
                        Location.location_address,
                        Location.location_postal_code,
                        Location.location_name,
                        Location.position_wkt,
                    ]
                },
                ProductProvider.product_provider_type,
                
                {ProductProvider.product_provider_details:[{ProviderDetails.naming_contribution:[]}]},
                ProductProvider.provider_image,
                {ProductProvider.product_provider_org : [{ProviderOrganisation.naming_contribution:[]}]},
            ],
            offset=offset,
            limit=limit,
            # serialize=True
        )
    
    def get_supplier_by_type(self, type_id: str) -> List[ProductProvider]:
        """Get suppliers by type"""
        return storage_broker.get(
            ProductProvider,
            {ProductProvider.product_provider_type_id: type_id},
            None,
            [{ProductProvider.product_provider_details:[{ProviderDetails.provider_naming_ref:[]}]}]
        )
    
    def create_supplier(self, supplier: ProductProvider) -> ProductProvider:
        """Create a new supplier"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(supplier)
    
    def update_supplier(self, supplier: ProductProvider) -> ProductProvider:
        """Update an existing supplier"""
        from features.insertion import update_record_in_api
        return update_record_in_api(supplier)
    
    def delete_supplier(self, supplier: ProductProvider) -> bool:
        """Delete a supplier"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(supplier)
    
    def get_supplier_type_by_id(self, type_id: str) -> Optional[ProductProviderType]:
        """Get supplier type by ID"""
        records = storage_broker.get(
            ProductProviderType,
            {ProductProviderType.id_product_provider_type: type_id},
            None,
            []
        )
        return records[0] if records else None
    
    def get_all_supplier_types(self) -> List[ProductProviderType]:
        """Get all supplier types"""
        return storage_broker.get(ProductProviderType, {}, None, [ProductProviderType.naming_contribution])
    
    def get_supplier_images(self, provider_id: str) -> List[ProviderImage]:
        """Get all images for a supplier"""
        return storage_broker.get(
            ProviderImage,
            {ProviderImage.provider_ref_id: provider_id},
            None,
            []
        )
    
    def get_supplier_image_by_id(self, image_id: str) -> Optional[ProviderImage]:
        """Get supplier image by ID"""
        records = storage_broker.get(
            ProviderImage,
            {ProviderImage.id_provider_image: image_id},
            None,
            None
        )
        return records[0] if records else None
    
    def create_supplier_image(self, image: ProviderImage) -> ProviderImage:
        """Create a supplier image"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(image)
    
    def update_supplier_image(self, image: ProviderImage) -> ProviderImage:
        """Update a supplier image"""
        from features.insertion import update_record_in_api
        return update_record_in_api(image)
    
    def delete_supplier_image(self, image: ProviderImage) -> bool:
        """Delete a supplier image"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(image)
    
    def search_by_filter(
        self,
        location: tuple[float, float],
        distance: float,
        offset: int = 0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search suppliers by location using PostGIS"""
        from storage.storage_broker import search_by_filter
        
        ST_location = WKTElement(
            f"POINT({location[0]} {location[1]})",
            srid=4326
        )
        
        labeled_attrs = [func.ST_Distance(Location.location_position, ST_location).label("distance")]
        
        selected_fields = [
            ProviderDetails.idprovider_details_id,
            ProviderDetails.provider_name,
            ProviderDetails.provider_contact_info,
            Location.id_location,
            Location.position_wkt,
            ProductProvider.id_product_provider,
            ProductProvider.product_provider_type_id,
            ProductProvider.product_provider_owner,
            ProviderOrganisation.idprovider_organisation,
            ProviderOrganisation.provider_organisation_name,
            Address.id_address,
            Address.address_street,
            Address.address_city,
            Address.address_postal_code,
            Address.address_country,
        ]
        
        return search_by_filter(
            ProductProvider,
            join_tables=[
                ProductProvider.product_provider_location,
                Location.location_address,
                ProductProvider.product_provider_details,
                ProductProvider.product_provider_org
            ],
            conditions=[func.ST_Distance(Location.location_position, ST_location) <= distance * 1000],
            labeled_attrs=labeled_attrs,
            ordering_attr=["distance"],
            selected_fields=selected_fields,
            eager_load_depth=None,
            offset=offset,
            limit=limit
        )
    
    def search_by_filter(
        self,
        location: Tuple[float, float],
        distance_km: float,
        offset: int = 0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search suppliers by geographic location using PostGIS.
        
        Args:
            location: Tuple of (longitude, latitude)
            distance_km: Search radius in kilometers
            offset: Pagination offset
            limit: Pagination limit
        
        Returns:
            List of suppliers with distance information
        """
        from storage.storage_broker import search_by_filter
        
        longitude, latitude = location
        ST_location = WKTElement(
            f"POINT({longitude} {latitude})",
            srid=4326
        )
        
        labeled_attrs = [
            func.ST_Distance(Location.location_position, ST_location).label("distance")
        ]
        
        selected_fields = [
            ProviderDetails.idprovider_details_id,
            ProviderDetails.provider_name,
            ProviderDetails.provider_contact_info,
            Location.id_location,
            Location.position_wkt,
            ProductProvider.id_product_provider,
            ProductProvider.product_provider_type_id,
            ProductProvider.product_provider_owner,
            Address.id_address,
            Address.address_street,
            Address.address_city,
            Address.address_postal_code,
            Address.address_country,
        ]
        
        return search_by_filter(
            ProductProvider,
            join_tables=[
                ProductProvider.product_provider_location,
                Location.location_address,
                ProductProvider.product_provider_details
            ],
            conditions=[
                func.ST_Distance(Location.location_position, ST_location) <= distance_km * 1000
            ],
            labeled_attrs=labeled_attrs,
            ordering_attr=["distance"],
            selected_fields=selected_fields,
            eager_load_depth=None,
            offset=offset,
            limit=limit
        )

# repositories/organisation_repository.py
from typing import Optional, List
from core.models.models import ProviderOrganisation, OrganisationImage
import storage.storage_broker as storage_broker

class OrganisationRepository:
    """Repository for Organisation-related database operations"""
    
    def get_org_by_id(self, org_id: str, eager_load: bool = True) -> Optional[ProviderOrganisation]:
        """Get organisation by ID"""
        if eager_load:
            records = storage_broker.get(
                ProviderOrganisation,
                {ProviderOrganisation.idprovider_organisation: org_id},
                None,
                [
                    ProviderOrganisation.organisation_image,
                    ProviderOrganisation.product_provider,
                    ProviderOrganisation.naming_contribution,
                    ProviderOrganisation.management_rule
                ]
            )
        else:
            records = storage_broker.get(
                ProviderOrganisation,
                {ProviderOrganisation.idprovider_organisation: org_id},
                None,
                []
            )
        return records[0] if records else None
    
    def get_org_by_name(self, org_name: str) -> Optional[ProviderOrganisation]:
        """Get organisation by name"""
        records = storage_broker.get(
            ProviderOrganisation,
            {ProviderOrganisation.provider_organisation_name: org_name},
            None,
            [ProviderOrganisation.naming_contribution,]
        )
        return records[0] if records else None
    
    def get_all_orgs(self, offset: int = 0, limit: int = 100) -> List[ProviderOrganisation]:
        """Get all organisations with pagination"""
        return storage_broker.get(
            ProviderOrganisation,
            {},
            None,
            eager_load_depth=[ProviderOrganisation.organisation_image,ProviderOrganisation.naming_contribution,],
            offset=offset,
            limit=limit,
            serialize=True
        )
    
    def create_org(self, organisation: ProviderOrganisation) -> ProviderOrganisation:
        """Create a new organisation"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(organisation)
    
    def update_org(self, organisation: ProviderOrganisation) -> ProviderOrganisation:
        """Update an existing organisation"""
        from features.insertion import update_record_in_api
        return update_record_in_api(organisation)
    
    def delete_org(self, organisation: ProviderOrganisation) -> bool:
        """Delete an organisation"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(organisation)
    
    def get_org_images(self, org_id: str) -> List[OrganisationImage]:
        """Get all images for an organisation"""
        return storage_broker.get(
            OrganisationImage,
            {OrganisationImage.org_ref_id: org_id},
            None,
            [],
            serialize=True
        )
    
    def get_org_image_by_id(self, image_id: str) -> Optional[OrganisationImage]:
        """Get organisation image by ID"""
        records = storage_broker.get(
            OrganisationImage,
            {OrganisationImage.id_org_image: image_id},
            None,
            None
        )
        return records[0] if records else None
    
    def create_org_image(self, image: OrganisationImage) -> OrganisationImage:
        """Create an organisation image"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(image)
    
    def update_org_image(self, image: OrganisationImage) -> OrganisationImage:
        """Update an organisation image"""
        from features.insertion import update_record_in_api
        return update_record_in_api(image)
    
    def delete_org_image(self, image: OrganisationImage) -> bool:
        """Delete an organisation image"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(image)