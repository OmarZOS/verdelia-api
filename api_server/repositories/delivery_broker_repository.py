# repositories/delivery_broker_repository.py
"""
Repository for `delivery_broker` rows.

Owns reads and writes for the `delivery_broker` table. The table
has one FK — `delivery_broker_wallet_id` — pointing at the wallet
that holds the broker's money. Reads are through `storage_broker`;
writes are through the same insertion helpers the rest of the
codebase uses.

No business logic. Callers that need "get or create a broker" or
"verify a broker" compose this repository with the services that
own those concerns.
"""

from typing import List, Optional

import storage.storage_broker as storage_broker
from core.models.models import DeliveryBroker


class DeliveryBrokerRepository:
    """Read and write access to `delivery_broker` rows."""

    # ==================== Reads ====================

    def get_by_id(
        self, broker_id: int,
    ) -> Optional[DeliveryBroker]:
        """Get a delivery broker by its primary key, with the
        broker's wallet eagerly loaded."""
        records = storage_broker.get(
            DeliveryBroker,
            {DeliveryBroker.id_delivery_broker: broker_id},
            [],
            [DeliveryBroker.delivery_broker_wallet],
        )
        return records[0] if records else None

    def get_by_wallet_id(
        self, wallet_id: int,
    ) -> Optional[DeliveryBroker]:
        """Find the broker whose wallet is `wallet_id`, if any.

        The wallet row has no owner column — the FK runs from the
        broker to the wallet, not the other way. This lookup is how
        "which broker owns this wallet?" is answered.

        Returns None when no broker points at the wallet, or when
        the wallet id doesn't exist.
        """
        records = storage_broker.get(
            DeliveryBroker,
            {DeliveryBroker.delivery_broker_wallet_id: wallet_id},
            [],
            [DeliveryBroker.delivery_broker_wallet],
        )
        return records[0] if records else None

    def get_by_name(
        self, name: str,
    ) -> Optional[DeliveryBroker]:
        """Find a broker by name.

        Names aren't unique in the schema, so this returns the
        first match. Callers that need strict uniqueness should
        check the model or add a constraint.
        """
        records = storage_broker.get(
            DeliveryBroker,
            {DeliveryBroker.delivery_broker_name: name},
            [],
        )
        return records[0] if records else None

    def get_all(
        self,
        *,
        verified_only: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> List[DeliveryBroker]:
        """List brokers, optionally filtered to verified ones.

        `verified_delivery_broker` is a TINYINT; the model maps it
        to a boolean. The filter passes `1` for the SQL comparison
        because that's the column's storage type.
        """
        conditions: dict = {}
        if verified_only:
            conditions[DeliveryBroker.verified_delivery_broker] = 1

        return storage_broker.get(
            DeliveryBroker,
            conditions,
            [],
            [DeliveryBroker.delivery_broker_wallet],
            offset,
            limit,
        )

    def count(
        self,
        *,
        verified_only: bool = False,
    ) -> int:
        """Count brokers, optionally filtered to verified ones."""
        conditions: dict = {}
        if verified_only:
            conditions[DeliveryBroker.verified_delivery_broker] = 1
        return storage_broker.count(DeliveryBroker, conditions)

    # ==================== Writes ====================

    def create(self, broker: DeliveryBroker) -> DeliveryBroker:
        """Insert a new broker row."""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(broker)

    def update(self, broker: DeliveryBroker) -> DeliveryBroker:
        """Update an existing broker row.

        `features.insertion.update_record_in_api` writes every
        column the ORM object exposes, so callers should mutate the
        object they got from `get_by_id` and pass it back. Partial
        updates come from mutating only the fields that changed.
        """
        from features.insertion import update_record_in_api
        return update_record_in_api(broker)

    def delete(self, broker: DeliveryBroker) -> bool:
        """Delete a broker row.

        The FK to `wallet` is not `ON DELETE CASCADE`, so deleting
        a broker leaves its wallet in place. That's the intended
        behavior — wallets outlive the entities that own them, and
        the ledger references the wallet, not the broker.
        """
        from features.insertion import delete_record_from_api
        return delete_record_from_api(broker)

    # ==================== Convenience ====================

    def set_wallet(
        self,
        broker: DeliveryBroker,
        wallet_id: int,
    ) -> DeliveryBroker:
        """Point a broker at a wallet and persist the change.

        Not a foreign-key enforcement point — the DB will reject a
        wallet id that doesn't exist. This method just exists so
        callers don't have to remember that the column name is
        `delivery_broker_wallet_id`.
        """
        broker.delivery_broker_wallet_id = wallet_id
        return self.update(broker)

    def set_verified(
        self,
        broker: DeliveryBroker,
        verified: bool,
    ) -> DeliveryBroker:
        """Toggle the broker's verification flag and persist."""
        broker.verified_delivery_broker = 1 if verified else 0
        return self.update(broker)