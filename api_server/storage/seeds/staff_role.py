# storage/seeds/staff_role.py
"""
Staff role seed module using the storage broker.

Each role is backed by a NamingContribution row carrying the Arabic /
French / English names. Seeding is idempotent: re-running inserts
nothing.

Naming contributions are keyed on the English name alone. Two roles
with the same name in different categories (e.g. "Physical Therapist"
in Orthopedics and in Physiotherapy) share one contribution, which is
correct as long as they translate identically. If a future role needs
per-category translations, extend the naming key with `category_ref`
and add the discriminator to `_naming.get_or_create_naming_contribution`.
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

# `en` is the English name and the lookup anchor (paired with
# `category_ref` when resolving the StaffRole row). `ar` / `fr` carry
# the translations. `category_ref` matches
# `provided_service_category_id` in the category seed.
SEED_STAFF_ROLES: List[Dict[str, Any]] = [
    # ---------- Medical Doctors (category 1) ----------
    {
        "en": "General Practitioner",
        "ar": "طبيب عام",
        "fr": "Médecin généraliste",
        "category_ref": 1,
        "icon_url": "icons/staff/doctor.svg",
    },
    {
        "en": "Family Physician",
        "ar": "طبيب الأسرة",
        "fr": "Médecin de famille",
        "category_ref": 1,
        "icon_url": "icons/staff/doctor.svg",
    },
    {
        "en": "Specialist Doctor",
        "ar": "طبيب أخصائي",
        "fr": "Médecin spécialiste",
        "category_ref": 2,
        "icon_url": "icons/staff/specialist.svg",
    },
    {
        "en": "Consultant",
        "ar": "استشاري",
        "fr": "Consultant",
        "category_ref": 2,
        "icon_url": "icons/staff/surgeon.svg",
    },

    # ---------- Surgeons (category 4) ----------
    {
        "en": "General Surgeon",
        "ar": "جراح عام",
        "fr": "Chirurgien généraliste",
        "category_ref": 4,
        "icon_url": "icons/staff/surgeon.svg",
    },
    {
        "en": "Cardiothoracic Surgeon",
        "ar": "جراح قلب وصدر",
        "fr": "Chirurgien cardiothoracique",
        "category_ref": 4,
        "icon_url": "icons/staff/surgeon.svg",
    },
    {
        "en": "Neurosurgeon",
        "ar": "جراح أعصاب",
        "fr": "Neurochirurgien",
        "category_ref": 4,
        "icon_url": "icons/staff/surgeon.svg",
    },
    {
        "en": "Orthopedic Surgeon",
        "ar": "جراح عظام",
        "fr": "Chirurgien orthopédiste",
        "category_ref": 4,
        "icon_url": "icons/staff/surgeon.svg",
    },
    {
        "en": "Plastic Surgeon",
        "ar": "جراح تجميل",
        "fr": "Chirurgien plasticien",
        "category_ref": 4,
        "icon_url": "icons/staff/surgeon.svg",
    },

    # ---------- Dental Staff (category 5) ----------
    {
        "en": "General Dentist",
        "ar": "طبيب أسنان عام",
        "fr": "Dentiste généraliste",
        "category_ref": 5,
        "icon_url": "icons/staff/dentist.svg",
    },
    {
        "en": "Orthodontist",
        "ar": "أخصائي تقويم الأسنان",
        "fr": "Orthodontiste",
        "category_ref": 5,
        "icon_url": "icons/staff/dentist.svg",
    },
    {
        "en": "Oral Surgeon",
        "ar": "جراح الفم",
        "fr": "Chirurgien buccal",
        "category_ref": 5,
        "icon_url": "icons/staff/dentist.svg",
    },
    {
        "en": "Dental Hygienist",
        "ar": "أخصائي صحة الفم",
        "fr": "Hygiéniste dentaire",
        "category_ref": 5,
        "icon_url": "icons/staff/dental_hygienist.svg",
    },
    {
        "en": "Dental Assistant",
        "ar": "مساعد طبيب أسنان",
        "fr": "Assistant dentaire",
        "category_ref": 5,
        "icon_url": "icons/staff/dental_assistant.svg",
    },

    # ---------- Orthopedic Staff (category 6) ----------
    {
        "en": "Orthopedic Surgeon",
        "ar": "جراح عظام",
        "fr": "Chirurgien orthopédiste",
        "category_ref": 6,
        "icon_url": "icons/staff/orthopedic.svg",
    },
    {
        "en": "Sports Medicine Specialist",
        "ar": "أخصائي الطب الرياضي",
        "fr": "Spécialiste en médecine du sport",
        "category_ref": 6,
        "icon_url": "icons/staff/orthopedic.svg",
    },
    {
        "en": "Physical Therapist",
        "ar": "أخصائي علاج طبيعي",
        "fr": "Kinésithérapeute",
        "category_ref": 6,
        "icon_url": "icons/staff/physical_therapist.svg",
    },

    # ---------- Dermatology (category 7) ----------
    {
        "en": "Dermatologist",
        "ar": "طبيب أمراض جلدية",
        "fr": "Dermatologue",
        "category_ref": 7,
        "icon_url": "icons/staff/dermatologist.svg",
    },
    {
        "en": "Cosmetic Dermatologist",
        "ar": "طبيب جلدية تجميلي",
        "fr": "Dermatologue esthétique",
        "category_ref": 7,
        "icon_url": "icons/staff/dermatologist.svg",
    },

    # ---------- Ophthalmology (category 8) ----------
    {
        "en": "Ophthalmologist",
        "ar": "طبيب عيون",
        "fr": "Ophtalmologue",
        "category_ref": 8,
        "icon_url": "icons/staff/ophthalmologist.svg",
    },
    {
        "en": "Optometrist",
        "ar": "أخصائي بصريات",
        "fr": "Optométriste",
        "category_ref": 8,
        "icon_url": "icons/staff/optometrist.svg",
    },

    # ---------- Cardiology (category 9) ----------
    {
        "en": "Interventional Cardiologist",
        "ar": "طبيب قلب تداخلي",
        "fr": "Cardiologue interventionnel",
        "category_ref": 9,
        "icon_url": "icons/staff/cardiologist.svg",
    },
    {
        "en": "Cardiac Surgeon",
        "ar": "جراح قلب",
        "fr": "Chirurgien cardiaque",
        "category_ref": 9,
        "icon_url": "icons/staff/cardiologist.svg",
    },
    {
        "en": "Cardiovascular Technician",
        "ar": "فني قلب وأوعية دموية",
        "fr": "Technicien cardiovasculaire",
        "category_ref": 9,
        "icon_url": "icons/staff/cardiologist.svg",
    },

    # ---------- Neurology (category 10) ----------
    {
        "en": "Neurologist",
        "ar": "طبيب أعصاب",
        "fr": "Neurologue",
        "category_ref": 10,
        "icon_url": "icons/staff/neurologist.svg",
    },
    {
        "en": "Neurosurgeon",
        "ar": "جراح أعصاب",
        "fr": "Neurochirurgien",
        "category_ref": 10,
        "icon_url": "icons/staff/neurologist.svg",
    },

    # ---------- Gynecology (category 11) ----------
    {
        "en": "Gynecologist",
        "ar": "طبيب أمراض نساء",
        "fr": "Gynécologue",
        "category_ref": 11,
        "icon_url": "icons/staff/gynecologist.svg",
    },
    {
        "en": "Obstetrician",
        "ar": "طبيب توليد",
        "fr": "Obstétricien",
        "category_ref": 11,
        "icon_url": "icons/staff/gynecologist.svg",
    },
    {
        "en": "Midwife",
        "ar": "قابلة",
        "fr": "Sage-femme",
        "category_ref": 11,
        "icon_url": "icons/staff/midwife.svg",
    },

    # ---------- Pediatrics (category 12) ----------
    {
        "en": "Pediatrician",
        "ar": "طبيب أطفال",
        "fr": "Pédiatre",
        "category_ref": 12,
        "icon_url": "icons/staff/pediatrician.svg",
    },
    {
        "en": "Neonatologist",
        "ar": "طبيب حديثي الولادة",
        "fr": "Néonatologiste",
        "category_ref": 12,
        "icon_url": "icons/staff/pediatrician.svg",
    },

    # ---------- Laboratory (category 13) ----------
    {
        "en": "Lab Technician",
        "ar": "فني مختبر",
        "fr": "Technicien de laboratoire",
        "category_ref": 13,
        "icon_url": "icons/staff/lab_technician.svg",
    },
    {
        "en": "Pathologist",
        "ar": "أخصائي علم الأمراض",
        "fr": "Pathologiste",
        "category_ref": 13,
        "icon_url": "icons/staff/pathologist.svg",
    },

    # ---------- Radiology (category 14) ----------
    {
        "en": "Radiologist",
        "ar": "أخصائي أشعة",
        "fr": "Radiologue",
        "category_ref": 14,
        "icon_url": "icons/staff/radiologist.svg",
    },
    {
        "en": "Radiology Technician",
        "ar": "فني أشعة",
        "fr": "Technicien en radiologie",
        "category_ref": 14,
        "icon_url": "icons/staff/radiology_technician.svg",
    },
    {
        "en": "Ultrasound Technician",
        "ar": "فني موجات فوق صوتية",
        "fr": "Technicien en échographie",
        "category_ref": 14,
        "icon_url": "icons/staff/ultrasound_technician.svg",
    },

    # ---------- Physiotherapy (category 16) ----------
    {
        "en": "Physical Therapist",
        "ar": "أخصائي علاج طبيعي",
        "fr": "Kinésithérapeute",
        "category_ref": 16,
        "icon_url": "icons/staff/physical_therapist.svg",
    },
    {
        "en": "Physical Therapy Assistant",
        "ar": "مساعد علاج طبيعي",
        "fr": "Assistant en kinésithérapie",
        "category_ref": 16,
        "icon_url": "icons/staff/physical_therapist.svg",
    },

    # ---------- Mental Health (category 19) ----------
    {
        "en": "Clinical Psychologist",
        "ar": "أخصائي علم نفس إكلينيكي",
        "fr": "Psychologue clinicien",
        "category_ref": 19,
        "icon_url": "icons/staff/psychologist.svg",
    },
    {
        "en": "Psychiatrist",
        "ar": "طبيب نفسي",
        "fr": "Psychiatre",
        "category_ref": 19,
        "icon_url": "icons/staff/psychiatrist.svg",
    },

    # ---------- Support Staff (category 1) ----------
    {
        "en": "Registered Nurse",
        "ar": "ممرض مسجل",
        "fr": "Infirmier diplômé",
        "category_ref": 1,
        "icon_url": "icons/staff/nurse.svg",
    },
    {
        "en": "Licensed Practical Nurse",
        "ar": "ممرض ممارس مرخص",
        "fr": "Infirmier auxiliaire diplômé",
        "category_ref": 1,
        "icon_url": "icons/staff/nurse.svg",
    },
    {
        "en": "Nurse Practitioner",
        "ar": "ممرض ممارس",
        "fr": "Infirmier praticien",
        "category_ref": 1,
        "icon_url": "icons/staff/nurse.svg",
    },
    {
        "en": "Medical Assistant",
        "ar": "مساعد طبي",
        "fr": "Assistant médical",
        "category_ref": 1,
        "icon_url": "icons/staff/medical_assistant.svg",
    },
    {
        "en": "Pharmacist",
        "ar": "صيدلي",
        "fr": "Pharmacien",
        "category_ref": 1,
        "icon_url": "icons/staff/pharmacist.svg",
    },
    {
        "en": "Pharmacy Technician",
        "ar": "فني صيدلة",
        "fr": "Technicien en pharmacie",
        "category_ref": 1,
        "icon_url": "icons/staff/pharmacist.svg",
    },
    {
        "en": "Medical Administrator",
        "ar": "مدير طبي",
        "fr": "Administrateur médical",
        "category_ref": 1,
        "icon_url": "icons/staff/administrator.svg",
    },
    {
        "en": "Medical Receptionist",
        "ar": "موظف استقبال طبي",
        "fr": "Réceptionniste médical",
        "category_ref": 1,
        "icon_url": "icons/staff/receptionist.svg",
    },

    # ---------- Emergency & Critical Care (category 3) ----------
    {
        "en": "Emergency Physician",
        "ar": "طبيب طوارئ",
        "fr": "Médecin urgentiste",
        "category_ref": 3,
        "icon_url": "icons/staff/emergency_doctor.svg",
    },
    {
        "en": "Paramedic",
        "ar": "مسعف",
        "fr": "Ambulancier",
        "category_ref": 3,
        "icon_url": "icons/staff/paramedic.svg",
    },
    {
        "en": "Emergency Nurse",
        "ar": "ممرض طوارئ",
        "fr": "Infirmier urgentiste",
        "category_ref": 3,
        "icon_url": "icons/staff/emergency_nurse.svg",
    },
    {
        "en": "Critical Care Nurse",
        "ar": "ممرض رعاية حرجة",
        "fr": "Infirmier en soins intensifs",
        "category_ref": 3,
        "icon_url": "icons/staff/critical_care_nurse.svg",
    },

    # ---------- Nutrition (category 21) ----------
    {
        "en": "Clinical Nutritionist",
        "ar": "أخصائي تغذية إكلينيكية",
        "fr": "Nutritionniste clinicien",
        "category_ref": 21,
        "icon_url": "icons/staff/nutritionist.svg",
    },
    {
        "en": "Registered Dietitian",
        "ar": "أخصائي تغذية مسجل",
        "fr": "Diététicien diplômé",
        "category_ref": 21,
        "icon_url": "icons/staff/dietitian.svg",
    },

    # ---------- Healthcare Support (category 1) ----------
    {
        "en": "Caregiver",
        "ar": "مقدم رعاية",
        "fr": "Aidant",
        "category_ref": 1,
        "icon_url": "icons/staff/caregiver.svg",
    },
    {
        "en": "Home Health Aide",
        "ar": "مساعد صحي منزلي",
        "fr": "Aide à domicile",
        "category_ref": 1,
        "icon_url": "icons/staff/home_health_aide.svg",
    },
    {
        "en": "Medical Social Worker",
        "ar": "أخصائي اجتماعي طبي",
        "fr": "Travailleur social médical",
        "category_ref": 1,
        "icon_url": "icons/staff/medical_social_worker.svg",
    },
    {
        "en": "Health Coach",
        "ar": "مدرب صحي",
        "fr": "Coach santé",
        "category_ref": 1,
        "icon_url": "icons/staff/health_coach.svg",
    },
]


# ==================== Helpers ====================

def _get_or_create_staff_role(
    *,
    name_en: str,
    category_ref: int,
    naming_contribution_id: int,
    icon_url: Optional[str] = None,
) -> Optional[Any]:
    """
    Return the existing StaffRole for (name, category), or insert a new
    one linked to `naming_contribution_id`.
    """
    existing = first(
        get(
            table=models.StaffRole,
            conditions={
                "staff_role_name": name_en,
                "staff_role_service_category_ref": category_ref,
            },
        )
    )
    if existing:
        return existing

    role = models.StaffRole(
        staff_role_name=name_en,
        staff_role_service_category_ref=category_ref,
        staff_role_icon_url=icon_url,
        staff_role_naming_ref=naming_contribution_id,
    )
    return first(insert_record(role))


# ==================== Seeding Functions ====================

def seed_staff_roles() -> int:
    """
    Seed staff roles and their multilingual names.

    Returns:
        Number of staff roles inserted (existing rows are not counted).
    """
    count_inserted = 0

    for entry in SEED_STAFF_ROLES:
        name_en = entry["en"]
        category_ref = entry["category_ref"]

        contribution = get_or_create_naming_contribution(
            name_en=name_en,
            name_ar=entry["ar"],
            name_fr=entry["fr"],
            contribution_type="role",
            icon_url=entry.get("icon_url"),
        )
        if contribution is None:
            logger.error(
                "Skipping staff role %r (category %s): could not resolve "
                "naming contribution",
                name_en,
                category_ref,
            )
            continue

        existing_role = first(
            get(
                table=models.StaffRole,
                conditions={
                    "staff_role_name": name_en,
                    "staff_role_service_category_ref": category_ref,
                },
            )
        )
        if existing_role:
            # Backfill the naming link and icon if missing.
            if getattr(existing_role, "staff_role_naming_ref", None) is None:
                existing_role.staff_role_naming_ref = (
                    contribution.id_naming_contribution
                )
                logger.debug(
                    "Backfilled naming ref for existing staff role %r "
                    "(category %s)",
                    name_en,
                    category_ref,
                )
            if entry.get("icon_url") and not existing_role.staff_role_icon_url:
                existing_role.staff_role_icon_url = entry["icon_url"]
            continue

        role = _get_or_create_staff_role(
            name_en=name_en,
            category_ref=category_ref,
            naming_contribution_id=contribution.id_naming_contribution,
            icon_url=entry.get("icon_url"),
        )
        if role:
            count_inserted += 1
            logger.debug(
                "Seeded staff role: %s (category %s)", name_en, category_ref
            )

    logger.info("Seeded %d new staff roles", count_inserted)
    return count_inserted


def seed_staff_role(role_data: Dict[str, Any]) -> bool:
    """
    Seed a single staff role.

    `role_data` may carry `en` / `ar` / `fr` plus `category_ref` and
    optional `icon_url`. Falls back to the old `staff_role_*` keys for
    backward compatibility.

    Returns True if inserted, False if the role already existed.
    """
    name_en = role_data.get("en") or role_data.get("staff_role_name")
    category_ref = role_data.get("category_ref") or role_data.get(
        "staff_role_service_category_ref"
    )
    if not name_en or category_ref is None:
        logger.warning(
            "seed_staff_role called with incomplete data: %r", role_data
        )
        return False

    existing = first(
        get(
            table=models.StaffRole,
            conditions={
                "staff_role_name": name_en,
                "staff_role_service_category_ref": category_ref,
            },
        )
    )
    if existing:
        logger.debug(
            "Staff role already exists: %s (category %s)",
            name_en,
            category_ref,
        )
        return False

    icon_url = role_data.get("icon_url") or role_data.get(
        "staff_role_icon_url"
    )

    contribution = get_or_create_naming_contribution(
        name_en=name_en,
        name_ar=role_data.get("ar", name_en),
        name_fr=role_data.get("fr", name_en),
        contribution_type="role",
        icon_url=icon_url,
    )
    if contribution is None:
        logger.error("Could not create naming contribution for %r", name_en)
        return False

    role = _get_or_create_staff_role(
        name_en=name_en,
        category_ref=category_ref,
        naming_contribution_id=contribution.id_naming_contribution,
        icon_url=icon_url,
    )
    if role:
        logger.debug("Seeded staff role: %s", name_en)
        return True
    return False


def seed_staff_roles_from_list(roles: List[Dict[str, Any]]) -> int:
    """
    Seed staff roles from a custom list.

    Each entry may carry `en` / `ar` / `fr`, `category_ref`, and
    optional `icon_url`. Falls back to the old `staff_role_*` keys for
    backward compatibility.

    Returns:
        Number of roles inserted.
    """
    count_inserted = 0

    for entry in roles:
        name_en = entry.get("en") or entry.get("staff_role_name")
        category_ref = entry.get("category_ref") or entry.get(
            "staff_role_service_category_ref"
        )
        if not name_en or category_ref is None:
            logger.warning("Skipping entry with incomplete data: %r", entry)
            continue

        icon_url = entry.get("icon_url") or entry.get("staff_role_icon_url")

        contribution = get_or_create_naming_contribution(
            name_en=name_en,
            name_ar=entry.get("ar", name_en),
            name_fr=entry.get("fr", name_en),
            contribution_type="role",
            icon_url=icon_url,
        )
        if contribution is None:
            logger.error(
                "Skipping %r: could not resolve naming contribution",
                name_en,
            )
            continue

        role = _get_or_create_staff_role(
            name_en=name_en,
            category_ref=category_ref,
            naming_contribution_id=contribution.id_naming_contribution,
            icon_url=icon_url,
        )
        if role:
            count_inserted += 1
            logger.debug("Seeded staff role: %s", name_en)

    logger.info("Seeded %d staff roles from custom list", count_inserted)
    return count_inserted


# ==================== Utility Functions ====================

def get_all_seeded_staff_roles() -> List[Dict[str, Any]]:
    """
    Return every staff role with its name in all three languages.

    The primary `name` field is the English name for backward
    compatibility with callers that only want one string.
    """
    with session_scope() as session:
        rows = (
            session.query(models.StaffRole, models.NamingContribution)
            .outerjoin(
                models.NamingContribution,
                models.StaffRole.staff_role_naming_ref
                == models.NamingContribution.id_naming_contribution,
            )
            .all()
        )

        result: List[Dict[str, Any]] = []
        for role, naming in rows:
            result.append(
                {
                    "id": role.id_staff_role,
                    "name": role.staff_role_name,
                    "en": role.staff_role_name,
                    "ar": getattr(naming, "naming_contribution_ar", None)
                    if naming
                    else None,
                    "fr": getattr(naming, "naming_contribution_fr", None)
                    if naming
                    else None,
                    "service_category_ref": role.staff_role_service_category_ref,
                    "icon_url": role.staff_role_icon_url,
                    "naming_ref": role.staff_role_naming_ref,
                }
            )
        return result


def get_staff_roles_by_service_category(
    category_id: int,
) -> List[models.StaffRole]:
    """
    Return all staff roles for a service category.
    """
    with session_scope() as session:
        return (
            session.query(models.StaffRole)
            .filter(
                models.StaffRole.staff_role_service_category_ref == category_id
            )
            .all()
        )


def staff_role_exists(role_name: str, category_id: int) -> bool:
    """
    Check whether a staff role with the given name exists in the given
    category.
    """
    existing = first(
        get(
            table=models.StaffRole,
            conditions={
                "staff_role_name": role_name,
                "staff_role_service_category_ref": category_id,
            },
        )
    )
    return bool(existing)


def get_staff_role_by_name(role_name: str) -> Optional[models.StaffRole]:
    """
    Return the first staff role matching the given English name, or
    None. Note: because the name alone is not unique, this returns
    whichever row the DB returns first; prefer
    `get_staff_roles_by_service_category` when category matters.
    """
    return first(
        get(
            table=models.StaffRole,
            conditions={"staff_role_name": role_name},
        )
    )


def get_staff_role_by_id(role_id: int) -> Optional[models.StaffRole]:
    """
    Return a staff role by its primary key, or None.
    """
    return first(
        get(
            table=models.StaffRole,
            conditions={"id_staff_role": role_id},
        )
    )


def delete_all_staff_roles() -> int:
    """
    Delete all staff roles. Leaves the naming contributions in place,
    since other tables may reference them.

    Returns the number of roles deleted.
    """
    with session_scope() as session:
        count = session.query(models.StaffRole).delete()
        session.commit()
        logger.info("Deleted %d staff roles", count)
        return count


def update_staff_role_icon(role_name: str, icon_url: str) -> bool:
    """
    Update the icon URL for every staff role with the given name.
    """
    with session_scope() as session:
        roles = (
            session.query(models.StaffRole)
            .filter(models.StaffRole.staff_role_name == role_name)
            .all()
        )
        if not roles:
            logger.warning("Staff role not found: %s", role_name)
            return False

        for role in roles:
            role.staff_role_icon_url = icon_url
        session.commit()
        logger.debug("Updated icon for staff role: %s", role_name)
        return True


def get_staff_roles_by_category_name(
    category_name: str,
) -> List[Dict[str, Any]]:
    """
    Return all staff roles for a service category looked up by name,
    each enriched with its multilingual name.
    """
    with session_scope() as session:
        category = (
            session.query(models.ProvidedServiceCategory)
            .filter(
                models.ProvidedServiceCategory.provided_service_category_name
                == category_name
            )
            .first()
        )
        if not category:
            logger.warning("Service category not found: %s", category_name)
            return []

        rows = (
            session.query(models.StaffRole, models.NamingContribution)
            .outerjoin(
                models.NamingContribution,
                models.StaffRole.staff_role_naming_ref
                == models.NamingContribution.id_naming_contribution,
            )
            .filter(
                models.StaffRole.staff_role_service_category_ref
                == category.provided_service_category_id
            )
            .all()
        )

        return [
            {
                "id": role.id_staff_role,
                "name": role.staff_role_name,
                "en": role.staff_role_name,
                "ar": getattr(naming, "naming_contribution_ar", None)
                if naming
                else None,
                "fr": getattr(naming, "naming_contribution_fr", None)
                if naming
                else None,
                "icon_url": role.staff_role_icon_url,
            }
            for role, naming in rows
        ]


# ==================== Main Execution ====================

def main():
    """Main entry point for seeding staff roles."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed staff roles")
    parser.add_argument(
        "--delete-first",
        action="store_true",
        help="Delete all existing staff roles before seeding",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--category",
        "-c",
        type=int,
        help="Only seed roles for a specific category ID",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    print("Starting staff role seeding...")

    try:
        if args.delete_first:
            delete_all_staff_roles()

        # The `--category` flag isn't wired to a filtered seed
        # function yet; the whole set is seeded either way. Filter
        # output below.
        count = seed_staff_roles()
        print(f"Successfully seeded {count} staff roles")

        if count > 0:
            roles = get_all_seeded_staff_roles()
            if args.category is not None:
                roles = [
                    r
                    for r in roles
                    if r["service_category_ref"] == args.category
                ]

            print("\nSeeded staff roles:")

            from collections import defaultdict

            grouped: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
            for role in roles:
                grouped[role["service_category_ref"]].append(role)

            for category_id, role_list in sorted(grouped.items()):
                print(f"\n  Category ID: {category_id}")
                for role in role_list:
                    languages = " / ".join(
                        filter(
                            None,
                            [
                                role.get("en"),
                                role.get("fr"),
                                role.get("ar"),
                            ],
                        )
                    )
                    print(f"    - {languages} (ID: {role['id']})")

    except Exception as e:
        print(f"Failed to seed staff roles: {e}")
        raise


if __name__ == "__main__":
    main()