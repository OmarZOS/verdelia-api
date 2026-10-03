# storage/seeds/ingredient.py
"""
Ingredient seed module using the storage broker.

Each ingredient is backed by a NamingContribution row carrying the
Arabic / French / English names. Seeding is idempotent: re-running
inserts nothing.
"""

import logging
from typing import Any, Dict, List, Optional

from storage.storage_broker import insert_record, get, session_scope
from core.models import models
from storage.seeds._naming import (
    first,
    get_or_create_naming_contribution,
)

from core.logging_config import get_logger

logger = get_logger(__name__)



# ==================== Seed Data ====================

# `en` is both the lookup anchor and the English name. `quantifier`
# defaults to "pc" when omitted. Descriptions are not seeded because
# Ingredient has no description column; add one if the schema grows.
SEED_INGREDIENTS: List[Dict[str, str]] = [
    # ---------- Grains ----------
    {"en": "Wheat", "ar": "القمح", "fr": "Blé", "quantifier": "g"},
    {"en": "Barley", "ar": "الشعير", "fr": "Orge", "quantifier": "g"},
    {"en": "Rye", "ar": "الجاودار", "fr": "Seigle", "quantifier": "g"},
    {"en": "Oats", "ar": "الشوفان", "fr": "Avoine", "quantifier": "g"},
    {"en": "Corn", "ar": "الذرة", "fr": "Maïs", "quantifier": "g"},
    {"en": "Rice", "ar": "الأرز", "fr": "Riz", "quantifier": "g"},
    {"en": "Soy", "ar": "الصويا", "fr": "Soja", "quantifier": "g"},
    {"en": "Buckwheat", "ar": "الحنطة السوداء", "fr": "Sarrasin", "quantifier": "g"},

    # ---------- Dairy ----------
    {"en": "Milk", "ar": "الحليب", "fr": "Lait", "quantifier": "mL"},
    {"en": "Butter", "ar": "الزبدة", "fr": "Beurre", "quantifier": "g"},
    {"en": "Margarine", "ar": "السمن النباتي", "fr": "Margarine", "quantifier": "g"},

    # ---------- Proteins ----------
    {"en": "Egg", "ar": "البيض", "fr": "Œuf", "quantifier": "pc"},
    {"en": "Peanuts", "ar": "الفول السوداني", "fr": "Arachides", "quantifier": "g"},
    {"en": "Tree Nuts", "ar": "المكسرات", "fr": "Fruits à coque", "quantifier": "g"},
    {"en": "Fish", "ar": "السمك", "fr": "Poisson", "quantifier": "g"},
    {"en": "Shellfish", "ar": "المحار", "fr": "Crustacés", "quantifier": "g"},
    {"en": "Lentils", "ar": "العدس", "fr": "Lentilles", "quantifier": "g"},
    {"en": "Chickpeas", "ar": "الحمص", "fr": "Pois chiches", "quantifier": "g"},
    {"en": "Lupin", "ar": "الترمس", "fr": "Lupin", "quantifier": "g"},

    # ---------- Nuts & Seeds ----------
    {"en": "Almond", "ar": "اللوز", "fr": "Amande", "quantifier": "g"},
    {"en": "Coconut", "ar": "جوز الهند", "fr": "Noix de coco", "quantifier": "g"},
    {"en": "Sunflower Seeds", "ar": "بذور عباد الشمس", "fr": "Graines de tournesol", "quantifier": "g"},
    {"en": "Pumpkin Seeds", "ar": "بذور اليقطين", "fr": "Graines de courge", "quantifier": "g"},
    {"en": "Sesame Seeds", "ar": "بذور السمسم", "fr": "Graines de sésame", "quantifier": "g"},

    # ---------- Vegetables ----------
    {"en": "Potato", "ar": "البطاطس", "fr": "Pomme de terre", "quantifier": "g"},
    {"en": "Sweet Potato", "ar": "البطاطا الحلوة", "fr": "Patate douce", "quantifier": "g"},
    {"en": "Ginger", "ar": "الزنجبيل", "fr": "Gingembre", "quantifier": "g"},
    {"en": "Garlic", "ar": "الثوم", "fr": "Ail", "quantifier": "g"},
    {"en": "Onion", "ar": "البصل", "fr": "Oignon", "quantifier": "g"},
    {"en": "Leek", "ar": "الكراث", "fr": "Poireau", "quantifier": "g"},
    {"en": "Shallot", "ar": "الكراث الأندلسي", "fr": "Échalote", "quantifier": "g"},
    {"en": "Scallion", "ar": "البصل الأخضر", "fr": "Ciboule", "quantifier": "g"},
    {"en": "Chive", "ar": "الثوم المعمر", "fr": "Ciboulette", "quantifier": "g"},
    {"en": "Parsley", "ar": "البقدونس", "fr": "Persil", "quantifier": "g"},
    {"en": "Cilantro", "ar": "الكزبرة", "fr": "Coriandre", "quantifier": "g"},
    {"en": "Basil", "ar": "الريحان", "fr": "Basilic", "quantifier": "g"},
    {"en": "Oregano", "ar": "الأوريجانو", "fr": "Origan", "quantifier": "g"},
    {"en": "Thyme", "ar": "الزعتر", "fr": "Thym", "quantifier": "g"},
    {"en": "Rosemary", "ar": "إكليل الجبل", "fr": "Romarin", "quantifier": "g"},
    {"en": "Sage", "ar": "المريمية", "fr": "Sauge", "quantifier": "g"},
    {"en": "Mint", "ar": "النعناع", "fr": "Menthe", "quantifier": "g"},
    {"en": "Lemongrass", "ar": "عشب الليمون", "fr": "Citronnelle", "quantifier": "g"},
    {"en": "Lavender", "ar": "الخزامى", "fr": "Lavande", "quantifier": "g"},

    # ---------- Spices ----------
    {"en": "Fennel", "ar": "الشمر", "fr": "Fenouil", "quantifier": "g"},
    {"en": "Cumin", "ar": "الكمون", "fr": "Cumin", "quantifier": "g"},
    {"en": "Paprika", "ar": "البابريكا", "fr": "Paprika", "quantifier": "g"},
    {"en": "Chili Pepper", "ar": "الفلفل الحار", "fr": "Piment", "quantifier": "g"},
    {"en": "Black Pepper", "ar": "الفلفل الأسود", "fr": "Poivre noir", "quantifier": "g"},
    {"en": "White Pepper", "ar": "الفلفل الأبيض", "fr": "Poivre blanc", "quantifier": "g"},
    {"en": "Green Pepper", "ar": "الفلفل الأخضر", "fr": "Poivre vert", "quantifier": "g"},
    {"en": "Red Pepper", "ar": "الفلفل الأحمر", "fr": "Poivre rouge", "quantifier": "g"},
    {"en": "Cinnamon", "ar": "القرفة", "fr": "Cannelle", "quantifier": "g"},
    {"en": "Allspice", "ar": "البهارات", "fr": "Piment de la Jamaïque", "quantifier": "g"},
    {"en": "Mustard", "ar": "الخردل", "fr": "Moutarde", "quantifier": "g"},

    # ---------- Oils & Fats ----------
    {"en": "Vegetable Oil", "ar": "الزيت النباتي", "fr": "Huile végétale", "quantifier": "mL"},

    # ---------- Baking Ingredients ----------
    {"en": "Baking Powder", "ar": "مسحوق الخبيز", "fr": "Levure chimique", "quantifier": "g"},
    {"en": "Baking Soda", "ar": "صودا الخبيز", "fr": "Bicarbonate de soude", "quantifier": "g"},
    {"en": "Cornstarch", "ar": "النشا", "fr": "Fécule de maïs", "quantifier": "g"},
    {"en": "All-Purpose Flour", "ar": "الطحين متعدد الاستخدامات", "fr": "Farine tout usage", "quantifier": "g"},
    {"en": "Pastry Flour", "ar": "طحين المعجنات", "fr": "Farine à pâtisserie", "quantifier": "g"},
    {"en": "Self-Rising Flour", "ar": "الطحين ذاتي التخمير", "fr": "Farine auto-levante", "quantifier": "g"},

    # ---------- Other ----------
    {"en": "Gelatin", "ar": "الجيلاتين", "fr": "Gélatine", "quantifier": "g"},
]


# ==================== Helpers ====================

def _get_or_create_ingredient(
    *,
    name_en: str,
    naming_contribution_id: int,
    quantifier: str,
    icon_url: Optional[str] = None,
) -> Optional[Any]:
    """
    Return the existing Ingredient for the given name, or insert a new
    one linked to `naming_contribution_id`.
    """
    existing = first(
        get(
            table=models.Ingredient,
            conditions={"ingredient_name": name_en},
        )
    )
    if existing:
        return existing

    ingredient = models.Ingredient(
        ingredient_name=name_en,
        ingredient_quantifier=quantifier,
        ingredient_icon_url=icon_url,
        ingredient_naming_contribution=naming_contribution_id,
    )
    return first(insert_record(ingredient))


# ==================== Seeding Functions ====================

def seed_ingredients() -> int:
    """
    Seed ingredients and their multilingual names.

    Returns:
        Number of ingredients inserted (existing rows are not counted).
    """
    count_inserted = 0

    for entry in SEED_INGREDIENTS:
        name_en = entry["en"]

        contribution = get_or_create_naming_contribution(
            name_en=name_en,
            name_ar=entry["ar"],
            name_fr=entry["fr"],
            contribution_type="ingredient",
            icon_url=entry.get("icon_url"),
        )
        if contribution is None:
            logger.error(
                "Skipping ingredient %r: could not resolve naming "
                "contribution",
                name_en,
            )
            continue

        existing_ingredient = first(
            get(
                table=models.Ingredient,
                conditions={"ingredient_name": name_en},
            )
        )
        if existing_ingredient:
            # Backfill the naming link, icon, and quantifier if missing.
            if (
                getattr(
                    existing_ingredient,
                    "ingredient_naming_contribution",
                    None,
                )
                is None
            ):
                existing_ingredient.ingredient_naming_contribution = (
                    contribution.id_naming_contribution
                )
                logger.debug(
                    "Backfilled naming ref for existing ingredient %r",
                    name_en,
                )
            if (
                entry.get("icon_url")
                and not existing_ingredient.ingredient_icon_url
            ):
                existing_ingredient.ingredient_icon_url = entry["icon_url"]
            if (
                entry.get("quantifier")
                and (
                    not existing_ingredient.ingredient_quantifier
                    or existing_ingredient.ingredient_quantifier == "pc"
                )
            ):
                existing_ingredient.ingredient_quantifier = entry["quantifier"]
            continue

        ingredient = _get_or_create_ingredient(
            name_en=name_en,
            naming_contribution_id=contribution.id_naming_contribution,
            quantifier=entry.get("quantifier", "pc"),
            icon_url=entry.get("icon_url"),
        )
        if ingredient:
            count_inserted += 1
            logger.debug("Seeded ingredient: %s", name_en)

    logger.info("Seeded %d new ingredients", count_inserted)
    return count_inserted


def seed_ingredient(ingredient_data: Dict[str, Any]) -> bool:
    """
    Seed a single ingredient.

    `ingredient_data` may carry `en` / `ar` / `fr` plus optional
    `quantifier` and `icon_url`. Falls back to the old
    `ingredient_name` / `ingredient_quantifier` keys for backward
    compatibility.

    Returns True if inserted, False if the ingredient already existed.
    """
    name_en = (
        ingredient_data.get("en") or ingredient_data.get("ingredient_name")
    )
    if not name_en:
        logger.warning(
            "seed_ingredient called with no name: %r", ingredient_data
        )
        return False

    existing = first(
        get(
            table=models.Ingredient,
            conditions={"ingredient_name": name_en},
        )
    )
    if existing:
        logger.debug("Ingredient already exists: %s", name_en)
        return False

    icon_url = ingredient_data.get("icon_url") or ingredient_data.get(
        "ingredient_icon_url"
    )
    quantifier = (
        ingredient_data.get("quantifier")
        or ingredient_data.get("ingredient_quantifier")
        or "pc"
    )

    contribution = get_or_create_naming_contribution(
        name_en=name_en,
        name_ar=ingredient_data.get("ar", name_en),
        name_fr=ingredient_data.get("fr", name_en),
        contribution_type="ingredient",
        icon_url=icon_url,
    )
    if contribution is None:
        logger.error("Could not create naming contribution for %r", name_en)
        return False

    ingredient = _get_or_create_ingredient(
        name_en=name_en,
        naming_contribution_id=contribution.id_naming_contribution,
        quantifier=quantifier,
        icon_url=icon_url,
    )
    if ingredient:
        logger.debug("Seeded ingredient: %s", name_en)
        return True
    return False


def seed_ingredients_from_list(
    ingredients: List[Dict[str, Any]],
) -> int:
    """
    Seed ingredients from a custom list.

    Each entry may carry `en` / `ar` / `fr` and optionally `quantifier`
    and `icon_url`. Falls back to the old `ingredient_name` /
    `ingredient_quantifier` keys for backward compatibility.

    Returns:
        Number of ingredients inserted.
    """
    count_inserted = 0

    for entry in ingredients:
        name_en = entry.get("en") or entry.get("ingredient_name")
        if not name_en:
            logger.warning("Skipping entry with no English name: %r", entry)
            continue

        icon_url = entry.get("icon_url") or entry.get("ingredient_icon_url")
        quantifier = (
            entry.get("quantifier")
            or entry.get("ingredient_quantifier")
            or "pc"
        )

        contribution = get_or_create_naming_contribution(
            name_en=name_en,
            name_ar=entry.get("ar", name_en),
            name_fr=entry.get("fr", name_en),
            contribution_type="ingredient",
            icon_url=icon_url,
        )
        if contribution is None:
            logger.error(
                "Skipping %r: could not resolve naming contribution",
                name_en,
            )
            continue

        ingredient = _get_or_create_ingredient(
            name_en=name_en,
            naming_contribution_id=contribution.id_naming_contribution,
            quantifier=quantifier,
            icon_url=icon_url,
        )
        if ingredient:
            count_inserted += 1
            logger.debug("Seeded ingredient: %s", name_en)

    logger.info(
        "Seeded %d ingredients from custom list", count_inserted
    )
    return count_inserted


# ==================== Utility Functions ====================

def get_all_seeded_ingredients() -> List[Dict[str, Any]]:
    """
    Return every ingredient with its name in all three languages.

    The primary `name` field is the English name for backward
    compatibility with callers that only want one string.
    """
    with session_scope() as session:
        rows = (
            session.query(models.Ingredient, models.NamingContribution)
            .outerjoin(
                models.NamingContribution,
                models.Ingredient.ingredient_naming_contribution
                == models.NamingContribution.id_naming_contribution,
            )
            .all()
        )

        result: List[Dict[str, Any]] = []
        for ingredient, naming in rows:
            result.append(
                {
                    "id": ingredient.id_ingredient,
                    "name": ingredient.ingredient_name,
                    "en": ingredient.ingredient_name,
                    "ar": getattr(naming, "naming_contribution_ar", None)
                    if naming
                    else None,
                    "fr": getattr(naming, "naming_contribution_fr", None)
                    if naming
                    else None,
                    "quantifier": ingredient.ingredient_quantifier,
                    "icon_url": ingredient.ingredient_icon_url,
                    "naming_contribution": ingredient.ingredient_naming_contribution,
                }
            )
        return result


def ingredient_exists(ingredient_name: str) -> bool:
    """
    Check whether an ingredient with the given English name exists.
    """
    existing = first(
        get(
            table=models.Ingredient,
            conditions={"ingredient_name": ingredient_name},
        )
    )
    return bool(existing)


def get_ingredient_by_name(
    ingredient_name: str,
) -> Optional[models.Ingredient]:
    """
    Return an ingredient by its English name, or None.
    """
    return first(
        get(
            table=models.Ingredient,
            conditions={"ingredient_name": ingredient_name},
        )
    )


def get_ingredient_by_id(
    ingredient_id: int,
) -> Optional[models.Ingredient]:
    """
    Return an ingredient by its primary key, or None.
    """
    return first(
        get(
            table=models.Ingredient,
            conditions={"id_ingredient": ingredient_id},
        )
    )


def get_ingredients_by_quantifier(
    quantifier: str,
) -> List[models.Ingredient]:
    """
    Return ingredients matching the given quantifier ('g', 'kg', 'mL',
    'pc', ...).
    """
    with session_scope() as session:
        return (
            session.query(models.Ingredient)
            .filter(models.Ingredient.ingredient_quantifier == quantifier)
            .all()
        )


def search_ingredients(
    query: str, limit: int = 20
) -> List[models.Ingredient]:
    """
    Search ingredients by English name.
    """
    with session_scope() as session:
        return (
            session.query(models.Ingredient)
            .filter(models.Ingredient.ingredient_name.ilike(f"%{query}%"))
            .limit(limit)
            .all()
        )


def delete_all_ingredients() -> int:
    """
    Delete all ingredients. Leaves the naming contributions in place,
    since other tables may reference them.

    Returns the number of ingredients deleted.
    """
    with session_scope() as session:
        count = session.query(models.Ingredient).delete()
        session.commit()
        logger.info("Deleted %d ingredients", count)
        return count


def update_ingredient_quantifier(
    ingredient_name: str, quantifier: str
) -> bool:
    """
    Update the quantifier for an ingredient.
    """
    valid_quantifiers = [
        "g",
        "kg",
        "mg",
        "L",
        "mL",
        "pc",
        "pkg",
        "box",
        "bag",
        "slice",
        "cup",
    ]
    if quantifier not in valid_quantifiers:
        logger.warning(
            "Invalid quantifier: %s. Must be one of %s",
            quantifier,
            valid_quantifiers,
        )
        return False

    with session_scope() as session:
        ingredient = (
            session.query(models.Ingredient)
            .filter(models.Ingredient.ingredient_name == ingredient_name)
            .first()
        )

        if not ingredient:
            logger.warning("Ingredient not found: %s", ingredient_name)
            return False

        ingredient.ingredient_quantifier = quantifier
        session.commit()
        logger.debug(
            "Updated quantifier for ingredient: %s -> %s",
            ingredient_name,
            quantifier,
        )
        return True


def update_ingredient_icon(ingredient_name: str, icon_url: str) -> bool:
    """
    Update the icon URL for an ingredient.
    """
    with session_scope() as session:
        ingredient = (
            session.query(models.Ingredient)
            .filter(models.Ingredient.ingredient_name == ingredient_name)
            .first()
        )

        if not ingredient:
            logger.warning("Ingredient not found: %s", ingredient_name)
            return False

        ingredient.ingredient_icon_url = icon_url
        session.commit()
        logger.debug("Updated icon for ingredient: %s", ingredient_name)
        return True


def get_ingredients_starting_with(prefix: str) -> List[models.Ingredient]:
    """
    Return ingredients whose English name starts with the given prefix.
    """
    with session_scope() as session:
        return (
            session.query(models.Ingredient)
            .filter(models.Ingredient.ingredient_name.startswith(prefix))
            .all()
        )


# ==================== Main Execution ====================

def main():
    """Main entry point for seeding ingredients."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed ingredients")
    parser.add_argument(
        "--delete-first",
        action="store_true",
        help="Delete all existing ingredients before seeding",
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

    print("Starting ingredient seeding...")

    try:
        if args.delete_first:
            delete_all_ingredients()

        count = seed_ingredients()
        print(f"Successfully seeded {count} ingredients")

        if count > 0:
            ingredients = get_all_seeded_ingredients()
            print(f"\nSeeded {len(ingredients)} ingredients:")

            from collections import defaultdict

            grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for ing in ingredients:
                first_letter = (
                    ing["name"][0].upper() if ing["name"] else "#"
                )
                grouped[first_letter].append(ing)

            for letter, ing_list in sorted(grouped.items()):
                print(f"\n  [{letter}]")
                for ing in sorted(ing_list, key=lambda x: x["name"]):
                    languages = " / ".join(
                        filter(
                            None,
                            [ing.get("en"), ing.get("fr"), ing.get("ar")],
                        )
                    )
                    quantifier_info = (
                        f" ({ing['quantifier']})" if ing["quantifier"] else ""
                    )
                    print(
                        f"    - {languages} "
                        f"(ID: {ing['id']}){quantifier_info}"
                    )

    except Exception as e:
        print(f"Failed to seed ingredients: {e}")
        raise


if __name__ == "__main__":
    main()