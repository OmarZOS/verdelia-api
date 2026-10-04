# routers/business_routers/product_router.py
"""
Product router for managing products, barcode search, image recognition,
and SSE updates.

The router talks to ProductWorkflow, which owns every cross-process call
(AIService, subscriber notification, background tasks) and sequences the
local ProductService calls. The router never talks to ProductService
directly for orchestrated operations; it still uses the workflow's
exposed accessor for pure-local reads when that's the whole job.
"""

import asyncio
import logging
import sys
from typing import Optional

from fastapi import (
    APIRouter,
    status,
    BackgroundTasks,
    File,
    UploadFile,
    Depends,
    Query,
)
from fastapi.encoders import jsonable_encoder
from sse_starlette.sse import EventSourceResponse

from core.logging_config import get_logger

from services.helpers.auth.auth_dependencies import get_current_user_id
from core.models.api_models import Iproduct_API, Product_API, ProductImage_API
from core.response_models import ErrorResponseModel, get_crud_error_responses
from core.exceptions.specific.product_exceptions import (
    ProductNotFoundException,
    ProductFetchNotFoundException,
    ProductImageNotFoundException,
    ProductDeleteFailedException,
    ProductInsertFailedException,
)
from services.product_service import ProductService
from workflows.product_workflow import ProductWorkflow

from core.logging_config import get_logger

logger = get_logger(__name__)



product_router = APIRouter()


# ==================== Dependency Injection ====================

def get_product_workflow() -> ProductWorkflow:
    return ProductWorkflow()


def get_product_service() -> ProductService:
    """
    Exposed for endpoints that only need local reads with no orchestration.
    Prefer `get_product_workflow` for anything that might touch AI, SSE, or
    background work.
    """
    return ProductService()


# ==================== SSE Endpoint for Product Updates ====================

@product_router.get(
    "/products/observer",
    summary="Subscribe to product updates",
    description="Server-Sent Events endpoint for real-time product updates",
    responses={
        200: {
            "description": "SSE stream established",
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "string",
                        "description": "Server-Sent Events data stream",
                    }
                }
            },
        },
        404: {"model": ErrorResponseModel},
    },
)
async def product_updates(
    product_id: int = Query(..., description="Product ID to observe"),
    user_id: int = Depends(get_current_user_id),
    workflow: ProductWorkflow = Depends(get_product_workflow),
):
    """
    Subscribe to real-time product updates via SSE.
    """
    logger.info(f"GET SSE subscription established for product {product_id}")

    # Verify the product exists via the local service.
    workflow.service.get_product_by_id(product_id)

    async def event_publisher():
        queue = asyncio.Queue()
        workflow.add_subscriber(product_id, queue)
        try:
            while True:
                data = await queue.get()
                yield {"event": "update", "data": jsonable_encoder(data)}
        except asyncio.CancelledError:
            logger.info(f"SSE connection cancelled for product {product_id}")
        finally:
            workflow.remove_subscriber(product_id, queue)

    return EventSourceResponse(event_publisher())


# ==================== Product Listing Endpoints ====================

@product_router.get(
    "/products",
    summary="Get all products",
    description=(
        "Fetch all products with pagination, filter by user, provider, "
        "category, domain, subdomain, and visibility."
    ),
    responses={
        200: {"description": "Products retrieved successfully"},
        **get_crud_error_responses(include_404=True),
    },
)
def get_all_products(
    user_id: int = Query(..., description="Owner user ID"),
    provider_id: int = Query(..., description="Provider ID"),
    category_id: int = Query(..., description="Category ID"),
    product_barcode: Optional[str] = Query(None, description="Product barcode"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=200, description="Pagination limit"),
    domain: Optional[str] = Query(
        None,
        description=(
            "Filter by top-level domain (e.g. 'food', 'health', 'retail'). "
            "Matches the first segment of a category key."
        ),
    ),
    subdomain: Optional[str] = Query(
        None,
        description=(
            "Filter by subdomain inside a domain (e.g. 'alimentary' when "
            "domain='food'). Matches the second segment of a category key."
        ),
    ),
    include_hidden: bool = Query(
        False,
        description=(
            "Include products with visibility=HIDDEN. Defaults to False "
            "so buyers only see the public catalog."
        ),
    ),
    service: ProductService = Depends(get_product_service),
):
    logger.info(
        f"GET /products — user:{user_id}, provider:{provider_id}, "
        f"category:{category_id}, domain:{domain}, subdomain:{subdomain}, "
        f"offset:{offset}, limit:{limit}, include_hidden:{include_hidden}"
    )
    return service.get_all_products(
        user_id,
        provider_id,
        category_id,
        product_barcode,
        offset,
        limit,
        include_hidden=include_hidden,
        domain=domain,
        subdomain=subdomain,
    )


@product_router.get(
    "/products/categories",
    summary="Get all categories",
    description="Fetch all product categories",
    responses={200: {"description": "Categories retrieved successfully"}},
)
def get_categories(service: ProductService = Depends(get_product_service)):
    logger.info("GET /products/categories")
    return service.get_product_categories()


@product_router.get(
    "/products/by-category",
    summary="Get products by category",
    description="Retrieve products by category with pagination",
    responses={
        200: {"description": "Products retrieved successfully"},
        404: {"model": ErrorResponseModel},
        **get_crud_error_responses(include_404=True),
    },
)
def get_products_by_category(
    category_id: int = Query(..., description="Category ID"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=200, description="Pagination limit"),
    include_hidden: bool = Query(
        False,
        description="Include products with visibility=HIDDEN.",
    ),
    service: ProductService = Depends(get_product_service),
):
    logger.info(
        f"GET /products/by-category — category:{category_id}, "
        f"offset:{offset}, limit:{limit}, include_hidden:{include_hidden}"
    )
    return service.get_products_by_category(
        category_id,
        offset,
        limit,
        include_hidden=include_hidden,
    )


@product_router.get(
    "/products/by-id",
    summary="Get product by ID",
    description="Retrieve a product by its ID",
    responses={
        200: {"description": "Product retrieved successfully"},
        404: {"model": ErrorResponseModel},
    },
)
def get_product_by_id(
    product_id: int = Query(..., description="Product ID"),
    include_hidden: bool = Query(
        True,
        description=(
            "Return the product even when visibility=HIDDEN. Defaults to "
            "True so editors can open a hidden product by id."
        ),
    ),
    service: ProductService = Depends(get_product_service),
):
    logger.info(
        f"GET /products/by-id — product:{product_id}, "
        f"include_hidden:{include_hidden}"
    )
    return service.get_product_by_id(
        product_id,
        include_hidden=include_hidden,
    )


# ==================== Barcode Search Endpoints ====================

@product_router.get(
    "/products/by-barcode",
    summary="Search product by barcode",
    description=(
        "Search for a product using a barcode. DB first, fallback to AI "
        "if needed."
    ),
    responses={
        200: {"description": "Product found"},
        404: {"model": ErrorResponseModel},
    },
)
async def get_product_from_barcode(
    barcode: str = Query(..., description="Product barcode"),
    workflow: ProductWorkflow = Depends(get_product_workflow),
):
    """
    DB first, AI fallback. The AI fallback is orchestration, so it lives
    in the workflow.
    """
    logger.info(f"GET /products/by-barcode — barcode:{barcode}")

    product = workflow.service.get_iproduct_by_barcode(barcode)
    if product:
        logger.info(f"Product found in database for barcode {barcode}")
        return product

    logger.info(f"Product not found in DB, trying AI for barcode {barcode}")
    iproduct_data = await workflow.get_product_info_by_barcode(barcode)
    return [iproduct_data]


@product_router.get(
    "/products/db/by-barcode",
    summary="Search product by barcode (DB only)",
    description="Search for a product using a barcode from database only",
    responses={
        200: {"description": "Product found"},
        404: {"model": ErrorResponseModel},
    },
)
async def get_product_barcode_db_only(
    barcode: str = Query(..., description="Product barcode"),
    service: ProductService = Depends(get_product_service),
):
    logger.info(f"GET /products/db/by-barcode — barcode:{barcode}")

    product = service.get_iproduct_by_barcode(barcode)
    if not product:
        raise ProductFetchNotFoundException(
            identifier=barcode, search_type="barcode_database"
        )

    return product


# ==================== Image Recognition Endpoint ====================

@product_router.post(
    "/products/search/image",
    status_code=status.HTTP_200_OK,
    summary="Search product by image",
    description="Search for a product using an uploaded image.",
    responses={
        200: {"description": "Product recognized successfully"},
        400: {"model": ErrorResponseModel},
        422: {"model": ErrorResponseModel},
    },
)
async def search_product_by_image(
    file: UploadFile = File(..., description="Product image file"),
    workflow: ProductWorkflow = Depends(get_product_workflow),
):
    logger.info(f"POST /products/search/image — file:{file.filename}")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise ProductInsertFailedException(
            error="File must be an image", product_name=file.filename
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise ProductInsertFailedException(
            error="Empty image file", product_name=file.filename
        )

    iproduct_data = await workflow.recognize_product_from_image(image_bytes)
    logger.info(f"Image search completed for {file.filename}")

    return [iproduct_data]


# ==================== Product Image Endpoints ====================

@product_router.get(
    "/products/image",
    summary="Get product image",
    description="Fetch product image by ID",
    responses={
        200: {"description": "Image retrieved successfully"},
        404: {"model": ErrorResponseModel},
    },
)
def get_product_image(
    image_id: int = Query(..., description="Product image ID"),
    service: ProductService = Depends(get_product_service),
):
    logger.info(f"GET /products/image — image:{image_id}")

    images = service.product_repo.get_product_image_by_id(image_id)
    if not images:
        raise ProductImageNotFoundException(image_id=image_id)

    return images[0]


# ==================== Product Modification Endpoints ====================

@product_router.put(
    "/products",
    summary="Update product",
    description="Update product details and notify subscribers",
    responses={
        200: {"description": "Product updated successfully"},
        404: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
def update_product_details(
    product: Product_API,
    image: ProductImage_API,
    background_tasks: BackgroundTasks,
    product_id: int = Query(..., description="Product ID to update"),
    user_id: int = Depends(get_current_user_id),
    workflow: ProductWorkflow = Depends(get_product_workflow),
):
    """
    Update product details and notify subscribers.
    """
    logger.info(f"PUT /products — product:{product_id}")
    return workflow.update_product(
        product_id=product_id,
        product_api=product,
        image=image,
        background_tasks=background_tasks,
    )


@product_router.patch(
    "/products/visibility",
    summary="Update product visibility",
    description="Toggle a product's visibility between VISIBLE and HIDDEN",
    responses={
        200: {"description": "Visibility updated successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
    },
)
def update_product_visibility(
    product_id: int = Query(..., description="Product ID"),
    visibility: str = Query(
        ...,
        description="Target visibility. Must be either VISIBLE or HIDDEN.",
        pattern="^(VISIBLE|HIDDEN)$",
    ),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user_id: int = Depends(get_current_user_id),
    workflow: ProductWorkflow = Depends(get_product_workflow),
):
    """
    Flip a product between visible and hidden.
    """
    logger.info(
        f"PATCH /products/visibility — product:{product_id}, "
        f"visibility:{visibility}"
    )

    current = workflow.service.get_product_by_id(
        product_id, include_hidden=True
    )

    updated_api = Product_API(
        id_product=current.id_product,
        product_name=current.product_name,
        product_brand=current.product_brand,
        product_barcode=current.product_barcode,
        product_price=current.product_price,
        product_base_price=current.product_base_price,
        product_quantifier=current.product_quantifier,
        product_quantity=current.product_quantity,
        product_reserved_quantity=current.product_reserved_quantity,
        product_visibility=visibility,
        product_description=current.product_description,
        product_owner=current.product_owner,
        product_provider_id=current.product_provider_id,
        product_category_id=current.product_category_id,
        product_origin_id=current.product_origin_id,
    )

    return workflow.update_product(
        product_id=product_id,
        product_api=updated_api,
        background_tasks=background_tasks,
    )


@product_router.post(
    "/products",
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    description="Insert a new product",
    responses={
        400: {"model": ErrorResponseModel},
        409: {"model": ErrorResponseModel},
    },
)
async def insert_product_details(
    product: Product_API,
    image: Optional[ProductImage_API] = None,
    iproduct: Optional[Iproduct_API] = None,
    user_id: int = Depends(get_current_user_id),
    workflow: ProductWorkflow = Depends(get_product_workflow),
):
    """
    Insert a new product.
    """
    logger.info(f"POST /products — name:{product.product_name}")
    return await workflow.create_product(product, image, iproduct)


@product_router.delete(
    "/products",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product",
    description="Delete a product by ID",
    responses={
        204: {"description": "Product deleted successfully"},
        400: {"model": ErrorResponseModel},
        404: {"model": ErrorResponseModel},
    },
)
def delete_product_by_id(
    product_id: int = Query(..., description="Product ID to delete"),
    force_delete: bool = Query(
        False, description="Force delete even if product has dependencies"
    ),
    user_id: int = Depends(get_current_user_id),
    service: ProductService = Depends(get_product_service),
):
    """
    Delete a product. Pure local operation; no orchestration needed.
    """
    logger.info(
        f"DELETE /products — product:{product_id}, "
        f"force:{force_delete}"
    )

    success = service.delete_product(product_id, force_delete)
    if not success:
        raise ProductDeleteFailedException(
            product_id=product_id,
            error="Product not found or cannot be deleted",
        )

    return None