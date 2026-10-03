# storage/seeds/iproduct.py
"""
Iproduct (External/Imported Product) seed module using the storage
broker.

Each iproduct is backed by a NamingContribution row carrying the
Arabic / French / English names. Seeding is idempotent: re-running
inserts nothing.

Barcode is the natural key for iproducts — it is the only stable
identifier across imports. `iproduct_name` is not unique on purpose
(two brands can have the same product name), so the naming lookup
keys on the English name and the barcode is what actually
distinguishes rows.
"""

import logging
import random
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from storage.storage_broker import insert_record, get, session_scope
from core.models import models
from storage.seeds._naming import (
    first,
    get_or_create_naming_contribution,
)

from core.logging_config import get_logger

from core.logging_config import get_logger

logger = get_logger(__name__)




# ==================== Seed Data ====================

# `en` is the English name that goes on the NamingContribution. All
# other fields belong on the Iproduct row. Category IDs reference the
# product_category seed.
SEED_IPRODUCTS: List[Dict[str, Any]] = [
    # ---------- Baked Goods (category 1) ----------
    {
        "en": "Whole Wheat Bread",
        "ar": "خبز القمح الكامل",
        "fr": "Pain complet",
        "barcode": "8901234567890",
        "brand": "HealthyLife",
        "estimated_price": 2.99,
        "currency": "DZD",
        "gluten_status": "contains_gluten",
        "category_id": 1,
        "image_url": "https://example.com/images/whole_wheat_bread.jpg",
        "info_source": "openai",
        "info_confidence": 0.95,
        "model_name": "gpt-4",
    },
    {
        "en": "Artisan Sourdough",
        "ar": "خبز العجين المخمر الحرفي",
        "fr": "Pain au levain artisanal",
        "barcode": "8901234567891",
        "brand": "Baker's Delight",
        "estimated_price": 4.50,
        "currency": "DZD",
        "gluten_status": "contains_gluten",
        "category_id": 1,
        "image_url": "https://example.com/images/sourdough.jpg",
        "info_source": "openai",
        "info_confidence": 0.92,
        "model_name": "gpt-4",
    },
    {
        "en": "Gluten-Free Bread",
        "ar": "خبز خالٍ من الغلوتين",
        "fr": "Pain sans gluten",
        "barcode": "8901234567892",
        "brand": "FreeLife",
        "estimated_price": 5.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 1,
        "image_url": "https://example.com/images/gluten_free_bread.jpg",
        "info_source": "openai",
        "info_confidence": 0.88,
        "model_name": "gpt-4",
    },

    # ---------- Spreads (category 2) ----------
    {
        "en": "Organic Peanut Butter",
        "ar": "زبدة الفول السوداني العضوية",
        "fr": "Beurre de cacahuète bio",
        "barcode": "8901234567893",
        "brand": "NutriSpread",
        "estimated_price": 3.49,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 2,
        "image_url": "https://example.com/images/peanut_butter.jpg",
        "info_source": "openai",
        "info_confidence": 0.94,
        "model_name": "gpt-4",
    },
    {
        "en": "Strawberry Jam",
        "ar": "مربى الفراولة",
        "fr": "Confiture de fraises",
        "barcode": "8901234567894",
        "brand": "FruitSpread",
        "estimated_price": 2.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 2,
        "image_url": "https://example.com/images/strawberry_jam.jpg",
        "info_source": "openai",
        "info_confidence": 0.91,
        "model_name": "gpt-4",
    },
    {
        "en": "Honey Spread",
        "ar": "عسل طبيعي للدهن",
        "fr": "Miel à tartiner",
        "barcode": "8901234567895",
        "brand": "PureHoney",
        "estimated_price": 6.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 2,
        "image_url": "https://example.com/images/honey.jpg",
        "info_source": "openai",
        "info_confidence": 0.96,
        "model_name": "gpt-4",
    },

    # ---------- Cereals (category 3) ----------
    {
        "en": "Oatmeal Cereal",
        "ar": "حبوب الشوفان",
        "fr": "Céréales d'avoine",
        "barcode": "8901234567896",
        "brand": "MorningOats",
        "estimated_price": 3.99,
        "currency": "DZD",
        "gluten_status": "contains_gluten",
        "category_id": 3,
        "image_url": "https://example.com/images/oatmeal.jpg",
        "info_source": "openai",
        "info_confidence": 0.93,
        "model_name": "gpt-4",
    },
    {
        "en": "Corn Flakes",
        "ar": "رقائق الذرة",
        "fr": "Flocons de maïs",
        "barcode": "8901234567897",
        "brand": "CrispyCorn",
        "estimated_price": 2.49,
        "currency": "DZD",
        "gluten_status": "contains_gluten",
        "category_id": 3,
        "image_url": "https://example.com/images/corn_flakes.jpg",
        "info_source": "openai",
        "info_confidence": 0.90,
        "model_name": "gpt-4",
    },
    {
        "en": "Gluten-Free Granola",
        "ar": "جرانولا خالية من الغلوتين",
        "fr": "Granola sans gluten",
        "barcode": "8901234567898",
        "brand": "GranolaHealth",
        "estimated_price": 4.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 3,
        "image_url": "https://example.com/images/granola.jpg",
        "info_source": "openai",
        "info_confidence": 0.87,
        "model_name": "gpt-4",
    },

    # ---------- Pasta (category 4) ----------
    {
        "en": "Spaghetti Pasta",
        "ar": "معكرونة إسباجيتي",
        "fr": "Pâtes spaghetti",
        "barcode": "8901234567899",
        "brand": "PastaItalia",
        "estimated_price": 1.99,
        "currency": "DZD",
        "gluten_status": "contains_gluten",
        "category_id": 4,
        "image_url": "https://example.com/images/spaghetti.jpg",
        "info_source": "openai",
        "info_confidence": 0.95,
        "model_name": "gpt-4",
    },
    {
        "en": "Gluten-Free Pasta",
        "ar": "معكرونة خالية من الغلوتين",
        "fr": "Pâtes sans gluten",
        "barcode": "8901234567900",
        "brand": "FreePasta",
        "estimated_price": 3.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 4,
        "image_url": "https://example.com/images/gluten_free_pasta.jpg",
        "info_source": "openai",
        "info_confidence": 0.89,
        "model_name": "gpt-4",
    },
    {
        "en": "Lasagna Sheets",
        "ar": "شرائح اللازانيا",
        "fr": "Feuilles de lasagne",
        "barcode": "8901234567901",
        "brand": "PastaItalia",
        "estimated_price": 2.49,
        "currency": "DZD",
        "gluten_status": "contains_gluten",
        "category_id": 4,
        "image_url": "https://example.com/images/lasagna.jpg",
        "info_source": "openai",
        "info_confidence": 0.92,
        "model_name": "gpt-4",
    },

    # ---------- Snacks (category 5) ----------
    {
        "en": "Potato Chips",
        "ar": "رقائق البطاطس",
        "fr": "Chips de pommes de terre",
        "barcode": "8901234567902",
        "brand": "CrispySnack",
        "estimated_price": 1.49,
        "currency": "DZD",
        "gluten_status": "contains_gluten",
        "category_id": 5,
        "image_url": "https://example.com/images/potato_chips.jpg",
        "info_source": "openai",
        "info_confidence": 0.94,
        "model_name": "gpt-4",
    },
    {
        "en": "Gluten-Free Crackers",
        "ar": "مقرمشات خالية من الغلوتين",
        "fr": "Crackers sans gluten",
        "barcode": "8901234567903",
        "brand": "FreeSnack",
        "estimated_price": 3.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 5,
        "image_url": "https://example.com/images/crackers.jpg",
        "info_source": "openai",
        "info_confidence": 0.88,
        "model_name": "gpt-4",
    },
    {
        "en": "Trail Mix",
        "ar": "خلطة المكسرات",
        "fr": "Mélange montagnard",
        "barcode": "8901234567904",
        "brand": "NutriMix",
        "estimated_price": 4.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 5,
        "image_url": "https://example.com/images/trail_mix.jpg",
        "info_source": "openai",
        "info_confidence": 0.91,
        "model_name": "gpt-4",
    },

    # ---------- Beverages (category 6) ----------
    {
        "en": "Orange Juice",
        "ar": "عصير البرتقال",
        "fr": "Jus d'orange",
        "barcode": "8901234567905",
        "brand": "FreshSqueeze",
        "estimated_price": 2.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 6,
        "image_url": "https://example.com/images/orange_juice.jpg",
        "info_source": "openai",
        "info_confidence": 0.96,
        "model_name": "gpt-4",
    },
    {
        "en": "Almond Milk",
        "ar": "حليب اللوز",
        "fr": "Lait d'amande",
        "barcode": "8901234567906",
        "brand": "PlantMilk",
        "estimated_price": 3.49,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 6,
        "image_url": "https://example.com/images/almond_milk.jpg",
        "info_source": "openai",
        "info_confidence": 0.93,
        "model_name": "gpt-4",
    },
    {
        "en": "Green Tea",
        "ar": "شاي أخضر",
        "fr": "Thé vert",
        "barcode": "8901234567907",
        "brand": "TeaLeaf",
        "estimated_price": 2.49,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 6,
        "image_url": "https://example.com/images/green_tea.jpg",
        "info_source": "openai",
        "info_confidence": 0.97,
        "model_name": "gpt-4",
    },

    # ---------- Desserts (category 7) ----------
    {
        "en": "Chocolate Brownie",
        "ar": "براوني الشوكولاتة",
        "fr": "Brownie au chocolat",
        "barcode": "8901234567908",
        "brand": "SweetTreat",
        "estimated_price": 2.99,
        "currency": "DZD",
        "gluten_status": "contains_gluten",
        "category_id": 7,
        "image_url": "https://example.com/images/brownie.jpg",
        "info_source": "openai",
        "info_confidence": 0.94,
        "model_name": "gpt-4",
    },
    {
        "en": "Gluten-Free Cookies",
        "ar": "بسكويت خالٍ من الغلوتين",
        "fr": "Cookies sans gluten",
        "barcode": "8901234567909",
        "brand": "FreeCookie",
        "estimated_price": 4.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 7,
        "image_url": "https://example.com/images/gluten_free_cookies.jpg",
        "info_source": "openai",
        "info_confidence": 0.89,
        "model_name": "gpt-4",
    },

    # ---------- Frozen Foods (category 8) ----------
    {
        "en": "Frozen Vegetables Mix",
        "ar": "خلطة خضروات مجمدة",
        "fr": "Mélange de légumes surgelés",
        "barcode": "8901234567910",
        "brand": "FrostFresh",
        "estimated_price": 3.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 8,
        "image_url": "https://example.com/images/frozen_veg.jpg",
        "info_source": "openai",
        "info_confidence": 0.95,
        "model_name": "gpt-4",
    },
    {
        "en": "Frozen Pizza",
        "ar": "بيتزا مجمدة",
        "fr": "Pizza surgelée",
        "barcode": "8901234567911",
        "brand": "PizzaFast",
        "estimated_price": 5.99,
        "currency": "DZD",
        "gluten_status": "contains_gluten",
        "category_id": 8,
        "image_url": "https://example.com/images/frozen_pizza.jpg",
        "info_source": "openai",
        "info_confidence": 0.92,
        "model_name": "gpt-4",
    },

    # ---------- Flours & Baking (category 9) ----------
    {
        "en": "All-Purpose Flour",
        "ar": "طحين متعدد الاستخدامات",
        "fr": "Farine tout usage",
        "barcode": "8901234567912",
        "brand": "BakeMaster",
        "estimated_price": 1.99,
        "currency": "DZD",
        "gluten_status": "contains_gluten",
        "category_id": 9,
        "image_url": "https://example.com/images/flour.jpg",
        "info_source": "openai",
        "info_confidence": 0.96,
        "model_name": "gpt-4",
    },
    {
        "en": "Almond Flour",
        "ar": "طحين اللوز",
        "fr": "Farine d'amande",
        "barcode": "8901234567913",
        "brand": "NutriFlour",
        "estimated_price": 7.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 9,
        "image_url": "https://example.com/images/almond_flour.jpg",
        "info_source": "openai",
        "info_confidence": 0.90,
        "model_name": "gpt-4",
    },

    # ---------- Canned & Packaged Goods (category 10) ----------
    {
        "en": "Canned Tomatoes",
        "ar": "طماطم معلبة",
        "fr": "Tomates en conserve",
        "barcode": "8901234567914",
        "brand": "CanFresh",
        "estimated_price": 1.49,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 10,
        "image_url": "https://example.com/images/canned_tomatoes.jpg",
        "info_source": "openai",
        "info_confidence": 0.95,
        "model_name": "gpt-4",
    },
    {
        "en": "Canned Beans",
        "ar": "فاصوليا معلبة",
        "fr": "Haricots en conserve",
        "barcode": "8901234567915",
        "brand": "BeanGood",
        "estimated_price": 1.99,
        "currency": "DZD",
        "gluten_status": "gluten_free",
        "category_id": 10,
        "image_url": "https://example.com/images/canned_beans.jpg",
        "info_source": "openai",
        "info_confidence": 0.94,
        "model_name": "gpt-4",
    },
]


# ==================== Additional Data Generators ====================

# Names for random generation. Each tuple is (en, ar, fr) so a random
# iproduct still gets a fully-formed naming contribution.
_RANDOM_NAME_POOL = [
    ("Organic Quinoa", "الكينوا العضوية", "Quinoa bio"),
    ("Chia Seeds", "بذور الشيا", "Graines de chia"),
    ("Coconut Oil", "زيت جوز الهند", "Huile de coco"),
    ("Olive Oil", "زيت الزيتون", "Huile d'olive"),
    ("Maple Syrup", "شراب القيقب", "Sirop d'érable"),
    ("Vanilla Extract", "خلاصة الفانيليا", "Extrait de vanille"),
    ("Cocoa Powder", "مسحوق الكاكاو", "Poudre de cacao"),
    ("Protein Powder", "مسحوق البروتين", "Poudre de protéines"),
    ("Coconut Flour", "طحين جوز الهند", "Farine de coco"),
    ("Tapioca Starch", "نشا التابيوكا", "Fécule de tapioca"),
    ("Xanthan Gum", "صمغ الزانثان", "Gomme xanthane"),
    ("Psyllium Husk", "قشور السيليوم", "Enveloppes de psyllium"),
]

_RANDOM_BRAND_POOL = [
    "HealthyLife",
    "NutriFood",
    "PureOrganic",
    "WholeFoods",
    "NaturalChoice",
    "GreenGarden",
    "FarmFresh",
    "OrganicHarvest",
]

_GLUTEN_STATUSES = [
    "gluten_free",
    "contains_gluten",
    "may_contain_gluten",
    "unknown",
]


def generate_random_iproduct_data(
    category_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate random iproduct data for testing. The returned dict has
    the same shape as SEED_IPRODUCTS entries, so it can be fed to
    `get_or_create_naming_contribution` and `_get_or_create_iproduct`
    directly.
    """
    name_en, name_ar, name_fr = random.choice(_RANDOM_NAME_POOL)
    return {
        "en": name_en,
        "ar": name_ar,
        "fr": name_fr,
        "barcode": str(random.randint(1000000000000, 9999999999999)),
        "brand": random.choice(_RANDOM_BRAND_POOL),
        "estimated_price": round(random.uniform(1.99, 29.99), 2),
        "currency": "DZD",
        "gluten_status": random.choice(_GLUTEN_STATUSES),
        "category_id": category_id or random.randint(1, 10),
        "image_url": (
            f"https://example.com/images/"
            f"product_{random.randint(1000, 9999)}.jpg"
        ),
        "info_source": "openai",
        "info_confidence": round(random.uniform(0.75, 0.99), 2),
        "model_name": "gpt-4",
    }


# ==================== Helpers ====================

def _get_or_create_iproduct(
    *,
    barcode: str,
    name_en: str,
    naming_contribution_id: int,
    brand: Optional[str],
    estimated_price: Optional[float],
    currency: str,
    gluten_status: str,
    category_id: Optional[int],
    image_url: Optional[str],
    info_source: Optional[str],
    info_confidence: Optional[float],
    model_name: Optional[str],
) -> Optional[Any]:
    """
    Return the existing Iproduct for the given barcode, or insert a
    new one linked to `naming_contribution_id`.
    """
    existing = first(
        get(
            table=models.Iproduct,
            conditions={"iproduct_barcode": barcode},
        )
    )
    if existing:
        return existing

    now = datetime.now()
    iproduct = models.Iproduct(
        iproduct_name=name_en,
        iproduct_barcode=barcode,
        iproduct_brand=brand,
        iproduct_estimated_price=Decimal(str(estimated_price or 0.00)),
        iproduct_price_currency=currency,
        iproduct_gluten_status=gluten_status,
        iproduct_category_id=category_id,
        iproduct_image_url=image_url,
        iproduct_info_source=info_source,
        iproduct_info_confidence=Decimal(str(info_confidence or 0.00)),
        iproduct_model_name=model_name,
        iproduct_naming_ref=naming_contribution_id,
        iproduct_last_price_update=now,
        iproduct_created_at=now,
        iproduct_last_update=now,
    )
    return first(insert_record(iproduct))


def _entry_to_fields(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise a seed entry to the field names `_get_or_create_iproduct`
    expects. Accepts both the new short keys (`barcode`, `brand`,
    `estimated_price`, ...) and the old `iproduct_*` keys.
    """
    return {
        "barcode": entry.get("barcode") or entry.get("iproduct_barcode"),
        "name_en": entry.get("en") or entry.get("iproduct_name"),
        "brand": entry.get("brand") or entry.get("iproduct_brand"),
        "estimated_price": entry.get("estimated_price")
        or entry.get("iproduct_estimated_price"),
        "currency": entry.get("currency")
        or entry.get("iproduct_price_currency")
        or "DZD",
        "gluten_status": entry.get("gluten_status")
        or entry.get("iproduct_gluten_status")
        or "unknown",
        "category_id": entry.get("category_id")
        or entry.get("iproduct_category_id"),
        "image_url": entry.get("image_url")
        or entry.get("iproduct_image_url"),
        "info_source": entry.get("info_source")
        or entry.get("iproduct_info_source"),
        "info_confidence": entry.get("info_confidence")
        or entry.get("iproduct_info_confidence"),
        "model_name": entry.get("model_name")
        or entry.get("iproduct_model_name"),
    }


# ==================== Seeding Functions ====================

def seed_iproducts() -> int:
    """
    Seed iproducts and their multilingual names.

    Returns:
        Number of iproducts inserted (existing rows are not counted).
    """
    count_inserted = 0

    for entry in SEED_IPRODUCTS:
        name_en = entry["en"]
        barcode = entry["barcode"]

        contribution = get_or_create_naming_contribution(
            name_en=entry["en"],
            name_ar=entry["ar"],
            name_fr=entry["fr"],
            contribution_type="product",
            icon_url=entry.get("image_url"),
        )
        if contribution is None:
            logger.error(
                "Skipping random iproduct %r: no naming contribution",
                entry["en"],
            )
            continue

        # Random barcodes are ~1 in 9 trillion; collisions are
        # vanishingly rare but checked anyway for determinism.
        existing_product = first(
            get(
                table=models.Iproduct,
                conditions={"iproduct_barcode": entry["barcode"]},
            )
        )
        if existing_product:
            continue

        fields = _entry_to_fields(entry)
        product = _get_or_create_iproduct(
            barcode=fields["barcode"],
            name_en=fields["name_en"],
            naming_contribution_id=contribution.id_naming_contribution,
            brand=fields["brand"],
            estimated_price=fields["estimated_price"],
            currency=fields["currency"],
            gluten_status=fields["gluten_status"],
            category_id=fields["category_id"],
            image_url=fields["image_url"],
            info_source=fields["info_source"],
            info_confidence=fields["info_confidence"],
            model_name=fields["model_name"],
        )
        if product:
            count_inserted += 1
            logger.debug("Seeded iproduct: %s", name_en)

    logger.info("Seeded %d new iproducts", count_inserted)
    return count_inserted


def seed_random_iproducts(count: int = 10) -> int:
    """
    Seed random iproducts. Each generated product gets its own naming
    contribution derived from the random name pool.
    """
    count_inserted = 0

    for _ in range(count):
        entry = generate_random_iproduct_data()

        contribution = get_or_create_naming_contribution(
            name_en=entry["en"],
            name_ar=entry["ar"],
            name_fr=entry["fr"],
            contribution_type="product",
            icon_url=entry.get("image_url"),
        )
        if contribution is None:
            logger.error(
                "Skipping random iproduct %r: no naming contribution",
                entry["en"],
            )
            continue

        # Random barcodes are ~1 in 9 trillion; collisions are
        # vanishingly rare but checked anyway for determinism.
        existing_product = first(
            get(
                table=models.Iproduct,
                conditions={"iproduct_barcode": entry["barcode"]},
            )
        )
        if existing_product:
            continue

        fields = _entry_to_fields(entry)
        product = _get_or_create_iproduct(
            barcode=fields["barcode"],
            name_en=fields["name_en"],
            naming_contribution_id=contribution.id_naming_contribution,
            brand=fields["brand"],
            estimated_price=fields["estimated_price"],
            currency=fields["currency"],
            gluten_status=fields["gluten_status"],
            category_id=fields["category_id"],
            image_url=fields["image_url"],
            info_source=fields["info_source"],
            info_confidence=fields["info_confidence"],
            model_name=fields["model_name"],
        )
        if product:
            count_inserted += 1

    logger.info("Seeded %d random iproducts", count_inserted)
    return count_inserted


def seed_iproduct(product_data: Dict[str, Any]) -> bool:
    """
    Seed a single iproduct.

    Accepts both the new short keys and the old `iproduct_*` keys.

    Returns True if inserted, False if the barcode already existed.
    """
    fields = _entry_to_fields(product_data)
    barcode = fields["barcode"]
    name_en = fields["name_en"]
    if not barcode or not name_en:
        logger.warning(
            "seed_iproduct called with incomplete data: %r", product_data
        )
        return False

    existing = first(
        get(
            table=models.Iproduct,
            conditions={"iproduct_barcode": barcode},
        )
    )
    if existing:
        logger.debug("Iproduct already exists: %s", name_en)
        return False

    contribution = get_or_create_naming_contribution(
        name_en=name_en,
        name_ar=product_data.get("ar", name_en),
        name_fr=product_data.get("fr", name_en),
        contribution_type="product",
        icon_url=fields.get("image_url"),
    )
    if contribution is None:
        logger.error("Could not create naming contribution for %r", name_en)
        return False

    product = _get_or_create_iproduct(
        barcode=barcode,
        name_en=name_en,
        naming_contribution_id=contribution.id_naming_contribution,
        brand=fields["brand"],
        estimated_price=fields["estimated_price"],
        currency=fields["currency"],
        gluten_status=fields["gluten_status"],
        category_id=fields["category_id"],
        image_url=fields["image_url"],
        info_source=fields["info_source"],
        info_confidence=fields["info_confidence"],
        model_name=fields["model_name"],
    )
    if product:
        logger.debug("Seeded iproduct: %s", name_en)
        return True
    return False


def seed_iproducts_from_list(products: List[Dict[str, Any]]) -> int:
    """
    Seed iproducts from a custom list. Accepts both the new short keys
    and the old `iproduct_*` keys.

    Returns the number of products inserted.
    """
    count_inserted = 0

    for entry in products:
        fields = _entry_to_fields(entry)
        barcode = fields["barcode"]
        name_en = fields["name_en"]
        if not barcode or not name_en:
            logger.warning("Skipping entry with incomplete data: %r", entry)
            continue

        existing = first(
            get(
                table=models.Iproduct,
                conditions={"iproduct_barcode": barcode},
            )
        )
        if existing:
            continue

        contribution = get_or_create_naming_contribution(
            name_en=name_en,
            name_ar=entry.get("ar", name_en),
            name_fr=entry.get("fr", name_en),
            contribution_type="product",
            icon_url=fields.get("image_url"),
        )
        if contribution is None:
            logger.error(
                "Skipping %r: could not resolve naming contribution",
                name_en,
            )
            continue

        product = _get_or_create_iproduct(
            barcode=barcode,
            name_en=name_en,
            naming_contribution_id=contribution.id_naming_contribution,
            brand=fields["brand"],
            estimated_price=fields["estimated_price"],
            currency=fields["currency"],
            gluten_status=fields["gluten_status"],
            category_id=fields["category_id"],
            image_url=fields["image_url"],
            info_source=fields["info_source"],
            info_confidence=fields["info_confidence"],
            model_name=fields["model_name"],
        )
        if product:
            count_inserted += 1
            logger.debug("Seeded iproduct: %s", name_en)

    logger.info(
        "Seeded %d iproducts from custom list", count_inserted
    )
    return count_inserted


# ==================== Utility Functions ====================

def get_all_seeded_iproducts() -> List[Dict[str, Any]]:
    """
    Return every iproduct with its name in all three languages.

    The primary `name` field is the English name for backward
    compatibility with callers that only want one string.
    """
    with session_scope() as session:
        rows = (
            session.query(models.Iproduct, models.NamingContribution)
            .outerjoin(
                models.NamingContribution,
                models.Iproduct.iproduct_naming_ref
                == models.NamingContribution.id_naming_contribution,
            )
            .all()
        )

        result: List[Dict[str, Any]] = []
        for product, naming in rows:
            result.append(
                {
                    "id": product.id_iproduct,
                    "name": product.iproduct_name,
                    "en": product.iproduct_name,
                    "ar": getattr(naming, "naming_contribution_ar", None)
                    if naming
                    else None,
                    "fr": getattr(naming, "naming_contribution_fr", None)
                    if naming
                    else None,
                    "barcode": product.iproduct_barcode,
                    "brand": product.iproduct_brand,
                    "price": float(product.iproduct_estimated_price)
                    if product.iproduct_estimated_price
                    else 0,
                    "currency": product.iproduct_price_currency,
                    "gluten_status": product.iproduct_gluten_status,
                    "category_id": product.iproduct_category_id,
                    "image_url": product.iproduct_image_url,
                    "naming_ref": product.iproduct_naming_ref,
                }
            )
        return result


def iproduct_exists(barcode: str) -> bool:
    """
    Check whether an iproduct with the given barcode exists.
    """
    existing = first(
        get(
            table=models.Iproduct,
            conditions={"iproduct_barcode": barcode},
        )
    )
    return bool(existing)


def get_iproduct_by_barcode(
    barcode: str,
) -> Optional[models.Iproduct]:
    """
    Return an iproduct by barcode, or None.
    """
    return first(
        get(
            table=models.Iproduct,
            conditions={"iproduct_barcode": barcode},
        )
    )


def get_iproduct_by_id(
    product_id: int,
) -> Optional[models.Iproduct]:
    """
    Return an iproduct by primary key, or None.
    """
    return first(
        get(
            table=models.Iproduct,
            conditions={"id_iproduct": product_id},
        )
    )


def get_iproducts_by_category(
    category_id: int,
) -> List[models.Iproduct]:
    """
    Return all iproducts in a category.
    """
    with session_scope() as session:
        return (
            session.query(models.Iproduct)
            .filter(models.Iproduct.iproduct_category_id == category_id)
            .all()
        )


def get_iproducts_by_gluten_status(
    gluten_status: str,
) -> List[models.Iproduct]:
    """
    Return iproducts matching a given gluten status.
    """
    with session_scope() as session:
        return (
            session.query(models.Iproduct)
            .filter(
                models.Iproduct.iproduct_gluten_status == gluten_status
            )
            .all()
        )


def delete_all_iproducts() -> int:
    """
    Delete all iproducts. Leaves the naming contributions in place,
    since other tables may reference them.

    Returns the number of products deleted.
    """
    with session_scope() as session:
        count = session.query(models.Iproduct).delete()
        session.commit()
        logger.info("Deleted %d iproducts", count)
        return count


def update_iproduct_price(barcode: str, new_price: float) -> bool:
    """
    Update the price of an iproduct.
    """
    with session_scope() as session:
        product = (
            session.query(models.Iproduct)
            .filter(models.Iproduct.iproduct_barcode == barcode)
            .first()
        )

        if not product:
            logger.warning("Iproduct not found with barcode: %s", barcode)
            return False

        product.iproduct_estimated_price = Decimal(str(new_price))
        product.iproduct_last_price_update = datetime.now()
        session.commit()
        logger.debug("Updated price for product: %s -> %s", barcode, new_price)
        return True


def update_iproduct_image(barcode: str, image_url: str) -> bool:
    """
    Update the image URL of an iproduct.
    """
    with session_scope() as session:
        product = (
            session.query(models.Iproduct)
            .filter(models.Iproduct.iproduct_barcode == barcode)
            .first()
        )

        if not product:
            logger.warning("Iproduct not found with barcode: %s", barcode)
            return False

        product.iproduct_image_url = image_url
        session.commit()
        logger.debug("Updated image for product: %s", barcode)
        return True


# ==================== Main Execution ====================

def main():
    """Main entry point for seeding iproducts."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed iproducts (external/imported products)"
    )
    parser.add_argument(
        "--delete-first",
        action="store_true",
        help="Delete all existing iproducts before seeding",
    )
    parser.add_argument(
        "--random",
        type=int,
        default=0,
        help="Generate and seed random iproducts (specify count)",
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

    print("Starting iproduct seeding...")

    try:
        if args.delete_first:
            delete_all_iproducts()

        count = 0

        if args.random > 0:
            count = seed_random_iproducts(args.random)
            print(f"Successfully seeded {count} random iproducts")
        else:
            count = seed_iproducts()
            print(f"Successfully seeded {count} iproducts")

        if count > 0:
            products = get_all_seeded_iproducts()
            print(f"\nSeeded {len(products)} iproducts:")

            from collections import defaultdict

            grouped: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
            for p in products:
                grouped[p["category_id"]].append(p)

            for category_id, product_list in sorted(
                grouped.items(), key=lambda kv: (kv[0] is None, kv[0])
            ):
                print(f"\n  Category ID: {category_id}")
                for p in product_list[:5]:
                    languages = " / ".join(
                        filter(None, [p.get("en"), p.get("fr"), p.get("ar")])
                    )
                    print(
                        f"    - {languages} "
                        f"(ID: {p['id']}, Price: {p['price']} {p['currency']})"
                    )
                if len(product_list) > 5:
                    print(f"      ... and {len(product_list) - 5} more")

    except Exception as e:
        print(f"Failed to seed iproducts: {e}")
        raise


if __name__ == "__main__":
    main()