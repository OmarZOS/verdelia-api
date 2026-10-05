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
    ):
        self.user_service = user_service or UserService()
        self.person_service = person_service or PersonService()
        self.auth_manager = auth_manager or AuthManager()

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
