# core/error_responses.py
from typing import Dict, Any, Optional
from fastapi import Request
from fastapi.responses import JSONResponse
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import uuid


def _json_safe(value: Any) -> Any:
    """Recursively coerce `value` into JSON-serializable primitives.

    Handles the types that routinely leak into error payloads:

      * `Decimal`   → `float`   (money / stock quantities)
      * `datetime`  → ISO 8601 string
      * `date`      → ISO 8601 string
      * `Enum`      → its `.value`
      * `set/tuple` → list
      * `dict`      → dict with sanitized values
      * `list`      → list with sanitized values

    Anything else is passed through unchanged. If a non-serializable
    type sneaks in after this, `json.dumps` will still raise — but
    it will name the type, not "Object of type Decimal".

    Why `float` and not `str` for `Decimal`:
      A `Decimal("10")` in an error payload is almost always a
      numeric value the client will compare or display. Emitting
      `10.0` matches what the success paths return and what the
      client's JSON parser expects. If you need exact decimal
      representation, swap to `str(value)` here — but then audit
      every consumer that reads error details as numbers.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        # `float()` on an infinite/nan Decimal raises — fall back to
        # its string form so the response still goes out.
        try:
            return float(value)
        except (ValueError, TypeError):
            return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(v) for v in value]
    return value


class ErrorResponse:
    """Builder for standardized error responses."""

    def __init__(self, request: Optional[Request] = None):
        self.request = request
        self.data: Dict[str, Any] = {
            "success": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid.uuid4()),
        }

        if request:
            self.data["path"] = request.url.path
            if request_id := request.headers.get("X-Request-ID"):
                self.data["request_id"] = request_id

    def build(self) -> Dict[str, Any]:
        """Return the error response dictionary (already JSON-safe)."""
        return _json_safe(self.data)

    def to_response(
        self, status_code: int, headers: Optional[Dict] = None
    ) -> JSONResponse:
        """Convert to FastAPI JSONResponse.

        `self.data` is run through `_json_safe` first — `JSONResponse`
        calls `json.dumps`, which cannot serialize `Decimal`, `date`,
        `datetime`, or `Enum`. Without this step a domain exception
        carrying any of those types becomes a 500 instead of the
        4xx the caller deserves.
        """
        return JSONResponse(
            status_code=status_code,
            content=_json_safe(self.data),
            headers=headers,
        )

    def with_code(self, code: str) -> "ErrorResponse":
        self.data["code"] = code
        return self

    def with_message(self, message: str) -> "ErrorResponse":
        self.data["message"] = message
        return self

    def with_details(self, details: Dict[str, Any]) -> "ErrorResponse":
        self.data["details"] = details
        return self

    def with_status_code(self, status_code: int) -> "ErrorResponse":
        self.data["status_code"] = status_code
        return self

    def with_validation_errors(self, errors: list) -> "ErrorResponse":
        self.data["code"] = "VALIDATION_ERROR"
        self.data["message"] = "Request validation failed"
        self.data["details"] = {"errors": errors}
        return self


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    request: Optional[Request] = None,
    details: Optional[Dict] = None,
    headers: Optional[Dict] = None,
) -> JSONResponse:
    """Factory function to create a JSON error response."""
    builder = ErrorResponse(request)
    response = (
        builder
        .with_status_code(status_code)
        .with_code(error_code)
        .with_message(message)
    )

    if details:
        response.with_details(details)

    return response.to_response(status_code, headers)


def create_validation_error_response(
    request: Request,
    errors: list,
    headers: Optional[Dict] = None,
) -> JSONResponse:
    """Create a 422 validation error response."""
    builder = ErrorResponse(request)
    response = (
        builder
        .with_status_code(422)
        .with_validation_errors(errors)
    )
    return response.to_response(422, headers)