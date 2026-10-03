# services/supplier_service.py
"""
Supplier and organisation services.

Naming-contribution handling is delegated to `NamingFlow`, which
resolves (or creates) a NamingContribution and returns only its id.
The id is passed to the delegate; no bound ORM object crosses the
service/delegate boundary, which keeps the read and write sessions
independent.
"""

import logging
from typing import Optional, List, Dict, Any

from services.delegates.supplier.supplier_search import SupplierSearch
from services.delegates.supplier.organisation_crud import OrganisationCrud
from services.delegates.supplier.supplier_crud import SupplierCrud
from core.models.api_models import (
    Location_API,
    ProductProvider_API,
    ProviderImage_API,
    ProviderOrganisation_API,
    OrganisationImage_API,
)
from core.models.models import (
    ProductProvider,
    ProductProviderType,
    ProviderOrganisation,
)
from repositories.naming_contribution_repository import (
    NamingContributionRepository,
)
from services.naming_flow import NamingFlow

from core.logging_config import get_logger

logger = get_logger(__name__)


# Contribution type. Matches the `naming_contribution_type` enum value
# used for both suppliers and organisations — the schema does not
# distinguish them, since both are "provider" names in the enum.
PROVIDER_CONTRIBUTION_TYPE = 'provider'


class SupplierService:
    """Service for supplier/provider-related business logic."""

    def __init__(self):
        self.supplier_crud = SupplierCrud()
        self.organisation_crud = OrganisationCrud()
        self.naming_repo = NamingContributionRepository()
        self._naming_flow = NamingFlow(
            self.naming_repo, PROVIDER_CONTRIBUTION_TYPE
        )

    # ==================== Retrieval ====================

    def get_supplier_by_id(
        self, provider_id: str, full: bool = True
    ) -> ProductProvider:
        return self.supplier_crud.get_by_id(provider_id, full)

    def get_suppliers_by_ids(
        self, provider_ids: List[str], full: bool = True
    ) -> List[ProductProvider]:
        return self.supplier_crud.get_suppliers_by_ids(provider_ids, full)

    def get_all_suppliers(
        self,
        owner_id: int = 0,
        org_id: int = 0,
        offset: int = 0,
        limit: int = 10,
    ) -> List[ProductProvider]:
        return self.supplier_crud.get_all(owner_id, org_id, offset, limit)

    def get_supplier_types(self) -> List[ProductProviderType]:
        return self.supplier_crud.get_types()

    # ==================== Create ====================

    def create_supplier(
        self,
        provider: ProductProvider_API,
        location: Location_API,
        image: Optional[ProviderImage_API] = None,
    ) -> ProductProvider:
        """
        Create a new supplier.

        The naming flow resolves the contribution id from the payload
        and rolls back a freshly-created row if the delegate raises.
        """
        with self._naming_flow.for_payload(
            naming=getattr(provider, "naming", None),
            fallback=provider.provider_name,
            context="supplier create",
        ) as resolved:
            return self.supplier_crud.create(
                provider,
                location,
                image,
                naming_contribution_id=resolved.id,
            )

    # ==================== Update ====================

    def update_supplier(
        self,
        provider: ProductProvider_API,
        image: Optional[ProviderImage_API] = None,
        location: Optional[Location_API] = None,
        user_id: Optional[int] = 0,
    ) -> ProductProvider:
        """Update an existing supplier."""
        with self._naming_flow.for_payload(
            naming=getattr(provider, "naming", None),
            fallback=provider.provider_name,
            context="supplier update",
        ) as resolved:
            return self.supplier_crud.update(
                provider,
                image,
                location,
                user_id,
                naming_contribution_id=resolved.id,
            )

    # ==================== Delete ====================

    def delete_supplier(
        self, provider_id: str, user_id: int
    ) -> Dict[str, Any]:
        return self.supplier_crud.delete(provider_id, user_id)

    # ==================== Search ====================

    def search_suppliers_by_location(
        self,
        longitude: float,
        latitude: float,
        distance_km: float,
        offset: int = 0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        search = SupplierSearch()
        logger.info(
            f"Searching suppliers near ({longitude}, {latitude}) "
            f"within {distance_km}km"
        )
        return search.search_by_filter(
            longitude, latitude, distance_km, offset, limit
        )


class OrganisationService:
    """Service for organisation-related business logic."""

    def __init__(self):
        self.organisation_crud = OrganisationCrud()
        self.naming_repo = NamingContributionRepository()
        self._naming_flow = NamingFlow(
            self.naming_repo, PROVIDER_CONTRIBUTION_TYPE
        )

    # ==================== Retrieval ====================

    def get_org_by_id(self, org_id: str) -> ProviderOrganisation:
        return self.organisation_crud.get_by_id(org_id)

    def get_org_by_name(
        self, org_name: str
    ) -> Optional[ProviderOrganisation]:
        return self.organisation_crud.get_by_name(org_name)

    def get_all_orgs(
        self, offset: int = 0, limit: int = 100
    ) -> List[ProviderOrganisation]:
        return self.organisation_crud.get_all(offset, limit)

    # ==================== Create ====================

    def create_organisation(
        self,
        org: ProviderOrganisation_API,
        org_image: Optional[OrganisationImage_API] = None,
    ) -> ProviderOrganisation:
        with self._naming_flow.for_payload(
            naming=getattr(org, "naming", None),
            fallback=org.provider_organisation_name,
            context="organisation create",
        ) as resolved:
            return self.organisation_crud.create(
                org,
                org_image,
                naming_contribution_id=resolved.id,
            )

    # ==================== Update ====================

    def update_organisation(
        self,
        organisation: ProviderOrganisation_API,
        image: Optional[OrganisationImage_API] = None,
    ) -> ProviderOrganisation:
        with self._naming_flow.for_payload(
            naming=getattr(organisation, "naming", None),
            fallback=organisation.provider_organisation_name,
            context="organisation update",
        ) as resolved:
            return self.organisation_crud.update(
                organisation,
                image,
                naming_contribution_id=resolved.id,
            )

    # ==================== Delete ====================

    def delete_organisation(
        self, org_id: str, user_id: int
    ) -> Dict[str, Any]:
        return self.organisation_crud.delete(org_id, user_id)