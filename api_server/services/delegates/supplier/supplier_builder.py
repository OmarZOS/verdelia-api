"""
Builder functions for supplier models.
"""

import logging
from typing import Optional

from core.models.api_models import Location_API, ProductProvider_API
from core.models.models import ProductProvider, ProductProviderType, ProviderDetails, ProviderOrganisation, Wallet
from services.location_service import LocationService
from .supplier_validator import SupplierValidator

from core.logging_config import get_logger

logger = get_logger(__name__)



class SupplierBuilder:
    """Builder for supplier models"""
    
    def __init__(self):
        self.validator = SupplierValidator()
        self.location_service = LocationService()
    
    def build_supplier_details(self, provider: ProductProvider_API) -> ProviderDetails:
        """
        Build ProviderDetails from API data.
        
        Args:
            provider: Provider API data
            
        Returns:
            ProviderDetails model instance
        """
        details = ProviderDetails(
            provider_name=provider.provider_name,
            provider_contact_info=provider.provider_contact_info,
        )
        if provider.idprovider_details_id != 0:
            details.idprovider_details_id = provider.idprovider_details_id
        return details
    
    def build_supplier_model(
        self,
        provider: ProductProvider_API,
        location: Optional[Location_API] = None,
        wallet_balance: Optional[float] = 0.0,
        wallet_type: Optional[str] = 'provider',
    ) -> ProductProvider:
        """
        Build ProductProvider model from API data.
        
        Args:
            provider: Provider API data
            location: Optional location API data
            
        Returns:
            ProductProvider model instance
        """
        # Validate supplier type
        self.validator.validate_supplier_type(provider.id_product_provider_type)
        
        new_supplier = ProductProvider()
        new_supplier.product_provider_type_id = provider.id_product_provider_type
        new_supplier.product_provider_owner = provider.id_provider_owner
        new_supplier.product_provider_details = self.build_supplier_details(provider)


        new_supplier.product_provider_wallet = Wallet(
                    wallet_balance= wallet_balance,
                    wallet_type = wallet_type,
                    wallet_status= 'active'
                )

        
        # Handle location
        if location:
            location_obj = self.location_service.build_location_model(location)
            new_supplier.product_provider_location = location_obj
        
        # Handle organisation
        if provider.id_provider_organisation == 0:
            new_supplier.product_provider_org = ProviderOrganisation(
                provider_organisation_name=provider.provider_organisation_name,
                provider_organisation_desc=provider.provider_organisation_desc,
                provider_organisation_wallet = Wallet(
                    wallet_balance= 0.0,
                    wallet_type = 'organisation',
                    wallet_status= 'active'
                )
            )
        else:
            new_supplier.product_provider_org_id = provider.id_provider_organisation
        
        return new_supplier