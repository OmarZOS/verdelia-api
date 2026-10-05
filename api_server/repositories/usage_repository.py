# repositories/usage_repository.py
"""
Repository for `subscription_usage` rows.

Takes primitives (ints, dates, strings) and returns primitives
(dicts, ints, None). No ORM objects cross this boundary — the
service layer is the only thing that knows about `ResourceCode`.

Each row covers one billing period. Counters are monotonic within
a period and reset when a new period starts.
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import storage.storage_broker as storage_broker
from core.models.models import AppUser, SubscriptionUsage


# The four counters on `subscription_usage`.
#
# This set is the repository's contract: `increment` and
# `increment_many` will only write these columns, and `_to_dict`
# only exports them. Adding a counter is a three-file change:
#
#   1. a new column on the `SubscriptionUsage` model
#   2. a new entry here
#   3. a new entry in `_RESOURCE_TO_COLUMN` in `services/usage_service`
#
# The set is public (no underscore-prefix-import restriction) so the
# service can assert that its own map only references columns that
# exist. That assertion is what prevents the drift that broke the
# previous version.
COUNTER_COLUMNS = frozenset({
    "ai_credits_used",
    "ai_product_searches",
    "ai_auto_fills",
    "products_created",
})


class UsageRepository:
    """Read and write access to `subscription_usage` rows."""

    # ==================== Reads ====================

    def get_by_id(self, usage_id: int) -> Optional[Dict[str, Any]]:
        """Get a usage row by primary key, as a plain dict."""
        records = storage_broker.get(
            SubscriptionUsage,
            {SubscriptionUsage.id_subscription_usage: usage_id},
            [],
        )
        return _to_dict(records[0]) if records else None

    def get_for_period(
        self, subscription_id: int, period_start: date
    ) -> Optional[Dict[str, Any]]:
        """Get the usage row for a specific period, if it exists.

        Returns None when no row has been created for this period —
        a normal state for a subscription whose first period hasn't
        seen any activity yet.
        """
        records = storage_broker.get(
            SubscriptionUsage,
            {
                SubscriptionUsage.subscription_id: subscription_id,
                SubscriptionUsage.period_start: period_start,
            },
            [],
        )
        return _to_dict(records[0]) if records else None

    def get_current(
        self, subscription_id: int, on_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """The usage row whose period contains `on_date` (default:
        today).

        Returns None when no row matches. Callers that need a row to
        exist should use `ensure_current`.
        """
        today = on_date or date.today()
        records = storage_broker.get(
            SubscriptionUsage,
            {SubscriptionUsage.subscription_id: subscription_id},
            [],
        )
        # Filter in Python: storage_broker's condition dict is
        # equality-only, so range queries happen here. The row count
        # per subscription is bounded by the subscription's lifetime
        # divided by the period length — for a monthly period over
        # five years, that's 60 rows. Acceptable to scan.
        for row in records:
            if _period_contains(row, today):
                return _to_dict(row)
        return None

    def list_for_subscription(
        self,
        subscription_id: int,
        limit: int = 12,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Recent periods for a subscription, newest first."""
        records = storage_broker.get(
            SubscriptionUsage,
            {SubscriptionUsage.subscription_id: subscription_id},
            [],
            limit=limit,
            offset=offset,
        )
        rows = [_to_dict(r) for r in records]
        rows.sort(key=lambda r: r["period_start"], reverse=True)
        return rows

    # ==================== Writes ====================

    def create(
        self,
        subscription_id: int,
        period_start: date,
        period_end: date,
    ) -> Dict[str, Any]:
        """Create a zeroed usage row for a period.

        Raises if a row already exists for `(subscription_id,
        period_start)` and the database enforces uniqueness. Callers
        that want "create or return existing" should use
        `ensure_current`.
        """
        from features.insertion import insert_or_complete_or_raise

        row = SubscriptionUsage(
            subscription_id=subscription_id,
            period_start=period_start,
            period_end=period_end,
            ai_credits_used=0,
            ai_product_searches=0,
            ai_auto_fills=0,
            products_created=0,
        )
        created = insert_or_complete_or_raise(row)
        return _to_dict(created)

    def ensure_current(
        self,
        subscription_id: int,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        on_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Return the usage row for the current period, creating one
        if it doesn't exist.

        `period_start` / `period_end` are used only when creating a
        new row. When omitted, the new row spans the current calendar
        month.

        The creation is not transactional with the read. Two
        concurrent callers can both see "no row" and both attempt to
        insert. When the database enforces a unique index on
        `(subscription_id, period_start)`, the second insert raises
        and this method retries the read. Without that index, this
        method can create duplicate rows — see the note at the
        bottom of this file.
        """
        existing = self.get_current(subscription_id, on_date=on_date)
        if existing is not None:
            return existing

        if period_start is None or period_end is None:
            period_start, period_end = _month_bounds(
                on_date or date.today()
            )

        try:
            return self.create(subscription_id, period_start, period_end)
        except Exception:
            # A concurrent caller won the race. Re-read and return
            # their row. If the re-read still finds nothing, the
            # exception wasn't a uniqueness collision — re-raise.
            reloaded = self.get_for_period(subscription_id, period_start)
            if reloaded is None:
                raise
            return reloaded

    def increment(
        self,
        subscription_id: int,
        column: str,
        amount: int = 1,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Add `amount` to `column` on the current period's row.

        `column` must be one of `COUNTER_COLUMNS`. Raises ValueError
        otherwise — that's a programming error at the service layer,
        not a runtime condition.

        Does not enforce caps. The caller is responsible for the
        corresponding limit check before invoking this.
        """
        if column not in COUNTER_COLUMNS:
            raise ValueError(
                f"{column!r} is not a counter column; "
                f"expected one of {sorted(COUNTER_COLUMNS)}"
            )

        row = self.ensure_current(
            subscription_id,
            period_start=period_start,
            period_end=period_end,
        )

        # Read-modify-write on the ORM object, then persist via the
        # same insertion helper the rest of the codebase uses.
        from features.insertion import update_record_in_api

        record = _load_orm(subscription_id, row["period_start"])
        current = getattr(record, column) or 0
        setattr(record, column, current + amount)
        updated = update_record_in_api(record)
        return _to_dict(updated)

    def increment_many(
        self,
        subscription_id: int,
        deltas: Dict[str, int],
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Add multiple counters in one round-trip.

        `deltas` maps column name → amount. Columns not in the dict
        are left unchanged. Zero-valued entries are skipped.
        """
        unknown = set(deltas) - COUNTER_COLUMNS
        if unknown:
            raise ValueError(
                f"Unknown counter columns: {sorted(unknown)}"
            )

        row = self.ensure_current(
            subscription_id,
            period_start=period_start,
            period_end=period_end,
        )

        from features.insertion import update_record_in_api

        record = _load_orm(subscription_id, row["period_start"])
        for column, amount in deltas.items():
            if amount == 0:
                continue
            current = getattr(record, column) or 0
            setattr(record, column, current + amount)
        updated = update_record_in_api(record)
        return _to_dict(updated)

        # ==================== User-scoped resolution ====================

    def _subscription_id_for_user(self, user_id: int) -> Optional[int]:
        """Resolve a user's subscription id, or None.

        Reads `AppUser.app_user_subscription_ref`, which is a single
        FK — so a user points at exactly one subscription, and this
        returns at most one row.
        """
        users = storage_broker.get(
            AppUser,
            {AppUser.id_app_user: user_id},
            [],
        )
        if not users:
            return None
        return users[0].app_user_subscription_ref

    # ==================== User-scoped reads ====================

    def get_current_for_user(
        self, user_id: int, on_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """The current period's row for the subscription a user
        points at. Returns None when the user has no subscription or
        no usage row yet."""
        sub_id = self._subscription_id_for_user(user_id)
        if sub_id is None:
            return None
        return self.get_current(sub_id, on_date=on_date)

    # ==================== Reduce ====================

    def decrement(
        self,
        subscription_id: int,
        column: str,
        amount: int = 1,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        floor: int = 0,
    ) -> Dict[str, Any]:
        """Subtract `amount` from `column` on the current period's row.

        Clamps at `floor` (default 0). If the current value is
        already at or below `floor`, this is a no-op and returns the
        row unchanged. Callers reducing after a failed operation
        shouldn't have to check the current value first — a
        refund-below-zero is not an error, it's a sign the refund
        was already applied.

        Does not touch `period_start` or `period_end`. Does not
        create a new period row if none exists — reducing usage for
        a period that has no row is a no-op, since the implicit
        value is already 0.
        """
        if column not in COUNTER_COLUMNS:
            raise ValueError(
                f"{column!r} is not a counter column; "
                f"expected one of {sorted(COUNTER_COLUMNS)}"
            )
        if amount < 0:
            raise ValueError(
                f"decrement amount must be non-negative, got {amount}"
            )

        existing = self.get_for_period(
            subscription_id,
            period_start or date.today(),
        ) if period_start else self.get_current(subscription_id)

        if existing is None:
            # No row for this period means the counter is implicitly
            # 0. Reducing 0 is a no-op — return a synthetic row so
            # the caller's shape is consistent.
            if period_start is None:
                return self.ensure_current(subscription_id)
            return {
                "subscription_id": subscription_id,
                "period_start": period_start,
                "period_end": period_end,
                column: 0,
                "created_at": None,
                "updated_at": None,
            }

        from features.insertion import update_record_in_api

        record = _load_orm(subscription_id, existing["period_start"])
        current = getattr(record, column) or 0
        new_value = max(floor, current - amount)

        if new_value == current:
            # Nothing to write. Return the row as-is so callers can
            # read the counter without a second fetch.
            return existing

        setattr(record, column, new_value)
        updated = update_record_in_api(record)
        return _to_dict(updated)

    def decrement_many(
        self,
        subscription_id: int,
        deltas: Dict[str, int],
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        floor: int = 0,
    ) -> Dict[str, Any]:
        """Subtract multiple counters in one write.

        `deltas` maps column name → amount to subtract. Zero-valued
        entries are skipped. All counters clamp at `floor`.
        """
        unknown = set(deltas) - COUNTER_COLUMNS
        if unknown:
            raise ValueError(
                f"Unknown counter columns: {sorted(unknown)}"
            )

        for column, amount in deltas.items():
            if amount < 0:
                raise ValueError(
                    f"decrement amount for {column!r} must be "
                    f"non-negative, got {amount}"
                )

        existing = self.get_current(subscription_id)
        if existing is None:
            return self.ensure_current(subscription_id)

        from features.insertion import update_record_in_api

        record = _load_orm(subscription_id, existing["period_start"])
        for column, amount in deltas.items():
            if amount == 0:
                continue
            current = getattr(record, column) or 0
            setattr(record, column, max(floor, current - amount))
        updated = update_record_in_api(record)
        return _to_dict(updated)

    # ==================== User-scoped writes ====================

    def add_for_user(
        self,
        user_id: int,
        column: str,
        amount: int = 1,
    ) -> Dict[str, Any]:
        """Add `amount` to `column` on the user's current period.

        Convenience wrapper over `increment` that resolves the
        subscription from the user id. Raises LookupError when the
        user has no subscription — unlike reads, which return None,
        a write with no target is a caller error.
        """
        sub_id = self._subscription_id_for_user(user_id)
        if sub_id is None:
            raise LookupError(
                f"User {user_id} has no subscription to record usage "
                f"against"
            )
        return self.increment(sub_id, column=column, amount=amount)

    def reduce_for_user(
        self,
        user_id: int,
        column: str,
        amount: int = 1,
        floor: int = 0,
    ) -> Dict[str, Any]:
        """Subtract `amount` from `column` on the user's current
        period. Convenience wrapper over `decrement`."""
        sub_id = self._subscription_id_for_user(user_id)
        if sub_id is None:
            raise LookupError(
                f"User {user_id} has no subscription to reduce usage "
                f"against"
            )
        return self.decrement(sub_id, column=column, amount=amount, floor=floor)


# ==================== Helpers ====================

def _to_dict(row: Any) -> Dict[str, Any]:
    """Convert a SubscriptionUsage ORM row to a plain dict.

    Explicit field list rather than `row.__dict__` so the
    repository's contract is visible in one place and doesn't leak
    SQLAlchemy internals.
    """
    return {
        "id_subscription_usage": row.id_subscription_usage,
        "subscription_id": row.subscription_id,
        "period_start": row.period_start,
        "period_end": row.period_end,
        "ai_credits_used": row.ai_credits_used or 0,
        "ai_product_searches": row.ai_product_searches or 0,
        "ai_auto_fills": row.ai_auto_fills or 0,
        "products_created": row.products_created or 0,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _load_orm(subscription_id: int, period_start: date):
    """Load the ORM row by its natural key, for mutation.

    The repository doesn't cache ORM objects across calls, so
    `increment` and `increment_many` re-load the row they just
    ensured. That's one extra query per write; acceptable at the
    call rates this sees.
    """
    records = storage_broker.get(
        SubscriptionUsage,
        {
            SubscriptionUsage.subscription_id: subscription_id,
            SubscriptionUsage.period_start: period_start,
        },
        [],
    )
    if not records:
        raise LookupError(
            f"Usage row vanished: subscription_id={subscription_id}, "
            f"period_start={period_start}"
        )
    return records[0]


def _period_contains(row: Any, day: date) -> bool:
    start = row.period_start
    end = row.period_end
    if start is None or end is None:
        return False
    return start <= day <= end


def _month_bounds(today: date) -> tuple[date, date]:
    first = today.replace(day=1)
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1)
    else:
        next_first = first.replace(month=first.month + 1)
    last = next_first - timedelta(days=1)
    return first, last