# repositories/product_repository.py
from typing import Any, Optional, List

from sqlalchemy import exists, or_, not_, and_, outerjoin

from core.models.models import (
    NamingContribution,
    Product,
    Iproduct,
    ProductCategory,
    ProductImage,
    ProductProvider,
    ProductReaction,
)
import storage.storage_broker as storage_broker


def _visible_filter():
    """
    SQLAlchemy clause that matches rows visible to buyers.

    Treats a NULL `product_visibility` as visible: rows that predate the
    visibility column are public by default. Anything else must be the
    literal `'VISIBLE'`.
    """
    return or_(
        Product.product_visibility.is_(None),
        Product.product_visibility == 'VISIBLE'
    )


def _category_key_filter(domain: Optional[str], subdomain: Optional[str]):
    """
    Build a filter on the category's dotted key
    (`domain.subdomain.category`).

    - `domain` only     → `key LIKE 'domain.%'`
    - `domain+subdomain`→ `key LIKE 'domain.subdomain.%'`
    - `subdomain` only  → rejected at the service layer; if reached,
                          match any domain that carries that subdomain.

    The key lives in `ProductCategory.product_category_name` (per the
    naming convention where the column stores the dotted key).
    """
    if domain and subdomain:
        prefix = f"{domain}.{subdomain}.%"
        return ProductCategory.product_category_name.like(prefix)
    if domain:
        prefix = f"{domain}.%"
        return ProductCategory.product_category_name.like(prefix)
    if subdomain:
        # Ambiguous across domains; the service raises before reaching
        # here, but keep this defensive branch for direct repo callers.
        return ProductCategory.product_category_name.like(f"%.{subdomain}.%")
    return None


class ProductRepository:
    """Repository for Product-related database operations."""

    # ==================== Product reads ====================

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
        """
        conditions = [Product.id_product == product_id]

        if not include_hidden:
            conditions.append(_visible_filter())

        eager = (
            [
                Product.product_reaction,
                Product.product_category,
                Product.product_provider,
                Product.product_image,
                {Product.product_origin: [{Iproduct: [Iproduct.naming_contribution]}]},
            ]
            if eager_load
            else []
        )

        records = storage_broker.get(
            Product,
            conditions,
            [],
            eager,
        )
        return records[0] if records else None

    def get_products_by_ids(
        self,
        product_ids: List[int],
        eager_load: bool = False,
        include_hidden: bool = True,
    ) -> List[Product]:
        """
        Get products by a list of IDs.

        `include_hidden` defaults to True because callers that already
        have the ids usually want them back regardless of visibility
        (basket items, order history, cart references).
        """
        if not product_ids:
            return []

        conditions = [Product.id_product.in_(product_ids)]
        conditions.append(not_(Product.product_visibility == "DELETED"))
        if not include_hidden:
            conditions.append(_visible_filter())

        eager = (
            [
                Product.product_reaction,
                Product.product_category,
                Product.product_provider,
                Product.product_image,
                {Product.product_origin: [{Iproduct: [Iproduct.naming_contribution]}]},
            ]
            if eager_load
            else []
        )

        return storage_broker.get(
            Product,
            conditions,
            [],
            eager,
        )

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
        Get all products with filters.

        `domain` / `subdomain` filter on the category's dotted key
        (`domain.subdomain.category`). `subdomain` alone is ambiguous
        across domains and is expected to be rejected at the service
        layer; the repo keeps a defensive branch in case it's called
        directly.

        `include_hidden` defaults to False so the public catalog never
        surfaces hidden products. Editors that need everything must opt
        in explicitly.
        """
        conditions = []
        conditions.append(not_(Product.product_visibility == "DELETED"))

        if user_id != 0:
            conditions.append(Product.product_owner == user_id)
        if category_id != 0:
            conditions.append(Product.product_category_id == category_id)
        if provider_id != 0:
            conditions.append(Product.product_provider_id == provider_id)
        if product_barcode :
            conditions.append(Product.product_barcode == product_barcode)
        if not include_hidden:
            conditions.append(_visible_filter())

        # Domain / subdomain filter. Requires a join to ProductCategory
        # so the LIKE clause can run against the dotted key column.
        category_filter = _category_key_filter(domain, subdomain)
        join_tables = []
        if category_filter is not None:
            join_tables.append(ProductCategory)
            conditions.append(category_filter)

        return storage_broker.get(
            Product,
            conditions=conditions,
            join_tables=join_tables,
            eager_load_depth=[
                Product.product_category,
                Product.product_provider,
                {
                    Product.product_image: [
                        ProductImage.id_product_image,
                        ProductImage.product_image_url,
                    ]
                },
                {Product.product_origin: [{Iproduct.naming_contribution: [NamingContribution]}]},
            ],
            offset=offset,
            limit=limit,
        )

    def get_products_by_category(
        self,
        category_id: int,
        offset: int = 0,
        limit: int = 10,
        include_hidden: bool = False,
    ) -> List[Product]:
        """Get products by category ID."""
        conditions = [Product.product_category_id == category_id]
        conditions.append(not_(Product.product_visibility == "DELETED"))
        if not include_hidden:
            conditions.append(_visible_filter())

        return storage_broker.get(
            Product,
            conditions,
            [ProductCategory, ProductProvider],
            [
                Product.product_image,
                Product.product_category,
                Product.product_provider,
                {Product.product_origin: [{Iproduct: [Iproduct.naming_contribution]}]},
            ],
            None,
            offset,
            limit,
            serialize=True,
        )

    # ==================== Product writes ====================

    def create_product(self, product: Product) -> Product:
        """Create a new product."""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(product)

    def update_product(self, product: Product) -> Product:
        """Update an existing product."""
        from features.insertion import update_record_in_api
        return update_record_in_api(product)

    def delete_product(self, product: Product) -> bool:
        """Delete a product."""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(product)

    # ==================== Categories ====================

    def get_product_categories(self) -> List[ProductCategory]:
        """Get all product categories."""
        return storage_broker.get(
            ProductCategory,
            conditions=None,
            join_tables=None,
            eager_load_depth=[ProductCategory.naming_contribution],
            offset=0,
            limit=300,
        )

    def get_product_category_by_id(
        self, category_id: int
    ) -> Optional[ProductCategory]:
        """Get product category by ID."""
        records = storage_broker.get(
            ProductCategory,
            {ProductCategory.id_product_category: category_id},
            None,
            [ProductCategory.naming_contribution],
        )
        return records[0] if records else None

    # ==================== Images ====================

    def get_product_image_by_id(self, image_id: int) -> List[ProductImage]:
        """Get product image by ID."""
        return storage_broker.get(
            ProductImage,
            {ProductImage.id_product_image: image_id},
        )

    def create_product_image(self, image: ProductImage) -> ProductImage:
        """Create a product image."""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(image)

    def update_product_image(self, image: ProductImage) -> ProductImage:
        """Update a product image."""
        from features.insertion import update_record_in_api
        return update_record_in_api(image)
    
    def search_products(
        self,
        token: str,
        offset: int = 0,
        limit: int = 20,
        include_hidden: bool = False,
        domain: Optional[str] = None,
        subdomain: Optional[str] = None,
    ) -> List[Product]:
        """
        Search products by token in:
        - the flat columns on Product (name, brand, description)
        - the trilingual NamingContribution attached to the product's
            origin Iproduct (EN / FR / AR)

        The naming match is expressed as an EXISTS subquery rather than a
        join, so products without an origin Iproduct (or without a naming
        row) are unaffected and still match on the flat columns. This
        avoids relying on outer joins that the storage broker does not
        currently expose.
        """
        conditions = [not_(Product.product_visibility == "DELETED")]

        pattern = f"%{token}%"

        # EXISTS clause: true when the product's origin Iproduct has a
        # naming row whose EN / FR / AR text matches the pattern.
        naming_exists = exists().where(
            and_(
                Iproduct.id_iproduct == Product.product_origin_id,
                NamingContribution.id_naming_contribution
                == Iproduct.iproduct_naming_ref,
                or_(
                    NamingContribution.naming_contribution_en.ilike(pattern),
                    NamingContribution.naming_contribution_fr.ilike(pattern),
                    NamingContribution.naming_contribution_ar.ilike(pattern),
                ),
            )
        )

        conditions.append(
            or_(
                Product.product_name.ilike(pattern),
                Product.product_brand.ilike(pattern),
                Product.product_description.ilike(pattern),
                naming_exists,
            )
        )

        if not include_hidden:
            conditions.append(_visible_filter())

        # No join needed for Iproduct / NamingContribution — the EXISTS
        # subquery handles it. ProductCategory is still joined only when a
        # domain / subdomain filter is present.
        join_tables = []

        key_filter = _category_key_filter(domain, subdomain)
        if key_filter is not None:
            join_tables.append(ProductCategory)
            conditions.append(key_filter)

        return storage_broker.get(
            Product,
            conditions=conditions,
            join_tables=join_tables,
            eager_load_depth=[
                Product.product_category,
                Product.product_provider,
                {
                    Product.product_image: [
                        ProductImage.id_product_image,
                        ProductImage.product_image_url,
                    ]
                },
                {
                    Product.product_origin: [
                        {Iproduct.naming_contribution: [NamingContribution]}
                    ]
                },
            ],
            offset=offset,
            limit=limit,
        )