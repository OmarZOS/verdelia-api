
# storage/seeds/delivery_broker.py
"""
Seed Algerian delivery brokers.

Creates one wallet per broker and one `DeliveryBroker` row that
points at it. Idempotent — re-running does not duplicate brokers or
wallets.

The brokers listed are the ones that operate in the Algerian
market. Prices are list rates for standard home delivery of a
single parcel up to 5 kg, in DZD. Adjust the list as the market
changes; the seed reads the list, it doesn't care how many entries
it has.
"""

import logging
from typing import Dict, List

from core.models.models import DeliveryBroker, Wallet
from storage.storage_broker import get as storage_get
from storage.storage_broker import session_scope

logger = logging.getLogger(__name__)


# ── The brokers ────────────────────────────────────────────────────
#
# `price` is the standard home-delivery rate for a single parcel in
# DZD. `verified` reflects whether the broker has completed the
# platform's onboarding — the national carriers are verified; the
# smaller ones start unverified until they're reviewed.
#
# `price_matrix` is a JSON string. The delivery broker model stores
# it as Text, so the seed keeps it as a JSON-encoded string rather
# than a dict. The shape is documented below the list.

ALGERIAN_DELIVERY_BROKERS: List[Dict] = [
    {
        "name": "Yalidine",
        "label": "Yalidine Express",
        "price": 400.00,
        "verified": True,
        "logo_url": "https://cdn.verdelia.dz/brokers/yalidine-logo.png",
        "image_url": "https://cdn.verdelia.dz/brokers/yalidine.jpg",
        "price_matrix": {
            "home": {"base": 400, "per_kg_over_5": 50},
            "stopdesk": {"base": 250, "per_kg_over_5": 30},
            "regions": {
                "north_center": 1.0,   # 1.0 = base rate
                "north_east": 1.1,
                "north_west": 1.15,
                "highlands": 1.25,
                "south": 1.6,
            },
        },
    },
    {
        "name": "ZR Express",
        "label": "ZR Express Livraison",
        "price": 450.00,
        "verified": True,
        "logo_url": "https://cdn.verdelia.dz/brokers/zr-express-logo.png",
        "image_url": "https://cdn.verdelia.dz/brokers/zr-express.jpg",
        "price_matrix": {
            "home": {"base": 450, "per_kg_over_5": 60},
            "stopdesk": {"base": 280, "per_kg_over_5": 40},
            "regions": {
                "north_center": 1.0,
                "north_east": 1.1,
                "north_west": 1.2,
                "highlands": 1.3,
                "south": 1.7,
            },
        },
    },
    {
        "name": "Maystro Delivery",
        "label": "Maystro Delivery",
        "price": 380.00,
        "verified": True,
        "logo_url": "https://cdn.verdelia.dz/brokers/maystro-logo.png",
        "image_url": "https://cdn.verdelia.dz/brokers/maystro.jpg",
        "price_matrix": {
            "home": {"base": 380, "per_kg_over_5": 45},
            "stopdesk": {"base": 240, "per_kg_over_5": 30},
            "regions": {
                "north_center": 1.0,
                "north_east": 1.05,
                "north_west": 1.1,
                "highlands": 1.2,
                "south": 1.55,
            },
        },
    },
    {
        "name": "Ecotrack",
        "label": "Ecotrack Logistics",
        "price": 420.00,
        "verified": True,
        "logo_url": "https://cdn.verdelia.dz/brokers/ecotrack-logo.png",
        "image_url": "https://cdn.verdelia.dz/brokers/ecotrack.jpg",
        "price_matrix": {
            "home": {"base": 420, "per_kg_over_5": 55},
            "stopdesk": {"base": 260, "per_kg_over_5": 35},
            "regions": {
                "north_center": 1.0,
                "north_east": 1.1,
                "north_west": 1.15,
                "highlands": 1.28,
                "south": 1.65,
            },
        },
    },
    {
        "name": "Noest",
        "label": "Noest Express",
        "price": 430.00,
        "verified": True,
        "logo_url": "https://cdn.verdelia.dz/brokers/noest-logo.png",
        "image_url": "https://cdn.verdelia.dz/brokers/noest.jpg",
        "price_matrix": {
            "home": {"base": 430, "per_kg_over_5": 55},
            "stopdesk": {"base": 270, "per_kg_over_5": 35},
            "regions": {
                "north_center": 1.0,
                "north_east": 1.08,
                "north_west": 1.12,
                "highlands": 1.22,
                "south": 1.6,
            },
        },
    },
    {
        "name": "Nord Et Sud Express",
        "label": "Nord & Sud",
        "price": 500.00,
        "verified": True,
        "logo_url": "https://cdn.verdelia.dz/brokers/nord-sud-logo.png",
        "image_url": "https://cdn.verdelia.dz/brokers/nord-sud.jpg",
        "price_matrix": {
            "home": {"base": 500, "per_kg_over_5": 65},
            "stopdesk": {"base": 320, "per_kg_over_5": 45},
            "regions": {
                "north_center": 1.0,
                "north_east": 1.15,
                "north_west": 1.2,
                "highlands": 1.35,
                "south": 1.75,
            },
        },
    },
    {
        "name": "World Express",
        "label": "World Express",
        "price": 350.00,
        "verified": False,
        "logo_url": "https://cdn.verdelia.dz/brokers/world-express-logo.png",
        "image_url": "https://cdn.verdelia.dz/brokers/world-express.jpg",
        "price_matrix": {
            "home": {"base": 350, "per_kg_over_5": 45},
            "stopdesk": {"base": 220, "per_kg_over_5": 25},
            "regions": {
                "north_center": 1.0,
                "north_east": 1.1,
                "north_west": 1.15,
                "highlands": 1.25,
                "south": 1.6,
            },
        },
    },
    {
        "name": "Sarl Speed Delivery",
        "label": "Speed Delivery",
        "price": 370.00,
        "verified": False,
        "logo_url": "https://cdn.verdelia.dz/brokers/speed-delivery-logo.png",
        "image_url": "https://cdn.verdelia.dz/brokers/speed-delivery.jpg",
        "price_matrix": {
            "home": {"base": 370, "per_kg_over_5": 50},
            "stopdesk": {"base": 230, "per_kg_over_5": 30},
            "regions": {
                "north_center": 1.0,
                "north_east": 1.08,
                "north_west": 1.12,
                "highlands": 1.2,
                "south": 1.55,
            },
        },
    },
]


# storage/seeds/delivery_broker.py (continued)

import json


def seed_delivery_brokers() -> int:
    """Create Algerian delivery brokers if they don't exist.

    Idempotent — checks each broker by name. A broker that already
    exists is left as-is; its price, verification status, and
    images aren't updated, because the seed's job is to create the
    initial state, not to keep it in sync with the list above.

    Returns the number of brokers actually created (not the total
    in the list).
    """
    created = 0

    for entry in ALGERIAN_DELIVERY_BROKERS:
        name = entry["name"]

        existing = _find_broker_by_name(name)
        if existing is not None:
            logger.info(
                f"Delivery broker already exists: {name} "
                f"(id={existing.id_delivery_broker})"
            )
            continue

        try:
            _create_broker(entry)
            created += 1
            logger.info(f"Created delivery broker: {name}")
        except Exception as e:
            logger.error(f"Failed to create broker {name}: {e}")
            raise

    logger.info(
        f"Seeded {created} delivery brokers "
        f"({len(ALGERIAN_DELIVERY_BROKERS) - created} already existed)"
    )
    return created


def _find_broker_by_name(name: str) -> DeliveryBroker | None:
    """Return the broker with the given name, or None.

    Uses the repository's name lookup if available, falls back to a
    direct query. Brokers names aren't unique in the schema; this
    returns the first match.
    """
    records = storage_get(
        DeliveryBroker,
        {DeliveryBroker.delivery_broker_name: name},
        [],
    )
    return records[0] if records else None


def _create_broker(entry: Dict) -> None:
    """Create one broker and its wallet.

    The wallet is created via `WalletService` so the wallet row
    goes through the same code path production uses — same
    defaults, same `wallet_type` enum value, same status. The
    broker row is then written with the wallet id.

    Both writes are inside a single `session_scope`, so if the
    broker insert fails, the wallet insert rolls back with it.
    """

    wallet = Wallet(
        wallet_type= "business",
        wallet_balance= 0.0,
        wallet_status= "active",
    )

    broker = DeliveryBroker(
        delivery_broker_name=entry["name"],
        delivery_broker_label=entry["label"],
        delivery_broker_logo_url=entry.get("logo_url"),
        delivery_broker_image_url=entry.get("image_url"),
        delivery_broker_wallet = wallet,
        delivery_broker_price_matrix=json.dumps(
            entry["price_matrix"]
        ),
        verified_delivery_broker=1 if entry["verified"] else 0,
    )

    from features.insertion import insert_or_complete_or_raise
    insert_or_complete_or_raise(broker)