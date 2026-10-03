# routers/search_router.py
"""
Search router for searching across multiple entity types
(products, recipes, users, people, suppliers).

Product search is delegated to ProductService — the router never talks
to the underlying repositories or the search service for products
directly. Recipes, users, people, and suppliers still go through
SearchService because they don't have a dedicated local service in this
layer yet.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from core.logging_config import get_logger
from core.response_models import ErrorResponseModel, get_crud_error_responses
from core.exceptions.specific.search_exceptions import (
    SearchQueryTooShortException,
    SearchEntityNotFoundException,
    SearchExecutionException,
)
from services.search_service import SearchService
from services.product_service import ProductService


from core.logging_config import get_logger

logger = get_logger(__name__)


search_router = APIRouter()


# ==================== Dependency Injection ====================

def get_search_service() -> SearchService:
    return SearchService()


def get_product_service() -> ProductService:
    return ProductService()


# ==================== Single Entity Search Endpoints ====================

@search_router.get(
    "/search/product",
    summary="Search products",
    description="Search products by token in name, brand, and description",
    responses={
        400: {"model": ErrorResponseModel, "description": "Search query too short"},
        404: {"model": ErrorResponseModel},
    },
)
def search_for_product(
    token: str = Query(..., min_length=2, description="Search query string"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=200, description="Pagination limit"),
    domain: Optional[str] = Query(
        None,
        description=(
            "Optional top-level domain filter (e.g. 'food', 'health'). "
            "Restricts results to categories under that domain."
        ),
    ),
    subdomain: Optional[str] = Query(
        None,
        description=(
            "Optional subdomain filter inside `domain` "
            "(e.g. 'alimentary' when domain='food')."
        ),
    ),
    include_hidden: bool = Query(
        False,
        description="Include hidden products. Defaults to False.",
    ),
    product_service: ProductService = Depends(get_product_service),
):
    """
    Search products by token in name, brand, and description.

    Delegated entirely to ProductService. Pagination, domain filters,
    and visibility follow the same rules as `GET /products`.
    """
    logger.info(
        f"Searching products with token: '{token}' "
        f"(offset={offset}, limit={limit}, domain={domain}, "
        f"subdomain={subdomain}, include_hidden={include_hidden})"
    )

    if len(token) < 2:
        raise SearchQueryTooShortException(min_length=2)

    results = product_service.search_products(
        token=token,
        offset=offset,
        limit=limit,
        domain=domain,
        subdomain=subdomain,
        include_hidden=include_hidden,
    )

    logger.info(f"Found {len(results)} products matching '{token}'")
    return results


@search_router.get(
    "/search/recipe",
    summary="Search recipes",
    description="Search recipes by token in name, description, and instructions",
    responses={
        400: {"model": ErrorResponseModel, "description": "Search query too short"},
        404: {"model": ErrorResponseModel},
    },
)
def search_for_recipe(
    token: str = Query(..., min_length=2, description="Search query string"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=200, description="Pagination limit"),
    search_service: SearchService = Depends(get_search_service),
):
    logger.info(
        f"Searching recipes with token: '{token}' "
        f"(offset={offset}, limit={limit})"
    )

    if len(token) < 2:
        raise SearchQueryTooShortException(min_length=2)

    results = search_service.search_recipes(token, offset, limit)
    logger.info(f"Found {len(results)} recipes matching '{token}'")
    return results


@search_router.get(
    "/search/personnel",
    summary="Search personnel/users",
    description="Search users (personnel) by token in person details and username",
    responses={
        400: {"model": ErrorResponseModel, "description": "Search query too short"},
        404: {"model": ErrorResponseModel},
    },
)
def search_for_user(
    token: str = Query(..., min_length=2, description="Search query string"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=200, description="Pagination limit"),
    search_service: SearchService = Depends(get_search_service),
):
    logger.info(
        f"Searching users with token: '{token}' "
        f"(offset={offset}, limit={limit})"
    )

    if len(token) < 2:
        raise SearchQueryTooShortException(min_length=2)

    results = search_service.search_users(token, offset, limit)
    logger.info(f"Found {len(results)} users matching '{token}'")
    return results


@search_router.get(
    "/search/people",
    summary="Search people",
    description=(
        "Search people by token in person details "
        "(first name, last name, nationality)"
    ),
    responses={
        400: {"model": ErrorResponseModel, "description": "Search query too short"},
        404: {"model": ErrorResponseModel},
    },
)
def search_for_people(
    token: str = Query(..., min_length=2, description="Search query string"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=200, description="Pagination limit"),
    search_service: SearchService = Depends(get_search_service),
):
    logger.info(
        f"Searching people with token: '{token}' "
        f"(offset={offset}, limit={limit})"
    )

    if len(token) < 2:
        raise SearchQueryTooShortException(min_length=2)

    results = search_service.search_people(token, offset, limit)
    logger.info(f"Found {len(results)} people matching '{token}'")
    return results


@search_router.get(
    "/search/supplier",
    summary="Search suppliers",
    description="Search suppliers by token in provider name and contact info",
    responses={
        400: {"model": ErrorResponseModel, "description": "Search query too short"},
        404: {"model": ErrorResponseModel},
    },
)
def search_supplier(
    token: str = Query(..., min_length=2, description="Search query string"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=200, description="Pagination limit"),
    search_service: SearchService = Depends(get_search_service),
):
    logger.info(
        f"Searching suppliers with token: '{token}' "
        f"(offset={offset}, limit={limit})"
    )

    if len(token) < 2:
        raise SearchQueryTooShortException(min_length=2)

    results = search_service.search_suppliers(token, offset, limit)
    logger.info(f"Found {len(results)} suppliers matching '{token}'")
    return results


@search_router.get(
    "/search/position/supplier",
    summary="Search suppliers by geographic position",
    description="Search suppliers by geographic position within a radius",
    responses={
        400: {"model": ErrorResponseModel, "description": "Invalid coordinates"},
        404: {"model": ErrorResponseModel},
    },
)
def search_supplier_by_position(
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    distance_km: float = Query(..., gt=0, description="Search radius in km"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=200, description="Pagination limit"),
    search_service: SearchService = Depends(get_search_service),
):
    logger.info(
        f"Searching suppliers near ({longitude}, {latitude}) "
        f"within {distance_km}km"
    )

    results = search_service.search_suppliers_by_location(
        longitude, latitude, distance_km, offset, limit
    )
    logger.info(f"Found {len(results)} suppliers in the specified area")
    return results


# ==================== Enhanced Multi-Search Endpoints ====================

@search_router.get(
    "/search/multi",
    summary="Multi-entity search",
    description="Search across multiple entity types in a single request",
    responses={
        400: {"model": ErrorResponseModel, "description": "Invalid parameters"},
    },
)
def multi_search(
    token: str = Query(..., min_length=2, description="Search query string"),
    entities: List[str] = Query(
        default=["products", "recipes", "users", "people", "suppliers"],
        description=(
            "Entity types to search "
            "(comma-separated: products,recipes,users,people,suppliers)"
        ),
    ),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum results per entity type"
    ),
    search_service: SearchService = Depends(get_search_service),
    product_service: ProductService = Depends(get_product_service),
):
    """
    Search across multiple entity types in a single request.

    Product results come from ProductService; every other entity type
    still comes from SearchService.
    """
    logger.info(f"Multi-search with token: '{token}', entities: {entities}")

    valid_entities = {"products", "recipes", "users", "people", "suppliers"}
    invalid_entities = [e for e in entities if e not in valid_entities]

    if invalid_entities:
        logger.warning(f"Invalid entity types requested: {invalid_entities}")
        raise SearchEntityNotFoundException(
            entity_type=", ".join(invalid_entities),
            valid_types=list(valid_entities),
        )

    # Product search is routed through ProductService; everything else
    # still uses SearchService.
    product_results = (
        product_service.search_products(token, offset, limit)
        if "products" in entities
        else []
    )

    other_entities = [e for e in entities if e != "products"]
    other_results = (
        search_service.multi_search(token, other_entities, offset, limit)
        if other_entities
        else {}
    )

    results = {"products": product_results, **other_results}

    return {
        "status": "success",
        "query": token,
        "entities_searched": entities,
        "results": results,
        "summary": {
            entity: len(results.get(entity, [])) for entity in entities
        },
    }


@search_router.get(
    "/search/quick",
    summary="Quick search (autocomplete)",
    description=(
        "Quick search across all entity types with small result sets "
        "for autocomplete"
    ),
    responses={
        400: {"model": ErrorResponseModel, "description": "Search query too short"},
    },
)
def quick_search(
    token: str = Query(..., min_length=2, description="Search query string"),
    limit: int = Query(
        5, ge=1, le=20, description="Maximum results per entity type"
    ),
    search_service: SearchService = Depends(get_search_service),
    product_service: ProductService = Depends(get_product_service),
):
    """
    Quick search across all entity types with small result sets.
    Useful for autocomplete or quick lookup features.
    """
    logger.info(f"Quick search with token: '{token}' (limit={limit})")

    product_results = product_service.search_products(token, 0, limit)

    other_entities = ["recipes", "users", "people", "suppliers"]
    other_results = search_service.multi_search(
        token, other_entities, 0, limit
    )

    return {
        "status": "success",
        "query": token,
        "results": {"products": product_results, **other_results},
    }


# ==================== Health Check Endpoint ====================

@search_router.get(
    "/search/health",
    summary="Search service health check",
    description="Check if search service is operational",
    responses={
        500: {"model": ErrorResponseModel, "description": "Service is unhealthy"},
    },
)
def search_health_check(
    search_service: SearchService = Depends(get_search_service),
    product_service: ProductService = Depends(get_product_service),
):
    """
    Health check endpoint for search service.

    Exercises both the product path (via ProductService) and the
    generic search path (via SearchService) so a failure in either is
    surfaced.
    """
    logger.info("Search service health check requested")

    try:
        # Product path first — this is the one that moved to ProductService.
        product_service.search_products("test", 0, 1)
        # Generic path — recipes/users/people/suppliers still through SearchService.
        search_service.search_products("test", 0, 1)

        return {
            "status": "healthy",
            "message": "Search service is operational",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Search service health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }, status.HTTP_500_INTERNAL_SERVER_ERROR