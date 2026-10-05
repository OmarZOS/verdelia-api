"""
CRUD operations for suppliers.
"""

import logging
from typing import Optional, List, Dict, Any

from core.models.api_models import (
    ProductProvider_API,
    Location_API,
    ProviderImage_API,
)
from core.models.models import (
    ProductProvider,
    ProductProviderType,
    ProviderImage,
    ProviderDetails,   # NEW: FK lives on this class
)
from core.exceptions.specific.supplier_exceptions import (
    SupplierAlreadyExistsException,
    SupplierInsertFailedException,
    SupplierUpdateFailedException,
    SupplierDeleteFailedException,
)
from repositories.supplier_repository import SupplierRepository
from .supplier_validator import SupplierValidator
from .supplier_builder import SupplierBuilder
from .supplier_image import SupplierImageHandler

from core.logging_config import get_logger

logger = get_logger(__name__)


_UNSET = object()


class SupplierCrud:
    """CRUD operations for suppliers."""

    def __init__(self):
        self.supplier_repo = SupplierRepository()
        self.validator = SupplierValidator()
        self.builder = SupplierBuilder()
        self.image_handler = SupplierImageHandler()


    # ==================== Retrieval ====================

    def get_by_id(
        self, provider_id: str, full: bool = True
    ) -> ProductProvider:
        """
        Get supplier by ID.
        """
        return self.validator.validate_supplier_exists(provider_id, full)

    def get_suppliers_by_ids(
        self, provider_ids: List[str], full: bool = True
    ) -> List[ProductProvider]:
        """
        Get suppliers by a list of IDs.
        """
        return self.supplier_repo.get_suppliers_by_ids(provider_ids, full)

    def get_all(
        self,
        owner_id: int = 0,
        org_id: int = 0,
        offset: int = 0,
        limit: int = 10,
    ) -> List[ProductProvider]:
        """
        Get all suppliers with filters.
        """
        logger.debug(
            f"Fetching suppliers - owner_id:{owner_id}, "
            f"org_id:{org_id}, offset:{offset}, limit:{limit}"
        )
        return self.supplier_repo.get_all_suppliers(
            owner_id, org_id, offset, limit
        )

    def get_types(self) -> List[ProductProviderType]:
        """
        Get all supplier types.
        """
        logger.debug("Fetching all supplier types")
        return self.supplier_repo.get_all_supplier_types()


    def create(
        self,
        provider: ProductProvider_API,
        location: Location_API,
        image: Optional[ProviderImage_API] = None,
        *,
        naming_contribution_id: Optional[int] = None,
    ) -> ProductProvider:
        """
        Create a new supplier.

        The naming FK lives on `ProviderDetails.provider_naming_ref`,
        not on `ProductProvider`. This method writes it there, on
        whichever details row the builder attached.
        """
        logger.info(f"Creating new supplier: {provider.provider_name}")

        existing = self.supplier_repo.get_supplier_by_id(
            provider.id_product_provider, eager_load=False
        )
        if existing:
            raise SupplierAlreadyExistsException(
                supplier_id=provider.id_product_provider,
                supplier_name=provider.provider_name,
            )

        new_supplier = self.builder.build_supplier_model(provider, location)

        # Attach the naming FK to the details row, not the provider row.
        if naming_contribution_id is not None:
            if new_supplier.product_provider_details is None:
                # Builder didn't attach a details row; create one so
                # the FK has somewhere to live.
                new_supplier.product_provider_details = ProviderDetails(
                    provider_naming_ref=naming_contribution_id,
                    provider_name=provider.provider_name,
                    provider_contact_info=provider.provider_contact_info,
                )
            else:
                new_supplier.product_provider_details.provider_naming_ref = (
                    naming_contribution_id
                )

        if image and image.provider_image_url:
            provider_image = ProviderImage(
                provider_image_url=image.provider_image_url
            )
            new_supplier.provider_image = [provider_image]

        try:
            result = self.supplier_repo.create_supplier(new_supplier)
            logger.info(
                f"Supplier created successfully with ID: "
                f"{result.id_product_provider}"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to create supplier: {e}")
            raise SupplierInsertFailedException(
                error=str(e),
                supplier_id=provider.id_product_provider,
                supplier_name=provider.provider_name,
            )

    def update(
        self,
        provider: ProductProvider_API,
        image: Optional[ProviderImage_API] = None,
        location: Optional[Location_API] = None,
        user_id: Optional[int] = 0,
        *,
        naming_contribution_id: Optional[int] = _UNSET,  # type: ignore
    ) -> ProductProvider:
        """
        Update an existing supplier.

        The naming FK update writes to
        `supplier_old.product_provider_details.provider_naming_ref`.
        """
        logger.info(
            f"Updating supplier with ID: {provider.id_product_provider}"
        )

        self.validator.validate_supplier_type(provider.id_product_provider_type)
        supplier_old = self.validator.validate_supplier_exists(
            provider.id_product_provider
        )
        self.validator.validate_ownership(supplier_old, user_id)

        if supplier_old.product_provider_details:
            supplier_old.product_provider_details.provider_name = (
                provider.provider_name
            )
            supplier_old.product_provider_details.provider_contact_info = (
                provider.provider_contact_info
            )

        supplier_old.product_provider_type_id = provider.id_product_provider_type
        supplier_old.product_provider_org_id = provider.id_provider_organisation

        # Write the FK on the details row when the caller told us to.
        if naming_contribution_id is not _UNSET:
            if supplier_old.product_provider_details is not None:
                supplier_old.product_provider_details.provider_naming_ref = (
                    naming_contribution_id
                )

        self.image_handler.handle_image(supplier_old, image)

        if location and location.id_location != 0:
            updated_location = self.builder.location_service.update_location(
                location.id_location, location
            )
            supplier_old.product_provider_location_id = (
                updated_location.id_location
            )

        try:
            result = self.supplier_repo.update_supplier(supplier_old)
            logger.info(
                f"Supplier updated successfully with ID: "
                f"{result.id_product_provider}"
            )
            return result
        except Exception as e:
            logger.error(
                f"Failed to update supplier "
                f"{provider.id_product_provider}: {e}"
            )
            raise SupplierUpdateFailedException(
                supplier_id=provider.id_product_provider,
                error=str(e),
            )

    # ==================== Delete ====================

    def delete(self, provider_id: str, user_id: int) -> Dict[str, Any]:
        """
        Delete a supplier and associated images.
        """
        logger.info(f"Deleting supplier with ID: {provider_id}")

        supplier = self.validator.validate_supplier_exists(provider_id)
        self.validator.validate_ownership(supplier, user_id)

        self.image_handler.delete_images(provider_id)

        success = self.supplier_repo.delete_supplier(supplier)

        if not success:
            logger.error(f"Failed to delete supplier {provider_id}")
            raise SupplierDeleteFailedException(
                supplier_id=provider_id,
                error="Repository returned False",
            )

        logger.info(f"Supplier {provider_id} deleted successfully")
        return {
            "success": True,
            "message": "Supplier deleted successfully",
            "supplier_id": provider_id,
        }

  

    def count_by_owner(self, owner_id: int) -> int:
        """How many suppliers a user owns.

        Scoped to the owner, not to any organisation — the plan
        limit is "how many suppliers can this user create",
        regardless of how they're grouped.
        """
        return self.supplier_repo.count_supplier_for_user(owner_id)