# services/delivery_broker_service.py
"""
Service for delivery brokers.

Owns three things beyond the raw CRUD that the repository provides:

  * Broker creation, which is two writes — a wallet, then a broker
    row pointing at it. The two share a session so a failure on
    the second rolls back the first.

  * Owner resolution — given a wallet id, find the broker that owns
    it. This is the reverse lookup the wallet schema implies (the
    FK runs broker → wallet, not the other way), and it's what
    lets the wallet service answer "who owns this wallet?" without
    a wallet-side owner column.

  * Verification policy — marking a broker verified or unverified,
    with the reason logged. The rule of *who* can verify belongs
    to the caller; this service just records the decision.

Callers are other finance-server services and, eventually, an HTTP
router. The service takes a `Session` and shares it with its
caller, so a broker creation and the wallet creation that
accompanies it are in the same transaction.
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from core.exceptions.handler import APIException
from core.models.models import DeliveryBroker, Wallet
from repositories.delivery_broker_repository import (
    DeliveryBrokerRepository,
)

logger = logging.getLogger(__name__)


class DeliveryBrokerService:
    """Business logic for delivery brokers."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = DeliveryBrokerRepository()

    # ==================== Reads ====================

    def get_by_id(self, broker_id: int) -> DeliveryBroker:
        """Return the broker, or raise 404.

        Callers that want to handle the missing case themselves
        should use `find_by_id`.
        """
        broker = self.repo.get_by_id(broker_id)
        if broker is None:
            raise APIException(
                status_code=404,
                error_code="DELIVERY_BROKER_NOT_FOUND",
                message=f"Delivery broker {broker_id} not found",
                details={"broker_id": broker_id},
            )
        return broker

    def find_by_id(
        self, broker_id: int,
    ) -> Optional[DeliveryBroker]:
        """Return the broker, or None."""
        return self.repo.get_by_id(broker_id)

    def get_by_name(self, name: str) -> DeliveryBroker:
        """Return the broker with the given name, or raise 404."""
        broker = self.repo.get_by_name(name)
        if broker is None:
            raise APIException(
                status_code=404,
                error_code="DELIVERY_BROKER_NOT_FOUND",
                message=f"Delivery broker {name!r} not found",
                details={"name": name},
            )
        return broker

    def list_brokers(
        self,
        *,
        verified_only: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> List[DeliveryBroker]:
        """List brokers, optionally filtered to verified ones."""
        return self.repo.get_all(
            verified_only=verified_only,
            offset=offset,
            limit=limit,
        )

    def count(
        self,
        *,
        verified_only: bool = False,
    ) -> int:
        """Count brokers, optionally filtered to verified ones."""
        return self.repo.count(verified_only=verified_only)

    # ==================== Create ====================

    def create_broker(
        self,
        *,
        name: str,
        label: Optional[str] = None,
        logo_url: Optional[str] = None,
        image_url: Optional[str] = None,
        price_matrix: Optional[str] = None,
        home_delivery_price: Optional[float] = None,
        verified: bool = False,
        currency: str = "DZD",
    ) -> DeliveryBroker:
        """Create a broker and its wallet in one transaction.

        The wallet is created first, then the broker row points at
        it. Both share the caller's session — if the broker insert
        fails, the wallet insert rolls back with it.

        `name` is required and not enforced unique by the schema.
        The service checks for an existing broker by the same name
        and refuses to create a duplicate, because two brokers with
        the same name is a data-quality problem that no query can
        fix.

        `price_matrix` is expected to be a JSON string. The service
        doesn't parse or validate it; the caller owns the format.

        Returns the created `DeliveryBroker` row.
        """
        existing = self.repo.get_by_name(name)
        if existing is not None:
            raise APIException(
                status_code=409,
                error_code="DELIVERY_BROKER_ALREADY_EXISTS",
                message=(
                    f"Delivery broker {name!r} already exists"
                ),
                details={
                    "name": name,
                    "existing_id": existing.id_delivery_broker,
                },
            )

        wallet = Wallet(
            wallet_type= "business",
            wallet_currency= currency,
            wallet_balance= 0.0,
            wallet_status= "active",
        )

        broker = DeliveryBroker(
            delivery_broker_name=name,
            delivery_broker_label=label,
            delivery_broker_logo_url=logo_url,
            delivery_broker_image_url=image_url,
            delivery_broker_wallet=wallet,
            delivery_broker_price_matrix=price_matrix,
            verified_delivery_broker=1 if verified else 0,
            delivery_broker_home_delivery_price=home_delivery_price,
        )

        try:
            created = self.repo.create(broker)
        except Exception as e:
            # The session is shared with the caller, so a failed
            # insert here leaves the wallet insert in the same
            # transaction. The caller is expected to roll back;
            # this service doesn't own the transaction boundary.
            logger.error(
                f"Failed to create delivery broker {name!r}: {e}"
            )
            raise APIException(
                status_code=417,
                error_code="DELIVERY_BROKER_CREATE_FAILED",
                message=(
                    f"Failed to create delivery broker {name!r}"
                ),
                details={"name": name, "error": str(e)},
            )

        logger.info(
            f"Delivery broker created: id={created.id_delivery_broker} "
        )
        return created

    # ==================== Update ====================

    def update_broker(
        self,
        broker_id: int,
        *,
        name: Optional[str] = None,
        label: Optional[str] = None,
        logo_url: Optional[str] = None,
        image_url: Optional[str] = None,
        price_matrix: Optional[str] = None,
        home_delivery_price: Optional[float] = None,
    ) -> DeliveryBroker:
        """Update fields on an existing broker.

        Only fields the caller supplies are changed. Name changes
        are checked for uniqueness against the same rule the
        create path uses.
        """
        broker = self.get_by_id(broker_id)

        if name is not None and name != broker.delivery_broker_name:
            existing = self.repo.get_by_name(name)
            if (
                existing is not None
                and existing.id_delivery_broker != broker_id
            ):
                raise APIException(
                    status_code=409,
                    error_code="DELIVERY_BROKER_ALREADY_EXISTS",
                    message=(
                        f"Delivery broker {name!r} already exists"
                    ),
                    details={
                        "name": name,
                        "existing_id": existing.id_delivery_broker,
                    },
                )
            broker.delivery_broker_name = name

        if label is not None:
            broker.delivery_broker_label = label
        if logo_url is not None:
            broker.delivery_broker_logo_url = logo_url
        if image_url is not None:
            broker.delivery_broker_image_url = image_url
        if price_matrix is not None:
            broker.delivery_broker_price_matrix = price_matrix
        if home_delivery_price is not None:
            broker.delivery_broker_home_delivery_price = (
                home_delivery_price
            )

        try:
            updated = self.repo.update(broker)
        except Exception as e:
            logger.error(
                f"Failed to update delivery broker "
                f"{broker_id}: {e}"
            )
            raise APIException(
                status_code=417,
                error_code="DELIVERY_BROKER_UPDATE_FAILED",
                message=(
                    f"Failed to update delivery broker {broker_id}"
                ),
                details={"broker_id": broker_id, "error": str(e)},
            )

        logger.info(f"Delivery broker updated: id={broker_id}")
        return updated

    def set_verified(
        self,
        broker_id: int,
        verified: bool,
        *,
        actor_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> DeliveryBroker:
        """Mark a broker verified or unverified.

        `actor_id` and `reason` are for logging — the service
        doesn't enforce who can call this or why. That policy is
        the caller's; this method records the decision.
        """
        broker = self.get_by_id(broker_id)

        if bool(broker.verified_delivery_broker) == verified:
            # No-op. Return early so the log line is honest about
            # whether anything changed.
            return broker

        broker.verified_delivery_broker = 1 if verified else 0
        updated = self.repo.update(broker)

        logger.info(
            f"Delivery broker verification changed: "
            f"id={broker_id} verified={verified} "
            f"actor={actor_id} reason={reason!r}"
        )
        return updated

    # ==================== Delete ====================

    def delete_broker(self, broker_id: int) -> bool:
        """Delete a broker row.

        The wallet is left in place — the FK is not `ON DELETE
        CASCADE`, and wallets outlive the entities that own them.
        The broker's ledger history remains queryable by wallet id.

        Refuses when the broker has deliveries associated with it.
        The `delivery` table's FK is the check; if the broker has
        ever shipped anything, deleting it would orphan those
        records.
        """
        broker = self.get_by_id(broker_id)

        # Check for deliveries. If the broker has ever shipped,
        # refuse. The check is defensive — the caller can override
        # by handling the FK error, but a clean 409 is a better
        # failure mode than an integrity exception.
        from core.models.models import Delivery
        deliveries = self.session.query(Delivery).filter(
            Delivery.delivery_broker_id == broker_id
        ).count()

        if deliveries > 0:
            raise APIException(
                status_code=409,
                error_code="DELIVERY_BROKER_IN_USE",
                message=(
                    f"Delivery broker {broker_id} has "
                    f"{deliveries} deliveries and cannot be deleted"
                ),
                details={
                    "broker_id": broker_id,
                    "delivery_count": deliveries,
                },
            )

        try:
            ok = self.repo.delete(broker)
        except Exception as e:
            logger.error(
                f"Failed to delete delivery broker "
                f"{broker_id}: {e}"
            )
            raise APIException(
                status_code=417,
                error_code="DELIVERY_BROKER_DELETE_FAILED",
                message=(
                    f"Failed to delete delivery broker {broker_id}"
                ),
                details={"broker_id": broker_id, "error": str(e)},
            )

        logger.info(f"Delivery broker deleted: id={broker_id}")
        return ok