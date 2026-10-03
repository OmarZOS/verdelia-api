# storage/seeds/recipe_category.py
"""
Recipe category seed module using the storage broker.

Each category is backed by a NamingContribution row carrying the
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

from core.logging_config import get_logger

logger = get_logger(__name__)



# ==================== Seed Data ====================

# `en` is both the lookup anchor and the English name. Treat it as
# immutable once shipped — downstream lookups key on it.
SEED_RECIPE_CATEGORIES: List[Dict[str, str]] = [
    {
        "ar": "المقبلات والوجبات الخفيفة",
        "fr": "Entrées et en-cas",
        "en": "Appetizers & Snacks",
    },
    {
        "ar": "الشوربات واليخنات",
        "fr": "Soupes et ragoûts",
        "en": "Soups & Stews",
    },
    {
        "ar": "السلطات",
        "fr": "Salades",
        "en": "Salads",
    },
    {
        "ar": "الأطباق الرئيسية",
        "fr": "Plats principaux",
        "en": "Main Courses",
    },
    {
        "ar": "الأطباق الجانبية",
        "fr": "Accompagnements",
        "en": "Side Dishes",
    },
    {
        "ar": "المعكرونة والنودلز",
        "fr": "Pâtes et nouilles",
        "en": "Pasta & Noodles",
    },
    {
        "ar": "أطباق الكسرول",
        "fr": "Casseroles",
        "en": "Casseroles",
    },
    {
        "ar": "الإفطار والغداء المتأخر",
        "fr": "Petit-déjeuner et brunch",
        "en": "Breakfast & Brunch",
    },
    {
        "ar": "الخبز والمخبوزات",
        "fr": "Pains et pâtisseries",
        "en": "Breads & Baking",
    },
    {
        "ar": "الحلويات",
        "fr": "Desserts",
        "en": "Desserts",
    },
    {
        "ar": "المشروبات",
        "fr": "Boissons",
        "en": "Drinks & Beverages",
    },
    {
        "ar": "الصلصات والتوابل",
        "fr": "Sauces et condiments",
        "en": "Sauces & Condiments",
    },
    {
        "ar": "المطبخ العالمي",
        "fr": "Cuisine internationale",
        "en": "International Cuisine",
    },
    {
        "ar": "الأنظمة الصحية والخاصة",
        "fr": "Alimentation saine et régimes spéciaux",
        "en": "Healthy & Special Diets",
    },
    {
        "ar": "المناسبات والأعياد",
        "fr": "Fêtes et saisons",
        "en": "Holiday & Seasonal",
    },
    {
        "ar": "أطباق الأطفال والعائلة",
        "fr": "Plats pour enfants et famille",
        "en": "Kids & Family",
    },
    {
        "ar": "الطهي البطيء والطنجرة الكهربائية",
        "fr": "Mijoteuse et autocuiseur",
        "en": "Slow Cooker & Instant Pot",
    },
    {
        "ar": "سريع وسهل",
        "fr": "Rapide et facile",
        "en": "Quick & Easy",
    },
    {
        "ar": "وصفات بصينية واحدة",
        "fr": "Recettes à une seule plaque",
        "en": "One-Pan Recipes",
    },
    {
        "ar": "الشوي والباربكيو",
        "fr": "Grillades et barbecue",
        "en": "Grilling & BBQ",
    },
]


# Optional: icon URLs keyed by English name. Kept separate from the
# translation data so translations and icons can be edited independently.
SEED_RECIPE_CATEGORY_ICONS: Dict[str, str] = {
    "Appetizers & Snacks": "https://example.com/icons/appetizers.png",
    "Soups & Stews": "https://example.com/icons/soups.png",
    "Salads": "https://example.com/icons/salads.png",
    "Main Courses": "https://example.com/icons/main-courses.png",
    "Desserts": "https://example.com/icons/desserts.png",
}


# ==================== Helpers ====================

def _get_or_create_recipe_category(
    *,
    name_en: str,
    naming_contribution_id: int,
    icon_url: Optional[str] = None,
) -> Optional[Any]:
    """
    Return the existing RecipeCategory for the given name, or insert a
    new one linked to `naming_contribution_id`.
    """
    existing = first(
        get(
            table=models.RecipeCategory,
            conditions={"recipe_category_name": name_en},
        )
    )
    if existing:
        return existing

    category = models.RecipeCategory(
        recipe_category_name=name_en,
        recipe_category_icon_url=icon_url,
        recipe_category_naming=naming_contribution_id,
    )
    return first(insert_record(category))


# ==================== Seeding Functions ====================

def seed_recipe_categories(use_icons: bool = False) -> int:
    """
    Seed recipe categories and their multilingual names.

    Args:
        use_icons: If True, attach the icon URLs from
            SEED_RECIPE_CATEGORY_ICONS to both the naming contribution
            and the category.

    Returns:
        Number of recipe categories inserted (existing rows are not
        counted).
    """
    count_inserted = 0

    for entry in SEED_RECIPE_CATEGORIES:
        name_en = entry["en"]
        icon_url = (
            SEED_RECIPE_CATEGORY_ICONS.get(name_en) if use_icons else None
        )

        contribution = get_or_create_naming_contribution(
            name_en=name_en,
            name_ar=entry["ar"],
            name_fr=entry["fr"],
            contribution_type="recipe",
            icon_url=icon_url,
        )
        if contribution is None:
            logger.error(
                "Skipping recipe category %r: could not resolve naming "
                "contribution",
                name_en,
            )
            continue

        existing_category = first(
            get(
                table=models.RecipeCategory,
                conditions={"recipe_category_name": name_en},
            )
        )
        if existing_category:
            # Backfill the naming link and icon if they're missing.
            if getattr(
                existing_category, "recipe_category_naming", None
            ) is None:
                existing_category.recipe_category_naming = (
                    contribution.id_naming_contribution
                )
                logger.debug(
                    "Backfilled naming ref for existing category %r",
                    name_en,
                )
            if icon_url and not existing_category.recipe_category_icon_url:
                existing_category.recipe_category_icon_url = icon_url
            continue

        category = _get_or_create_recipe_category(
            name_en=name_en,
            naming_contribution_id=contribution.id_naming_contribution,
            icon_url=icon_url,
        )
        if category:
            count_inserted += 1
            logger.debug("Seeded recipe category: %s", name_en)

    logger.info("Seeded %d new recipe categories", count_inserted)
    return count_inserted


def seed_recipe_categories_from_list(
    categories: List[Dict[str, Any]],
) -> int:
    """
    Seed recipe categories from a custom list.

    Each entry may carry `en` / `ar` / `fr` for the naming contribution,
    and optionally `recipe_category_icon_url`. The English name is the
    lookup key.

    Returns:
        Number of categories inserted.
    """
    count_inserted = 0

    for entry in categories:
        name_en = entry.get("en") or entry.get("recipe_category_name")
        if not name_en:
            logger.warning(
                "Skipping entry with no English name: %r", entry
            )
            continue

        icon_url = entry.get("recipe_category_icon_url")

        contribution = get_or_create_naming_contribution(
            name_en=name_en,
            name_ar=entry.get("ar", name_en),
            name_fr=entry.get("fr", name_en),
            contribution_type="recipe",
            icon_url=icon_url,
        )
        if contribution is None:
            logger.error(
                "Skipping %r: could not resolve naming contribution",
                name_en,
            )
            continue

        category = _get_or_create_recipe_category(
            name_en=name_en,
            naming_contribution_id=contribution.id_naming_contribution,
            icon_url=icon_url,
        )
        if category:
            count_inserted += 1
            logger.debug("Seeded recipe category: %s", name_en)

    logger.info(
        "Seeded %d recipe categories from custom list", count_inserted
    )
    return count_inserted


# ==================== Utility Functions ====================

def get_all_seeded_categories() -> List[Dict[str, Any]]:
    """
    Return every recipe category with its name in all three languages.

    The primary `name` field is the English name for backward
    compatibility with callers that only want one string.
    """
    with session_scope() as session:
        rows = (
            session.query(models.RecipeCategory, models.NamingContribution)
            .outerjoin(
                models.NamingContribution,
                models.RecipeCategory.recipe_category_naming
                == models.NamingContribution.id_naming_contribution,
            )
            .all()
        )

        result: List[Dict[str, Any]] = []
        for category, naming in rows:
            result.append(
                {
                    "id": category.id_recipe_category,
                    "name": category.recipe_category_name,
                    "en": category.recipe_category_name,
                    "ar": getattr(naming, "naming_contribution_ar", None)
                    if naming
                    else None,
                    "fr": getattr(naming, "naming_contribution_fr", None)
                    if naming
                    else None,
                    "icon_url": category.recipe_category_icon_url,
                }
            )
        return result


def category_exists(category_name: str) -> bool:
    """
    Check whether a recipe category with the given English name exists.
    """
    existing = first(
        get(
            table=models.RecipeCategory,
            conditions={"recipe_category_name": category_name},
        )
    )
    return bool(existing)


def seed_recipe_category(category_data: Dict[str, Any]) -> bool:
    """
    Seed a single recipe category.

    `category_data` may carry `en` / `ar` / `fr` and optionally
    `recipe_category_icon_url`. Falls back to `recipe_category_name`
    as the English name for backward compatibility with the old shape.

    Returns True if inserted, False if the category already existed.
    """
    name_en = category_data.get("en") or category_data.get(
        "recipe_category_name"
    )
    if not name_en:
        logger.warning(
            "seed_recipe_category called with no name: %r", category_data
        )
        return False

    existing = first(
        get(
            table=models.RecipeCategory,
            conditions={"recipe_category_name": name_en},
        )
    )
    if existing:
        logger.debug("Category already exists: %s", name_en)
        return False

    icon_url = category_data.get("recipe_category_icon_url")

    contribution = get_or_create_naming_contribution(
        name_en=name_en,
        name_ar=category_data.get("ar", name_en),
        name_fr=category_data.get("fr", name_en),
        contribution_type="recipe",
        icon_url=icon_url,
    )
    if contribution is None:
        logger.error("Could not create naming contribution for %r", name_en)
        return False

    category = _get_or_create_recipe_category(
        name_en=name_en,
        naming_contribution_id=contribution.id_naming_contribution,
        icon_url=icon_url,
    )
    if category:
        logger.debug("Seeded recipe category: %s", name_en)
        return True
    return False


def delete_all_recipe_categories() -> int:
    """
    Delete all recipe categories. Leaves the naming contributions in
    place, since other tables may reference them.

    Returns the number of categories deleted.
    """
    with session_scope() as session:
        count = session.query(models.RecipeCategory).delete()
        session.commit()
        logger.info("Deleted %d recipe categories", count)
        return count


# ==================== Main Execution ====================

def main():
    """Main entry point for seeding recipe categories."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed recipe categories")
    parser.add_argument(
        "--with-icons",
        action="store_true",
        help="Attach icon URLs to naming contributions and categories",
    )
    parser.add_argument(
        "--delete-first",
        action="store_true",
        help="Delete all existing categories before seeding",
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

    print("Starting recipe category seeding...")

    try:
        if args.delete_first:
            delete_all_recipe_categories()

        count = seed_recipe_categories(use_icons=args.with_icons)
        print(f"Successfully seeded {count} recipe categories")

        if count > 0:
            categories = get_all_seeded_categories()
            print("\nSeeded categories:")
            for cat in categories:
                languages = " / ".join(
                    filter(None, [cat.get("en"), cat.get("fr"), cat.get("ar")])
                )
                print(f"  - {languages} (ID: {cat['id']})")

    except Exception as e:
        print(f"Failed to seed recipe categories: {e}")
        raise


if __name__ == "__main__":
    main()