# repositories/subscription_repository.py (complete)
from typing import Optional, List
from core.models.models import Subscription, Plan, AppUser
import storage.storage_broker as storage_broker


class SubscriptionRepository:
    """Repository for subscription and plan database operations"""

    # ==================== Subscription Operations ====================

    def get_by_id(self, subscription_id: int) -> Optional[Subscription]:
        """Get subscription by ID, with its plan eagerly loaded."""
        records = storage_broker.get(
            Subscription,
            {Subscription.id_subscription: subscription_id},
            [],
            [Subscription.subscription_plan],
        )
        return records[0] if records else None

    def get_by_user_id(self, user_id: int) -> Optional[Subscription]:
        """Get the subscription a user currently points at, or None.

        The link is via `AppUser.app_user_subscription_ref`, which is a
        single FK — not a history table. So this returns at most one
        row, and only when the user has an active pointer.
        """
        users = storage_broker.get(
            AppUser,
            {AppUser.id_app_user: user_id},
            [],
            [AppUser.subscription],
        )
        if not users:
            return None
        return users[0].subscription

    def get_by_payment_id(self, payment_id: int) -> Optional[Subscription]:
        """Get the subscription created by a specific payment, if any."""
        records = storage_broker.get(
            Subscription,
            {Subscription.subscription_payment_id: payment_id},
            [],
            [Subscription.subscription_plan],
        )
        return records[0] if records else None

    def get_by_plan_id(self, plan_id: int) -> List[Subscription]:
        """Get all subscriptions on a given plan."""
        return storage_broker.get(
            Subscription,
            {Subscription.subscription_plan_id: plan_id},
            [],
            [Subscription.subscription_plan],
        )

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Subscription]:
        """Get all subscriptions with their plans, paginated."""
        return storage_broker.get(
            Subscription,
            {},
            [Subscription.subscription_plan],
            limit=limit,
            offset=offset,
        )

    def create(self, subscription: Subscription) -> Subscription:
        """Create a subscription record."""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(subscription)

    def update(self, subscription: Subscription) -> Subscription:
        """Update a subscription record."""
        from features.insertion import update_record_in_api
        return update_record_in_api(subscription)

    def delete(self, subscription: Subscription) -> bool:
        """Delete a subscription record."""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(subscription)

    # ==================== Plan Operations ====================

    def get_plan_by_id(self, plan_id: int) -> Optional[Plan]:
        """Get plan by ID."""
        records = storage_broker.get(
            Plan,
            {Plan.id_plan: plan_id},
            [],
        )
        return records[0] if records else None

    def get_plan_by_name(self, plan_name: str) -> Optional[Plan]:
        """Get plan by name."""
        records = storage_broker.get(
            Plan,
            {Plan.plan_name: plan_name},
            [],
        )
        return records[0] if records else None

    def get_all_plans(
        self,
        plan_type: Optional[str] = None,
        billing_cycle: Optional[str] = None,
    ) -> List[Plan]:
        """Get all plans, optionally filtered by type and/or billing cycle."""
        conditions = {}
        if plan_type:
            conditions[Plan.plan_type] = plan_type
        if billing_cycle:
            conditions[Plan.billing_cycle] = billing_cycle

        return storage_broker.get(Plan, conditions, [])

    def create_plan(self, plan: Plan) -> Plan:
        """Create a plan record."""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(plan)

    def update_plan(self, plan: Plan) -> Plan:
        """Update a plan record."""
        from features.insertion import update_record_in_api
        return update_record_in_api(plan)

    def delete_plan(self, plan: Plan) -> bool:
        """Delete a plan record."""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(plan)