# storage/seeds/plans.py
"""
Seed plans, plan features, and plan limits.

Idempotent: re-running upserts by plan name, feature code, and
resource code. Plan names and feature/limit labels are registered
through `_naming` so each translatable string has a matching
NamingContribution row.
"""

from typing import Any, Dict, List, Optional

from storage.storage_broker import get, insert_record, update_record
from core.models import models

from storage.seeds._naming import (
    first,
    get_or_create_naming_contribution,
)


# ==================================================================
# FEATURE TEMPLATES
# ==================================================================
#
# Features are qualitative. They carry a name, an optional
# description, a stable code for code-side checks, and an optional
# value for things like "SLA: 99.9%" where the value is descriptive
# rather than a counted resource.
#
# Order in each list is the display order on the pricing card.

# ==================================================================
# PLAN FEATURES
# ==================================================================
#
# Feature flags describe *capabilities*. Limits describe *quantities*.
# A plan's value comes from the combination of the two, not from
# either alone. See the `value_axis` field on each plan for which
# kind of upgrade that step represents:
#
#   "capability"     — unlocks a new kind of action
#   "capacity"       — unlocks more of an existing action
#   "governance"     — unlocks control over other people / audit
#   "infrastructure" — unlocks operational dependency / isolation

_FEATURES_FREE: List[Dict[str, Any]] = [
    # Free has no feature flags. It is a *consumer* tier: browse the
    # marketplace, scan products, save favorites, read recipes. It
    # cannot create a supplier, cannot invite team members, cannot
    # call the API. Those restrictions are enforced by the limits
    # rather than by feature flags — one place to check instead of two.
]

_FEATURES_STARTER: List[Dict[str, Any]] = [
    # Starter is a quota step, not a capability step. Same reasoning
    # as Free: the upgrade is "you can now create a supplier, here is
    # how much of one", not "here is a new feature".
]

_FEATURES_PRO: List[Dict[str, Any]] = [
    {
        "code": "advanced_inventory",
        "name_en": "Advanced inventory",
        "name_ar": "مخزون متقدم",
        "name_fr": "Inventaire avancé",
        "description_en": "Stock tracking, reservations, and low-stock alerts",
        "description_ar": "تتبع المخزون والحجوزات وتنبيهات المخزون المنخفض",
        "description_fr": "Suivi du stock, réservations et alertes de stock faible",
        "value": None,
    },
    {
        "code": "bulk_import_export",
        "name_en": "Bulk import / export",
        "name_ar": "استيراد وتصدير جماعي",
        "name_fr": "Import / export en masse",
        "description_en": "CSV import and export for products and customers",
        "description_ar": "استيراد وتصدير CSV للمنتجات والعملاء",
        "description_fr": "Import et export CSV pour produits et clients",
        "value": None,
    },
    {
        "code": "ai_assistant",
        "name_en": "AI assistant",
        "name_ar": "مساعد ذكي",
        "name_fr": "Assistant IA",
        "description_en": "Product search, auto-fill, and description generation",
        "description_ar": "بحث وتعبئة تلقائية وإنشاء وصف المنتجات",
        "description_fr": "Recherche, saisie automatique et génération de descriptions",
        "value": None,
    },
]

_FEATURES_BUSINESS_STARTER: List[Dict[str, Any]] = [
    {
        "code": "team_management",
        "name_en": "Team management",
        "name_ar": "إدارة الفريق",
        "name_fr": "Gestion d'équipe",
        "description_en": "Invite, assign roles, and audit access",
        "description_ar": "دعوة الأعضاء، تعيين الأدوار، وتدقيق الوصول",
        "description_fr": "Invitez, attribuez des rôles et auditez les accès",
        "value": None,
    },
    {
        "code": "custom_roles",
        "name_en": "Custom roles",
        "name_ar": "أدوار مخصصة",
        "name_fr": "Rôles personnalisés",
        "description_en": "Define your own roles and privileges",
        "description_ar": "حدّد أدوارك وصلاحياتك الخاصة",
        "description_fr": "Définissez vos propres rôles et privilèges",
        "value": None,
    },
    {
        "code": "api_access",
        "name_en": "API access",
        "name_ar": "الوصول إلى واجهة API",
        "name_fr": "Accès API",
        "description_en": "REST API with rate limits",
        "description_ar": "واجهة REST مع حدود معدل",
        "description_fr": "API REST avec limites de débit",
        "value": None,
    },
    {
        "code": "ai_assistant",
        "name_en": "AI assistant",
        "name_ar": "مساعد ذكي",
        "name_fr": "Assistant IA",
        "description_en": "Product search, auto-fill, and description generation",
        "description_ar": "بحث وتعبئة تلقائية وإنشاء وصف المنتجات",
        "description_fr": "Recherche, saisie automatique et génération de descriptions",
        "value": None,
    },
]

_FEATURES_BUSINESS_PRO: List[Dict[str, Any]] = [
    {
        "code": "team_management",
        "name_en": "Team management",
        "name_ar": "إدارة الفريق",
        "name_fr": "Gestion d'équipe",
        "description_en": "Invite, assign roles, and audit access",
        "description_ar": "دعوة الأعضاء، تعيين الأدوار، وتدقيق الوصول",
        "description_fr": "Invitez, attribuez des rôles et auditez les accès",
        "value": None,
    },
    {
        "code": "custom_roles",
        "name_en": "Custom roles",
        "name_ar": "أدوار مخصصة",
        "name_fr": "Rôles personnalisés",
        "description_en": "Define your own roles and privileges",
        "description_ar": "حدّد أدوارك وصلاحياتك الخاصة",
        "description_fr": "Définissez vos propres rôles et privilèges",
        "value": None,
    },
    {
        "code": "bulk_import_export",
        "name_en": "Bulk import / export",
        "name_ar": "استيراد وتصدير جماعي",
        "name_fr": "Import / export en masse",
        "description_en": "CSV import and export for products and customers",
        "description_ar": "استيراد وتصدير CSV للمنتجات والعملاء",
        "description_fr": "Import et export CSV pour produits et clients",
        "value": None,
    },
    {
        "code": "ai_assistant",
        "name_en": "AI assistant",
        "name_ar": "مساعد ذكي",
        "name_fr": "Assistant IA",
        "description_en": "Product search, auto-fill, and description generation",
        "description_ar": "بحث وتعبئة تلقائية وإنشاء وصف المنتجات",
        "description_fr": "Recherche, saisie automatique et génération de descriptions",
        "value": None,
    },
    {
        "code": "api_access",
        "name_en": "API access",
        "name_ar": "الوصول إلى واجهة API",
        "name_fr": "Accès API",
        "description_en": "REST API and webhooks",
        "description_ar": "واجهة REST والويب هوك",
        "description_fr": "API REST et webhooks",
        "value": None,
    },
    {
        "code": "dedicated_support",
        "name_en": "Dedicated support",
        "name_ar": "دعم مخصص",
        "name_fr": "Support dédié",
        "description_en": "Named support contact and priority queue",
        "description_ar": "جهة اتصال دعم محددة وقائمة انتظار ذات أولوية",
        "description_fr": "Contact de support nommé et file prioritaire",
        "value": None,
    },
]

_FEATURES_ENTERPRISE: List[Dict[str, Any]] = [
    {
        "code": "team_management",
        "name_en": "Team management",
        "name_ar": "إدارة الفريق",
        "name_fr": "Gestion d'équipe",
        "description_en": "Unlimited team with granular roles",
        "description_ar": "فريق غير محدود بأدوار دقيقة",
        "description_fr": "Équipe illimitée avec rôles granulaires",
        "value": None,
    },
    {
        "code": "custom_roles",
        "name_en": "Custom roles",
        "name_ar": "أدوار مخصصة",
        "name_fr": "Rôles personnalisés",
        "description_en": "Define your own roles and privileges",
        "description_ar": "حدّد أدوارك وصلاحياتك الخاصة",
        "description_fr": "Définissez vos propres rôles et privilèges",
        "value": None,
    },
    {
        "code": "bulk_import_export",
        "name_en": "Bulk import / export",
        "name_ar": "استيراد وتصدير جماعي",
        "name_fr": "Import / export en masse",
        "description_en": "CSV import and export for products and customers",
        "description_ar": "استيراد وتصدير CSV للمنتجات والعملاء",
        "description_fr": "Import et export CSV pour produits et clients",
        "value": None,
    },
    {
        "code": "ai_assistant",
        "name_en": "AI assistant",
        "name_ar": "مساعد ذكي",
        "name_fr": "Assistant IA",
        "description_en": "Full AI suite, highest quota",
        "description_ar": "مجموعة ذكاء اصطناعي كاملة بأعلى حصة",
        "description_fr": "Suite IA complète, quota maximal",
        "value": None,
    },
    {
        "code": "api_access",
        "name_en": "API access",
        "name_ar": "الوصول إلى واجهة API",
        "name_fr": "Accès API",
        "description_en": "Unmetered REST API",
        "description_ar": "واجهة REST غير محدودة",
        "description_fr": "API REST sans limite",
        "value": None,
    },
    {
        "code": "dedicated_support",
        "name_en": "Dedicated support",
        "name_ar": "دعم مخصص",
        "name_fr": "Support dédié",
        "description_en": "Dedicated account manager",
        "description_ar": "مدير حساب مخصص",
        "description_fr": "Gestionnaire de compte dédié",
        "value": None,
    },
    {
        "code": "dedicated_infrastructure",
        "name_en": "Dedicated infrastructure",
        "name_ar": "بنية تحتية مخصصة",
        "name_fr": "Infrastructure dédiée",
        "description_en": "Isolated compute and storage",
        "description_ar": "حوسبة وتخزين معزولان",
        "description_fr": "Calcul et stockage isolés",
        "value": None,
    },
    {
        "code": "support_sla",
        "name_en": "Support SLA",
        "name_ar": "اتفاقية مستوى الخدمة",
        "name_fr": "SLA de support",
        "description_en": "Response within 4 hours",
        "description_ar": "الرد خلال 4 ساعات",
        "description_fr": "Réponse sous 4 heures",
        "value": "4h",
    },
]

# ==================================================================
# PLAN LIMITS
# ==================================================================
#
# Limit values are integers.
#
#   0   = not allowed
#   n>0 = allowed, capped at n
#   -1  = unlimited (internal plans only — never sold as flat price)
#   -2  = negotiated per contract (Enterprise only)
#
# `organization_owned` and `provider_owned` are *creation* limits,
# not membership limits. A user on a higher plan can still be a
# member of another organization; these numbers only bound how many
# new ones that user can create.
#
# This is why Business Starter (team plan) can have lower org/provider
# counts than Pro (solo scale plan): a team plan is about *shared*
# resources, not about *more* resources.

_LIMITS_FREE: Dict[str, int] = {
    "organization_owned": 0,               # consumer tier
    "provider_owned": 0,                   # cannot create a supplier
    "team_members": 0,
    "products_per_provider": 20,
    "services_per_provider": 5,
    "ads_enabled": 1,
}

_LIMITS_STARTER: Dict[str, int] = {
    "organization_owned": 1,
    "provider_owned": 1,
    "team_members": 2,
    "products_per_provider": 100,
    "services_per_provider": 25,
    "ads_enabled": 1,
}

_LIMITS_PRO: Dict[str, int] = {
    "organization_owned": 2,
    "provider_owned": 3,
    "team_members": 5,
    "products_per_provider": 500,
    "services_per_provider": 100,
    "ads_enabled": 0,
}

_LIMITS_BUSINESS_STARTER: Dict[str, int] = {
    "organization_owned": 1,               # one team workspace
    "provider_owned": 1,                   # one supplier under that workspace
    "team_members": 10,                    # this IS the team plan
    "products_per_provider": 500,
    "services_per_provider": 100,
    "ads_enabled": 0,
}

_LIMITS_BUSINESS_PRO: Dict[str, int] = {
    "organization_owned": 5,
    "provider_owned": 10,
    "team_members": 20,
    "products_per_provider": 5_000,
    "services_per_provider": 1_000,
    "ads_enabled": 0,
}

_LIMITS_ENTERPRISE: Dict[str, int] = {
    "organization_owned": -2,              # negotiated per contract
    "provider_owned": -2,
    "team_members": -2,
    "products_per_provider": -2,
    "services_per_provider": -2,
    "ads_enabled": 0,
}

# ==================================================================
# PLAN DEFINITIONS
# ==================================================================
#
# Each entry references one of the feature lists and one of the
# limit dicts above. The `plan_name` here doubles as the seed key —
# re-running the seed matches on it to avoid duplicates.
#
# `value_axis` records what kind of upgrade this step represents:
#   "capability"     — unlocks a new kind of action
#   "capacity"       — unlocks more of an existing action
#   "governance"     — unlocks control over other people / audit
#   "infrastructure" — unlocks operational dependency / isolation
#
# `positioning_*` is the one-line answer to the customer question
# this plan exists to answer. It is not marketing copy — it is the
# internal statement of intent that every feature and limit on this
# plan must serve.

SEED_PLANS: List[Dict[str, Any]] = [
    # ── Individual ────────────────────────────────────────────
    {
        "plan_name": "Free",
        "plan_name_en": "Free",
        "plan_name_ar": "مجاني",
        "plan_name_fr": "Gratuit",
        "plan_price": 0.00,
        "billing_cycle": "lifetime",
        "plan_type": "individual",
        "value_axis": "capability",
        "positioning_en": "Can I use Verdelia?",
        "positioning_ar": "هل يمكنني استخدام فيرديليا؟",
        "positioning_fr": "Puis-je utiliser Verdelia ?",
        "features": _FEATURES_FREE,
        "limits": _LIMITS_FREE,
    },
    {
        "plan_name": "Starter Monthly",
        "plan_name_en": "Starter Monthly",
        "plan_name_ar": "المبتدئ الشهري",
        "plan_name_fr": "Débutant mensuel",
        "plan_price": 990.00,
        "billing_cycle": "monthly",
        "plan_type": "individual",
        "value_axis": "capability",
        "positioning_en": "Can I run my small activity?",
        "positioning_ar": "هل يمكنني إدارة نشاطي الصغير؟",
        "positioning_fr": "Puis-je gérer ma petite activité ?",
        "features": _FEATURES_STARTER,
        "limits": _LIMITS_STARTER,
    },
    {
        "plan_name": "Starter Yearly",
        "plan_name_en": "Starter Yearly",
        "plan_name_ar": "المبتدئ السنوي",
        "plan_name_fr": "Débutant annuel",
        "plan_price": 9_900.00,
        "billing_cycle": "yearly",
        "plan_type": "individual",
        "value_axis": "capability",
        "positioning_en": "Can I run my small activity?",
        "positioning_ar": "هل يمكنني إدارة نشاطي الصغير؟",
        "positioning_fr": "Puis-je gérer ma petite activité ?",
        "features": _FEATURES_STARTER,
        "limits": _LIMITS_STARTER,
    },
    {
        "plan_name": "Pro Monthly",
        "plan_name_en": "Pro Monthly",
        "plan_name_ar": "المحترف الشهري",
        "plan_name_fr": "Pro mensuel",
        "plan_price": 2_490.00,
        "billing_cycle": "monthly",
        "plan_type": "individual",
        "value_axis": "capability",
        "positioning_en": "Can I operate professionally, on my own?",
        "positioning_ar": "هل يمكنني العمل باحتراف، بمفردي؟",
        "positioning_fr": "Puis-je opérer professionnellement, seul ?",
        "features": _FEATURES_PRO,
        "limits": _LIMITS_PRO,
    },
    {
        "plan_name": "Pro Yearly",
        "plan_name_en": "Pro Yearly",
        "plan_name_ar": "المحترف السنوي",
        "plan_name_fr": "Pro annuel",
        "plan_price": 24_900.00,
        "billing_cycle": "yearly",
        "plan_type": "individual",
        "value_axis": "capability",
        "positioning_en": "Can I operate professionally, on my own?",
        "positioning_ar": "هل يمكنني العمل باحتراف، بمفردي؟",
        "positioning_fr": "Puis-je opérer professionnellement, seul ?",
        "features": _FEATURES_PRO,
        "limits": _LIMITS_PRO,
    },

    # ── Organization ─────────────────────────────────────────
    {
        "plan_name": "Business Starter",
        "plan_name_en": "Business Starter",
        "plan_name_ar": "الأعمال المبتدئ",
        "plan_name_fr": "Entreprise Débutant",
        "plan_price": 9_900.00,
        "billing_cycle": "monthly",
        "plan_type": "organization",
        "value_axis": "governance",
        "positioning_en": "Can my team operate on it?",
        "positioning_ar": "هل يمكن لفريقي العمل عليه؟",
        "positioning_fr": "Mon équipe peut-elle y opérer ?",
        "features": _FEATURES_BUSINESS_STARTER,
        "limits": _LIMITS_BUSINESS_STARTER,
    },
    {
        "plan_name": "Business Pro",
        "plan_name_en": "Business Pro",
        "plan_name_ar": "الأعمال المحترف",
        "plan_name_fr": "Entreprise Pro",
        "plan_price": 24_900.00,
        "billing_cycle": "monthly",
        "plan_type": "organization",
        "value_axis": "infrastructure",
        "positioning_en": "Can my organization depend on it?",
        "positioning_ar": "هل يمكن لمؤسستي الاعتماد عليه؟",
        "positioning_fr": "Mon organisation peut-elle en dépendre ?",
        "features": _FEATURES_BUSINESS_PRO,
        "limits": _LIMITS_BUSINESS_PRO,
    },
    {
        "plan_name": "Business Yearly",
        "plan_name_en": "Business Yearly",
        "plan_name_ar": "الأعمال السنوي",
        "plan_name_fr": "Entreprise annuel",
        "plan_price": 249_000.00,
        "billing_cycle": "yearly",
        "plan_type": "organization",
        "value_axis": "infrastructure",
        "positioning_en": "Can my organization depend on it?",
        "positioning_ar": "هل يمكن لمؤسستي الاعتماد عليه؟",
        "positioning_fr": "Mon organisation peut-elle en dépendre ?",
        "features": _FEATURES_BUSINESS_PRO,
        "limits": _LIMITS_BUSINESS_PRO,
    },

    # ── Enterprise ───────────────────────────────────────────
    #
    # `price_is_floor: True` means the listed `plan_price` is a
    # starting price, not a fixed price. Limits are `-2` (negotiated)
    # rather than `-1` (unlimited) so that a real enterprise contract
    # can be sized to its actual consumption without exposing the
    # business to unbounded infrastructure cost at a flat rate.
    {
        "plan_name": "Enterprise",
        "plan_name_en": "Enterprise",
        "plan_name_ar": "المؤسسات",
        "plan_name_fr": "Grands comptes",
        "plan_price": 49_900.00,
        "price_is_floor": True,
        "billing_cycle": "monthly",
        "plan_type": "organization",
        "value_axis": "infrastructure",
        "positioning_en": "Can Verdelia become part of our infrastructure?",
        "positioning_ar": "هل يمكن أن تصبح فيرديليا جزءًا من بنيتنا التحتية؟",
        "positioning_fr": "Verdelia peut-elle faire partie de notre infrastructure ?",
        "features": _FEATURES_ENTERPRISE,
        "limits": _LIMITS_ENTERPRISE,
    },
    {
        "plan_name": "Enterprise Yearly",
        "plan_name_en": "Enterprise Yearly",
        "plan_name_ar": "المؤسسات السنوي",
        "plan_name_fr": "Grands comptes annuel",
        "plan_price": 499_000.00,
        "price_is_floor": True,
        "billing_cycle": "yearly",
        "plan_type": "organization",
        "value_axis": "infrastructure",
        "positioning_en": "Can Verdelia become part of our infrastructure?",
        "positioning_ar": "هل يمكن أن تصبح فيرديليا جزءًا من بنيتنا التحتية؟",
        "positioning_fr": "Verdelia peut-elle faire partie de notre infrastructure ?",
        "features": _FEATURES_ENTERPRISE,
        "limits": _LIMITS_ENTERPRISE,
    },
]


# ==================================================================
# SEED LOGIC
# ==================================================================

def _upsert_plan(
    spec: Dict[str, Any],
) -> Optional[models.Plan]:
    """
    Insert or update a plan row, resolving the display name through
    a cached NamingContribution lookup.
    """
    naming = _cached_naming(
        name_en=spec["plan_name_en"],
        name_ar=spec["plan_name_ar"],
        name_fr=spec["plan_name_fr"],
        contribution_type="plan",
    )
    if naming is None:
        return None

    existing = first(
        get(
            table=models.Plan,
            conditions={"plan_name": spec["plan_name"]},
        )
    )

    if existing:
        existing.plan_price = spec["plan_price"]
        existing.billing_cycle = spec["billing_cycle"]
        existing.plan_type = spec["plan_type"]
        if existing.plan_naming_id != naming.id_naming_contribution:
            existing.plan_naming_id = naming.id_naming_contribution
        return first(update_record(existing))

    plan = models.Plan(
        plan_name=spec["plan_name"],
        plan_price=spec["plan_price"],
        billing_cycle=spec["billing_cycle"],
        plan_type=spec["plan_type"],
        plan_naming_id=naming.id_naming_contribution,
    )
    return first(insert_record(plan))


_naming_cache: Dict[tuple, Optional[models.NamingContribution]] = {}


def _cached_naming(
    *,
    name_en: str,
    name_ar: str,
    name_fr: str,
    contribution_type: str,
    icon_url: Optional[str] = None,
) -> Optional[models.NamingContribution]:
    """
    Wrapper around `get_or_create_naming_contribution` that avoids
    hitting the database when the same (type, en) pair has already
    been resolved in this run.

    The database call is still the source of truth — on a cache miss
    we fall through to it. On a hit, the previously-resolved row is
    returned as-is.

    Keying on (contribution_type, name_en) rather than just name_en
    matters because a plan named "Free" and a feature named "Free"
    are different rows with different `naming_contribution_type`
    values. Same English text, different type, different row.
    """
    key = (contribution_type, name_en)
    if key in _naming_cache:
        return _naming_cache[key]

    resolved = get_or_create_naming_contribution(
        name_en=name_en,
        name_ar=name_ar,
        name_fr=name_fr,
        contribution_type=contribution_type,
        icon_url=icon_url,
    )
    _naming_cache[key] = resolved
    return resolved

def _upsert_feature(
    plan_id: int,
    order: int,
    spec: Dict[str, Any],
) -> None:
    """
    Insert or update a PlanFeature row for `plan_id`.

    Matches on (plan_id, feature_code). The name and description are
    resolved through `_cached_naming`, which deduplicates across the
    whole seed run: every feature named "Email support" shares one
    NamingContribution row, and every description string that appears
    more than once shares one too.

    The description is deliberately allowed to differ per tier even
    when the feature code is the same — "Email support" on Free
    describes a 72-hour SLA, on Pro a same-day SLA. Sharing a name
    across plans doesn't mean sharing a description.
    """
    # Feature name — shared by every plan that offers this feature.
    name_naming = _cached_naming(
        name_en=spec["name_en"],
        name_ar=spec["name_ar"],
        name_fr=spec["name_fr"],
        contribution_type="plan_feature",
    )

    # Feature description — tier-specific. Only rows with a description
    # get a naming row. The cache still applies: two plans with the
    # same description ("Same-day replies") share one naming row.
    description_naming_id: Optional[int] = None
    if spec.get("description_en"):
        desc_naming = _cached_naming(
            name_en=spec["description_en"],
            name_ar=spec["description_ar"],
            name_fr=spec["description_fr"],
            contribution_type="plan_feature",
        )
        description_naming_id = (
            desc_naming.id_naming_contribution if desc_naming else None
        )

    existing = first(
        get(
            table=models.PlanFeature,
            conditions={
                "plan_id": plan_id,
                "feature_code": spec["code"],
            },
        )
    )

    if existing:
        existing.display_order = order
        existing.is_visible = True
        existing.feature_value = spec.get("value")
        if name_naming:
            existing.feature_naming_id = name_naming.id_naming_contribution
        existing.feature_description_naming_id = description_naming_id
        update_record(existing)
        return

    feature = models.PlanFeature(
        plan_id=plan_id,
        feature_code=spec["code"],
        feature_naming_id=(
            name_naming.id_naming_contribution if name_naming else None
        ),
        feature_description_naming_id=description_naming_id,
        display_order=order,
        is_visible=True,
        feature_value=spec.get("value"),
    )
    insert_record(feature)


def _upsert_limit(
    plan_id: int,
    resource_code: str,
    limit_value: int,
) -> None:
    """
    Insert or update a PlanLimit row.

    Matches on (plan_id, resource_code). No naming lookup — the
    display label is derived from `resource_code` on the app side.
    """
    existing = first(
        get(
            table=models.PlanLimit,
            conditions={
                "plan_id": plan_id,
                "resource_code": resource_code,
            },
        )
    )

    if existing:
        existing.limit_value = limit_value
        update_record(existing)
        return

    limit = models.PlanLimit(
        plan_id=plan_id,
        resource_code=resource_code,
        limit_value=limit_value,
    )
    insert_record(limit)


def seed() -> None:
    """
    Entry point. Idempotent: safe to run repeatedly.

    For each plan:
      1. Upsert the plan row (and its naming contribution).
      2. Upsert every feature in display order.
      3. Upsert every limit by resource code.
    """
    for spec in SEED_PLANS:
        plan = _upsert_plan(spec)
        if plan is None:
            continue

        plan_id = plan.id_plan

        for i, feature in enumerate(spec["features"]):
            _upsert_feature(plan_id, i * 10, feature)

        for resource_code, limit_value in spec["limits"].items():
            _upsert_limit(plan_id, resource_code, limit_value)