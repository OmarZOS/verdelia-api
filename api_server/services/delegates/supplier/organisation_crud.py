"""
CRUD operations for organisations.
"""

import logging
from typing import Optional, List, Dict, Any

from core.models.api_models import (
    ProviderOrganisation_API,
    OrganisationImage_API,
)
from core.models.models import OrganisationImage, ProviderOrganisation
from core.exceptions.specific.supplier_exceptions import (
    OrganisationInsertFailedException,
    OrganisationUpdateFailedException,
    OrganisationDeleteFailedException,
)
from repositories.supplier_repository import OrganisationRepository
from .organisation_validator import OrganisationValidator
from .organisation_image import OrganisationImageHandler

from core.logging_config import get_logger

logger = get_logger(__name__)


_UNSET = object()


class OrganisationCrud:
    """CRUD operations for organisations."""

    def __init__(self):
        self.org_repo = OrganisationRepository()
        self.validator = OrganisationValidator()
        self.image_handler = OrganisationImageHandler()

    # ==================== Retrieval ====================

    def get_by_id(self, org_id: str) -> ProviderOrganisation:
        """
        Get organisation by ID.
        """
        return self.validator.validate_org_exists(org_id)

    def get_by_name(
        self, org_name: str
    ) -> Optional[ProviderOrganisation]:
        """
        Get organisation by name.
        """
        return self.org_repo.get_org_by_name(org_name)

    def get_all(
        self, offset: int = 0, limit: int = 100
    ) -> List[ProviderOrganisation]:
        """
        Get all organisations with pagination.
        """
        logger.debug(
            f"Fetching all organisations (offset={offset}, limit={limit})"
        )
        return self.org_repo.get_all_orgs(offset, limit)


    def create(
        self,
        org: ProviderOrganisation_API,
        org_image: Optional[OrganisationImage_API] = None,
        *,
        naming_contribution_id: Optional[int] = None,
    ) -> ProviderOrganisation:
        """Create a new organisation."""
        logger.info(
            f"Creating new organisation: {org.provider_organisation_name}"
        )

        self.validator.validate_org_name_unique(org.provider_organisation_name)

        model_org = ProviderOrganisation(
            app_user_id=org.app_user_id,
            provider_organisation_name=org.provider_organisation_name,
            provider_organisation_desc=org.provider_organisation_desc,
        )

        # The FK column is `provider_organisation_naming`, not
        # `provider_organisation_naming_ref`.
        if naming_contribution_id is not None:
            model_org.provider_organisation_naming = naming_contribution_id

        if org_image and org_image.org_image_url:
            organisation_image = OrganisationImage(
                org_image_url=org_image.org_image_url
            )
            model_org.organisation_image = [organisation_image]

        try:
            result = self.org_repo.create_org(model_org)
            logger.info(
                f"Organisation created successfully with ID: "
                f"{result.idprovider_organisation}"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to create organisation: {e}")
            raise OrganisationInsertFailedException(
                error=str(e),
                org_name=org.provider_organisation_name,
            )

    def update(
        self,
        organisation: ProviderOrganisation_API,
        image: Optional[OrganisationImage_API] = None,
        *,
        naming_contribution_id: Optional[int] = _UNSET,  # type: ignore
    ) -> ProviderOrganisation:
        """Update an existing organisation."""
        logger.info(
            f"Updating organisation with ID: "
            f"{organisation.id_provider_organisation}"
        )

        org_old = self.validator.validate_org_exists(
            organisation.id_provider_organisation
        )
        self.validator.validate_ownership(org_old, organisation.app_user_id)

        if (
            org_old.provider_organisation_name
            != organisation.provider_organisation_name
        ):
            self.validator.validate_org_name_unique(
                organisation.provider_organisation_name,
                exclude_org_id=organisation.id_provider_organisation,
            )

        org_old.provider_organisation_name = (
            organisation.provider_organisation_name
        )
        org_old.provider_organisation_desc = (
            organisation.provider_organisation_desc
        )

        # Same column rename on update.
        if naming_contribution_id is not _UNSET:
            org_old.provider_organisation_naming = naming_contribution_id

        self.image_handler.handle_image(org_old, image)

        try:
            result = self.org_repo.update_org(org_old)
            logger.info(
                f"Organisation updated successfully with ID: "
                f"{result.idprovider_organisation}"
            )
            return result
        except Exception as e:
            logger.error(
                f"Failed to update organisation "
                f"{organisation.id_provider_organisation}: {e}"
            )
            raise OrganisationUpdateFailedException(
                org_id=organisation.id_provider_organisation,
                error=str(e),
            )

    # ==================== Delete ====================

    def delete(self, org_id: str, user_id: int) -> Dict[str, Any]:
        """
        Delete an organisation and associated images.
        """
        logger.info(f"Deleting organisation with ID: {org_id}")

        org = self.validator.validate_org_exists(org_id)
        self.validator.validate_ownership(org, user_id)

        self.image_handler.delete_images(org_id)

        success = self.org_repo.delete_org(org)

        if not success:
            logger.error(f"Failed to delete organisation {org_id}")
            raise OrganisationDeleteFailedException(
                org_id=org_id,
                error="Repository returned False",
            )

        logger.info(f"Organisation {org_id} deleted successfully")
        return {
            "success": True,
            "message": "Organisation deleted successfully",
            "organisation_id": org_id,
        }