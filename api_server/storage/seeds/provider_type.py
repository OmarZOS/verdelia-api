# storage/seeds/product_provider_type.py
"""
Product provider type seed module using the storage broker.

Each provider type is backed by a NamingContribution row carrying the
Arabic / French / English names. Seeding is idempotent: re-running
inserts nothing.

The canonical identity of a provider type is its dotted key
(`domain.subdomain.key`, e.g. `provider.food.restaurant`), stored in
`product_provider_type_name`. Human-readable display names come from
the joined NamingContribution row — never from the name column.
"""

import logging
from typing import Any, Dict, List, Optional

from storage.storage_broker import insert_record, get, session_scope
from core.models import models

from core.logging_config import get_logger

logger = get_logger(__name__)

# ==================== Seed Data ====================

# `key` is the immutable lookup anchor, stored in
# `product_provider_type_name`. Treat it as frozen once shipped —
# downstream lookups and NamingContribution rows key on it.
SEED_PROVIDER_TYPES: List[Dict[str, str]] = [
    # ══════════════════════════════════════════════════════════════
    # DOMAIN: food
    # ══════════════════════════════════════════════════════════════
    # ── food · dining ────────────────────────────────────────────
    {"key": "food.dining.restaurant",          "en": "Restaurant",              "fr": "Restaurant",                    "ar": "مطعم"},
    {"key": "food.dining.cafe",                "en": "Cafe",                    "fr": "Café",                          "ar": "مقهى"},
    {"key": "food.dining.fast_food",           "en": "Fast Food",               "fr": "Restauration rapide",           "ar": "وجبات سريعة"},
    {"key": "food.dining.food_truck",          "en": "Food Truck",              "fr": "Camion-restaurant",             "ar": "شاحنة طعام"},
    {"key": "food.dining.catering",            "en": "Catering",                "fr": "Traiteur",                      "ar": "خدمات التموين"},
    {"key": "food.dining.juice_bar",           "en": "Juice Bar",               "fr": "Bar à jus",                     "ar": "بار عصائر"},

    # ── food · production ────────────────────────────────────────
    {"key": "food.production.bakery",          "en": "Bakery",                  "fr": "Boulangerie",                   "ar": "مخبزة"},
    {"key": "food.production.factory",         "en": "Factory",                 "fr": "Usine",                         "ar": "مصنع"},
    {"key": "food.production.ice_cream",       "en": "Ice Cream Shop",          "fr": "Glacier",                       "ar": "متجر مثلجات"},

    # ── food · specialty ─────────────────────────────────────────
    {"key": "food.specialty.butcher",          "en": "Butcher",                 "fr": "Boucherie",                     "ar": "جزارة"},
    {"key": "food.specialty.fishmonger",       "en": "Fishmonger",              "fr": "Poissonnerie",                  "ar": "سمكة"},
    {"key": "food.specialty.deli",             "en": "Delicatessen",            "fr": "Charcuterie",                   "ar": "مأكولات جاهزة"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: retail
    # ══════════════════════════════════════════════════════════════
    # ── retail · food_retail ─────────────────────────────────────
    {"key": "retail.food_retail.supermarket",  "en": "Supermarket",             "fr": "Supermarché",                   "ar": "سوبر ماركت"},
    {"key": "retail.food_retail.grocery_store","en": "Grocery Store",           "fr": "Épicerie",                      "ar": "بقالة"},
    {"key": "retail.food_retail.convenience_store","en": "Convenience Store",   "fr": "Supérette",                     "ar": "متجر صغير"},
    {"key": "retail.food_retail.hypermarket",  "en": "Hypermarket",             "fr": "Hypermarché",                   "ar": "هايبر ماركت"},

    # ── retail · fashion ─────────────────────────────────────────
    {"key": "retail.fashion.clothing_store",   "en": "Clothing Store",          "fr": "Boutique de vêtements",         "ar": "متجر ملابس"},
    {"key": "retail.fashion.shoe_store",       "en": "Shoe Store",              "fr": "Magasin de chaussures",         "ar": "متجر أحذية"},
    {"key": "retail.fashion.jewelry_store",    "en": "Jewelry Store",           "fr": "Bijouterie",                    "ar": "متجر مجوهرات"},

    # ── retail · home_living ─────────────────────────────────────
    {"key": "retail.home_living.furniture_store","en": "Furniture Store",       "fr": "Magasin de meubles",            "ar": "متجر أثاث"},
    {"key": "retail.home_living.electronics_store","en": "Electronics Store",   "fr": "Magasin d'électronique",        "ar": "متجر إلكترونيات"},
    {"key": "retail.home_living.florist",      "en": "Florist",                 "fr": "Fleuriste",                     "ar": "متجر زهور"},

    # ── retail · lifestyle ───────────────────────────────────────
    {"key": "retail.lifestyle.bookstore",      "en": "Bookstore",               "fr": "Librairie",                     "ar": "مكتبة"},
    {"key": "retail.lifestyle.toy_store",      "en": "Toy Store",               "fr": "Magasin de jouets",             "ar": "متجر ألعاب"},
    {"key": "retail.lifestyle.sports_store",   "en": "Sports Store",            "fr": "Magasin de sport",              "ar": "متجر رياضي"},
    {"key": "retail.lifestyle.pet_store",      "en": "Pet Store",               "fr": "Animalerie",                    "ar": "متجر حيوانات"},

    # ── retail · health_retail ───────────────────────────────────
    {"key": "retail.health_retail.pharmacy",   "en": "Pharmacy",                "fr": "Pharmacie",                     "ar": "صيدلية"},
    {"key": "retail.health_retail.optician",   "en": "Optician",                "fr": "Opticien",                      "ar": "متجر نظارات"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: trade
    # ══════════════════════════════════════════════════════════════
    # ── trade · distribution ─────────────────────────────────────
    {"key": "trade.distribution.distributor",  "en": "Distributor",             "fr": "Distributeur",                  "ar": "موزّع"},
    {"key": "trade.distribution.wholesaler",   "en": "Wholesaler",              "fr": "Grossiste",                     "ar": "تاجر جملة"},

    # ── trade · international ────────────────────────────────────
    {"key": "trade.international.importer",    "en": "Importer",                "fr": "Importateur",                   "ar": "مستورد"},
    {"key": "trade.international.exporter",    "en": "Exporter",                "fr": "Exportateur",                   "ar": "مصدر"},

    # ── trade · intermediary ─────────────────────────────────────
    {"key": "trade.intermediary.broker",       "en": "Broker",                  "fr": "Courtier",                      "ar": "وسيط"},
    {"key": "trade.intermediary.agent",        "en": "Commercial Agent",        "fr": "Agent commercial",              "ar": "وكيل تجاري"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: services
    # ══════════════════════════════════════════════════════════════
    # ── services · construction ──────────────────────────────────
    {"key": "services.construction.plumber",   "en": "Plumber",                 "fr": "Plombier",                      "ar": "سبّاك"},
    {"key": "services.construction.electrician","en": "Electrician",            "fr": "Électricien",                   "ar": "كهربائي"},
    {"key": "services.construction.carpenter", "en": "Carpenter",               "fr": "Charpentier",                   "ar": "نجار"},
    {"key": "services.construction.painter",   "en": "Painter",                 "fr": "Peintre",                       "ar": "دهّان"},
    {"key": "services.construction.mason",     "en": "Mason",                   "fr": "Maçon",                         "ar": "بنّاء"},
    {"key": "services.construction.locksmith", "en": "Locksmith",               "fr": "Serrurier",                     "ar": "حداد أقفال"},

    # ── services · home ──────────────────────────────────────────
    {"key": "services.home.cleaning",          "en": "Cleaning Service",        "fr": "Service de nettoyage",          "ar": "خدمة تنظيف"},
    {"key": "services.home.moving",            "en": "Moving Service",          "fr": "Déménagement",                  "ar": "خدمة نقل"},
    {"key": "services.home.gardening",         "en": "Gardening Service",       "fr": "Jardinage",                     "ar": "خدمة بستنة"},
    {"key": "services.home.pest_control",      "en": "Pest Control",            "fr": "Dératisation",                  "ar": "مكافحة الحشرات"},
    {"key": "services.home.appliance_repair",  "en": "Appliance Repair",        "fr": "Réparation d'électroménager",   "ar": "إصلاح الأجهزة"},

    # ── services · professional ──────────────────────────────────
    {"key": "services.professional.legal",     "en": "Legal Services",          "fr": "Services juridiques",           "ar": "خدمات قانونية"},
    {"key": "services.professional.accounting","en": "Accounting Service",      "fr": "Comptabilité",                  "ar": "محاسبة"},
    {"key": "services.professional.consulting","en": "Consulting",              "fr": "Conseil",                       "ar": "استشارات"},
    {"key": "services.professional.translation","en": "Translation Service",    "fr": "Service de traduction",         "ar": "خدمة ترجمة"},

    # ── services · technology ────────────────────────────────────
    {"key": "services.technology.it_services", "en": "IT Services",             "fr": "Services informatiques",        "ar": "خدمات تقنية المعلومات"},
    {"key": "services.technology.web_development","en": "Web Development",      "fr": "Développement web",             "ar": "تطوير الويب"},
    {"key": "services.technology.digital_marketing","en": "Digital Marketing",  "fr": "Marketing digital",             "ar": "التسويق الرقمي"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: beauty
    # ══════════════════════════════════════════════════════════════
    # ── beauty · hair ────────────────────────────────────────────
    {"key": "beauty.hair.hair_salon",          "en": "Hair Salon",              "fr": "Salon de coiffure",             "ar": "صالون حلاقة"},
    {"key": "beauty.hair.barbershop",          "en": "Barbershop",              "fr": "Barbier",                       "ar": "محل حلاقة رجالية"},

    # ── beauty · wellness ────────────────────────────────────────
    {"key": "beauty.wellness.spa",             "en": "Spa",                     "fr": "Spa",                           "ar": "منتجع صحي"},
    {"key": "beauty.wellness.massage",         "en": "Massage Parlor",          "fr": "Salon de massage",              "ar": "صالون تدليك"},

    # ── beauty · aesthetics ──────────────────────────────────────
    {"key": "beauty.aesthetics.nail_salon",    "en": "Nail Salon",              "fr": "Salon de manucure",             "ar": "صالون أظافر"},
    {"key": "beauty.aesthetics.makeup_artist", "en": "Makeup Artist",           "fr": "Maquilleur",                    "ar": "خبير مكياج"},
    {"key": "beauty.aesthetics.skincare",      "en": "Skincare Clinic",         "fr": "Clinique de soins de peau",     "ar": "عيادة عناية بالبشرة"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: health
    # ══════════════════════════════════════════════════════════════
    # ── health · facilities ──────────────────────────────────────
    {"key": "health.facilities.clinic",        "en": "Clinic",                  "fr": "Clinique",                      "ar": "عيادة"},
    {"key": "health.facilities.hospital",      "en": "Hospital",                "fr": "Hôpital",                       "ar": "مستشفى"},
    {"key": "health.facilities.dental_clinic", "en": "Dental Clinic",           "fr": "Clinique dentaire",             "ar": "عيادة أسنان"},
    {"key": "health.facilities.veterinary",    "en": "Veterinary Clinic",       "fr": "Clinique vétérinaire",          "ar": "عيادة بيطرية"},

    # ── health · diagnostics ─────────────────────────────────────
    {"key": "health.diagnostics.laboratory",   "en": "Laboratory",              "fr": "Laboratoire",                   "ar": "مختبر"},
    {"key": "health.diagnostics.imaging_center","en": "Imaging Center",         "fr": "Centre d'imagerie",             "ar": "مركز تصوير"},

    # ── health · therapy ─────────────────────────────────────────
    {"key": "health.therapy.physiotherapy",    "en": "Physiotherapy Center",    "fr": "Centre de kinésithérapie",      "ar": "مركز علاج طبيعي"},
    {"key": "health.therapy.psychology",       "en": "Psychology Practice",     "fr": "Cabinet de psychologie",        "ar": "عيادة نفسية"},
    {"key": "health.therapy.nutritionist",     "en": "Nutritionist",            "fr": "Nutritionniste",                "ar": "أخصائي تغذية"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: education
    # ══════════════════════════════════════════════════════════════
    # ── education · institutions ─────────────────────────────────
    {"key": "education.institutions.school",   "en": "School",                  "fr": "École",                         "ar": "مدرسة"},
    {"key": "education.institutions.university","en": "University",              "fr": "Université",                    "ar": "جامعة"},

    # ── education · training ─────────────────────────────────────
    {"key": "education.training.training_center","en": "Training Center",       "fr": "Centre de formation",           "ar": "مركز تدريب"},
    {"key": "education.training.language_school","en": "Language School",       "fr": "École de langues",              "ar": "مدرسة لغات"},
    {"key": "education.training.tutoring",     "en": "Tutoring Center",         "fr": "Centre de soutien scolaire",    "ar": "مركز دروس خصوصية"},
    {"key": "education.training.driving_school","en": "Driving School",         "fr": "Auto-école",                    "ar": "مدرسة تعليم القيادة"},
    {"key": "education.training.music_school", "en": "Music School",            "fr": "École de musique",              "ar": "مدرسة موسيقى"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: logistics
    # ══════════════════════════════════════════════════════════════
    # ── logistics · transport ────────────────────────────────────
    {"key": "logistics.transport.courier",     "en": "Courier Service",         "fr": "Service de courrier",           "ar": "خدمة بريد سريع"},
    {"key": "logistics.transport.freight",     "en": "Freight Forwarder",       "fr": "Transitaire",                   "ar": "وكيل شحن"},

    # ── logistics · storage ──────────────────────────────────────
    {"key": "logistics.storage.warehouse",     "en": "Warehouse",               "fr": "Entrepôt",                      "ar": "مستودع"},
    {"key": "logistics.storage.fulfillment",   "en": "Fulfillment Center",      "fr": "Centre de distribution",        "ar": "مركز تنفيذ الطلبات"},
    {"key": "logistics.storage.cold_storage",  "en": "Cold Storage",            "fr": "Entrepôt frigorifique",         "ar": "مخزن مبرد"},

    # ── logistics · customs ──────────────────────────────────────
    {"key": "logistics.customs.broker",        "en": "Customs Broker",          "fr": "Courtier en douane",            "ar": "وسيط جمركي"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: automotive
    # ══════════════════════════════════════════════════════════════
    # ── automotive · sales ───────────────────────────────────────
    {"key": "automotive.sales.dealership",     "en": "Car Dealership",          "fr": "Concession automobile",         "ar": "معرض سيارات"},
    {"key": "automotive.sales.rental",         "en": "Car Rental",              "fr": "Location de voitures",          "ar": "تأجير سيارات"},

    # ── automotive · maintenance ─────────────────────────────────
    {"key": "automotive.maintenance.repair_shop","en": "Repair Shop",           "fr": "Atelier de réparation",         "ar": "ورشة إصلاح"},
    {"key": "automotive.maintenance.tire_shop","en": "Tire Shop",               "fr": "Magasin de pneus",              "ar": "متجر إطارات"},
    {"key": "automotive.maintenance.car_wash", "en": "Car Wash",                "fr": "Lavage auto",                   "ar": "غسيل سيارات"},

    # ── automotive · parts ───────────────────────────────────────
    {"key": "automotive.parts.parts_shop",     "en": "Auto Parts Shop",         "fr": "Magasin de pièces auto",        "ar": "متجر قطع غيار"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: agriculture
    # ══════════════════════════════════════════════════════════════
    # ── agriculture · production ─────────────────────────────────
    {"key": "agriculture.production.farm",     "en": "Farm",                    "fr": "Ferme",                         "ar": "مزرعة"},
    {"key": "agriculture.production.greenhouse","en": "Greenhouse",             "fr": "Serre",                         "ar": "بيت محمي"},
    {"key": "agriculture.production.livestock","en": "Livestock Farm",          "fr": "Élevage",                       "ar": "مزرعة مواشي"},

    # ── agriculture · supply ─────────────────────────────────────
    {"key": "agriculture.supply.cooperative",  "en": "Cooperative",             "fr": "Coopérative",                   "ar": "تعاونية"},
    {"key": "agriculture.supply.nursery",      "en": "Plant Nursery",           "fr": "Pépinière",                     "ar": "مشتل"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: hospitality
    # ══════════════════════════════════════════════════════════════
    # ── hospitality · accommodation ──────────────────────────────
    {"key": "hospitality.accommodation.hotel", "en": "Hotel",                   "fr": "Hôtel",                         "ar": "فندق"},
    {"key": "hospitality.accommodation.motel", "en": "Motel",                   "fr": "Motel",                         "ar": "موتيل"},
    {"key": "hospitality.accommodation.guesthouse","en": "Guesthouse",          "fr": "Maison d'hôtes",                "ar": "بيت ضيافة"},
    {"key": "hospitality.accommodation.hostel","en": "Hostel",                  "fr": "Auberge",                       "ar": "نزل شبابي"},

    # ── hospitality · events ─────────────────────────────────────
    {"key": "hospitality.events.event_venue",  "en": "Event Venue",             "fr": "Salle des fêtes",               "ar": "قاعة مناسبات"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: finance
    # ══════════════════════════════════════════════════════════════
    # ── finance · banking ────────────────────────────────────────
    {"key": "finance.banking.bank",            "en": "Bank",                    "fr": "Banque",                        "ar": "بنك"},
    {"key": "finance.banking.microfinance",    "en": "Microfinance",            "fr": "Microfinance",                  "ar": "تمويل صغير"},
    {"key": "finance.banking.exchange",        "en": "Currency Exchange",       "fr": "Bureau de change",              "ar": "صرافة"},

    # ── finance · insurance ──────────────────────────────────────
    {"key": "finance.insurance.insurance",     "en": "Insurance Company",       "fr": "Compagnie d'assurance",         "ar": "شركة تأمين"},
]


# Optional: icon URLs keyed by the immutable provider type key.
# Kept separate from translation data so translations and icons can
# be edited independently.
SEED_PROVIDER_TYPE_ICONS: Dict[str, str] = {
    "provider.food.restaurant":      "https://example.com/icons/restaurant.png",
    "provider.food.bakery":          "https://example.com/icons/bakery.png",
    "provider.food.factory":         "https://example.com/icons/factory.png",
    "provider.retail.supermarket":   "https://example.com/icons/supermarket.png",
    "provider.retail.grocery_store": "https://example.com/icons/grocery.png",
    "provider.trade.distributor":    "https://example.com/icons/distributor.png",
}


# ==================== Helpers ====================

def _get_or_create_naming_contribution(
    *,
    name_en: str,
    name_ar: str,
    name_fr: str,
    icon_url: Optional[str] = None,
    contribution_type: str = "provider",
) -> Optional[Any]:
    """
    Return the existing NamingContribution for the given English name,
    or insert a new one. Returns the contribution row (with its id
    populated) on success, None on failure.

    The English name doubles as the naming row's natural key, since
    every provider type key is unique and maps 1:1 to a naming row.
    """
    existing = get(
        table=models.NamingContribution,
        conditions={"naming_contribution_en": name_en},
    )
    if existing:
        return existing[0] if isinstance(existing, list) else existing

    contribution = models.NamingContribution(
        naming_contribution_en=name_en,
        naming_contribution_ar=name_ar,
        naming_contribution_fr=name_fr,
        naming_contribution_status="APP_TRANSLATED",
        naming_contribution_type=contribution_type,
        naming_contribution_icon_url=icon_url,
        naming_contribution_by=None,
        naming_contribution_app_version=None,
    )
    result = insert_record(contribution)
    return result if result else None


def _get_or_create_provider_type(
    *,
    key: str,
    naming_contribution_id: int,
    icon_url: Optional[str] = None,
) -> Optional[Any]:
    """
    Return the existing ProductProviderType for the given dotted key,
    or insert a new one linked to `naming_contribution_id`.

    `product_provider_type_name` stores the key verbatim.
    """
    existing = get(
        table=models.ProductProviderType,
        conditions={"product_provider_type_name": key},
    )
    if existing:
        return existing[0] if isinstance(existing, list) else existing

    provider_type = models.ProductProviderType(
        product_provider_type_name=key,
        product_provider_type_icon_url=icon_url,
        product_provider_type_naming_ref=naming_contribution_id,
    )
    result = insert_record(provider_type)
    return result if result else None


# ==================== Seeding Functions ====================

def seed_product_provider_types(use_icons: bool = False) -> int:
    """
    Seed product provider types and their multilingual names.

    Args:
        use_icons: If True, attach the icon URLs from
            SEED_PROVIDER_TYPE_ICONS to both the naming contribution
            and the provider type.

    Returns:
        Number of provider types inserted (existing rows are not
        counted).
    """
    count_inserted = 0

    for entry in SEED_PROVIDER_TYPES:
        key = entry["key"]
        name_en = entry["en"]
        icon_url = SEED_PROVIDER_TYPE_ICONS.get(key) if use_icons else None

        contribution = _get_or_create_naming_contribution(
            name_en=name_en,
            name_ar=entry["ar"],
            name_fr=entry["fr"],
            icon_url=icon_url,
        )
        if contribution is None:
            logger.error(
                "Skipping provider type %r: could not resolve naming "
                "contribution",
                key,
            )
            continue

        existing_type = get(
            table=models.ProductProviderType,
            conditions={"product_provider_type_name": key},
        )
        existing_type_row = (
            existing_type[0]
            if isinstance(existing_type, list) and existing_type
            else existing_type
        )

        if existing_type_row:
            # Backfill the naming link and icon if they're missing.
            if (
                getattr(
                    existing_type_row,
                    "product_provider_type_naming_ref",
                    None,
                )
                is None
            ):
                existing_type_row.product_provider_type_naming_ref = (
                    contribution.id_naming_contribution
                )
                logger.debug(
                    "Backfilled naming ref for existing provider type %r",
                    key,
                )
            if (
                icon_url
                and not existing_type_row.product_provider_type_icon_url
            ):
                existing_type_row.product_provider_type_icon_url = icon_url
            continue

        provider_type = _get_or_create_provider_type(
            key=key,
            naming_contribution_id=contribution.id_naming_contribution,
            icon_url=icon_url,
        )
        if provider_type:
            count_inserted += 1
            logger.debug("Seeded product provider type: %s", key)

    logger.info("Seeded %d new product provider types", count_inserted)
    return count_inserted


def seed_product_provider_type(provider_type_data: Dict[str, Any]) -> bool:
    """
    Seed a single product provider type.

    `provider_type_data` must carry `key`; it may carry `en` / `ar` /
    `fr` and optionally `product_provider_type_icon_url`. Falls back
    to using the key as the English name when `en` is absent.

    Returns True if inserted, False if the provider type already
    existed or the entry was invalid.
    """
    key = provider_type_data.get("key")
    if not key:
        logger.warning(
            "seed_product_provider_type called with no key: %r",
            provider_type_data,
        )
        return False

    name_en = provider_type_data.get("en") or key

    existing = get(
        table=models.ProductProviderType,
        conditions={"product_provider_type_name": key},
    )
    if existing:
        logger.debug("Provider type already exists: %s", key)
        return False

    icon_url = provider_type_data.get("product_provider_type_icon_url")

    contribution = _get_or_create_naming_contribution(
        name_en=name_en,
        name_ar=provider_type_data.get("ar", name_en),
        name_fr=provider_type_data.get("fr", name_en),
        icon_url=icon_url,
    )
    if contribution is None:
        logger.error("Could not create naming contribution for %r", key)
        return False

    provider_type = _get_or_create_provider_type(
        key=key,
        naming_contribution_id=contribution.id_naming_contribution,
        icon_url=icon_url,
    )
    if provider_type:
        logger.debug("Seeded product provider type: %s", key)
        return True
    return False


def seed_product_provider_types_from_list(
    provider_types: List[Dict[str, Any]],
) -> int:
    """
    Seed product provider types from a custom list.

    Each entry must carry `key`; it may carry `en` / `ar` / `fr` for
    the naming contribution, and optionally
    `product_provider_type_icon_url`.

    Returns:
        Number of provider types inserted.
    """
    count_inserted = 0

    for entry in provider_types:
        key = entry.get("key")
        if not key:
            logger.warning("Skipping entry with no key: %r", entry)
            continue

        name_en = entry.get("en") or key
        icon_url = entry.get("product_provider_type_icon_url")

        contribution = _get_or_create_naming_contribution(
            name_en=name_en,
            name_ar=entry.get("ar", name_en),
            name_fr=entry.get("fr", name_en),
            icon_url=icon_url,
        )
        if contribution is None:
            logger.error(
                "Skipping %r: could not resolve naming contribution",
                key,
            )
            continue

        provider_type = _get_or_create_provider_type(
            key=key,
            naming_contribution_id=contribution.id_naming_contribution,
            icon_url=icon_url,
        )
        if provider_type:
            count_inserted += 1
            logger.debug("Seeded product provider type: %s", key)

    logger.info(
        "Seeded %d product provider types from custom list", count_inserted
    )
    return count_inserted


# ==================== Utility Functions ====================

def get_all_seeded_provider_types() -> List[Dict[str, Any]]:
    """
    Return every provider type with its name in all three languages.

    `key` is the value stored in `product_provider_type_name`; `name`
    is the English display string for backward compatibility with
    callers that only want one string.
    """
    with session_scope() as session:
        rows = (
            session.query(
                models.ProductProviderType,
                models.NamingContribution,
            )
            .outerjoin(
                models.NamingContribution,
                models.ProductProviderType.product_provider_type_naming_ref
                == models.NamingContribution.id_naming_contribution,
            )
            .all()
        )

        result: List[Dict[str, Any]] = []
        for provider_type, naming in rows:
            key = provider_type.product_provider_type_name
            name_en = (
                getattr(naming, "naming_contribution_en", None) or key
                if naming
                else key
            )
            result.append(
                {
                    "id": provider_type.id_product_provider_type,
                    "key": key,
                    "name": name_en,
                    "en": name_en,
                    "ar": getattr(naming, "naming_contribution_ar", None)
                    if naming
                    else None,
                    "fr": getattr(naming, "naming_contribution_fr", None)
                    if naming
                    else None,
                    "icon_url": provider_type.product_provider_type_icon_url,
                    "naming_ref": provider_type.product_provider_type_naming_ref,
                }
            )
        return result


def provider_type_exists(provider_type_key: str) -> bool:
    """
    Check whether a provider type with the given dotted key exists.
    """
    existing = get(
        table=models.ProductProviderType,
        conditions={"product_provider_type_name": provider_type_key},
    )
    return bool(existing)


def get_provider_type_by_key(
    provider_type_key: str,
) -> Optional[models.ProductProviderType]:
    """
    Return a provider type by its dotted key, or None.
    """
    result = get(
        table=models.ProductProviderType,
        conditions={"product_provider_type_name": provider_type_key},
    )
    if not result:
        return None
    return result[0] if isinstance(result, list) else result


def get_provider_type_by_id(
    provider_type_id: int,
) -> Optional[models.ProductProviderType]:
    """
    Return a provider type by its primary key, or None.
    """
    result = get(
        table=models.ProductProviderType,
        conditions={"id_product_provider_type": provider_type_id},
    )
    if not result:
        return None
    return result[0] if isinstance(result, list) else result


def delete_all_product_provider_types() -> int:
    """
    Delete all product provider types. Leaves the naming contributions
    in place, since other tables may reference them.

    Returns the number of provider types deleted.
    """
    with session_scope() as session:
        count = session.query(models.ProductProviderType).delete()
        session.commit()
        logger.info("Deleted %d product provider types", count)
        return count


def update_provider_type_icon(
    provider_type_key: str, icon_url: str
) -> bool:
    """
    Update the icon URL for a provider type, addressed by its key.
    """
    with session_scope() as session:
        provider_type = (
            session.query(models.ProductProviderType)
            .filter(
                models.ProductProviderType.product_provider_type_name
                == provider_type_key
            )
            .first()
        )

        if not provider_type:
            logger.warning("Provider type not found: %s", provider_type_key)
            return False

        provider_type.product_provider_type_icon_url = icon_url
        session.commit()
        logger.debug("Updated icon for provider type: %s", provider_type_key)
        return True


# ==================== Main Execution ====================

def main():
    """Main entry point for seeding product provider types."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed product provider types")
    parser.add_argument(
        "--with-icons",
        action="store_true",
        help="Attach icon URLs to naming contributions and provider types",
    )
    parser.add_argument(
        "--delete-first",
        action="store_true",
        help="Delete all existing provider types before seeding",
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

    print("Starting product provider type seeding...")

    try:
        if args.delete_first:
            delete_all_product_provider_types()

        count = seed_product_provider_types(use_icons=args.with_icons)
        print(f"Successfully seeded {count} product provider types")

        if count > 0:
            provider_types = get_all_seeded_provider_types()
            print("\nSeeded provider types:")
            for pt in provider_types:
                languages = " / ".join(
                    filter(None, [pt.get("en"), pt.get("fr"), pt.get("ar")])
                )
                icon_info = (
                    f" (icon: {pt['icon_url']})" if pt["icon_url"] else ""
                )
                print(
                    f"  - [{pt['key']}] {languages} (ID: {pt['id']})"
                    f"{icon_info}"
                )

    except Exception as e:
        print(f"Failed to seed product provider types: {e}")
        raise


if __name__ == "__main__":
    main()