# storage/seeds/plan.py
from storage.seeds._naming import first

"""
Plan seed module using the storage broker.

Each plan is a self-contained row: name, price, billing cycle, and
type. No naming contribution because Plan has no translatable
columns — the plan name is a single English string and that's what
the schema carries.

Seeding is idempotent: re-running inserts nothing. The lookup anchor
is `plan_name`, which the schema treats as effectively unique for
seeding purposes.
"""

import logging
from typing import Any, Dict, List, Optional

from storage.storage_broker import insert_record, get, session_scope
from core.models import models

from core.logging_config import get_logger

logger = get_logger(__name__)


# ==================== Seed Data ====================

# `plan_name` is the lookup anchor. `plan_price` is a decimal in the
# schema; pass it as a float here and SQLAlchemy coerces.
# `billing_cycle` must be one of: monthly, semestrial, yearly, lifetime.
# `plan_type` must be one of: individual, organization.
SEED_PLANS = [

    # ==========================================================
    # INDIVIDUAL
    # ==========================================================

    {
        "plan_name": "Free",
        "plan_price": 0.00,
        "billing_cycle": "lifetime",
        "plan_type": "individual",
    },

    {
        "plan_name": "Starter Monthly",
        "plan_price": 990.00,
        "billing_cycle": "monthly",
        "plan_type": "individual",
    },

    {
        "plan_name": "Starter Yearly",
        "plan_price": 9900.00,
        "billing_cycle": "yearly",
        "plan_type": "individual",
    },

    {
        "plan_name": "Pro Monthly",
        "plan_price": 2490.00,
        "billing_cycle": "monthly",
        "plan_type": "individual",
    },

    {
        "plan_name": "Pro Semestrial",
        "plan_price": 12900.00,
        "billing_cycle": "semestrial",
        "plan_type": "individual",
    },

    {
        "plan_name": "Pro Yearly",
        "plan_price": 24900.00,
        "billing_cycle": "yearly",
        "plan_type": "individual",
    },

    # ==========================================================
    # BUSINESS
    # ==========================================================

    {
        "plan_name": "Business Starter",
        "plan_price": 9900.00,
        "billing_cycle": "monthly",
        "plan_type": "organization",
    },

    {
        "plan_name": "Business Pro",
        "plan_price": 24900.00,
        "billing_cycle": "monthly",
        "plan_type": "organization",
    },

    {
        "plan_name": "Business Yearly",
        "plan_price": 249000.00,
        "billing_cycle": "yearly",
        "plan_type": "organization",
    },

    # ==========================================================
    # ENTERPRISE
    # ==========================================================

    {
        "plan_name": "Enterprise",
        "plan_price": 49900.00,
        "billing_cycle": "monthly",
        "plan_type": "organization",
    },

    {
        "plan_name": "Enterprise Yearly",
        "plan_price": 499000.00,
        "billing_cycle": "yearly",
        "plan_type": "organization",
    },
]


# ==================== Helpers ====================

def _get_or_create_plan(
    *,
    plan_name: str,
    plan_price: float,
    billing_cycle: str,
    plan_type: str,
) -> Optional[Any]:
    """
    Return the existing Plan for the given name, or insert a new one.
    """
    existing = first(
        get(
            table=models.Plan,
            conditions={"plan_name": plan_name},
        )
    )
    if existing:
        return existing

    plan = models.Plan(
        plan_name=plan_name,
        plan_price=plan_price,
        billing_cycle=billing_cycle,
        plan_type=plan_type,
    )
    return first(insert_record(plan))


# ==================== Seeding Functions ====================

def seed_plans() -> int:
    """
    Seed the standard plans.

    Returns:
        Number of plans inserted (existing rows are not counted).
    """
    count_inserted = 0

    for entry in SEED_PLANS:
        plan_name = entry["plan_name"]

        existing = first(
            get(
                table=models.Plan,
                conditions={"plan_name": plan_name},
            )
        )
        if existing:
            # Backfill anything that drifted — price changes, or a
            # cycle/type that was recorded wrong. Name is the anchor,
            # so we don't touch it.
            changed = False
            if existing.plan_price != entry["plan_price"]:
                existing.plan_price = entry["plan_price"]
                changed = True
            if existing.billing_cycle != entry["billing_cycle"]:
                existing.billing_cycle = entry["billing_cycle"]
                changed = True
            if existing.plan_type != entry["plan_type"]:
                existing.plan_type = entry["plan_type"]
                changed = True
            if changed:
                logger.debug("Backfilled plan %r", plan_name)
            continue

        plan = _get_or_create_plan(
            plan_name=plan_name,
            plan_price=entry["plan_price"],
            billing_cycle=entry["billing_cycle"],
            plan_type=entry["plan_type"],
        )
        if plan:
            count_inserted += 1
            logger.debug("Seeded plan: %s", plan_name)

    logger.info("Seeded %d new plans", count_inserted)
    return count_inserted


def seed_plan(plan_data: Dict[str, Any]) -> bool:
    """
    Seed a single plan.

    `plan_data` must carry `plan_name`. `plan_price`, `billing_cycle`,
    and `plan_type` default to 0.00, `monthly`, and `individual`.

    Returns True if inserted, False if the plan already existed.
    """
    plan_name = plan_data.get("plan_name")
    if not plan_name:
        logger.warning("seed_plan called with no name: %r", plan_data)
        return False

    existing = first(
        get(
            table=models.Plan,
            conditions={"plan_name": plan_name},
        )
    )
    if existing:
        logger.debug("Plan already exists: %s", plan_name)
        return False

    plan = _get_or_create_plan(
        plan_name=plan_name,
        plan_price=plan_data.get("plan_price", 0.00),
        billing_cycle=plan_data.get("billing_cycle", "monthly"),
        plan_type=plan_data.get("plan_type", "individual"),
    )
    if plan:
        logger.debug("Seeded plan: %s", plan_name)
        return True
    return False


def seed_plans_from_list(plans: List[Dict[str, Any]]) -> int:
    """
    Seed plans from a custom list. Each entry must carry `plan_name`.

    Returns:
        Number of plans inserted.
    """
    count_inserted = 0

    for entry in plans:
        plan_name = entry.get("plan_name")
        if not plan_name:
            logger.warning("Skipping entry with no name: %r", entry)
            continue

        existing = first(
            get(
                table=models.Plan,
                conditions={"plan_name": plan_name},
            )
        )
        if existing:
            continue

        plan = _get_or_create_plan(
            plan_name=plan_name,
            plan_price=entry.get("plan_price", 0.00),
            billing_cycle=entry.get("billing_cycle", "monthly"),
            plan_type=entry.get("plan_type", "individual"),
        )
        if plan:
            count_inserted += 1
            logger.debug("Seeded plan: %s", plan_name)

    logger.info("Seeded %d plans from custom list", count_inserted)
    return count_inserted


# ==================== Utility Functions ====================

def get_all_seeded_plans() -> List[Dict[str, Any]]:
    """
    Return every plan as a dict, ordered by plan type then price.
    """
    with session_scope() as session:
        rows = (
            session.query(models.Plan)
            .order_by(models.Plan.plan_type, models.Plan.plan_price)
            .all()
        )
        return [
            {
                "id": p.id_plan,
                "name": p.plan_name,
                "price": float(p.plan_price) if p.plan_price is not None else 0.0,
                "billing_cycle": p.billing_cycle,
                "plan_type": p.plan_type,
            }
            for p in rows
        ]


def plan_exists(plan_name: str) -> bool:
    """Check whether a plan with the given name exists."""
    existing = first(
        get(
            table=models.Plan,
            conditions={"plan_name": plan_name},
        )
    )
    return bool(existing)


def get_plan_by_name(plan_name: str) -> Optional[models.Plan]:
    """Return a plan by name, or None."""
    return first(
        get(
            table=models.Plan,
            conditions={"plan_name": plan_name},
        )
    )


def get_plan_by_id(plan_id: int) -> Optional[models.Plan]:
    """Return a plan by primary key, or None."""
    return first(
        get(
            table=models.Plan,
            conditions={"id_plan": plan_id},
        )
    )


def get_plans_by_type(plan_type: str) -> List[models.Plan]:
    """Return plans matching 'individual' or 'organization'."""
    with session_scope() as session:
        return (
            session.query(models.Plan)
            .filter(models.Plan.plan_type == plan_type)
            .all()
        )


def get_plans_by_cycle(billing_cycle: str) -> List[models.Plan]:
    """Return plans matching 'monthly', 'semestrial', 'yearly', or 'lifetime'."""
    with session_scope() as session:
        return (
            session.query(models.Plan)
            .filter(models.Plan.billing_cycle == billing_cycle)
            .all()
        )


def delete_all_plans() -> int:
    """
    Delete all plans. Will fail at the DB level if any subscription
    still references a plan (FK is RESTRICT), which is the correct
    behaviour — you can't yank a plan out from under an active
    subscription.

    Returns the number of plans deleted.
    """
    with session_scope() as session:
        count = session.query(models.Plan).delete()
        session.commit()
        logger.info("Deleted %d plans", count)
        return count


def update_plan_price(plan_name: str, new_price: float) -> bool:
    """Update the price for a plan by name."""
    with session_scope() as session:
        plan = (
            session.query(models.Plan)
            .filter(models.Plan.plan_name == plan_name)
            .first()
        )
        if not plan:
            logger.warning("Plan not found: %s", plan_name)
            return False

        plan.plan_price = new_price
        session.commit()
        logger.debug("Updated price for plan %s -> %s", plan_name, new_price)
        return True


# ==================== Main Execution ====================

def main():
    """Main entry point for seeding plans."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed plans")
    parser.add_argument(
        "--delete-first",
        action="store_true",
        help="Delete all existing plans before seeding",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    print("Starting plan seeding...")

    try:
        if args.delete_first:
            delete_all_plans()

        count = seed_plans()
        print(f"Successfully seeded {count} plans")

        if count > 0:
            plans = get_all_seeded_plans()
            print(f"\nSeeded {len(plans)} plans:")

            from collections import defaultdict

            grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for p in plans:
                grouped[p["plan_type"] or "untyped"].append(p)

            for plan_type, plan_list in sorted(grouped.items()):
                print(f"\n  [{plan_type}]")
                for p in sorted(plan_list, key=lambda x: x["price"]):
                    print(
                        f"    - {p['name']} "
                        f"({p['price']:.2f} DZD / {p['billing_cycle']}) "
                        f"(ID: {p['id']})"
                    )

    except Exception as e:
        print(f"Failed to seed plans: {e}")
        raise


if __name__ == "__main__":
    main()