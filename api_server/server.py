# main.py
"""
FastAPI application entry point for Verdelia API.
Configures middleware, exception handlers, routers, and root endpoints.
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from routers.app_routers.wallet_router import wallet_router
from routers.business_routers.action_link_router import action_link_router
from core.logging_config import get_logger
from storage.seed import seed_database_if_needed
from core.exceptions.handler import setup_exception_handlers_with_config
from core.response_models import SuccessResponseModel
from config import settings
from constants import API_SECRET_KEY

# Import routers
from routers.app_routers.user_router import app_user_router
from routers.app_routers.subscription_router import subscription_router
from routers.app_routers.auth_router import auth_router
from routers.health_routers.person_router import person_router
from routers.app_routers.notification_router import notification_router
from routers.business_routers.product_router import product_router
from routers.business_routers.supplier_router import supplier_router
from routers.business_routers.staff_router import staff_router
from routers.business_routers.business_router import business_router
# from routers.business_routers.document_router import document_router
from routers.health_routers.recipe_router import recipe_router
from routers.health_routers.health_router import health_router
from routers.search_router import search_router
from routers.business_routers.order_router import order_router
from routers.business_routers.cart_router import cart_router
from routers.business_routers.delivery_router import delivery_router
from routers.business_routers.service_router import service_router
from routers.business_routers.financial_router import financial_router
from routers.business_routers.business_operation_router import business_operation_router
from routers.business_routers.address_router import address_router
from routers.business_routers.invoice_router import invoice_router

from routers.app_routers.reaction_router import reaction_router


# Configure logging
logging.basicConfig(
    level=logging.INFO if not (settings.DEBUG== "PRODUCTION") else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
from core.logging_config import get_logger

logger = get_logger(__name__)






# ==================== Lifespan Context Manager ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting up Verdelia API...")
    logger.info(f"Environment: {settings.DEBUG}")
    logger.info(f"API Version: {settings.API_VERSION}")
    
    # Seed database in DEV mode
    await seed_database_if_needed()

    yield
    
    # Shutdown
    logger.info("Shutting down Verdelia API...")
    
    # Clean up resources
    # await close_db_pool()


# ==================== Middleware Configuration ====================

def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware in the correct order.
    Middleware order matters - they execute in reverse order of addition.
    """
    
    # GZip compression (compress responses > 500 bytes)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    
    # Trusted Hosts (security)
    if settings.TRUSTED_HOSTS:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.TRUSTED_HOSTS
        )
    
    # Session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=API_SECRET_KEY,
        max_age=settings.SESSION_MAX_AGE,
        same_site=settings.SESSION_SAME_SITE,
        https_only=settings.SESSION_HTTPS_ONLY
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
        expose_headers=["X-Process-Time", "X-Request-ID"]
    )
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all incoming requests with timing information."""
        request_id = request.headers.get("X-Request-ID", generate_request_id())
        start_time = time.time()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add custom headers
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-Request-ID"] = request_id
        
        # Log request
        logger.info(
            f"{request.method} {request.url.path} - "
            f"{response.status_code} - "
            f"{process_time:.3f}s - "
            f"ID: {request_id}"
        )
        
        return response


def generate_request_id() -> str:
    """Generate a unique request ID."""
    import uuid
    return str(uuid.uuid4())[:8]


# ==================== Router Configuration ====================

def setup_routers(app: FastAPI) -> None:
    """
    Configure all API routers with their prefixes and tags.
    """
    
    # Version 1 API group
    api_version = f"/api/{settings.CURRENT_VERSION}" if settings.USE_VERSIONING else "/api"
    
    # Authentication and user routes
    app.include_router(auth_router, prefix=api_version, tags=["Authentication"])
    app.include_router(app_user_router, prefix=api_version, tags=["Users"])
    app.include_router(subscription_router, prefix=api_version, tags=["Subscriptions"])
    
    # Business core routes
    app.include_router(invoice_router, prefix=api_version, tags=["Invoices"])
    app.include_router(product_router, prefix=api_version, tags=["Products"])
    app.include_router(supplier_router, prefix=api_version, tags=["Suppliers"])
    app.include_router(person_router, prefix=api_version, tags=["People"])
    app.include_router(staff_router, prefix=api_version, tags=["Staff"])
    app.include_router(wallet_router, prefix=api_version, tags=["Wallet"])
    # app.include_router(document_router, prefix=api_version, tags=["Documents"])
    
    # Business sub-modules
    business_prefix = f"{api_version}/business"
    app.include_router(order_router, prefix=business_prefix, tags=["Business Orders"])
    app.include_router(cart_router, prefix=business_prefix, tags=["Business Carts"])
    app.include_router(delivery_router, prefix=f"{business_prefix}/delivery", tags=["Business Deliveries"])
    app.include_router(service_router, prefix=business_prefix, tags=["Business Services"])
    app.include_router(financial_router, prefix=business_prefix, tags=["Business Finance"])
    app.include_router(business_operation_router, prefix=business_prefix, tags=["Business Operations"])
    # Health and wellness routes
    app.include_router(health_router, prefix=api_version, tags=["Health"])
    app.include_router(recipe_router, prefix=api_version, tags=["Recipes"])
    app.include_router(address_router, prefix=f"{api_version}/addresses", tags=["Addresses"])
    app.include_router(reaction_router, prefix=f"{api_version}/reactions", tags=["Reactions"])
    app.include_router(action_link_router, prefix=f"{api_version}/action", tags=["Action Links"])
    
    
    # Notification routes
    app.include_router(notification_router, prefix=f"{api_version}/notifications", tags=["Notifications"])
    
    # Search routes
    app.include_router(search_router, prefix=api_version, tags=["Search"])


# ==================== Root Endpoints ====================

def setup_root_endpoints(app: FastAPI) -> None:
    """
    Configure root and health check endpoints.
    """
    
    @app.get("/", tags=["Root"])
    async def root():
        """API root endpoint with service information."""
        return SuccessResponseModel(
            success=True,
            message=f"Welcome to {settings.API_TITLE}",
            data={
                "service": settings.API_TITLE,
                "version": settings.API_VERSION,
                "environment": settings.DEBUG,
                "docs": "/api/docs",
                "redoc": "/api/redoc",
                "openapi": "/api/openapi.json"
            }
        )
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for load balancers and monitoring."""
        return {
            "status": "healthy",
            "service": settings.API_TITLE,
            "version": settings.API_VERSION,
            "timestamp": get_current_timestamp()
        }
    
    @app.get("/ready", tags=["Health"])
    async def readiness_check():
        """Readiness check for orchestration (Kubernetes, etc.)."""
        # Perform actual dependency checks
        checks = {
            "database": check_database_connection(),
            "cache": check_cache_connection(),
        }
        
        all_ready = all(checks.values())
        status = "ready" if all_ready else "not_ready"
        
        return JSONResponse(
            status_code=status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": status,
                "checks": checks,
                "timestamp": get_current_timestamp()
            }
        )
    
    @app.get("/metrics", tags=["Monitoring"])
    async def metrics():
        """Prometheus metrics endpoint handled by Instrumentator."""
        # This is a placeholder - Instrumentator exposes its own endpoint
        return {"message": "Metrics available at /metrics"}


# ==================== Health Check Helpers ====================

def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"


def check_database_connection() -> bool:
    """
    Check database connectivity.
    Override with actual database check.
    """
    # TODO: Implement actual database health check
    return True


def check_cache_connection() -> bool:
    """
    Check cache connectivity.
    Override with actual cache check.
    """
    # TODO: Implement actual cache health check
    return True


# ==================== Application Factory ====================

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application using factory pattern.
    """
    
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
        contact={
            "name": "API Support",
            "email": settings.CONTACT_EMAIL if hasattr(settings, 'CONTACT_EMAIL') else None,
        },
        license_info={
            "name": "Proprietary",
        }
    )
    
    # Setup instrumentation (Prometheus metrics)
    if not (settings.DEBUG == "PRODUCTION"):
        instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/health", "/ready", "/metrics"],
            env_var_name="ENABLE_METRICS",
        )
        instrumentator.instrument(app).expose(app, endpoint="/metrics")
        logger.info("Prometheus metrics instrumentation enabled")
    
    # Setup exception handlers
    setup_exception_handlers_with_config(app, debug=(settings.DEBUG == "PRODUCTION"))
    
    # Setup middleware (order matters!)
    setup_middleware(app)
    
    # Setup routers
    setup_routers(app)
    
    # Setup root endpoints
    setup_root_endpoints(app)
    
    logger.info("Application created successfully")
    
    return app


# ==================== Application Instance ====================

app = create_app()


# ==================== Development Server ====================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.DEBUG == "PRODUCTION"),
        log_level="info" if not (settings.DEBUG== "PRODUCTION") else "debug",
        access_log=True,
        workers=settings.WORKERS if hasattr(settings, 'WORKERS') else 1,
    )