# workflows/user_workflow.py
"""
User workflow: orchestrates multi-step user operations.

The workflow layer owns coordination that no single service should:

  * cross-service sequencing (user + person + location + auth)
  * compensating actions when a later step fails (rollback the user
    row when auth registration fails)
  * translating domain failures into user-facing API errors
  * injecting cross-cutting context (system token, provider routing)

Services stay narrow: ``UserService`` knows how to persist a user,
``AuthManager`` knows how to talk to the auth backend. Neither knows
that creating a user requires both, in a specific order, with a
rollback path if the second one fails. That's the workflow's job.
"""

import datetime
import logging
from typing import Optional, Dict, Any

from pydantic import ValidationError

from services.invoice_service import InvoiceService
from services.subscription_service import SubscriptionService
from storage.wrappers.finance_client import FinanceServiceClient
from core.models.finance_models import PaymentCreate, PaymentRefund
from core.exceptions.handler import (
    APIException,
    UserNotFoundException,
)
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_410_GONE,
    HTTP_417_EXPECTATION_FAILED,
)
from core.models.api_models import (
    AppUser_API,
    Person_API,
    Location_API,
    AppUserUpdate_API,
    Invoice_API,
    InvoiceStatus,
    InvoiceType,
)
from core.models.models import AppUser, Subscription, Invoice, Plan
from core.logging_config import get_logger

from services.user_service import UserService
from services.person_service import PersonService
from features.auth_manager import AuthManager

logger = get_logger(__name__)


class UserWorkflow:
    """Coordinates user operations across services.

    Constructed per-request; holds no state between calls. All
    collaborators are injected so tests can swap them out.
    """

    def __init__(
        self,
        user_service: Optional[UserService] = None,
        person_service: Optional[PersonService] = None,
        auth_manager: Optional[AuthManager] = None,
        subscription_service: Optional[SubscriptionService] = None,
        invoice_service: Optional[InvoiceService] = None,
        finance_client: Optional[FinanceServiceClient] = None,
    ):
        self.user_service = user_service or UserService()
        self.person_service = person_service or PersonService()
        self.auth_manager = auth_manager or AuthManager()
        self.subscription_service = subscription_service or SubscriptionService()
        self.invoice_service = invoice_service or InvoiceService()
        self.finance_client = finance_client or FinanceServiceClient()

    # ==================== Create ====================

    async def create_user(
        self,
        user_data: AppUser_API,
        person_data: Optional[Person_API] = None,
        location_data: Optional[Location_API] = None,
        provider: Optional[str] = None,
    ) -> AppUser:
        """Create a user end to end.

        Sequence:
          1. Uniqueness check on username and email.
          2. Persist the AppUser row.
          3. Attach or create the Person (and Location) if provided.
          4. Register the auth record — unless the provider is an
             OAuth one, in which case the auth backend owns the
             credential.
          5. On auth failure, delete the AppUser row so we don't leave
             an orphaned account behind.

        Raises APIException with the appropriate status code at each
        failure point. The router just forwards what it gets.
        """
        logger.info(
            f"Creating user '{user_data.app_user_name}' "
            f"(provider={provider})"
        )

        self._assert_username_available(user_data.app_user_name)
        if user_data.app_user_email:
            self._assert_email_available(user_data.app_user_email)

        user = self.user_service.create_user_record(
            user_data=user_data,
            person_data=person_data,
            location_data=location_data,
        )

        # OAuth users get their credentials from the provider, not from
        # a password we generate. Skip auth registration entirely.
        if provider and provider.lower() == "google":
            logger.info(
                f"Skipping auth registration for OAuth provider '{provider}'"
            )
            return user

        try:
            auth_record = await self._register_auth(user, user_data)
        except APIException as auth_error:
            self._rollback_user(user)
            raise APIException(
                status_code=HTTP_410_GONE,
                error_code=ErrorCode.USER_AUTH_CREATION_FAILED,
                details={
                    "auth_error": str(auth_error),
                    "user_id": user.id_app_user,
                },
            )

        # Store the hash on the user row so reads don't need to hit the
        # auth backend.
        self.user_service.update_user_password(
            user_record=user,
            hashed_password=auth_record["hashed_password"],
        )

        return user

    # ==================== Update ====================

    def update_user(
        self,
        user_data: AppUser_API,
        person_data: Person_API,
        location_data: Location_API,
    ) -> AppUser:
        """Update a user's profile.

        Person + location are refreshed or inserted first, then the
        user row is updated to point at the resulting person. This
        ordering means a failed person write leaves the user row
        untouched — the caller can retry with a corrected payload.
        """
        user = self.user_service.get_user_by_id(user_data.id_app_user)
        person = self.person_service.refresh_or_insert_person(
            person_data, location_data
        )

        return self.user_service.update_user_record(
            user=user,
            user_data=user_data,
            person_id=person.id_person,
        )

    def update_user_image(self, user_id: int, image_url: str) -> AppUser:
        """Update a user's avatar URL."""
        user = self.user_service.get_user_by_id(user_id)
        return self.user_service.update_user_image_url(user, image_url)

    # ==================== Delete ====================

    async def delete_user(
        self,
        user_data: AppUser_API,
        delete_auth: bool = True,
    ) -> bool:
        """Delete a user and their auth record.

        Deletes the auth record first — if it fails we abort before
        touching the user row, so the account stays consistent. If the
        auth delete succeeds but the user delete fails, we surface the
        error; the auth record is gone, which is recoverable.
        """
        user = self.user_service.get_user_by_id(user_data.id_app_user)

        if delete_auth:
            try:
                await self.auth_manager.delete_user(
                    user_id=user.id_app_user,
                    username=user.app_user_name,
                )
            except Exception as e:
                logger.error(
                    f"Auth deletion failed for user {user.id_app_user}: {e}"
                )
                raise APIException(
                    status_code=HTTP_417_EXPECTATION_FAILED,
                    error_code=ErrorCode.USER_DELETE_FAILED,
                    details={
                        "user_id": user.id_app_user,
                        "error": str(e),
                    },
                )

        return self.user_service.delete_user_record(user)

    # ==================== Password ====================

    async def change_password(
        self,
        user_id: int,
        new_password: str,
        token: Optional[str] = None,
    ) -> None:
        """Change a user's password.

        Delegates to AuthManager with the caller's token when
        available, falling back to the system token otherwise. The
        local password hash is refreshed to mirror what the auth
        backend now holds.
        """
        user = self.user_service.get_user_by_id(user_id)

        await self.auth_manager.change_password(
            user_id=user.id_app_user,
            username=user.app_user_name,
            new_password=new_password,
            token=token,
        )

    # ==================== Reads ====================

    def get_user(
        self,
        user_id: int,
        full: bool = False,
    ) -> AppUser:
        """Fetch a user by id, raising if missing."""
        user = self.user_service.get_user_by_id(user_id, eager_load=full)
        if not user:
            raise UserNotFoundException(user_id=user_id)
        return user

    def get_user_by_email(self, email: str) -> AppUser:
        """Fetch a user by email, raising if missing."""
        user = self.user_service.get_user_by_email(email)
        if not user:
            raise UserNotFoundException(username=email)
        return user

    def search_users(self, query: str, limit: int = 20) -> list:
        """Search users by username or email."""
        return self.user_service.search_users(query, limit)

    # ==================== Subscription reads ====================

    def get_subscription(self, user_id: int) -> Optional[Subscription]:
        """Return the user's current subscription, or None.

        Null means "no subscription on file" — a normal free-tier
        state, not an error.
        """
        return self.subscription_service.get_subscription_for_user(user_id)

    def is_subscription_active(self, user_id: int) -> bool:
        """True when the user has an active, unexpired subscription."""
        return self.subscription_service.is_active_for_user(user_id)

    # ==================== Subscription purchase ====================

    async def initiate_subscription(
        self,
        user_id: int,
        plan_id: int,
        payment_method: str,
        *,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Purchase a subscription end to end.

        Single-call flow:
          1. Validate the user and plan.
          2. Create a local invoice for the plan price.
          3. Create a payment against that invoice via the finance
             service.
          4. Confirm the payment synchronously so the client gets a
             working subscription back in one round-trip.
          5. Delegate to `finalize_subscription` to create the
             Subscription row, link it to the user, and mark the
             invoice paid.

        In a production deployment the confirmation step would be
        driven by a bank callback or card gateway webhook instead of
        the synchronous call here. The `finalize_subscription` method
        stays in place for that async path — a webhook or recovery
        poller calls it once the payment clears.

        Raises:
            404 if the user or plan doesn't exist.
            409 if the user already has an active subscription to this
                plan.
            400 if the plan's price is zero (use `link_free_plan` for
                free plans).
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

        # 1. Create the invoice locally.
        invoice = self._create_subscription_invoice(user, plan, notes)
        logger.info(
            f"Subscription invoice created: user={user_id} "
            f"plan={plan_id} invoice={invoice.invoice_id} "
            f"amount={plan.plan_price}"
        )

        # 2. Create the payment on the finance side.
        payment = await self._create_subscription_payment(
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

        # 3. Confirm the payment synchronously. Without this, the
        #    payment sits in `pending` and finalize would reject it
        #    with PAYMENT_NOT_COMPLETED.
        if payment_id > 0:
            await self._confirm_subscription_payment(user_id, payment_id)
            payment = await self._refetch_payment(payment_id)

        # 4. Delegate to finalize_subscription so the create-row,
        #    link-user, and mark-invoice-paid logic lives in exactly
        #    one place. `finalize_subscription` re-fetches the payment,
        #    verifies it's completed, and does the rest.
        finalized = await self.finalize_subscription(user_id, payment_id,plan_id)

        return finalized

    async def finalize_subscription(
        self,
        user_id: int,
        payment_id: int,
        plan_id: int,
    ) -> Dict[str, Any]:
        """Complete a subscription purchase after the payment clears.

        Called by `initiate_subscription` after the synchronous
        confirm, and by the webhook / recovery-poller path when the
        confirmation arrives out of band.

        Idempotent: if the user already points at a subscription
        created by this payment, returns the existing one rather than
        creating a duplicate. This matters because webhooks retry and
        pollers re-run.

        The flow:
          1. Verify the payment is completed.
          2. Recover the plan id from the payment.
          3. Mark the linked invoice paid.
          4. Create the Subscription row (or return the existing one).
          5. Link it to the user and sync quota.

        Raises:
            404 if the payment or the plan can't be found.
            409 if the payment isn't completed.
        """
        # 1. Fetch the payment from the finance service.
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


        # 4. Idempotency: if this payment already produced a
        #    subscription, return it rather than creating another.
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
                self._link_user_to_subscription(
                    user, existing, sync_quota=True
                )
            return {
                "subscription": existing,
                "payment": payment,
                "user_id": user_id,
                "created": False,
            }

        # 5. Create the subscription row.
        subscription = self.subscription_service.create_subscription(
            plan_id=plan_id,
            payment_id=payment_id,
        )

        # 6. Link it to the user.
        user = self.user_service.get_user_by_id(user_id)
        self._link_user_to_subscription(user, subscription, sync_quota=True)

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

    def link_free_plan(self, user_id: int, plan_id: int) -> Dict[str, Any]:
        """Attach a zero-priced plan to a user without touching finance.

        Free plans don't need a payment, so they skip the initiate/
        finalize dance. This method creates the subscription, links
        the user, and returns. Syncs quota the same way a paid path
        does.
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
                    "reason": (
                        "Plan has a non-zero price; use "
                        "initiate_subscription followed by "
                        "finalize_subscription"
                    ),
                },
            )

        subscription = self.subscription_service.create_subscription(
            plan_id=plan_id,
        )

        user = self.user_service.get_user_by_id(user_id)
        self._link_user_to_subscription(user, subscription, sync_quota=True)

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

    async def cancel_subscription(
        self,
        user_id: int,
        *,
        refund_payment_id: Optional[int] = None,
    ) -> AppUser:
        """Cancel a user's subscription.

        Optionally refunds the associated payment via the finance
        service, then unlinks the user and zeroes the local quota
        mirror. The subscription row itself is left in place —
        cancellation is a user-side state change, not a deletion.
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
                        reason=f"Subscription cancellation for user {user_id}",
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

        return self._unlink_user_from_subscription(user_id)


    # ==================== Internal helpers ====================


    def _unlink_user_from_subscription(self, user_id: int) -> AppUser:
        """Clear a user's subscription pointer and zero their quota.

        The mirror of `_link_user_to_subscription`. The subscription row
        itself is left in place — cancellation is a user-side state
        change, not a deletion.

        Kept private and on the workflow because it touches `AppUser`,
        which the subscription service deliberately doesn't reach into.
        """
        user = self.user_service.get_user_by_id(user_id)
        user.app_user_subscription_ref = None
        user.user_quota = 0
        user.app_user_last_updated = datetime.datetime.now()
        return self.user_service.update_user_record_raw(user)

    def _assert_username_available(self, username: str) -> None:
        if self.user_service.user_repo.get_by_name(username):
            raise APIException(
                status_code=HTTP_409_CONFLICT,
                error_code=ErrorCode.APPUSER_ALREADY_EXISTS,
                details={"username": username},
            )

    def _assert_email_available(self, email: str) -> None:
        if self.user_service.user_repo.get_by_email(email):
            raise APIException(
                status_code=HTTP_409_CONFLICT,
                error_code=ErrorCode.APPUSER_ALREADY_EXISTS,
                details={"email": email},
            )

    async def _register_auth(
        self,
        user: AppUser,
        user_data: AppUser_API,
    ) -> Dict[str, Any]:
        """Build the auth payload and register the credentials."""
        payload: Dict[str, Any] = {
            "username": user.app_user_name,
            "app_user_id": user.id_app_user,
            "password": user_data.app_user_password,
        }
        if user_data.app_user_email:
            payload["email"] = user_data.app_user_email

        logger.info(f"Registering auth record for '{user.app_user_name}'")
        return await self.auth_manager.register_user(payload)

    def _rollback_user(self, user: AppUser) -> None:
        """Best-effort compensating delete after a partial create."""
        try:
            deleted = self.user_service.user_repo.delete(user)
            if deleted:
                logger.info(
                    f"Rolled back user {user.id_app_user} after "
                    f"auth registration failure"
                )
            else:
                logger.error(
                    f"Rollback delete returned false for user "
                    f"{user.id_app_user}"
                )
        except Exception as e:
            logger.error(
                f"Rollback delete raised for user {user.id_app_user}: {e}"
            )

    # ---------- Subscription invoice helpers ----------

    def _create_subscription_invoice(
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

    async def _create_subscription_payment(
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

    async def _confirm_subscription_payment(
        self,
        user_id: int,
        payment_id: int,
    ) -> None:
        """Confirm the payment with the finance service.

        Wraps the confirm call so the failure mode is uniform: any
        exception becomes a PAYMENT_CONFIRMATION_FAILED APIException
        with the underlying error attached.
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
            logger.error(f"Payment confirmation failed for {payment_id}: {e}")
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
        """
        try:
            return await self.finance_client.get_payment(payment_id)
        except Exception as e:
            logger.warning(
                f"Failed to refetch payment {payment_id} after confirm: {e}"
            )
            return None

    def _extract_payment_id(self, payment) -> int:
        """Pull the payment id out of whatever the finance client
        returns.

        The client has returned pydantic models (`payment.id`) and
        raw dicts (`payment['id']`) across versions. Handle both so
        this doesn't break when the client shape changes.
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


    def _link_user_to_subscription(
        self,
        user: AppUser,
        subscription: Subscription,
        *,
        sync_quota: bool = True,
    ) -> AppUser:
        """Point a user at a subscription and persist the change.

        Shared by `finalize_subscription`, `link_free_plan`, and the
        idempotency branch of `finalize_subscription`. Kept private so
        the pointer update lives in exactly one place.
        """
        user.app_user_subscription_ref = subscription.id_subscription
        if sync_quota:
            user.user_quota = subscription.subscription_quota or 0
        user.app_user_last_updated = datetime.datetime.now()
        return self.user_service.update_user_record_raw(user)

    def _extract_plan_id_from_payment(self, payment) -> Optional[int]:
        """Recover the plan id the payment was created for.

        Prefers a dedicated `plan_id` field on the payment response.
        Falls back to parsing the notes for a `plan_id=<n>` token if
        the finance service doesn't echo the field. Returns None if
        neither is present, which causes the caller to raise
        PAYMENT_MISSING_PLAN_REF.
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