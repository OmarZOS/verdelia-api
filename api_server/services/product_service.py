# services/product_service.py
"""
Product service — local operations only.

Responsibilities (strictly local):
  - validations against the repository (existence, category, uniqueness)
  - model construction (Product, ProductImage, Iproduct)
  - persistence via repositories
  - entity-level rollback (delete local rows)

Allowed collaborators:
  - repositories (ProductRepository, IProductRepository,
    NamingContributionRepository)
  - the NamingFlow helper for trilingual names
  - pure-local helpers that have no I/O beyond repos

Forbidden collaborators:
  - AIService (network / model inference)
  - any service that performs a remote call
  - subscriber notification (that belongs to the workflow or the router)
  - background task scheduling

Every method the workflow needs to reach is public (no leading underscore).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from storage import storage_broker
from core.logging_config import get_logger
from core.exceptions.specific.supplier_exceptions import (
    ImageInsertFailedException,
    ImageUpdateFailedException,
)
from core.models.api_models import (
    Product_API,
    ProductImage_API,
    Iproduct_API,
    NamingContribution_API,
)
from core.exceptions.specific.product_exceptions import (
    ProductNotFoundException,
    ProductAlreadyExistsException,
    ProductInsertFailedException,
    ProductUpdateFailedException,
    ProductDeleteFailedException,
    ProductCategoryNotFoundException,
    ProductImageNotFoundException,
)
from core.models.models import Product, ProductImage, Iproduct
from repositories.product_repository import ProductRepository, _visible_filter
from repositories.iproduct_repository import IProductRepository
from repositories.naming_contribution_repository import (
    NamingContributionRepository,
)
from services.naming_flow import NamingFlow, ResolvedNaming


from core.logging_config import get_logger

logger = get_logger(__name__)



VISIBILITY_VISIBLE = "VISIBLE"
VISIBILITY_HIDDEN = "HIDDEN"
VISIBILITY_DELETED = "DELETED"

# Contribution type for iproduct naming rows. Matches the
# `naming_contribution_type` enum value.
IPRODUCT_CONTRIBUTION_TYPE = "product"


class ProductService:
    """Local-only product operations."""

    def __init__(self):
        self.product_repo = ProductRepository()
        self.iproduct_repo = IProductRepository()
        self.naming_repo = NamingContributionRepository()
        # One flow, reused by every method that resolves a name.
        self._naming_flow = NamingFlow(
            self.naming_repo, IPRODUCT_CONTRIBUTION_TYPE
        )

    # ==================== Retrieval ====================

    def get_product_by_id(
        self,
        product_id: int,
        eager_load: bool = False,
        include_hidden: bool = True,
    ) -> Optional[Product]:
        """
        Get a product by ID.

        `include_hidden` defaults to True so the editor can always open a
        product by id, even when it's hidden. Pass False to treat a hidden
        product as if it doesn't exist.

        `eager_load` controls how deep the hydration goes:
        - False → just the row itself plus its category and images.
            Cheap; used by listings and cards.
        - True  → the full details graph. Category with its naming row,
            provider with details / org / location / images / type, the
            product's own images, the origin Iproduct with its category
            and naming row, and reactions. One HTTP round trip; everything
            the details screen needs to render without a second call.
        """
        conditions = [Product.id_product == product_id]

        if not include_hidden:
            conditions.append(_visible_filter())

        eager = (
            [


                # Product's own image gallery.
                Product.product_image,

                # Origin Iproduct — the AI-derived metadata plus the
                # trilingual name and the reference category.
                {
                    Product.product_origin: [
                        Iproduct.naming_contribution,
                    ]
                },

                # Reactions — cheap enough to include; the details screen
                # typically renders like/rating counts.
                Product.product_reaction,
            ]
            if eager_load
            else [
                Product.product_category,
                Product.product_image,
            ]
        )

        records = storage_broker.get(
            Product,
            conditions,
            [],
            eager,
        )
        return records[0] if records else None

    def get_all_products(
        self,
        user_id: int = 0,
        provider_id: int = 0,
        category_id: int = 0,
        product_barcode = None,
        offset: int = 0,
        limit: int = 10,
        serialize: bool = False,
        include_hidden: bool = False,
        domain: Optional[str] = None,
        subdomain: Optional[str] = None,
    ) -> List[Product]:
        """
        Fetch all products with filters.

        `domain` and `subdomain` follow the `domain.subdomain.category`
        naming convention used by product categories. `subdomain`
        requires `domain` — filtering by subdomain alone is ambiguous
        across domains, so we reject it early rather than silently
        matching every domain that happens to carry that subdomain.
        """
        domain_n = self._normalize_segment(domain)
        subdomain_n = self._normalize_segment(subdomain)

        if subdomain_n and not domain_n:
            raise ValueError(
                "`subdomain` requires `domain` to be specified as well."
            )

        return self.product_repo.get_all_products(
            user_id,
            provider_id,
            category_id,
            product_barcode,
            offset,
            limit,
            serialize,
            include_hidden=include_hidden,
            domain=domain_n,
            subdomain=subdomain_n,
        )

    def count_products_for_provider(self, provider_id: int) -> int:
        """Count products currently attached to a provider.

        The plan limit is enforced against the current provider count,
        not against a guessed value in the router. Use the storage
        broker's count API instead of a paginated list query so the
        call never hits the global `limit` validation guard.
        """
        return int(
            storage_broker.count(
                Product,
                conditions={Product.product_provider_id: provider_id},
            )
            or 0
        )

    def get_products_by_category(
        self,
        category_id: int,
        offset: int = 0,
        limit: int = 10,
        include_hidden: bool = False,
    ) -> List[Product]:
        category = self.product_repo.get_product_category_by_id(category_id)
        if not category:
            raise ProductCategoryNotFoundException(category_id=category_id)
        return self.product_repo.get_products_by_category(
            category_id,
            offset,
            limit,
            include_hidden=include_hidden,
        )

    def get_product_categories(self) -> List:
        return self.product_repo.get_product_categories()

    def get_iproduct_by_barcode(
        self, barcode: str
    ) -> Optional[List[Iproduct]]:
        return self.iproduct_repo.get_by_barcode(barcode)

    def get_iproduct_by_id(self, iproduct_id: int) -> Optional[Iproduct]:
        return self.iproduct_repo.get_by_id(iproduct_id)

    # ==================== Category validation ====================

    def validate_category(self, category_id: int) -> Any:
        """Local: fetch the category or raise."""
        category = self.product_repo.get_product_category_by_id(category_id)
        if not category:
            logger.warning(f"Product category not found with ID: {category_id}")
            raise ProductCategoryNotFoundException(category_id=category_id)
        return category

    # ==================== Creation ====================

    def create_product(
        self,
        product_api: Product_API,
        image: Optional[ProductImage_API] = None,
        iproduct: Optional[Iproduct_API] = None,
    ) -> Product:
        """
        Local: build and persist a Product.

        When `iproduct` is provided, its naming contribution is resolved
        inside `attach_iproduct` before the iproduct row is inserted.
        """
        logger.info(f"Creating new product: {product_api.product_name}")

        if product_api.id_product:
            existing = self.product_repo.get_product_by_id(
                product_api.id_product,
                include_hidden=True,
            )
            if existing:
                raise ProductAlreadyExistsException(
                    product_id=product_api.id_product,
                    product_name=product_api.product_name,
                )

        product_category = self.validate_category(
            product_api.product_category_id
        )

        product = self.build_product_model(product_api)
        product.product_category_id = product_category.id_product_category

        if image and image.product_image_url:
            product.product_image = [
                ProductImage(product_image_url=image.product_image_url)
            ]

        if iproduct:
            self.attach_iproduct(product, iproduct)

        try:
            result = self.product_repo.create_product(product)
            logger.info(
                f"Product created successfully with ID: {result.id_product}"
            )
            return result
        except Exception as e:
            logger.error(f"Failed to create product: {e}")
            raise ProductInsertFailedException(
                error=str(e),
                product_name=product_api.product_name,
            )

    # ==================== Update ====================

    def update_product(
        self,
        product_id: int,
        product_api: Product_API,
        image: Optional[ProductImage_API] = None,
    ) -> Product:
        """Local: apply fields and persist."""
        logger.info(f"Updating product with ID: {product_id}")

        product_category = self.validate_category(
            product_api.product_category_id
        )
        product = self.get_product_by_id(product_id, include_hidden=True)

        changes = self._collect_changes(product, product_api)

        product.product_name = product_api.product_name
        product.product_brand = product_api.product_brand
        product.product_barcode = product_api.product_barcode
        product.product_price = product_api.product_price
        product.product_base_price = getattr(
            product_api, "product_base_price", product.product_base_price
        )
        product.product_quantity = product_api.product_quantity
        product.product_reserved_quantity = getattr(
            product_api,
            "product_reserved_quantity",
            product.product_reserved_quantity,
        )
        product.product_quantifier = product_api.product_quantifier
        product.product_description = product_api.product_description
        product.product_visibility = getattr(
            product_api, "product_visibility", product.product_visibility
        )
        product.product_origin_id = getattr(
            product_api, "product_origin_id", product.product_origin_id
        )
        product.product_category_id = product_category.id_product_category
        product.last_updated = datetime.now()

        if image and image.product_image_url:
            self.handle_product_image(image, product)

        try:
            updated = self.product_repo.update_product(product)
            logger.info(
                f"Product {product_id} updated successfully. "
                f"Changes: {changes if changes else 'none'}"
            )
            return updated
        except Exception as e:
            logger.error(f"Failed to update product {product_id}: {e}")
            raise ProductUpdateFailedException(
                product_id=product_id,
                error=str(e),
            )

    def update_product_visibility(
        self,
        product_id: int,
        visibility: str,
    ) -> Product:
        """
        Local: set only the visibility field and persist.

        Single point of truth for visibility changes. The router calls
        this directly instead of rebuilding a Product_API from the
        current row.
        """
        normalized = (visibility or "").strip().upper()
        if normalized not in (VISIBILITY_VISIBLE, VISIBILITY_HIDDEN):
            raise ValueError(
                f"Invalid visibility '{visibility}'. "
                f"Expected '{VISIBILITY_VISIBLE}' or '{VISIBILITY_HIDDEN}'."
            )

        product = self.get_product_by_id(product_id, include_hidden=True)

        if product.product_visibility == normalized:
            logger.info(
                f"Product {product_id} visibility already '{normalized}'; "
                f"no change."
            )
            return product

        previous = product.product_visibility
        product.product_visibility = normalized
        product.last_updated = datetime.now()

        try:
            updated = self.product_repo.update_product(product)
            logger.info(
                f"Product {product_id} visibility: {previous} → {normalized}"
            )
            return updated
        except Exception as e:
            logger.error(
                f"Failed to update visibility for product {product_id}: {e}"
            )
            raise ProductUpdateFailedException(
                product_id=product_id,
                error=str(e),
            )

    # ==================== Deletion ====================

    def delete_product(
        self, product_id: int, force_delete: bool = False
    ) -> bool:
        logger.info(
            f"Deleting product with ID: {product_id} (force={force_delete})"
        )
        product = self.get_product_by_id(product_id, include_hidden=True)

        product.product_visibility = VISIBILITY_DELETED

        try:
            result = self.product_repo.update_product(product)
            if not result:
                raise ProductDeleteFailedException(
                    product_id=product_id,
                    error="Repository returned False",
                )
            logger.info(f"Product {product_id} deleted successfully")
            return result
        except ProductDeleteFailedException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete product {product_id}: {e}")
            raise ProductDeleteFailedException(
                product_id=product_id,
                error=str(e),
            )

    def check_product_dependencies(self, product_id: int) -> bool:
        """Local: true when the product is referenced by any order or cart."""
        order_items = self.product_repo.get_order_items_by_product(product_id)
        if order_items:
            logger.debug(
                f"Product {product_id} has {len(order_items)} order items"
            )
            return True

        cart_items = self.product_repo.get_cart_items_by_product(product_id)
        if cart_items:
            logger.debug(
                f"Product {product_id} has {len(cart_items)} cart items"
            )
            return True

        return False

    # ==================== Model builders ====================

    def build_product_model(self, product_api: Product_API) -> Product:
        return Product(
            product_name=product_api.product_name,
            product_brand=product_api.product_brand,
            product_barcode=product_api.product_barcode,
            product_price=product_api.product_price,
            product_base_price=product_api.product_base_price,
            product_quantifier=product_api.product_quantifier,
            product_quantity=product_api.product_quantity,
            product_reserved_quantity=product_api.product_reserved_quantity,
            product_visibility=getattr(
                product_api, "product_visibility", VISIBILITY_VISIBLE
            ),
            product_description=product_api.product_description,
            product_owner=product_api.product_owner,
            product_provider_id=product_api.product_provider_id,
            product_origin_id=getattr(
                product_api, "product_origin_id", None
            ),
            created=datetime.now(),
            last_updated=datetime.now(),
        )

    # ==================== Iproduct ====================

    def attach_iproduct(
        self, product: Product, iproduct_api: Iproduct_API
    ) -> None:
        """
        Link an Iproduct to a Product.

        New iproducts get a naming contribution resolved through the
        NamingFlow helper, which returns only the contribution id. The
        helper also manages rollback on downstream failure.
        """
        if iproduct_api.id_iproduct:
            existing = self.iproduct_repo.get_by_id(iproduct_api.id_iproduct)
            if existing:
                self.update_iproduct(existing, iproduct_api)
                product.product_origin_id = existing.id_iproduct
                logger.debug(
                    f"Linked existing IProduct {existing.id_iproduct}"
                )
                return

        # New iproduct: resolve the naming id inside the flow, and let
        # the flow roll back if the insert fails.
        with self._naming_flow.for_payload(
            naming=getattr(iproduct_api, "naming", None),
            fallback=iproduct_api.iproduct_name,
            context="iproduct insert",
        ) as resolved:
            new_iproduct = self.create_iproduct_from_api(
                iproduct_api,
                naming_contribution_id=resolved.id,
            )
            product.product_origin_id = new_iproduct.id_iproduct
            logger.debug("Linked new IProduct to product")

    def create_iproduct_from_api(
        self,
        iproduct_api: Iproduct_API,
        naming_contribution_id: Optional[int] = None,
    ) -> Iproduct:
        """
        Build and persist an Iproduct.

        `iproduct_name` is set from `naming.en` when a naming block is
        present, so the flat column and the naming row never drift.
        """
        now = datetime.now()

        nested: Optional[NamingContribution_API] = getattr(
            iproduct_api, "naming", None
        )
        flat_name = (iproduct_api.iproduct_name or "").strip()
        resolved_name = (
            (nested.en or "").strip() if nested is not None else ""
        ) or flat_name or "Unknown"

        iproduct = Iproduct(
            iproduct_name=resolved_name,
            iproduct_barcode=iproduct_api.iproduct_barcode,
            iproduct_brand=iproduct_api.iproduct_brand or "Unknown",
            iproduct_estimated_price=(
                iproduct_api.iproduct_estimated_price or 0.0
            ),
            iproduct_price_currency=(
                iproduct_api.iproduct_price_currency or "DZD"
            ),
            iproduct_gluten_status=(
                iproduct_api.iproduct_gluten_status or "unknown"
            ),
            iproduct_info_source=(
                iproduct_api.iproduct_info_source or "ai_analysis"
            ),
            iproduct_info_confidence=(
                iproduct_api.iproduct_info_confidence or 0.0
            ),
            iproduct_last_price_update=(
                iproduct_api.iproduct_last_price_update or now
            ),
            iproduct_created_at=iproduct_api.iproduct_created_at or now,
            iproduct_last_update=(
                iproduct_api.iproduct_last_update or now.isoformat()
            ),
            iproduct_model_name=iproduct_api.iproduct_model_name,
            iproduct_image_url=iproduct_api.iproduct_image_url,
            iproduct_naming_ref=naming_contribution_id,
        )

        self.iproduct_repo.create(iproduct)
        return iproduct

    def update_iproduct(
        self, existing: Iproduct, new_data: Iproduct_API
    ) -> Iproduct:
        """
        Apply fields to an existing Iproduct.

        When the payload carries a `naming` block, the flow resolves
        (or creates) the contribution and the iproduct's FK is updated
        to point at it. If the flow created a new contribution and the
        repo update fails, the flow rolls it back.
        """
        now = datetime.now()

        nested: Optional[NamingContribution_API] = getattr(
            new_data, "naming", None
        )

        if nested is not None and (nested.en or "").strip():
            with self._naming_flow.for_payload(
                naming=nested,
                fallback=None,
                context="iproduct update",
            ) as resolved:
                if resolved.is_usable:
                    existing.iproduct_naming_ref = resolved.id
                    existing.iproduct_name = (nested.en or "").strip()
                    self._apply_iproduct_fields(existing, new_data, now)
                    self.iproduct_repo.update(existing)
                    logger.debug(f"Updated IProduct {existing.id_iproduct}")
                    return existing
                # Flow could not resolve a name; fall through to the
                # no-naming path below.
        elif new_data.iproduct_name:
            existing.iproduct_name = new_data.iproduct_name

        self._apply_iproduct_fields(existing, new_data, now)
        self.iproduct_repo.update(existing)
        logger.debug(f"Updated IProduct {existing.id_iproduct}")
        return existing

    @staticmethod
    def _apply_iproduct_fields(
        existing: Iproduct,
        new_data: Iproduct_API,
        now: datetime,
    ) -> None:
        """Copy the flat fields that aren't naming-related."""
        if new_data.iproduct_brand:
            existing.iproduct_brand = new_data.iproduct_brand
        if new_data.iproduct_estimated_price is not None:
            existing.iproduct_estimated_price = (
                new_data.iproduct_estimated_price
            )
            existing.iproduct_last_price_update = now
        if new_data.iproduct_gluten_status:
            existing.iproduct_gluten_status = (
                new_data.iproduct_gluten_status
            )
        if new_data.iproduct_info_source:
            existing.iproduct_info_source = new_data.iproduct_info_source
        if new_data.iproduct_info_confidence is not None:
            existing.iproduct_info_confidence = (
                new_data.iproduct_info_confidence
            )
        if new_data.iproduct_image_url:
            existing.iproduct_image_url = new_data.iproduct_image_url
        existing.iproduct_last_update = now.isoformat()

    # ==================== Images ====================

    def handle_product_image(
        self, image: ProductImage_API, product: Product
    ) -> None:
        """Local: create or update the product's image row."""
        if image.id_product_image == 0:
            new_image = ProductImage(
                product_image_url=image.product_image_url
            )
            new_image.product_ref = product
            try:
                self.product_repo.create_product_image(new_image)
                logger.info(
                    f"Created product image for product {product.id_product}"
                )
            except Exception as e:
                logger.error(f"Failed to create product image: {e}")
                raise ImageInsertFailedException(
                    error=str(e),
                    details={"product_id": product.id_product},
                )
        else:
            existing_images = self.product_repo.get_product_image_by_id(
                image.id_product_image
            )
            if existing_images:
                existing_image = existing_images[0]
                existing_image.product_image_url = image.product_image_url
                try:
                    self.product_repo.update_product_image(existing_image)
                    logger.info(
                        f"Updated product image {image.id_product_image}"
                    )
                except Exception as e:
                    logger.error(f"Failed to update product image: {e}")
                    raise ImageUpdateFailedException(
                        image_id=image.id_product_image,
                        error=str(e),
                    )

    # ==================== Helpers ====================

    @staticmethod
    def _normalize_segment(value: Optional[str]) -> Optional[str]:
        """
        Normalize a domain or subdomain segment: trim, lowercase, and
        return None when empty. Ensures comparisons against dotted keys
        are case- and whitespace-insensitive.
        """
        if value is None:
            return "%"
        cleaned = f"%{value.strip().lower()}%"
        return cleaned or "%"

    def _collect_changes(
        self, product: Product, product_api: Product_API
    ) -> List[str]:
        changes: List[str] = []
        if product.product_name != product_api.product_name:
            changes.append(
                f"name: {product.product_name} -> {product_api.product_name}"
            )
        if product.product_price != product_api.product_price:
            changes.append(
                f"price: {product.product_price} -> {product_api.product_price}"
            )
        if product.product_quantity != product_api.product_quantity:
            changes.append(
                f"quantity: {product.product_quantity} -> "
                f"{product_api.product_quantity}"
            )
        if product.product_visibility != getattr(
            product_api, "product_visibility", product.product_visibility
        ):
            changes.append(
                f"visibility: {product.product_visibility} -> "
                f"{getattr(product_api, 'product_visibility', None)}"
            )
        return changes

    def product_to_dict(self, product: Product) -> Dict[str, Any]:
        """Local: serialise a Product for notifications."""
        out: Dict[str, Any] = {}
        for key, value in product.__dict__.items():
            if key.startswith("_"):
                continue
            if hasattr(value, "isoformat"):
                out[key] = value.isoformat()
            else:
                out[key] = value
        return out

    def search_products(
        self,
        token: str,
        offset: int = 0,
        limit: int = 20,
        domain: Optional[str] = None,
        subdomain: Optional[str] = None,
        include_hidden: bool = False,
    ):
        """
        Local: search products by token in name, brand, and description.

        Token matching is delegated to the repository, which owns the
        SQL-level LIKE/ILIKE clauses. Domain/subdomain filtering uses the
        same convention as `get_all_products`.
        """
        token_n = (token or "").strip()
        if len(token_n) < 2:
            # The router already guards, but keep the service safe for
            # direct callers.
            raise ValueError("Search token must be at least 2 characters.")

        return self.product_repo.search_products(
            token=token_n,
            offset=offset,
            limit=limit,
            include_hidden=include_hidden,
            domain=self._normalize_segment(domain),
            subdomain=self._normalize_segment(subdomain),
        )