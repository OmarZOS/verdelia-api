# storage/wrappers/finance_client.py
"""
Finance service client.

Wraps the finance server's HTTP API. Every method:

  * Returns the parsed payload on success (a dict, or a Pydantic
    model when the endpoint has one).
  * Raises a typed `FinanceClientError` subclass on failure,
    carrying the HTTP status and the server's error message.

No method silently returns an empty dict on failure. No method
lets a bare `Exception` escape — callers can branch on the
error type and status.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging

from core.exceptions.specific.finance_exceptions import FinanceClientError,    FinanceClientError,FinanceValidationError,FinanceNotFoundError,FinanceConflictError,FinanceServerError,FinanceUnavailableError

from constants import FINANCE_SERVER_URL
from core.models.finance_models import (
    DailyPaymentStats,
    InvoicePaymentSummary,
    PaymentCreate,
    PaymentRefund,
    PaymentResponse,
    PaymentConfirm,
    ErrorResponse,
)
from communication.communication_broker import (
    send_post_request,
    send_get_request,
    send_put_request,
    send_delete_request,
)

from core.logging_config import get_logger

logger = get_logger(__name__)


class FinanceServiceClient:
    """Client for Finance API"""

    base_url = FINANCE_SERVER_URL
    timeout = 30

    # ================================================================
    # Transport — one method, one place, used by every caller
    # ================================================================

    async def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        action: str = "request",
    ) -> Any:
        """
        Send an HTTP request and return the parsed body.

        * Returns whatever is under the `data` key of the finance
          server's `{success, message, data}` envelope, or the raw
          body when there's no envelope.
        * Returns `{}` for empty 2xx bodies (204).
        * Raises a typed `FinanceClientError` subclass on non-2xx,
          carrying the HTTP status and the server's message.

        `action` is a human label for logs and error messages.
        """
        try:
            if method == "GET":
                response = await send_get_request(
                    endpoint=endpoint, params=params or {},
                )
            elif method == "POST":
                response = await send_post_request(
                    endpoint=endpoint,
                    json_data=json_data or {},
                    headers={"Content-Type": "application/json"},
                )
            elif method == "PUT":
                response = await send_put_request(
                    endpoint=endpoint,
                    json_data=json_data or {},
                    headers={"Content-Type": "application/json"},
                )
            elif method == "DELETE":
                response = await send_delete_request(
                    endpoint=endpoint, params=params or {},
                )
            else:
                raise ValueError(f"Unsupported method: {method!r}")
        except FinanceClientError:
            raise
        except Exception as transport_err:
            # Transport-level failure: DNS, connection refused,
            # timeout, TLS error. Everything under `communication`
            # lands here.
            logger.exception(
                "Finance client [%s]: transport failure", action,
            )
            raise FinanceUnavailableError(
                action=action,
                detail=str(transport_err),
            ) from transport_err

        parsed = self._parse_response(response)
        status = self._get_status_code(response)

        logger.info(
            "Finance client [%s]: HTTP %s method=%s endpoint=%s",
            action, status, method, endpoint,
        )

        if status in (200, 201, 204):
            if not parsed:
                return {}
            if isinstance(parsed, dict) and "data" in parsed:
                return parsed["data"]
            return parsed

        error_msg = self._extract_error_message(parsed) or f"HTTP {status}"
        logger.error("%s failed: %s", action, error_msg)

        # Classify the failure so the caller can branch.
        if status == 400 or status == 422:
            raise FinanceValidationError(
                action=action, status=status, detail=error_msg,
            )
        if status == 404:
            raise FinanceNotFoundError(
                action=action, status=status, detail=error_msg,
            )
        if status == 409:
            raise FinanceConflictError(
                action=action, status=status, detail=error_msg,
            )
        if 500 <= status < 600:
            raise FinanceServerError(
                action=action, status=status, detail=error_msg,
            )
        raise FinanceClientError(
            action=action, status=status, detail=error_msg,
        )

    @staticmethod
    def _extract_error_message(parsed: Any) -> Optional[str]:
        if not isinstance(parsed, dict):
            return None
        # Prefer `detail`, fall back to `message`, then `error`.
        for key in ("detail", "message", "error"):
            value = parsed.get(key)
            if value:
                return str(value)
        return None

    # ================================================================
    # Response parsing (kept private, no external callers)
    # ================================================================

    def _parse_response(self, response) -> Any:
        """Coerce whatever the transport returned into a Python value."""
        try:
            if isinstance(response, (dict, list)):
                return response

            if hasattr(response, "json"):
                try:
                    return response.json()
                except Exception as e:
                    logger.warning("Failed to parse response.json(): %s", e)

            if hasattr(response, "text"):
                try:
                    return json.loads(response.text)
                except Exception as e:
                    logger.warning("Failed to parse response.text: %s", e)

            if isinstance(response, str):
                try:
                    return json.loads(response)
                except Exception as e:
                    logger.warning(
                        "Failed to parse response string: %s", e,
                    )

            if hasattr(response, "content"):
                try:
                    return json.loads(response.content.decode("utf-8"))
                except Exception as e:
                    logger.warning(
                        "Failed to parse response.content: %s", e,
                    )

            if hasattr(response, "status_code"):
                logger.warning(
                    "Response object with status %s but no parsable "
                    "content",
                    response.status_code,
                )
                return {}

            logger.warning(
                "Could not parse response: %s", type(response),
            )
            return {}
        except Exception:
            logger.exception("Failed to parse response")
            return {}

    def _get_status_code(self, response) -> int:
        if isinstance(response, dict):
            return response.get("status_code", 500)
        if hasattr(response, "status_code"):
            return response.status_code
        return 500

    # ================================================================
    # Payments
    # ================================================================

    async def create_payment(
        self, payment_data: PaymentCreate,
    ) -> PaymentResponse:
        """
        Create a new payment with pending status.
        The invoice must already exist.
        """
        endpoint = f"{self.base_url}/payments/payment"
        request_data = payment_data.model_dump(exclude_none=True)

        logger.info(
            "Creating payment for invoice %s", payment_data.invoice_id,
        )

        raw = await self._request_json(
            "POST",
            endpoint,
            json_data=request_data,
            action=f"create payment for invoice {payment_data.invoice_id}",
        )

        try:
            return PaymentResponse(**(raw or {}))
        except Exception as parse_err:
            logger.exception(
                "Finance server returned an unparseable payment: %s",
                parse_err,
            )
            raise FinanceServerError(
                action="create payment",
                status=200,
                detail=f"Unparseable response: {parse_err}",
            ) from parse_err

    async def confirm_payment(
        self,
        payment_id: int,
        transaction_details: Dict,
    ) -> PaymentResponse:
        """
        Confirm a pending payment.

        This creates the money transactions for wallet transfers.
        After this call the payment's status on the finance side
        should be `completed` — but the caller must verify, because
        some failures (a gateway decline) return 200 with
        `status='failed'`.
        """
        endpoint = f"{self.base_url}/payments/confirm/{payment_id}"
        request_data = {"transaction_details": transaction_details or {}}

        logger.info("Confirming payment %s", payment_id)

        raw = await self._request_json(
            "POST",
            endpoint,
            json_data=request_data,
            action=f"confirm payment {payment_id}",
        )

        try:
            return PaymentResponse(**(raw or {}))
        except Exception as parse_err:
            logger.exception(
                "Finance server returned an unparseable payment: %s",
                parse_err,
            )
            raise FinanceServerError(
                action="confirm payment",
                status=200,
                detail=f"Unparseable response: {parse_err}",
            ) from parse_err

    async def reject_payment(
        self, payment_id: int, reason: str,
    ) -> PaymentResponse:
        """Reject a pending payment. No transactions are created."""
        endpoint = f"{self.base_url}/payments/reject/{payment_id}"
        logger.info(
            "Rejecting payment %s - Reason: %s", payment_id, reason,
        )

        raw = await self._request_json(
            "POST",
            endpoint,
            json_data={"reason": reason},
            action=f"reject payment {payment_id}",
        )

        try:
            return PaymentResponse(**(raw or {}))
        except Exception as parse_err:
            raise FinanceServerError(
                action="reject payment",
                status=200,
                detail=f"Unparseable response: {parse_err}",
            ) from parse_err

    async def refund_payment(
        self, payment_id: int, refund_data: PaymentRefund,
    ) -> PaymentResponse:
        """Refund a completed payment. Creates reverse transactions."""
        endpoint = f"{self.base_url}/payments/refund/{payment_id}"
        logger.info(
            "Refunding payment %s - Amount: %s",
            payment_id, refund_data.amount,
        )

        raw = await self._request_json(
            "POST",
            endpoint,
            json_data=refund_data.model_dump(exclude_none=True),
            action=f"refund payment {payment_id}",
        )

        try:
            return PaymentResponse(**(raw or {}))
        except Exception as parse_err:
            raise FinanceServerError(
                action="refund payment",
                status=200,
                detail=f"Unparseable response: {parse_err}",
            ) from parse_err

    async def get_payment(self, payment_id: int) -> PaymentResponse:
        """Get payment details with transactions."""
        endpoint = f"{self.base_url}/payments/{payment_id}"
        raw = await self._request_json(
            "GET",
            endpoint,
            action=f"get payment {payment_id}",
        )
        try:
            return PaymentResponse(**(raw or {}))
        except Exception as parse_err:
            raise FinanceServerError(
                action="get payment",
                status=200,
                detail=f"Unparseable response: {parse_err}",
            ) from parse_err

    async def get_invoice_payments(
        self, invoice_id: int,
    ) -> InvoicePaymentSummary:
        """Get all payments for an invoice."""
        endpoint = f"{self.base_url}/payments/invoice/{invoice_id}"
        raw = await self._request_json(
            "GET",
            endpoint,
            action=f"get invoice payments {invoice_id}",
        )
        try:
            return InvoicePaymentSummary(**(raw or {}))
        except Exception as parse_err:
            raise FinanceServerError(
                action="get invoice payments",
                status=200,
                detail=f"Unparseable response: {parse_err}",
            ) from parse_err

    async def get_daily_stats(
        self, date: Optional[str] = None,
    ) -> DailyPaymentStats:
        """Get daily payment statistics."""
        endpoint = f"{self.base_url}/payments/stats/daily"
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        logger.info("Getting daily stats for %s", target_date)

        raw = await self._request_json(
            "GET",
            endpoint,
            params={"date": target_date},
            action=f"get daily stats {target_date}",
        )
        try:
            return DailyPaymentStats(**(raw or {}))
        except Exception as parse_err:
            raise FinanceServerError(
                action="get daily stats",
                status=200,
                detail=f"Unparseable response: {parse_err}",
            ) from parse_err

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the Finance API. Never raises."""
        endpoint = f"{self.base_url}/payments/health"
        try:
            raw = await self._request_json(
                "GET", endpoint, action="health check",
            )
            return raw or {"status": "healthy"}
        except FinanceClientError as e:
            return {"status": "unhealthy", "error": e.detail}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    # ================================================================
    # Wallets
    # ================================================================

    async def get_wallet_by_id(self, wallet_id: int) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/wallets/{wallet_id}"
        return await self._request_json(
            "GET", endpoint, action=f"get wallet {wallet_id}",
        )

    async def get_user_wallet(self, user_id: int) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/wallets/user/{user_id}"
        return await self._request_json(
            "GET", endpoint, action=f"get user wallet {user_id}",
        )

    async def get_provider_wallet(self, provider_id: int) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/wallets/provider/{provider_id}"
        return await self._request_json(
            "GET", endpoint, action=f"get provider wallet {provider_id}",
        )

    async def get_wallet_by_owner(
        self,
        *,
        owner_type: str,
        owner_id: int,
    ) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/wallets/by-owner"
        return await self._request_json(
            "POST",
            endpoint,
            json_data={"owner_type": owner_type, "owner_id": owner_id},
            action=f"resolve wallet for {owner_type} {owner_id}",
        )

    async def get_wallet_transactions(
        self,
        wallet_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Fetch a wallet's transaction ledger, newest first.

        The endpoint returns a bare array, `_request_json` returns
        it unchanged. When the server wraps it in `{"items": [...]}`,
        that shape is unwrapped here.
        """
        endpoint = f"{self.base_url}/wallets/{wallet_id}/transactions"
        raw = await self._request_json(
            "GET",
            endpoint,
            params={"limit": limit, "offset": offset},
            action=f"get wallet transactions {wallet_id}",
        )
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict) and isinstance(raw.get("items"), list):
            return raw["items"]
        return []

    async def get_system_wallet(self) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/wallets/system"
        return await self._request_json(
            "GET", endpoint, action="get system wallet",
        )

    async def transfer_between_wallets(
        self,
        *,
        source_wallet_id: int,
        destination_wallet_id: int,
        amount: float,
        intent: str,
        reference: str,
    ) -> Dict[str, Any]:
        """
        Move money between two wallets.

        The debit and the credit are one operation on the finance
        side: two ledger rows in the same transaction.
        """
        endpoint = f"{self.base_url}/wallets/transfer"
        return await self._request_json(
            "POST",
            endpoint,
            json_data={
                "source_wallet_id": source_wallet_id,
                "destination_wallet_id": destination_wallet_id,
                "amount": amount,
                "intent": intent,
                "reference": reference,
            },
            action=(
                f"transfer {amount} from wallet {source_wallet_id} "
                f"to {destination_wallet_id}"
            ),
        )