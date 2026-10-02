# storage/seeds/provided_service_category.py
"""
Provided service category seed module using the storage broker.

Each category is backed by a NamingContribution row carrying the
Arabic / French / English names. Seeding is idempotent: re-running
inserts nothing.

The canonical identity of a category is its dotted key
(`domain.subdomain.key`, e.g. `services.health_services.dentistry`),
stored in `provided_service_category_name`. Human-readable display
names come from the joined NamingContribution row — never from the
name column.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from storage.storage_broker import insert_record, get, session_scope
from core.models import models

logger = logging.getLogger(__name__)


# ==================== Seed Data ====================

# `key` is the immutable lookup anchor, stored in
# `provided_service_category_name`. Treat it as frozen once shipped —
# downstream lookups and NamingContribution rows key on it.
#
# `description_{en,ar,fr}` is per-locale. Where a translation isn't
# provided, `ar` / `fr` fall back to the English string so the row is
# never half-empty.
SEED_SERVICE_CATEGORIES: List[Dict[str, Any]] = [
    # ══════════════════════════════════════════════════════════════
    # DOMAIN: health
    # ══════════════════════════════════════════════════════════════

    # ── health · diagnostics ─────────────────────────────────────
    {
        "key": "health.diagnostics.blood_testing",
        "en": "Blood Testing", "ar": "تحاليل الدم", "fr": "Analyses sanguines",
        "icon_url": "https://example.com/icons/blood-test.svg",
        "avg_duration": Decimal("30.00"),
        "description_en": "Complete blood count, cholesterol, glucose, and other blood tests",
        "description_ar": "تعداد الدم الكامل والكوليسترول والجلوكوز وفحوصات دم أخرى",
        "description_fr": "Numération formule sanguine, cholestérol, glucose et autres analyses",
    },
    {
        "key": "health.diagnostics.diagnostic_imaging",
        "en": "Diagnostic Imaging", "ar": "التصوير التشخيصي", "fr": "Imagerie diagnostique",
        "icon_url": "https://example.com/icons/xray.svg",
        "avg_duration": Decimal("45.00"),
        "description_en": "X-rays, MRIs, CT scans, and ultrasound services",
        "description_ar": "الأشعة السينية والرنين المغناطيسي والتصوير المقطعي والموجات فوق الصوتية",
        "description_fr": "Radiographies, IRM, scanners et échographies",
    },
    {
        "key": "health.diagnostics.pathology_tests",
        "en": "Pathology Tests", "ar": "اختبارات علم الأمراض", "fr": "Examens pathologiques",
        "icon_url": "https://example.com/icons/microscope.svg",
        "avg_duration": Decimal("120.00"),
        "description_en": "Tissue biopsy analysis and histopathology",
        "description_ar": "تحليل خزعات الأنسجة وعلم الأنسجة المرضية",
        "description_fr": "Analyse de biopsies tissulaires et histopathologie",
    },
    {
        "key": "health.diagnostics.urine_analysis",
        "en": "Urine Analysis", "ar": "تحليل البول", "fr": "Analyse d'urine",
        "icon_url": "https://example.com/icons/urine-test.svg",
        "avg_duration": Decimal("20.00"),
        "description_en": "Complete urinalysis and culture tests",
        "description_ar": "تحليل البول الكامل واختبارات الزراعة",
        "description_fr": "Analyse d'urine complète et cultures",
    },
    {
        "key": "health.diagnostics.allergy_testing",
        "en": "Allergy Testing", "ar": "اختبارات الحساسية", "fr": "Tests d'allergie",
        "icon_url": "https://example.com/icons/allergy.svg",
        "avg_duration": Decimal("90.00"),
        "description_en": "Skin prick tests and allergen screening",
        "description_ar": "اختبارات وخز الجلد وفحص مسببات الحساسية",
        "description_fr": "Tests cutanés et dépistage des allergènes",
    },
    {
        "key": "health.diagnostics.genetic_testing",
        "en": "Genetic Testing", "ar": "الفحوصات الجينية", "fr": "Tests génétiques",
        "icon_url": "https://example.com/icons/dna.svg",
        "avg_duration": Decimal("180.00"),
        "description_en": "DNA analysis and genetic screening services",
        "description_ar": "خدمات تحليل الحمض النووي والفحص الجيني",
        "description_fr": "Analyses ADN et services de dépistage génétique",
    },

    # ── health · primary_care ────────────────────────────────────
    {
        "key": "health.primary_care.vaccination",
        "en": "Vaccination", "ar": "التطعيم", "fr": "Vaccination",
        "icon_url": "https://example.com/icons/vaccine.svg",
        "avg_duration": Decimal("15.00"),
        "description_en": "Routine immunizations and travel vaccinations",
        "description_ar": "التحصينات الروتينية وتطعيمات السفر",
        "description_fr": "Vaccinations de routine et vaccins de voyage",
    },
    {
        "key": "health.primary_care.health_checkup",
        "en": "Health Check-up", "ar": "الفحص الطبي الشامل", "fr": "Bilan de santé",
        "icon_url": "https://example.com/icons/stethoscope.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "Comprehensive annual physical examinations",
        "description_ar": "الفحوصات الجسدية السنوية الشاملة",
        "description_fr": "Examens physiques annuels complets",
    },

    # ── health · specialized_care ────────────────────────────────
    {
        "key": "health.specialized_care.prenatal_care",
        "en": "Prenatal Care", "ar": "رعاية ما قبل الولادة", "fr": "Soins prénatals",
        "icon_url": "https://example.com/icons/pregnancy.svg",
        "avg_duration": Decimal("30.00"),
        "description_en": "Pregnancy monitoring and prenatal check-ups",
        "description_ar": "متابعة الحمل والفحوصات قبل الولادة",
        "description_fr": "Suivi de grossesse et examens prénatals",
    },
    {
        "key": "health.specialized_care.pediatric_care",
        "en": "Pediatric Care", "ar": "رعاية الأطفال", "fr": "Soins pédiatriques",
        "icon_url": "https://example.com/icons/baby-care.svg",
        "avg_duration": Decimal("25.00"),
        "description_en": "Child healthcare and development monitoring",
        "description_ar": "رعاية صحة الطفل ومتابعة النمو",
        "description_fr": "Soins de santé infantile et suivi du développement",
    },
    {
        "key": "health.specialized_care.geriatric_care",
        "en": "Geriatric Care", "ar": "رعاية كبار السن", "fr": "Soins gériatriques",
        "icon_url": "https://example.com/icons/elderly-care.svg",
        "avg_duration": Decimal("40.00"),
        "description_en": "Elderly health monitoring and management",
        "description_ar": "متابعة وإدارة صحة كبار السن",
        "description_fr": "Suivi et gestion de la santé des personnes âgées",
    },
    {
        "key": "health.specialized_care.sports_medicine",
        "en": "Sports Medicine", "ar": "الطب الرياضي", "fr": "Médecine du sport",
        "icon_url": "https://example.com/icons/sports-medicine.svg",
        "avg_duration": Decimal("50.00"),
        "description_en": "Injury assessment and sports-related healthcare",
        "description_ar": "تقييم الإصابات والرعاية الصحية المتعلقة بالرياضة",
        "description_fr": "Évaluation des blessures et soins liés au sport",
    },

    # ── health · dental ──────────────────────────────────────────
    {
        "key": "health.dental.dental_care",
        "en": "Dental Care", "ar": "العناية بالأسنان", "fr": "Soins dentaires",
        "icon_url": "https://example.com/icons/dental.svg",
        "avg_duration": Decimal("40.00"),
        "description_en": "Teeth cleaning, fillings, and basic dental procedures",
        "description_ar": "تنظيف الأسنان والحشوات والإجراءات الأساسية لطب الأسنان",
        "description_fr": "Nettoyage dentaire, plombages et procédures dentaires de base",
    },
    {
        "key": "health.dental.orthodontics",
        "en": "Orthodontics", "ar": "تقويم الأسنان", "fr": "Orthodontie",
        "icon_url": "https://example.com/icons/orthodontics.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "Braces, aligners, and bite correction",
        "description_ar": "التقويم المعدني والشفاف وتصحيح الإطباق",
        "description_fr": "Bagues, gouttières et correction de l'occlusion",
    },
    {
        "key": "health.dental.teeth_whitening",
        "en": "Teeth Whitening", "ar": "تبييض الأسنان", "fr": "Blanchiment dentaire",
        "icon_url": "https://example.com/icons/whitening.svg",
        "avg_duration": Decimal("45.00"),
        "description_en": "Professional teeth whitening treatments",
        "description_ar": "علاجات تبييض الأسنان الاحترافية",
        "description_fr": "Traitements professionnels de blanchiment dentaire",
    },

    # ── health · therapy ─────────────────────────────────────────
    {
        "key": "health.therapy.physiotherapy",
        "en": "Physiotherapy", "ar": "العلاج الطبيعي", "fr": "Physiothérapie",
        "icon_url": "https://example.com/icons/physical-therapy.svg",
        "avg_duration": Decimal("50.00"),
        "description_en": "Rehabilitation and physical therapy sessions",
        "description_ar": "جلسات إعادة التأهيل والعلاج الطبيعي",
        "description_fr": "Séances de rééducation et de physiothérapie",
    },
    {
        "key": "health.therapy.acupuncture",
        "en": "Acupuncture", "ar": "الوخز بالإبر", "fr": "Acupuncture",
        "icon_url": "https://example.com/icons/acupuncture.svg",
        "avg_duration": Decimal("40.00"),
        "description_en": "Traditional acupuncture therapy sessions",
        "description_ar": "جلسات العلاج التقليدي بالوخز بالإبر",
        "description_fr": "Séances de thérapie traditionnelle par acupuncture",
    },
    {
        "key": "health.therapy.mental_health_counseling",
        "en": "Mental Health Counseling", "ar": "استشارات الصحة النفسية", "fr": "Conseil en santé mentale",
        "icon_url": "https://example.com/icons/mental-health.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "Therapy and psychological counseling sessions",
        "description_ar": "جلسات العلاج والاستشارات النفسية",
        "description_fr": "Séances de thérapie et de conseil psychologique",
    },
    {
        "key": "health.therapy.nutrition_counseling",
        "en": "Nutrition Counseling", "ar": "الاستشارات الغذائية", "fr": "Conseil nutritionnel",
        "icon_url": "https://example.com/icons/nutrition.svg",
        "avg_duration": Decimal("45.00"),
        "description_en": "Diet planning and nutritional guidance",
        "description_ar": "تخطيط النظام الغذائي والإرشاد التغذوي",
        "description_fr": "Planification alimentaire et conseils nutritionnels",
    },

    # ── health · clinical_procedures ─────────────────────────────
    {
        "key": "health.clinical_procedures.minor_surgery",
        "en": "Minor Surgery", "ar": "الجراحة البسيطة", "fr": "Chirurgie mineure",
        "icon_url": "https://example.com/icons/surgery.svg",
        "avg_duration": Decimal("75.00"),
        "description_en": "Outpatient minor surgical procedures",
        "description_ar": "الإجراءات الجراحية البسيطة للمرضى الخارجيين",
        "description_fr": "Interventions chirurgicales mineures en ambulatoire",
    },
    {
        "key": "health.clinical_procedures.wound_care",
        "en": "Wound Care", "ar": "العناية بالجروح", "fr": "Soins des plaies",
        "icon_url": "https://example.com/icons/wound-care.svg",
        "avg_duration": Decimal("25.00"),
        "description_en": "Dressing changes and wound management",
        "description_ar": "تغيير الضمادات وإدارة الجروح",
        "description_fr": "Changement de pansements et gestion des plaies",
    },
    {
        "key": "health.clinical_procedures.iv_therapy",
        "en": "IV Therapy", "ar": "العلاج الوريدي", "fr": "Thérapie intraveineuse",
        "icon_url": "https://example.com/icons/iv-therapy.svg",
        "avg_duration": Decimal("35.00"),
        "description_en": "Intravenous hydration and vitamin therapy",
        "description_ar": "الترطيب الوريدي والعلاج بالفيتامينات",
        "description_fr": "Hydratation intraveineuse et vitaminothérapie",
    },

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: beauty
    # ══════════════════════════════════════════════════════════════

    # ── beauty · hair ────────────────────────────────────────────
    {
        "key": "beauty.hair.haircut",
        "en": "Haircut", "ar": "قص الشعر", "fr": "Coupe de cheveux",
        "icon_url": "https://example.com/icons/haircut.svg",
        "avg_duration": Decimal("30.00"),
        "description_en": "Basic haircut and styling",
        "description_ar": "قص وتصفيف أساسي للشعر",
        "description_fr": "Coupe et coiffage de base",
    },
    {
        "key": "beauty.hair.hair_coloring",
        "en": "Hair Coloring", "ar": "صبغ الشعر", "fr": "Coloration",
        "icon_url": "https://example.com/icons/hair-color.svg",
        "avg_duration": Decimal("90.00"),
        "description_en": "Full color, highlights, and balayage",
        "description_ar": "صبغ كامل وهايلايت وبالاياج",
        "description_fr": "Couleur complète, mèches et balayage",
    },
    {
        "key": "beauty.hair.hair_treatment",
        "en": "Hair Treatment", "ar": "علاج الشعر", "fr": "Soin capillaire",
        "icon_url": "https://example.com/icons/hair-treatment.svg",
        "avg_duration": Decimal("45.00"),
        "description_en": "Deep conditioning and keratin treatments",
        "description_ar": "علاجات ترطيب عميق وكيراتين",
        "description_fr": "Soins profonds et traitements à la kératine",
    },

    # ── beauty · nails ───────────────────────────────────────────
    {
        "key": "beauty.nails.manicure",
        "en": "Manicure", "ar": "العناية بالأظافر", "fr": "Manucure",
        "icon_url": "https://example.com/icons/manicure.svg",
        "avg_duration": Decimal("45.00"),
        "description_en": "Nail shaping, cuticle care, and polish",
        "description_ar": "تشكيل الأظافر والعناية بالجلد والطلاء",
        "description_fr": "Mise en forme, soin des cuticules et vernis",
    },
    {
        "key": "beauty.nails.pedicure",
        "en": "Pedicure", "ar": "العناية بالقدمين", "fr": "Pédicure",
        "icon_url": "https://example.com/icons/pedicure.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "Foot care and nail treatment",
        "description_ar": "العناية بالقدمين ومعالجة الأظافر",
        "description_fr": "Soins des pieds et traitement des ongles",
    },
    {
        "key": "beauty.nails.gel_extensions",
        "en": "Gel Extensions", "ar": "تركيب الأظافر جل", "fr": "Extensions en gel",
        "icon_url": "https://example.com/icons/gel-nails.svg",
        "avg_duration": Decimal("90.00"),
        "description_en": "Gel or acrylic nail extensions",
        "description_ar": "تركيب أظافر الجل أو الأكريليك",
        "description_fr": "Extensions d'ongles en gel ou acrylique",
    },

    # ── beauty · skincare ────────────────────────────────────────
    {
        "key": "beauty.skincare.facial",
        "en": "Facial Treatment", "ar": "علاج الوجه", "fr": "Soin du visage",
        "icon_url": "https://example.com/icons/facial.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "Deep cleansing and hydrating facials",
        "description_ar": "تنظيف عميق وترطيب للوجه",
        "description_fr": "Nettoyage profond et soins hydratants",
    },
    {
        "key": "beauty.skincare.massage",
        "en": "Massage", "ar": "التدليك", "fr": "Massage",
        "icon_url": "https://example.com/icons/massage.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "Relaxation and therapeutic massage",
        "description_ar": "تدليك استرخائي وعلاجي",
        "description_fr": "Massage relaxant et thérapeutique",
    },
    {
        "key": "beauty.skincare.hair_removal",
        "en": "Hair Removal", "ar": "إزالة الشعر", "fr": "Épilation",
        "icon_url": "https://example.com/icons/hair-removal.svg",
        "avg_duration": Decimal("40.00"),
        "description_en": "Waxing, laser, and threading",
        "description_ar": "الشمع والليزر والخيط",
        "description_fr": "Cire, laser et fil",
    },
    {
        "key": "beauty.skincare.makeup",
        "en": "Makeup", "ar": "المكياج", "fr": "Maquillage",
        "icon_url": "https://example.com/icons/makeup.svg",
        "avg_duration": Decimal("45.00"),
        "description_en": "Professional makeup application",
        "description_ar": "تطبيق مكياج احترافي",
        "description_fr": "Application de maquillage professionnel",
    },

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: home
    # ══════════════════════════════════════════════════════════════

    # ── home · repair ────────────────────────────────────────────
    {
        "key": "home.repair.plumbing",
        "en": "Plumbing", "ar": "السباكة", "fr": "Plomberie",
        "icon_url": "https://example.com/icons/plumbing.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "Pipe repair, leak fixing, and installation",
        "description_ar": "إصلاح الأنابيب ومعالجة التسربات والتركيب",
        "description_fr": "Réparation de tuyaux, fuites et installation",
    },
    {
        "key": "home.repair.electrical",
        "en": "Electrical Work", "ar": "الأعمال الكهربائية", "fr": "Travaux électriques",
        "icon_url": "https://example.com/icons/electrical.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "Wiring, outlets, and electrical repair",
        "description_ar": "الأسلاك والمقابس وإصلاح الكهرباء",
        "description_fr": "Câblage, prises et réparation électrique",
    },
    {
        "key": "home.repair.appliance",
        "en": "Appliance Repair", "ar": "إصلاح الأجهزة", "fr": "Réparation d'électroménager",
        "icon_url": "https://example.com/icons/appliance.svg",
        "avg_duration": Decimal("45.00"),
        "description_en": "Fridge, washer, and oven repair",
        "description_ar": "إصلاح الثلاجة والغسالة والفرن",
        "description_fr": "Réparation de réfrigérateur, lave-linge et four",
    },
    {
        "key": "home.repair.painting",
        "en": "Painting", "ar": "الدهان", "fr": "Peinture",
        "icon_url": "https://example.com/icons/painting.svg",
        "avg_duration": Decimal("180.00"),
        "description_en": "Interior and exterior painting services",
        "description_ar": "خدمات الدهان الداخلي والخارجي",
        "description_fr": "Services de peinture intérieure et extérieure",
    },

    # ── home · maintenance ───────────────────────────────────────
    {
        "key": "home.maintenance.cleaning",
        "en": "House Cleaning", "ar": "تنظيف المنزل", "fr": "Nettoyage à domicile",
        "icon_url": "https://example.com/icons/cleaning.svg",
        "avg_duration": Decimal("120.00"),
        "description_en": "Regular and deep house cleaning",
        "description_ar": "تنظيف منزلي دوري وعميق",
        "description_fr": "Nettoyage régulier et en profondeur",
    },
    {
        "key": "home.maintenance.pest_control",
        "en": "Pest Control", "ar": "مكافحة الحشرات", "fr": "Dératisation",
        "icon_url": "https://example.com/icons/pest-control.svg",
        "avg_duration": Decimal("90.00"),
        "description_en": "Extermination and pest prevention",
        "description_ar": "الإبادة والوقاية من الحشرات",
        "description_fr": "Extermination et prévention des nuisibles",
    },
    {
        "key": "home.maintenance.gardening",
        "en": "Gardening", "ar": "البستنة", "fr": "Jardinage",
        "icon_url": "https://example.com/icons/gardening.svg",
        "avg_duration": Decimal("120.00"),
        "description_en": "Lawn care, pruning, and landscaping",
        "description_ar": "العناية بالعشب والتشذيب وتنسيق الحدائق",
        "description_fr": "Entretien de pelouse, taille et aménagement",
    },

    # ── home · moving ────────────────────────────────────────────
    {
        "key": "home.moving.local_moving",
        "en": "Local Moving", "ar": "نقل محلي", "fr": "Déménagement local",
        "icon_url": "https://example.com/icons/moving.svg",
        "avg_duration": Decimal("240.00"),
        "description_en": "Same-city residential moving",
        "description_ar": "نقل سكني داخل نفس المدينة",
        "description_fr": "Déménagement résidentiel dans la même ville",
    },
    {
        "key": "home.moving.long_distance",
        "en": "Long Distance Moving", "ar": "نقل بعيد المدى", "fr": "Déménagement longue distance",
        "icon_url": "https://example.com/icons/moving-long.svg",
        "avg_duration": Decimal("480.00"),
        "description_en": "Inter-city and inter-region moving",
        "description_ar": "النقل بين المدن والمناطق",
        "description_fr": "Déménagement inter-villes et inter-régions",
    },

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: professional
    # ══════════════════════════════════════════════════════════════

    # ── professional · legal ─────────────────────────────────────
    {
        "key": "professional.legal.consultation",
        "en": "Legal Consultation", "ar": "استشارة قانونية", "fr": "Consultation juridique",
        "icon_url": "https://example.com/icons/legal.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "General legal advice and consultation",
        "description_ar": "استشارة قانونية عامة",
        "description_fr": "Conseil et consultation juridiques généraux",
    },
    {
        "key": "professional.legal.contract_drafting",
        "en": "Contract Drafting", "ar": "صياغة العقود", "fr": "Rédaction de contrats",
        "icon_url": "https://example.com/icons/contract.svg",
        "avg_duration": Decimal("120.00"),
        "description_en": "Contract preparation and review",
        "description_ar": "إعداد ومراجعة العقود",
        "description_fr": "Préparation et révision de contrats",
    },

    # ── professional · accounting ────────────────────────────────
    {
        "key": "professional.accounting.bookkeeping",
        "en": "Bookkeeping", "ar": "مسك الدفاتر", "fr": "Tenue de comptabilité",
        "icon_url": "https://example.com/icons/accounting.svg",
        "avg_duration": Decimal("90.00"),
        "description_en": "Monthly bookkeeping and reporting",
        "description_ar": "مسك الدفاتر الشهرية وإعداد التقارير",
        "description_fr": "Comptabilité mensuelle et reporting",
    },
    {
        "key": "professional.accounting.tax_preparation",
        "en": "Tax Preparation", "ar": "إعداد الضرائب", "fr": "Préparation fiscale",
        "icon_url": "https://example.com/icons/tax.svg",
        "avg_duration": Decimal("120.00"),
        "description_en": "Annual tax filing and planning",
        "description_ar": "الإقرار الضريبي السنوي والتخطيط",
        "description_fr": "Déclaration fiscale annuelle et planification",
    },

    # ── professional · consulting ────────────────────────────────
    {
        "key": "professional.consulting.business",
        "en": "Business Consulting", "ar": "استشارات الأعمال", "fr": "Conseil en entreprise",
        "icon_url": "https://example.com/icons/consulting.svg",
        "avg_duration": Decimal("120.00"),
        "description_en": "Business strategy and operations consulting",
        "description_ar": "استشارات استراتيجية وتشغيل الأعمال",
        "description_fr": "Conseil en stratégie et opérations",
    },
    {
        "key": "professional.consulting.marketing",
        "en": "Marketing Consulting", "ar": "استشارات التسويق", "fr": "Conseil marketing",
        "icon_url": "https://example.com/icons/marketing.svg",
        "avg_duration": Decimal("90.00"),
        "description_en": "Marketing strategy and campaigns",
        "description_ar": "استراتيجية التسويق والحملات",
        "description_fr": "Stratégie marketing et campagnes",
    },
    {
        "key": "professional.consulting.translation",
        "en": "Translation", "ar": "الترجمة", "fr": "Traduction",
        "icon_url": "https://example.com/icons/translation.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "Document translation and interpretation",
        "description_ar": "ترجمة الوثائق والترجمة الفورية",
        "description_fr": "Traduction de documents et interprétation",
    },

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: education
    # ══════════════════════════════════════════════════════════════

    # ── education · tutoring ─────────────────────────────────────
    {
        "key": "education.tutoring.academic",
        "en": "Academic Tutoring", "ar": "الدروس الأكاديمية", "fr": "Soutien scolaire",
        "icon_url": "https://example.com/icons/tutoring.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "One-on-one academic tutoring",
        "description_ar": "دروس أكاديمية فردية",
        "description_fr": "Cours particuliers académiques",
    },
    {
        "key": "education.tutoring.language",
        "en": "Language Lessons", "ar": "دروس اللغة", "fr": "Cours de langue",
        "icon_url": "https://example.com/icons/language.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "Language learning and conversation practice",
        "description_ar": "تعلم اللغات وممارسة المحادثة",
        "description_fr": "Apprentissage des langues et conversation",
    },
    {
        "key": "education.tutoring.music",
        "en": "Music Lessons", "ar": "دروس الموسيقى", "fr": "Cours de musique",
        "icon_url": "https://example.com/icons/music.svg",
        "avg_duration": Decimal("45.00"),
        "description_en": "Instrument and vocal lessons",
        "description_ar": "دروس الآلات والموسيقى الصوتية",
        "description_fr": "Cours d'instruments et de chant",
    },

    # ── education · training ─────────────────────────────────────
    {
        "key": "education.training.first_aid",
        "en": "First Aid Training", "ar": "تدريب الإسعافات الأولية", "fr": "Formation aux premiers secours",
        "icon_url": "https://example.com/icons/first-aid.svg",
        "avg_duration": Decimal("240.00"),
        "description_en": "CPR and emergency first aid certification",
        "description_ar": "شهادة الإنعاش القلبي الرئوي والإسعافات الأولية الطارئة",
        "description_fr": "Certification RCR et premiers secours d'urgence",
    },
    {
        "key": "education.training.driving",
        "en": "Driving Lessons", "ar": "دروس القيادة", "fr": "Cours de conduite",
        "icon_url": "https://example.com/icons/driving.svg",
        "avg_duration": Decimal("60.00"),
        "description_en": "Driving instruction and test preparation",
        "description_ar": "تعليم القيادة والتحضير للاختبار",
        "description_fr": "Enseignement de la conduite et préparation au permis",
    },
    {
        "key": "education.training.professional_certification",
        "en": "Professional Certification", "ar": "شهادات مهنية", "fr": "Certification professionnelle",
        "icon_url": "https://example.com/icons/certification.svg",
        "avg_duration": Decimal("480.00"),
        "description_en": "Industry certifications and licensing",
        "description_ar": "شهادات وتراخيص الصناعة",
        "description_fr": "Certifications et licences professionnelles",
    },

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: technology
    # ══════════════════════════════════════════════════════════════

    # ── technology · it_support ──────────────────────────────────
    {
        "key": "technology.it_support.computer_repair",
        "en": "Computer Repair", "ar": "إصلاح الحاسوب", "fr": "Réparation informatique",
        "icon_url": "https://example.com/icons/computer-repair.svg",
        "avg_duration": Decimal("90.00"),
        "description_en": "Hardware and software repair services",
        "description_ar": "خدمات إصلاح الأجهزة والبرمجيات",
        "description_fr": "Services de réparation matériel et logiciel",
    },
    {
        "key": "technology.it_support.network_setup",
        "en": "Network Setup", "ar": "إعداد الشبكات", "fr": "Installation réseau",
        "icon_url": "https://example.com/icons/network.svg",
        "avg_duration": Decimal("120.00"),
        "description_en": "Home and office network installation",
        "description_ar": "تركيب شبكات المنازل والمكاتب",
        "description_fr": "Installation de réseaux domestiques et bureaux",
    },

    # ── technology · development ─────────────────────────────────
    {
        "key": "technology.development.web_development",
        "en": "Web Development", "ar": "تطوير الويب", "fr": "Développement web",
        "icon_url": "https://example.com/icons/web-dev.svg",
        "avg_duration": Decimal("2400.00"),
        "description_en": "Website and web application development",
        "description_ar": "تطوير المواقع وتطبيقات الويب",
        "description_fr": "Développement de sites et applications web",
    },
    {
        "key": "technology.development.mobile_apps",
        "en": "Mobile App Development", "ar": "تطوير تطبيقات الجوال", "fr": "Développement mobile",
        "icon_url": "https://example.com/icons/mobile-dev.svg",
        "avg_duration": Decimal("3600.00"),
        "description_en": "iOS and Android app development",
        "description_ar": "تطوير تطبيقات iOS و Android",
        "description_fr": "Développement d'applications iOS et Android",
    },

    # ── technology · digital_marketing ───────────────────────────
    {
        "key": "technology.digital_marketing.seo",
        "en": "SEO Services", "ar": "خدمات تحسين محركات البحث", "fr": "Services SEO",
        "icon_url": "https://example.com/icons/seo.svg",
        "avg_duration": Decimal("180.00"),
        "description_en": "Search engine optimization services",
        "description_ar": "خدمات تحسين محركات البحث",
        "description_fr": "Services d'optimisation pour les moteurs de recherche",
    },
    {
        "key": "technology.digital_marketing.social_media",
        "en": "Social Media Management", "ar": "إدارة وسائل التواصل", "fr": "Gestion des réseaux sociaux",
        "icon_url": "https://example.com/icons/social.svg",
        "avg_duration": Decimal("120.00"),
        "description_en": "Social media strategy and content",
        "description_ar": "استراتيجية المحتوى ووسائل التواصل",
        "description_fr": "Stratégie et contenu pour réseaux sociaux",
    },
]

# ==================== Helpers ====================

def _first_or_none(result: Any) -> Optional[Any]:
    """
    Normalise the return value of `storage_broker.get()`.

    The broker may return a single row, a list of rows, or None. This
    helper collapses all three into "one row or None" so the caller
    never has to guess.

    If `result` is a list, the first element is returned — matching
    the seed's assumption that the lookup key (`*_name` column)
    uniquely identifies a row.
    """
    if result is None:
        return None
    if isinstance(result, list):
        return result[0] if result else None
    return result


def _get_or_create_naming_contribution(
    *,
    name_en: str,
    name_ar: str,
    name_fr: str,
    icon_url: Optional[str] = None,
    contribution_type: str = "service",
) -> Optional[Any]:
    """
    Return the existing NamingContribution for the given English name,
    or insert a new one. Returns the contribution row (with its id
    populated) on success, None on failure.
    """
    existing = _first_or_none(
        get(
            table=models.NamingContribution,
            conditions={"naming_contribution_en": name_en},
        )
    )
    if existing is not None:
        return existing

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
    return _first_or_none(result)


def _get_or_create_service_category(
    *,
    key: str,
    naming_contribution_id: int,
    icon_url: Optional[str],
    avg_duration: Optional[Decimal],
    description: Optional[str],
) -> Optional[Any]:
    """
    Return the existing ProvidedServiceCategory for the given dotted
    key, or insert a new one linked to `naming_contribution_id`.

    `provided_service_category_name` stores the key verbatim.
    """
    existing = _first_or_none(
        get(
            table=models.ProvidedServiceCategory,
            conditions={"provided_service_category_name": key},
        )
    )
    if existing is not None:
        return existing

    category = models.ProvidedServiceCategory(
        provided_service_category_name=key,
        provided_service_category_icon_url=icon_url,
        provided_service_category_avg_duration=avg_duration,
        provided_service_category_description=description,
        provided_service_category_naming_ref=naming_contribution_id,
    )
    result = insert_record(category)
    return _first_or_none(result)


def _pick_description(entry: Dict[str, Any], lang: str) -> Optional[str]:
    """
    Return the description for the given language, falling back to the
    English one when a translation isn't provided.
    """
    return entry.get(f"description_{lang}") or entry.get("description_en")


# ==================== Seeding Functions ====================

def seed_service_categories() -> int:
    """
    Seed provided service categories and their multilingual names.

    Returns:
        Number of categories inserted (existing rows are not counted).
    """
    count_inserted = 0

    for entry in SEED_SERVICE_CATEGORIES:
        key = entry["key"]
        name_en = entry["en"]

        contribution = _get_or_create_naming_contribution(
            name_en=name_en,
            name_ar=entry["ar"],
            name_fr=entry["fr"],
            icon_url=entry.get("icon_url"),
        )
        if contribution is None:
            logger.error(
                "Skipping service category %r: could not resolve naming "
                "contribution",
                key,
            )
            continue

        existing_category = _first_or_none(
            get(
                table=models.ProvidedServiceCategory,
                conditions={"provided_service_category_name": key},
            )
        )
        if existing_category is not None:
            # Backfill the naming link, icon, and duration if missing.
            if (
                getattr(
                    existing_category,
                    "provided_service_category_naming_ref",
                    None,
                )
                is None
            ):
                existing_category.provided_service_category_naming_ref = (
                    contribution.id_naming_contribution
                )
                logger.debug(
                    "Backfilled naming ref for existing category %r", key
                )
            if (
                entry.get("icon_url")
                and not existing_category.provided_service_category_icon_url
            ):
                existing_category.provided_service_category_icon_url = entry[
                    "icon_url"
                ]
            if (
                entry.get("avg_duration") is not None
                and existing_category.provided_service_category_avg_duration
                is None
            ):
                existing_category.provided_service_category_avg_duration = (
                    entry["avg_duration"]
                )
            continue

        category = _get_or_create_service_category(
            key=key,
            naming_contribution_id=contribution.id_naming_contribution,
            icon_url=entry.get("icon_url"),
            avg_duration=entry.get("avg_duration"),
            description=_pick_description(entry, "en"),
        )
        if category:
            count_inserted += 1
            logger.debug("Seeded service category: %s", key)

    logger.info("Seeded %d new provided service categories", count_inserted)
    return count_inserted


def seed_service_category(category_data: Dict[str, Any]) -> bool:
    """
    Seed a single provided service category.

    `category_data` must carry `key`; it may carry `en` / `ar` / `fr`
    plus optional `icon_url`, `avg_duration`, and
    `description_{en,ar,fr}`.

    Returns True if inserted, False if the category already existed or
    the entry was invalid.
    """
    key = category_data.get("key")
    if not key:
        logger.warning(
            "seed_service_category called with no key: %r", category_data
        )
        return False

    name_en = category_data.get("en") or key

    existing = _first_or_none(
        get(
            table=models.ProvidedServiceCategory,
            conditions={"provided_service_category_name": key},
        )
    )
    if existing is not None:
        logger.debug("Service category already exists: %s", key)
        return False

    icon_url = category_data.get("icon_url")
    avg_duration = category_data.get("avg_duration")

    contribution = _get_or_create_naming_contribution(
        name_en=name_en,
        name_ar=category_data.get("ar", name_en),
        name_fr=category_data.get("fr", name_en),
        icon_url=icon_url,
    )
    if contribution is None:
        logger.error("Could not create naming contribution for %r", key)
        return False

    category = _get_or_create_service_category(
        key=key,
        naming_contribution_id=contribution.id_naming_contribution,
        icon_url=icon_url,
        avg_duration=avg_duration,
        description=_pick_description(category_data, "en"),
    )
    if category:
        logger.debug("Seeded service category: %s", key)
        return True
    return False


def seed_service_categories_from_list(
    categories: List[Dict[str, Any]],
) -> int:
    """
    Seed provided service categories from a custom list.

    Each entry must carry `key`; it may carry `en` / `ar` / `fr` and
    optionally `icon_url`, `avg_duration`, and
    `description_{en,ar,fr}`.

    Returns:
        Number of categories inserted.
    """
    count_inserted = 0

    for entry in categories:
        key = entry.get("key")
        if not key:
            logger.warning("Skipping entry with no key: %r", entry)
            continue

        name_en = entry.get("en") or key
        icon_url = entry.get("icon_url")
        avg_duration = entry.get("avg_duration")

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

        category = _get_or_create_service_category(
            key=key,
            naming_contribution_id=contribution.id_naming_contribution,
            icon_url=icon_url,
            avg_duration=avg_duration,
            description=_pick_description(entry, "en"),
        )
        if category:
            count_inserted += 1
            logger.debug("Seeded service category: %s", key)

    logger.info(
        "Seeded %d provided service categories from custom list",
        count_inserted,
    )
    return count_inserted


# ==================== Utility Functions ====================

def get_all_seeded_service_categories() -> List[Dict[str, Any]]:
    """
    Return every service category with its name and description in all
    three languages.

    `key` is the value stored in `provided_service_category_name`;
    `name` is the English display string for backward compatibility.
    """
    with session_scope() as session:
        rows = (
            session.query(
                models.ProvidedServiceCategory,
                models.NamingContribution,
            )
            .outerjoin(
                models.NamingContribution,
                models.ProvidedServiceCategory.provided_service_category_naming_ref
                == models.NamingContribution.id_naming_contribution,
            )
            .all()
        )

        result: List[Dict[str, Any]] = []
        for category, naming in rows:
            key = category.provided_service_category_name
            name_en = (
                getattr(naming, "naming_contribution_en", None) or key
                if naming
                else key
            )
            result.append(
                {
                    "id": category.provided_service_category_id,
                    "key": key,
                    "name": name_en,
                    "en": name_en,
                    "ar": getattr(naming, "naming_contribution_ar", None)
                    if naming
                    else None,
                    "fr": getattr(naming, "naming_contribution_fr", None)
                    if naming
                    else None,
                    "icon_url": category.provided_service_category_icon_url,
                    "avg_duration": float(
                        category.provided_service_category_avg_duration
                    )
                    if category.provided_service_category_avg_duration
                    else None,
                    "description": category.provided_service_category_description,
                    "naming_ref": category.provided_service_category_naming_ref,
                }
            )
        return result


def service_category_exists(category_key: str) -> bool:
    """
    Check whether a service category with the given dotted key exists.
    """
    existing = _first_or_none(
        get(
            table=models.ProvidedServiceCategory,
            conditions={"provided_service_category_name": category_key},
        )
    )
    return existing is not None


def get_service_category_by_key(
    category_key: str,
) -> Optional[models.ProvidedServiceCategory]:
    """
    Return a service category by its dotted key, or None.
    """
    return _first_or_none(
        get(
            table=models.ProvidedServiceCategory,
            conditions={"provided_service_category_name": category_key},
        )
    )


def get_service_category_by_id(
    category_id: int,
) -> Optional[models.ProvidedServiceCategory]:
    """
    Return a service category by its primary key, or None.
    """
    return _first_or_none(
        get(
            table=models.ProvidedServiceCategory,
            conditions={"provided_service_category_id": category_id},
        )
    )


def get_service_categories_by_duration(
    max_duration: int,
) -> List[models.ProvidedServiceCategory]:
    """
    Return service categories whose average duration is at or below
    `max_duration` minutes.
    """
    with session_scope() as session:
        return (
            session.query(models.ProvidedServiceCategory)
            .filter(
                models.ProvidedServiceCategory.provided_service_category_avg_duration
                <= max_duration
            )
            .all()
        )


def delete_all_service_categories() -> int:
    """
    Delete all provided service categories. Leaves the naming
    contributions in place, since other tables may reference them.

    Returns the number of categories deleted.
    """
    with session_scope() as session:
        count = session.query(models.ProvidedServiceCategory).delete()
        session.commit()
        logger.info("Deleted %d provided service categories", count)
        return count


def update_service_category_duration(
    category_key: str, avg_duration: Decimal
) -> bool:
    """
    Update the average duration for a service category, addressed by
    its dotted key.
    """
    with session_scope() as session:
        category = (
            session.query(models.ProvidedServiceCategory)
            .filter(
                models.ProvidedServiceCategory.provided_service_category_name
                == category_key
            )
            .first()
        )

        if not category:
            logger.warning("Service category not found: %s", category_key)
            return False

        category.provided_service_category_avg_duration = avg_duration
        session.commit()
        logger.debug(
            "Updated duration for service category: %s", category_key
        )
        return True


def update_service_category_icon(category_key: str, icon_url: str) -> bool:
    """
    Update the icon URL for a service category, addressed by its
    dotted key.
    """
    with session_scope() as session:
        category = (
            session.query(models.ProvidedServiceCategory)
            .filter(
                models.ProvidedServiceCategory.provided_service_category_name
                == category_key
            )
            .first()
        )

        if not category:
            logger.warning("Service category not found: %s", category_key)
            return False

        category.provided_service_category_icon_url = icon_url
        session.commit()
        logger.debug("Updated icon for service category: %s", category_key)
        return True


# ==================== Main Execution ====================

def main():
    """Main entry point for seeding provided service categories."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed provided service categories"
    )
    parser.add_argument(
        "--delete-first",
        action="store_true",
        help="Delete all existing service categories before seeding",
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

    print("Starting provided service category seeding...")

    try:
        if args.delete_first:
            delete_all_service_categories()

        count = seed_service_categories()
        print(f"Successfully seeded {count} provided service categories")

        if count > 0:
            categories = get_all_seeded_service_categories()
            print("\nSeeded service categories:")
            for cat in categories:
                languages = " / ".join(
                    filter(None, [cat.get("en"), cat.get("fr"), cat.get("ar")])
                )
                duration = (
                    f"{cat['avg_duration']} min"
                    if cat["avg_duration"]
                    else "N/A"
                )
                icon_info = (
                    f" (icon: {cat['icon_url']})" if cat["icon_url"] else ""
                )
                print(
                    f"  - [{cat['key']}] {languages} "
                    f"(ID: {cat['id']}, Duration: {duration}){icon_info}"
                )

    except Exception as e:
        print(f"Failed to seed provided service categories: {e}")
        raise


if __name__ == "__main__":
    main()