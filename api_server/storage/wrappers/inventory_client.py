# storage/wrappers/inventory_client.py
"""
HTTP client for the Inventory (Silo) service.

Transport-layer only: builds requests, parses responses, and raises
typed `InventoryClientError` subclasses for every failure mode.

Failure contract:
  - 2xx                → return parsed body
  - 4xx/5xx with body  → raise the matching InventoryClientError subclass
  - transport failure  → raise InventoryUnavailableError / InventoryTimeoutError
  - unparseable body   → raise InventoryProtocolError

Callers (workflows) are expected to catch `InventoryClientError` for
"any inventory failure" or a specific subclass (e.g. InsufficientStockError)
to branch on domain outcomes.
"""

from typing import Optional, List, Dict, Any
import json
import logging

from constants import SILO_SERVER_URL
from communication.communication_broker import (
    send_post_request,
    send_get_request,
    send_put_request,
    send_delete_request,
)

from storage.wrappers.inventory_exceptions import (
    InventoryClientError,
    InsufficientStockError,
    ReservationNotFoundError,
    InventoryAuthError,
    InventoryPermissionError,
    InventoryValidationError,
    InventoryItemNotFoundError,
    InventoryConflictError,
    InventoryRateLimitedError,
    InventoryServerError,
    InventoryUnavailableError,
    InventoryProtocolError,
)

from core.logging_config import get_logger

logger = get_logger(__name__)


# Mapping from upstream HTTP status → exception class.
# Anything not listed falls through to InventoryServerError (5xx)
# or a generic InventoryClientError.
_STATUS_TO_EXCEPTION = {
    400: InventoryValidationError,
    401: InventoryAuthError,
    403: InventoryPermissionError,
    404: InventoryItemNotFoundError,
    409: InventoryConflictError,
    429: InventoryRateLimitedError,
}


# Domain error codes the upstream may return in its body. When one of
# these is present, it wins over the generic status-code bucket — the
# upstream is telling us exactly what happened.
_DOMAIN_ERROR_CODES = {
    "INSUFFICIENT_STOCK": InsufficientStockError,
    "RESERVATION_NOT_FOUND": ReservationNotFoundError,
}


class InventoryServiceClient:
    """Client for the Inventory API (Silo)."""

    base_url = SILO_SERVER_URL
    timeout = 30

    # ================================================================
    # RESPONSE HANDLING
    # ================================================================

    def _parse_response(self, response) -> Dict:
        """Parse an HTTP response into a dict.

        Tolerates Response objects, raw dicts, JSON strings, and
        objects exposing .text / .content / .json(). Returns {} when
        nothing parseable is present — callers should treat that as
        a protocol failure via `_raise_for_response`.
        """
        try:
            if isinstance(response, dict):
                return response

            if hasattr(response, "json"):
                try:
                    return response.json()
                except Exception as e:
                    logger.warning(f"Failed to parse response.json(): {e}")

            if hasattr(response, "text"):
                try:
                    return json.loads(response.text)
                except Exception as e:
                    logger.warning(f"Failed to parse response.text: {e}")

            if isinstance(response, str):
                try:
                    return json.loads(response)
                except Exception as e:
                    logger.warning(f"Failed to parse response string: {e}")

            if hasattr(response, "content"):
                try:
                    return json.loads(response.content.decode("utf-8"))
                except Exception as e:
                    logger.warning(f"Failed to parse response.content: {e}")

            logger.warning(f"Could not parse response: {type(response)}")
            return {}

        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return {}

    @staticmethod
    def _extract_detail_code(parsed: Dict[str, Any]) -> Optional[str]:
        """Pull an error code out of `{"detail": "...: SOME_CODE"}`.

        Bridge for the current inventory service, which still embeds
        codes in prose. Delete once upstream returns structured
        `error_code` fields — otherwise you're maintaining a parser
        for a format nobody promised to keep stable.
        """
        detail = parsed.get("detail")
        if not isinstance(detail, str):
            return None
        tail = detail.rsplit(":", 1)[-1].strip()
        if tail and tail.replace("_", "").isalnum() and tail.isupper():
            return tail
        return None

    def _raise_for_response(
        self,
        response,
        parsed: Dict[str, Any],
        operation: str,
    ) -> None:
        """Translate a non-2xx response into a typed exception.

        No-op on success. Prefers an explicit `error_code` in the
        body (domain error) over the HTTP status bucket, so
        INSUFFICIENT_STOCK is raised even if upstream answers with
        a 500 instead of a 409.
        """
        status_code = getattr(response, "status_code", None)

        if status_code is not None and 200 <= status_code < 300:
            return

        # No status at all → the call never reached the service.
        if status_code is None:
            raise InventoryUnavailableError(
                message="Inventory service did not return a status code",
                details=parsed,
                operation=operation,
            )

        # Domain error codes win over status.
        upstream_code = (
            parsed.get("error_code")
            or parsed.get("code")
            or self._extract_detail_code(parsed)
        )
        exc_cls = _DOMAIN_ERROR_CODES.get(upstream_code)
        if exc_cls is not None:
            raise exc_cls(
                message=(
                    parsed.get("message")
                    or parsed.get("detail")
                    or f"Inventory rejected {operation}"
                ),
                details=parsed,
                operation=operation,
            )

        # Status-code bucket.
        exc_cls = _STATUS_TO_EXCEPTION.get(status_code)
        if exc_cls is not None:
            raise exc_cls(
                message=(
                    parsed.get("message")
                    or parsed.get("detail")
                    or f"Inventory returned {status_code}"
                ),
                details=parsed,
                operation=operation,
            )

        if 500 <= status_code < 600:
            raise InventoryServerError(
                message=(
                    parsed.get("message")
                    or parsed.get("detail")
                    or f"Inventory returned {status_code}"
                ),
                status_code=status_code,
                details=parsed,
                operation=operation,
            )

        # Everything else — unknown 3xx/4xx, weird statuses.
        raise InventoryClientError(
            message=(
                parsed.get("message")
                or parsed.get("detail")
                or f"Inventory returned {status_code}"
            ),
            status_code=status_code,
            details=parsed,
            operation=operation,
        )


    # ================================================================
    # ORDERED ITEMS & CONSUMPTIONS
    # ================================================================

    async def reserve_inventory(
        self,
        items: List[Dict],
        item_type: str = "ordered_item",
    ) -> Dict:
        """Reserve inventory for ordered items or consumptions."""
        endpoint = f"{self.base_url}/inventory/reserve"
        request_data = {"items": items, "item_type": item_type}

        logger.info(f"Reserving {len(items)} {item_type}(s)")

        response = await send_post_request(
            endpoint=endpoint,
            json_data=request_data,
            headers={"Content-Type": "application/json"},
        )
        parsed = self._parse_response(response)
        self._raise_for_response(response, parsed, operation="reserve_inventory")
 
        logger.info(f"✅ Successfully reserved {len(items)} items")
        return parsed

    async def confirm_inventory(
        self,
        items: List[Dict],
        item_type: str = "ordered_item",
    ) -> Dict:
        """Confirm inventory reservations (deduct from stock)."""
        endpoint = f"{self.base_url}/inventory/confirm"
        request_data = {"items": items, "item_type": item_type}

        logger.info(f"Confirming {len(items)} {item_type}(s)")

        response = await send_post_request(
            endpoint=endpoint,
            json_data=request_data,
            headers={"Content-Type": "application/json"},
        )
        parsed = self._parse_response(response)
        self._raise_for_response(response, parsed, operation="confirm_inventory")

        logger.info(f"✅ Successfully confirmed {len(items)} items")
        return parsed

    async def release_inventory(
        self,
        items: List[Dict],
        item_type: str = "ordered_item",
    ) -> Dict:
        """Release inventory reservations (cancel reservation)."""
        endpoint = f"{self.base_url}/inventory/release"
        request_data = {"items": items, "item_type": item_type}

        logger.info(f"Releasing {len(items)} {item_type}(s)")

        response = await send_post_request(
            endpoint=endpoint,
            json_data=request_data,
            headers={"Content-Type": "application/json"},
        )
        parsed = self._parse_response(response)
        self._raise_for_response(response, parsed, operation="release_inventory")

        logger.info(f"✅ Successfully released {len(items)} items")
        return parsed

    async def check_and_reserve(
        self,
        items: List[Dict],
        item_type: str = "ordered_item",
    ) -> Dict:
        """Check availability and reserve in one operation."""
        endpoint = f"{self.base_url}/inventory/check-and-reserve"
        request_data = {"items": items, "item_type": item_type}

        logger.info(f"Checking and reserving {len(items)} {item_type}(s)")

        response = await send_post_request(
            endpoint=endpoint,
            json_data=request_data,
            headers={"Content-Type": "application/json"},
        )
        parsed = self._parse_response(response)
        self._raise_for_response(response, parsed, operation="check_and_reserve")

        logger.info(f"✅ Successfully checked and reserved {len(items)} items")
        return parsed

    # ================================================================
    # STOCK QUERIES
    # ================================================================

    async def get_stock_status(self, product_id: int) -> Dict:
        """Get stock status for a single product."""
        endpoint = f"{self.base_url}/inventory/stock/{product_id}"

        logger.info(f"Getting stock status for product {product_id}")

        response = await send_get_request(endpoint=endpoint, params={})
        parsed = self._parse_response(response)
        self._raise_for_response(response, parsed, operation="get_stock_status")
        return parsed

    async def get_bulk_stock_status(self, product_ids: List[int]) -> Dict:
        """Get stock status for multiple products."""
        endpoint = f"{self.base_url}/inventory/stock/bulk"
        request_data = {"product_ids": product_ids}

        logger.info(f"Getting bulk stock status for {len(product_ids)} products")

        response = await send_post_request(
            endpoint=endpoint,
            json_data=request_data,
            headers={"Content-Type": "application/json"},
        )
        parsed = self._parse_response(response)
        self._raise_for_response(response, parsed, operation="get_bulk_stock_status")
        return parsed

    async def get_available_quantity(self, product_id: int) -> Dict:
        """Get available quantity for a product."""
        endpoint = f"{self.base_url}/inventory/available/{product_id}"

        logger.info(f"Getting available quantity for product {product_id}")

        response = await send_get_request(endpoint=endpoint, params={})
        parsed = self._parse_response(response)
        self._raise_for_response(
            response, parsed, operation="get_available_quantity"
        )
        return parsed

    # ================================================================
    # BULK OPERATIONS
    # ================================================================

    async def bulk_reserve(
        self,
        ordered_items: Optional[List[Dict]] = None,
        consumptions: Optional[List[Dict]] = None,
    ) -> Dict:
        """Bulk reserve inventory for both ordered items and consumptions."""
        endpoint = f"{self.base_url}/inventory/bulk/reserve"

        request_data: Dict[str, Any] = {}
        if ordered_items:
            request_data["ordered_items"] = ordered_items
        if consumptions:
            request_data["consumptions"] = consumptions

        logger.info(
            f"Bulk reserving: {len(ordered_items or [])} ordered items, "
            f"{len(consumptions or [])} consumptions"
        )

        response = await send_post_request(
            endpoint=endpoint,
            json_data=request_data,
            headers={"Content-Type": "application/json"},
        )
        parsed = self._parse_response(response)
        self._raise_for_response(response, parsed, operation="bulk_reserve")
        return parsed

    async def bulk_confirm(
        self,
        ordered_items: Optional[List[Dict]] = None,
        consumptions: Optional[List[Dict]] = None,
    ) -> Dict:
        """Bulk confirm inventory for both ordered items and consumptions ATOMICALLY."""
        endpoint = f"{self.base_url}/inventory/bulk/confirm"

        request_data: Dict[str, Any] = {}
        if ordered_items:
            request_data["ordered_items"] = ordered_items
        if consumptions:
            request_data["consumptions"] = consumptions

        logger.info(
            f"Bulk confirming: {len(ordered_items or [])} ordered items, "
            f"{len(consumptions or [])} consumptions"
        )

        response = await send_post_request(
            endpoint=endpoint,
            json_data=request_data,
            headers={"Content-Type": "application/json"},
        )
        parsed = self._parse_response(response)
        self._raise_for_response(response, parsed, operation="bulk_confirm")
        return parsed

    async def bulk_release(
        self,
        ordered_items: Optional[List[Dict]] = None,
        consumptions: Optional[List[Dict]] = None,
    ) -> Dict:
        """Bulk release inventory for both ordered items and consumptions."""
        endpoint = f"{self.base_url}/inventory/bulk/release"

        request_data: Dict[str, Any] = {}
        if ordered_items:
            request_data["ordered_items"] = ordered_items
        if consumptions:
            request_data["consumptions"] = consumptions

        logger.info(
            f"Bulk releasing: {len(ordered_items or [])} ordered items, "
            f"{len(consumptions or [])} consumptions"
        )

        response = await send_post_request(
            endpoint=endpoint,
            json_data=request_data,
            headers={"Content-Type": "application/json"},
        )
        parsed = self._parse_response(response)
        self._raise_for_response(response, parsed, operation="bulk_release")
        return parsed

    # ================================================================
    # HEALTH
    # ================================================================

    async def health_check(self) -> Dict[str, str]:
        """Liveness probe. Never raises — returns a status dict."""
        try:
            endpoint = f"{self.base_url}/inventory/health"
            response = await send_get_request(endpoint=endpoint, params={})
            parsed = self._parse_response(response)

            if getattr(response, "status_code", None) == 200:
                return parsed
            return {"status": "unhealthy", "error": str(parsed)}

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}