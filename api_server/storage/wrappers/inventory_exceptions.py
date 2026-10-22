"""Exceptions raised by InventoryServiceClient.

Mirrors the shape of core/exceptions/specific/cart_exceptions.py:
a base class carrying (message, error_code, status_code, details),
and typed subclasses per failure mode. Callers can catch the base
for "any inventory failure" or a specific subclass to branch.
"""

from typing import Any, Dict, List, Optional

from core.messages.error_codes import ErrorCode


class InventoryClientError(Exception):
    """Base for every failure originating from the Inventory API.

    `status_code` is the HTTP status the inventory service returned
    (or a synthesized code when the call never reached it).
    `error_code` is the machine-readable code the caller should
    branch on. `details` is the parsed response body, unmodified.
    """

    default_status_code: int = 502  # Bad Gateway — we called upstream and it failed
    default_error_code: str = "INVENTORY_ERROR"

    def __init__(
        self,
        message: str = "Inventory service error",
        *,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
    ):
        self.status_code = (
            status_code if status_code is not None else self.default_status_code
        )
        self.error_code = error_code or self.default_error_code
        self.details = details or {}
        self.operation = operation
        super().__init__(message)


# ---------- 409 / domain ----------

class InsufficientStockError(InventoryClientError):
    """Inventory refused because requested quantity exceeds available."""

    default_status_code = 409
    default_error_code = "INSUFFICIENT_STOCK"

    def __init__(
        self,
        message: str = "Insufficient stock",
        *,
        product_id: Optional[int] = None,
        requested: Optional[int] = None,
        available: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
    ):
        merged = dict(details or {})
        if product_id is not None:
            merged["product_id"] = product_id
        if requested is not None:
            merged["requested"] = requested
        if available is not None:
            merged["available"] = available

        super().__init__(
            message,
            error_code=self.default_error_code,
            status_code=self.default_status_code,
            details=merged,
            operation=operation,
        )


class ReservationNotFoundError(InventoryClientError):
    """Confirm/release called against a reservation that no longer exists."""

    default_status_code = 409
    default_error_code = "RESERVATION_NOT_FOUND"


# ---------- 404 ----------

class InventoryItemNotFoundError(InventoryClientError):
    """Product/item id doesn't exist in the inventory service."""

    default_status_code = 404
    default_error_code = "INVENTORY_ITEM_NOT_FOUND"


# ---------- 4xx client errors ----------

class InventoryValidationError(InventoryClientError):
    """Inventory rejected the request payload (missing/invalid fields)."""

    default_status_code = 400
    default_error_code = "INVENTORY_VALIDATION_ERROR"


class InventoryAuthError(InventoryClientError):
    """Inventory rejected our credentials."""

    default_status_code = 401
    default_error_code = "INVENTORY_AUTH_ERROR"


class InventoryPermissionError(InventoryClientError):
    """Inventory accepted our identity but refused the operation."""

    default_status_code = 403
    default_error_code = "INVENTORY_PERMISSION_ERROR"


class InventoryConflictError(InventoryClientError):
    """Generic 409 when a more specific subclass doesn't apply."""

    default_status_code = 409
    default_error_code = "INVENTORY_CONFLICT"


class InventoryRateLimitedError(InventoryClientError):
    """Inventory is throttling us."""

    default_status_code = 429
    default_error_code = "INVENTORY_RATE_LIMITED"


# ---------- 5xx / transport ----------

class InventoryServerError(InventoryClientError):
    """Inventory returned a 5xx. Retryable in principle."""

    default_status_code = 502
    default_error_code = "INVENTORY_SERVER_ERROR"


class InventoryUnavailableError(InventoryClientError):
    """Inventory didn't answer — connection refused, timeout, DNS."""

    default_status_code = 503
    default_error_code = "INVENTORY_UNAVAILABLE"


class InventoryTimeoutError(InventoryUnavailableError):
    """Specific timeout, in case callers want to retry differently."""

    default_error_code = "INVENTORY_TIMEOUT"


class InventoryProtocolError(InventoryClientError):
    """Inventory answered, but with a body we couldn't parse."""

    default_status_code = 502
    default_error_code = "INVENTORY_PROTOCOL_ERROR"