# storage/seeds/system_user.py
"""
The system user.

Every deployment has exactly one. It owns nothing in the domain and
acts as the principal for background jobs, admin scripts, and seed
data. Its credentials come from the environment; if they aren't set,
sensible DEV defaults are used, but production deployments must
provide them.

The creation is idempotent: running the seed twice does not create a
second system user, and does not modify the first except to
re-assert the role and password hash.

Public API:

    get_system_user()            -> Optional[AppUser]
    ensure_system_user()         -> AppUser
    get_system_user_id()         -> int

`ensure_system_user` is what the seed calls. `get_system_user_id`
is what domain seeders call when they need an owner id.
"""

import logging
import os
from typing import Optional

from core.models.api_models import AppUserType
from core.models.models import AppUser
from services.user_service import UserService
from storage.storage_broker import get as storage_get

logger = logging.getLogger(__name__)


# The system user's well-known username. Anything that needs to
# identify it by name (audit logs, "is this the system?" checks)
# uses this constant rather than a magic string.
SYSTEM_USERNAME = "system"

# Environment variable names. The seed reads these and falls back
# to the DEV defaults only when they're absent.
_ENV_USERNAME = "DEFAULT_ADMIN_USERNAME"
_ENV_PASSWORD = "DEFAULT_ADMIN_PASSWORD"
_ENV_EMAIL = "SYSTEM_USER_EMAIL"

# DEV defaults. Not secrets — just predictable values for local
# development. A production deployment must set the env vars.
_DEV_DEFAULT_PASSWORD = "SystemUser123!@#"
_DEV_DEFAULT_EMAIL = "system@verdelia.local"


def get_system_user() -> Optional[AppUser]:
    """Return the system user row, or None when it doesn't exist."""
    username = _system_username()
    users = storage_get(
        AppUser,
        {AppUser.app_user_name: username},
        [],
    )
    return users[0] if users else None


def get_system_user_id() -> int:
    """Return the system user's id.

    Raises LookupError when the system user doesn't exist — a caller
    that needs the id cannot proceed without it, and fabricating a
    fallback (0, 1, or the first user) would hide the fact that the
    seed never ran.
    """
    user = get_system_user()
    if user is None:
        raise LookupError(
            "System user does not exist. Run `python -m storage.seed` "
            "or call `ensure_system_user()` first."
        )
    return user.id_app_user


def ensure_system_user() -> AppUser:
    """Create the system user if it doesn't exist, or return the
    existing one.

    Idempotent: the second call is a read. The function never
    modifies an existing user's roles or password — if you need to
    rotate credentials, do it explicitly through the user service,
    not as a side effect of the seed.
    """
    existing = get_system_user()
    if existing is not None:
        logger.info(
            f"System user already exists: "
            f"id={existing.id_app_user} name={existing.app_user_name}"
        )
        return existing

    logger.info("Creating system user")

    username = _system_username()
    password = _system_password()
    email = _system_email()

    user_service = UserService()

    # Build the AppUser row directly through the service so the
    # creation path matches how any other user is created — the
    # same validation, the same FK setup, the same defaults.
    from core.models.api_models import AppUser_API

    user_api = AppUser_API(
        app_user_name=username,
        app_user_password=password,
        app_user_email=email,
        app_user_type=AppUserType.PROVIDER,
        app_user_image_url=None,
    )

    created = user_service.create_user_record(
        user_data=user_api,
        person_data=None,
        location_data=None,
        wallet_balance=100000000.0,
        wallet_type = "system"
    )

    logger.info(
        f"System user created: id={created.id_app_user} "
        f"name={created.app_user_name}"
    )
    return created


# ── Internal ──────────────────────────────────────────────────────

def _system_username() -> str:
    return os.getenv(_ENV_USERNAME)


def _system_password() -> str:
    value = os.getenv(_ENV_PASSWORD)
    if value:
        return value

    # In DEV, fall back to a known password. In production, refuse.
    from config import settings
    if settings.DEBUG == "PRODUCTION":
        raise RuntimeError(
            f"{_ENV_PASSWORD} must be set in production. The system "
            f"user's credentials cannot default."
        )
    return _DEV_DEFAULT_PASSWORD


def _system_email() -> str:
    return os.getenv(_ENV_EMAIL, _DEV_DEFAULT_EMAIL)