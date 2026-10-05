# workflows/subscription_workflow.py
"""
Subscription workflow: purchase, finalize, cancel, and read.

Owns the sequence that combines invoice creation, finance-side payment,
the local Subscription row, and the user's subscription pointer. None
of those steps belongs in `SubscriptionService` — a service persists
one kind of row; the workflow is what makes a purchase atomic across
several.
"""

import datetime
import logging
from typing import Any, Dict, Optional

from pydantic import ValidationError

from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_417_EXPECTATION_FAILED,
)
from core.models.api_models import Invoice_API, InvoiceStatus, InvoiceType
from core.models.models import AppUser, Invoice, Plan, Subscription
from core.models.finance_models import PaymentCreate, PaymentRefund

from features.auth_manager import AuthManager  # not used here; drop if unused
from services.invoice_service import InvoiceService
from services.subscription_service import SubscriptionService
from services.user_service import UserService
from storage.wrappers.finance_client import FinanceServiceClient

from workflows.usage_workflow import UsageWorkflow

logger = logging.getLogger(__name__)


class SubscriptionWorkflow:
    """Coordinates subscription operations across services.

    Constructed per-request; holds no state between calls. All
    collaborators are injected so tests can swap them out.
    """

    def __init__(
        self,
        subscription_service: Optional[SubscriptionService] = None,
        invoice_service: Optional[InvoiceService] = None,
        finance_client: Optional[FinanceServiceClient] = None,
        user_service: Optional[UserService] = None,
        usage_workflow: Optional[UsageWorkflow] = None,
    ):
        self.subscription_service = (
            subscription_service or SubscriptionService()
        )
        self.invoice_service = invoice_service or InvoiceService()
        self.finance_client = finance_client or FinanceServiceClient()
        self.user_service = user_service or UserService()
        self.usage_workflow = usage_workflow or UsageWorkflow()

    # ==================== Reads ====================

    def get_subscription(self, user_id: int) -> Optional[Subscription]:
        """Return the user's current subscription, or None.

        Null means "no subscription on file" — a normal free-tier
        state, not an error.
        """
        return self.subscription_service.get_subscription_for_user(user_id)

    def is_subscription_active(self, user_id: int) -> bool:
        """True when the user has an active, unexpired subscription."""
        return self.subscription_service.is_active_for_user(user_id)

    def get_plan_by_id(self, plan_id: int) -> Optional[Plan]:
        return self.subscription_service.get_plan_by_id(plan_id)

    # ==================== Purchase: paid plan ====================

    async def initiate(
        self,
        user_id: int,
        plan_id: int,
        payment_method: str,
        *,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Purchase a subscription end to end. (Body unchanged from
        `UserWorkflow.initiate_subscription`.)

        The only change: the finalize call below routes through this
        class's `finalize` method, which now syncs the user's quota
        via `UsageWorkflow` rather than writing it directly.
        """
        user = self.user_service.get_user_by_id(user_id)

        plan = self.subscription_service.get_plan_by_id(plan_id)
        if plan is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.PLAN_NOT_FOUND,
                details={"plan_id": plan_id},
            )

        if plan.plan_price is None or float(plan.plan_price) <= 0:
            raise APIException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.FREE_PLAN_REQUIRES_LINK,
                details={
                    "plan_id": plan_id,
                    "reason": (
                        "Plan price is zero; use link_free_plan instead "
                        "of initiate_subscription"
                    ),
                },
            )

        current = self.subscription_service.get_subscription_for_user(user_id)
        if (
            current is not None
            and self.subscription_service.is_active(current)
            and current.subscription_plan_id == plan_id
        ):
            raise APIException(
                status_code=HTTP_409_CONFLICT,
                error_code=ErrorCode.SUBSCRIPTION_ALREADY_ACTIVE,
                details={
                    "user_id": user_id,
                    "plan_id": plan_id,
                    "subscription_id": current.id_subscription,
                },
            )

        invoice = self._create_invoice(user, plan, notes)
        logger.info(
            f"Subscription invoice created: user={user_id} "
            f"plan={plan_id} invoice={invoice.invoice_id} "
            f"amount={plan.plan_price}"
        )

        payment = await self._create_payment(
            user_id=user_id,
            plan=plan,
            invoice=invoice,
            payment_method=payment_method,
            notes=notes,
        )
        payment_id = self._extract_payment_id(payment)
        logger.info(
            f"Subscription payment created: user={user_id} plan={plan_id} "
            f"invoice={invoice.invoice_id} payment={payment_id}"
        )

        if payment_id > 0:
            await self._confirm_payment(user_id, payment_id)
            payment = await self._refetch_payment(payment_id)

        finalized = await self.finalize(user_id, payment_id, plan_id)
        return finalized

    # ==================== Purchase: finalize ====================

    async def finalize(
        self,
        user_id: int,
        payment_id: int,
        plan_id: int,
    ) -> Dict[str, Any]:
        """Complete a subscription purchase after the payment clears.

        (Body unchanged from `UserWorkflow.finalize_subscription`,
        except the two `_link_user_to_subscription` calls now
        delegate to `UsageWorkflow.sync_user_quota` after writing
        the pointer.)
        """
        try:
            payment = await self.finance_client.get_payment(payment_id)
        except Exception as e:
            logger.error(f"Failed to fetch payment {payment_id}: {e}")
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.PAYMENT_NOT_FOUND,
                details={"payment_id": payment_id},
            )

        if payment.status != "completed":
            raise APIException(
                status_code=HTTP_409_CONFLICT,
                error_code=ErrorCode.PAYMENT_NOT_COMPLETED,
                details={
                    "payment_id": payment_id,
                    "status": payment.status,
                },
            )

        existing = (
            self.subscription_service.subscription_repo.get_by_payment_id(
                payment_id
            )
        )
        if existing is not None:
            logger.info(
                f"Subscription already finalized for payment "
                f"{payment_id}: subscription={existing.id_subscription}"
            )
            user = self.user_service.get_user_by_id(user_id)
            if user.app_user_subscription_ref != existing.id_subscription:
                self._point_user_at(user, existing)
            return {
                "subscription": existing,
                "payment": payment,
                "user_id": user_id,
                "created": False,
            }

        subscription = self.subscription_service.create_subscription(
            plan_id=plan_id,
            payment_id=payment_id,
        )

        user = self.user_service.get_user_by_id(user_id)
        self._point_user_at(user, subscription)

        logger.info(
            f"Subscription finalized: user={user_id} plan={plan_id} "
            f"subscription={subscription.id_subscription} "
            f"payment={payment_id}"
        )

        return {
            "subscription": subscription,
            "payment": payment,
            "user_id": user_id,
            "created": True,
        }

    # ==================== Purchase: free plan ====================

    def link_free_plan(self, user_id: int, plan_id: int) -> Dict[str, Any]:
        """Attach a zero-priced plan to a user without touching finance.
        (Body unchanged from `UserWorkflow.link_free_plan`; the link
        step delegates the same way.)
        """
        plan = self.subscription_service.get_plan_by_id(plan_id)
        if plan is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.PLAN_NOT_FOUND,
                details={"plan_id": plan_id},
            )

        if plan.plan_price is not None and float(plan.plan_price) > 0:
            raise APIException(
                status_code=HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.PAID_PLAN_REQUIRES_PAYMENT,
                details={
                    "plan_id": plan_id,
                    "plan_price": float(plan.plan_price),
                },
            )

        subscription = self.subscription_service.create_subscription(
            plan_id=plan_id,
        )
        user = self.user_service.get_user_by_id(user_id)
        self._point_user_at(user, subscription)

        logger.info(
            f"Free plan linked: user={user_id} plan={plan_id} "
            f"subscription={subscription.id_subscription}"
        )

        return {
            "subscription": subscription,
            "plan": plan,
            "payment": None,
            "user_id": user_id,
            "created": True,
        }

    # ==================== Cancel ====================

    async def cancel(
        self,
        user_id: int,
        *,
        refund_payment_id: Optional[int] = None,
    ) -> AppUser:
        """Cancel a user's subscription. (Body unchanged, except the
        unlink step delegates to `_clear_user_pointer`.)
        """
        subscription = self.get_subscription(user_id)
        if subscription is None:
            raise APIException(
                status_code=HTTP_404_NOT_FOUND,
                error_code=ErrorCode.SUBSCRIPTION_NOT_FOUND,
                details={"user_id": user_id},
            )

        if refund_payment_id is not None:
            try:
                await self.finance_client.refund_payment(
                    refund_payment_id,
                    PaymentRefund(
                        amount=None,
                        reason=(
                            f"Subscription cancellation for user {user_id}"
                        ),
                    ),
                )
            except Exception as e:
                logger.error(
                    f"Refund of payment {refund_payment_id} failed for "
                    f"user {user_id}: {e}"
                )
                raise APIException(
                    status_code=HTTP_417_EXPECTATION_FAILED,
                    error_code=ErrorCode.SUBSCRIPTION_CANCEL_FAILED,
                    details={
                        "user_id": user_id,
                        "payment_id": refund_payment_id,
                        "error": str(e),
                    },
                )

        return self._clear_user_pointer(user_id)

    # ==================== Internal: pointer updates ====================

    def _point_user_at(
        self,
        user: AppUser,
        subscription: Subscription,
    ) -> AppUser:
        """Set a user's subscription pointer, then sync their quota.

        The pointer write lives here (it's an `AppUser` field). The
        quota sync lives in `UsageWorkflow` — the two concerns are
        separate even though they touch the same row.

        Quota sync happens *after* the pointer is persisted, so a
        reader that sees the new pointer also sees the matching
        quota. A reader that sees the old pointer sees the old quota,
        which is consistent with the old subscription.
        """
        user.app_user_subscription_ref = subscription.id_subscription
        user.app_user_last_updated = datetime.datetime.now()
        updated = self.user_service.update_user_record_raw(user)

        # Sync via the usage workflow — the only writer of
        # `AppUser.user_quota`.
        self.usage_workflow.sync_user_quota(user.id_app_user)
        return updated

    def _clear_user_pointer(self, user_id: int) -> AppUser:
        """Clear a user's subscription pointer and zero their quota.

        The mirror of `_point_user_at`. The subscription row itself
        is left in place — cancellation is a user-state change, not
        a deletion.
        """
        user = self.user_service.get_user_by_id(user_id)
        user.app_user_subscription_ref = None
        user.app_user_last_updated = datetime.datetime.now()
        updated = self.user_service.update_user_record_raw(user)

        # Zero the quota through the same path as the sync — that's
        # the only place that decides what "no subscription" means
        # for `user_quota`.
        self.usage_workflow.sync_user_quota(user_id)
        return updated

    # ==================== Internal: invoice/payment helpers ====================

    def _create_invoice(
        self,
        user: AppUser,
        plan: Plan,
        notes: Optional[str] = None,
    ) -> Invoice:
        """Create an invoice for a plan purchase.

        The invoice is dated now and due immediately — a subscription
        purchase is prepaid. Amount comes from the plan's list price;
        taxes are assumed included, matching how the finance service
        treats plan prices.
        """
        invoice_data = Invoice_API(
            invoice_number=None,  # service generates one
            invoice_total_amount=float(plan.plan_price),
            invoice_status=InvoiceStatus.UNPAID,
            invoice_type=InvoiceType.INVOICE,
            invoice_issue_date=datetime.datetime.now().date(),
            invoice_due_date=datetime.datetime.now().date(),
            invoice_notes=notes or f"Subscription: {plan.plan_name}",
            invoice_tax_applied=False,
        )
        return self.invoice_service.create_invoice(invoice_data)

    async def _create_payment(
        self,
        user_id: int,
        plan: Plan,
        invoice: Invoice,
        payment_method: str,
        notes: Optional[str],
    ) -> Any:
        """Create the finance-side payment for a subscription invoice.

        The `plan_id` is passed alongside the invoice so the finalize
        step can recover it from the payment without a second lookup.
        The `PaymentCreate` payload validates the request shape
        locally before the network call, so a malformed field is a
        417 here rather than an opaque 400 from the finance service.
        """
        payment_payload_data: Dict[str, Any] = {
            "amount": float(plan.plan_price),
            "payment_method": payment_method,
            "user_id": user_id,
            "notes": notes or f"Subscription purchase: {plan.plan_name}",
            "payment_type": "payment",
            "invoice_id": invoice.invoice_id,
            "plan_id": plan.id_plan,
        }

        try:
            payment_payload = PaymentCreate(**payment_payload_data)
        except ValidationError as e:
            logger.error(f"PaymentCreate validation failed: {e}")
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.PAYMENT_CREATION_FAILED,
                details={"validation": str(e)},
            )

        try:
            return await self.finance_client.create_payment(payment_payload)
        except Exception as e:
            logger.error(
                f"Payment creation failed for user {user_id} plan "
                f"{plan.id_plan}: {e}"
            )
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.PAYMENT_CREATION_FAILED,
                details={
                    "user_id": user_id,
                    "plan_id": plan.id_plan,
                    "invoice_id": invoice.invoice_id,
                    "error": str(e),
                },
            )

    async def _confirm_payment(
        self,
        user_id: int,
        payment_id: int,
    ) -> None:
        """Confirm the payment with the finance service.

        Wraps the confirm call so the failure mode is uniform: any
        exception becomes a PAYMENT_CONFIRMATION_FAILED APIException
        with the underlying error attached.

        In a production deployment this synchronous call is replaced
        by a bank callback or card gateway webhook. The current
        synchronous path exists so the client gets a working
        subscription in one round-trip; the webhook path calls
        `finalize` directly once the payment clears.
        """
        try:
            await self.finance_client.confirm_payment(
                payment_id=payment_id,
                transaction_details={
                    "user_id": user_id,
                    "reference": f"SUB-{user_id}-{payment_id}",
                    "notes": "Auto-confirmed during subscription purchase",
                },
            )
            logger.info(f"Payment {payment_id} confirmed")
        except Exception as e:
            logger.error(
                f"Payment confirmation failed for {payment_id}: {e}"
            )
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.PAYMENT_CONFIRMATION_FAILED,
                details={
                    "user_id": user_id,
                    "payment_id": payment_id,
                    "error": str(e),
                },
            )

    async def _refetch_payment(self, payment_id: int):
        """Re-fetch the payment so the response carries its completed
        state rather than the pending snapshot the create call
        returned.

        Returns None on failure rather than raising — the caller uses
        this to enrich the response, and a missing refresh is less
        bad than an exception from what is effectively a cache
        warm-up. The payment row itself is already correct on the
        finance side; this is only for the response payload.
        """
        try:
            return await self.finance_client.get_payment(payment_id)
        except Exception as e:
            logger.warning(
                f"Failed to refetch payment {payment_id} after "
                f"confirm: {e}"
            )
            return None

    def _extract_payment_id(self, payment) -> int:
        """Pull the payment id out of whatever the finance client
        returns.

        The client has returned pydantic models (`payment.id`) and
        raw dicts (`payment['id']`) across versions. Handle both so
        this doesn't break when the client shape changes.

        Returns 0 when no id is found. Callers should treat 0 as
        "payment creation failed to return an id" and skip the
        confirm step.
        """
        if payment is None:
            return 0

        # Pydantic model
        for attr in ("id", "payment_id"):
            val = getattr(payment, attr, None)
            if val is not None:
                try:
                    return int(val)
                except (ValueError, TypeError):
                    pass

        # Dict
        if isinstance(payment, dict):
            for key in ("id", "payment_id"):
                val = payment.get(key)
                if val is not None:
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        pass

        return 0

    def _extract_plan_id_from_payment(self, payment) -> Optional[int]:
        """Recover the plan id the payment was created for.

        Prefers a dedicated `plan_id` field on the payment response.
        Falls back to parsing the notes for a `plan_id=<n>` token if
        the finance service doesn't echo the field.

        Returns None if neither is present. The current `finalize`
        signature takes `plan_id` explicitly, so this helper is only
        used if you later switch to the async webhook path where the
        plan must be recovered from the payment alone.
        """
        # Option 1: dedicated field on a pydantic model
        plan_id = getattr(payment, "plan_id", None)

        # Option 1b: dedicated field on a dict
        if plan_id is None and isinstance(payment, dict):
            plan_id = payment.get("plan_id")

        if plan_id is not None:
            try:
                return int(plan_id)
            except (ValueError, TypeError):
                pass

        # Option 2: parse from notes
        notes = getattr(payment, "notes", None)
        if notes is None and isinstance(payment, dict):
            notes = payment.get("notes")
        notes = notes or ""

        for token in notes.split():
            if token.startswith("plan_id="):
                try:
                    return int(token.split("=", 1)[1])
                except (ValueError, IndexError):
                    continue

        return None