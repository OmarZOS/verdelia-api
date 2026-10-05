# repositories/subscription_repository.py (complete)
from typing import Optional, List
from core.models.models import PlanFeature, Subscription, Plan, AppUser
import storage.storage_broker as storage_broker
from repositories.cache.plan_cache import plan_cache

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
        """
        Get plan by ID.

        Not served from the cache. The cache holds the *catalogue*
        (all plans under a filter); a single-plan lookup is a
        different, cheap query and caching it would require keeping
        two structures in sync. If this becomes hot, cache it
        separately.
        """
        records = storage_broker.get(
            Plan,
            {Plan.id_plan: plan_id},
            [],
        )
        return records[0] if records else None

    def get_plan_by_name(self, plan_name: str) -> Optional[Plan]:
        """Get plan by name. Same rationale as get_plan_by_id."""
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
        force_refresh: bool = False,
    ) -> List[Plan]:
        """
        Get all plans, optionally filtered by type and/or billing cycle.

        Served from the process-local cache when populated. The cache
        is invalidated by every write path in this repository
        (create_plan, update_plan, delete_plan) and can be force-
        refreshed by passing `force_refresh=True` — for instance from
        an admin endpoint or a test fixture.

        The eager-load set is the reason this query is expensive: it
        pulls every plan's limits, features, feature names, and the
        plan's own naming row. The cache is keyed on the filter tuple,
        so a request for `(individual, monthly)` does not evict the
        `(None, None)` entry.
        """
        if not force_refresh:
            cached = plan_cache.get(plan_type, billing_cycle)
            if cached is not None:
                return cached

        # Snapshot the generation *before* the query so a concurrent
        # invalidation is detected when we try to store the result.
        generation = plan_cache.generation()

        conditions = {}
        if plan_type:
            conditions[Plan.plan_type] = plan_type
        if billing_cycle:
            conditions[Plan.billing_cycle] = billing_cycle

        plans = storage_broker.get(
            Plan,
            conditions,
            [],
            [
                Plan.plan_limit,
                {Plan.plan_feature: [{PlanFeature.feature_naming: []}]},
                {Plan.plan_naming: []},
            ],
            0,
            100,
        )

        # Store under the caller's filter. If an invalidation raced us
        # to the write, discard — the newer generation will refetch.
        plan_cache.put(plan_type, billing_cycle, plans, generation)
        return plans

    # ==================== Plan writes (invalidate) ====================

    def create_plan(self, plan: Plan) -> Plan:
        """Create a plan record. Invalidates the catalogue cache."""
        from features.insertion import insert_or_complete_or_raise
        created = insert_or_complete_or_raise(plan)
        plan_cache.invalidate()
        return created

    def update_plan(self, plan: Plan) -> Plan:
        """Update a plan record. Invalidates the catalogue cache."""
        from features.insertion import update_record_in_api
        updated = update_record_in_api(plan)
        plan_cache.invalidate()
        return updated

    def delete_plan(self, plan: Plan) -> bool:
        """Delete a plan record. Invalidates the catalogue cache."""
        from features.insertion import delete_record_from_api
        ok = delete_record_from_api(plan)
        if ok:
            plan_cache.invalidate()
        return ok

    # ==================== Cache helpers (optional) ====================

    def invalidate_plan_cache(self) -> None:
        """
        Drop every cached catalogue entry.

        Call this from any code path that mutates the plan tables
        *outside* the three write methods above — a raw SQL admin
        script, a bulk import, a background job that adjusts prices.
        """
        plan_cache.invalidate()