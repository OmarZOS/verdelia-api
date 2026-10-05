# test_runner/data.py
"""Static data pools, payload generators, and response helpers.

Split out of the runner so the runner file focuses on scenarios. The
generators are pure: dict in, dict out. No HTTP, no context.
"""

import json
import random
import uuid
from typing import Any, Dict, List, Optional


# ══════════════════════════════════════════════════════════════════
# Static pools
# ══════════════════════════════════════════════════════════════════

IPRODUCT_NAME_POOL = [
    ("Paracetamol", "باراسيتامول", "Paracétamol"),
    ("Ibuprofen", "إيبوبروفين", "Ibuprofène"),
    ("Amoxicillin", "أموكسيسيلين", "Amoxicilline"),
    ("Vitamin C", "فيتامين سي", "Vitamine C"),
    ("Omega-3", "أوميغا 3", "Oméga-3"),
    ("Antibiotic", "مضاد حيوي", "Antibiotique"),
    ("Pain Relief", "مسكن للألم", "Antidouleur"),
    ("Allergy Medicine", "دواء الحساسية", "Médicament antiallergique"),
    ("Cough Syrup", "شراب السعال", "Sirop pour la toux"),
    ("Medical Device", "جهاز طبي", "Dispositif médical"),
    ("Surgical Mask", "كمامة جراحية", "Masque chirurgical"),
    ("Hand Sanitizer", "معقم اليدين", "Désinfectant pour les mains"),
    ("Thermometer", "ميزان حرارة", "Thermomètre"),
    ("Blood Pressure Monitor", "جهاز قياس ضغط الدم", "Tensiomètre"),
    ("Stethoscope", "سماعة طبية", "Stéthoscope"),
    ("Syringe", "محقنة", "Seringue"),
    ("Bandage", "ضمادة", "Bandage"),
    ("Antiseptic", "مطهر", "Antiseptique"),
    ("Antibiotic Cream", "كريم مضاد حيوي", "Crème antibiotique"),
    ("Painkiller", "مسكن", "Antalgique"),
    ("Antihistamine", "مضاد الهيستامين", "Antihistaminique"),
    ("Decongestant", "مزيل الاحتقان", "Décongestionnant"),
    ("Antacid", "مضاد للحموضة", "Anti-acide"),
    ("Insulin", "الأنسولين", "Insuline"),
    ("Vaccine", "لقاح", "Vaccin"),
    ("Antiviral", "مضاد فيروسات", "Antiviral"),
    ("Antifungal", "مضاد فطريات", "Antifongique"),
    ("Hemostatic Agent", "عامل مرقئ", "Hémostatique"),
    ("Suture Kit", "طقم خياطة", "Kit de suture"),
    ("Surgical Gloves", "قفازات جراحية", "Gants chirurgicaux"),
    ("Medical Tape", "شريط طبي", "Ruban médical"),
    ("Wound Dressing", "ضمادة الجروح", "Pansement"),
    ("Compression Bandage", "ضمادة ضاغطة", "Bande de compression"),
    ("First Aid Kit", "حقيبة الإسعافات الأولية", "Trousse de premiers secours"),
    ("Splint", "جبيرة", "Attelle"),
]


REAL_FIRST_NAMES = [
    "Mohamed", "Ahmed", "Ali", "Fatima", "Youssef", "Amina", "Karim", "Sara",
    "Nadia", "Rachid", "Leila", "Hassan", "Khadija", "Omar", "Soukaina",
    "Hamza", "Salma", "Mehdi", "Yasmina", "Anas", "Imane", "Reda", "Nour",
    "Zakaria", "Houda", "Ayoub", "Maryam", "Amine", "Sana", "Adil", "Malak",
    "Adam", "Lina", "Rayane", "Ines", "Yacine", "Lydia", "Selim", "Nora",
    "Sofiane", "Amira", "Rayan", "Hana", "Kamel", "Mona", "Fares", "Dina",
]

REAL_LAST_NAMES = [
    "Benali", "Khan", "Cohen", "Lopez", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Peterson", "Murphy", "Cook", "Morgan", "Bell",
    "Ward", "Watson", "Brooks", "Kelly", "Sanders", "Price", "Bennett", "Wood",
    "Barnes", "Ross", "Henderson", "Coleman", "Jenkins", "Perry", "Powell", "Long",
    "Patterson", "Hughes", "Flores", "Washington", "Butler", "Simmons", "Foster", "Gonzales",
]

REAL_ORG_NAMES = [
    "HealthCare Plus", "MediCorp", "Wellness Center", "Global Health",
    "Premium Care", "MediServe", "HealthFirst", "CarePlus", "MediHealth",
    "WellnessWorks", "City Medical", "Advanced Care", "Prime Health",
    "Elite Medical", "Family Care", "Specialist Center", "Medical Arts",
    "LifeLine Health", "CareBridge", "MediLink", "HealthWave", "VitalCare",
    "Optimum Health", "Pulse Medical", "Core Wellness", "Apex Healthcare",
    "Zenith Medical", "Nova Health", "Virtue Care", "Harmony Medical",
    "Pinnacle Health", "Radiant Care", "Summit Medical", "Tranquil Health",
]

REAL_SUPPLIER_NAMES = [
    "City Medical Center", "HealthFirst Clinic", "MediLab Services",
    "PharmaCare", "Advanced Medical Supplies", "Precision Diagnostics",
    "Wellness Medical Group", "Prime Healthcare", "Elite Medical Services",
    "CarePlus Pharmacy", "MediHealth Solutions", "Global Medical Supply",
    "MediTech Services", "HealthBridge", "Vitality Medical", "Apex Diagnostics",
    "CuraMed", "NovaCare", "Virtue Health", "Optimum Medical",
    "Pulse Healthcare", "Zenith Medical Supply", "Radiant Health", "Core Medical",
]

REAL_PRODUCT_NAMES = [
    "Paracetamol", "Ibuprofen", "Amoxicillin", "Vitamin C", "Omega-3",
    "Antibiotic", "Pain Relief", "Allergy Medicine", "Cough Syrup",
    "Medical Device", "Surgical Mask", "Hand Sanitizer", "Thermometer",
    "Blood Pressure Monitor", "Stethoscope", "Syringe", "Bandage", "Antiseptic",
    "Antibiotic Cream", "Painkiller", "Antihistamine", "Decongestant", "Antacid",
    "Insulin", "Vaccine", "Antiviral", "Antifungal", "Antiparasitic",
    "Hemostatic Agent", "Suture Kit", "Surgical Gloves", "Medical Tape",
    "Wound Dressing", "Compression Bandage", "First Aid Kit", "Splint",
]

REAL_STREETS = [
    "Rue Didouche Mourad", "Avenue du 1er Novembre", "Rue Larbi Ben Mhidi",
    "Boulevard Krim Belkacem", "Rue des Freres Bouadou", "Avenue de l'Independance",
    "Rue Ali Khodja", "Boulevard Colonel Amirouche", "Rue Emir Abdelkader",
    "Avenue Ahmed Ben Bella", "Rue de la Liberte", "Boulevard des Martyrs",
    "Rue Abane Ramdane", "Avenue Franklin Roosevelt", "Rue de l'Alma",
    "Boulevard Zighout Youcef", "Rue des Freres Addad", "Avenue du Docteur Benzerdjeb",
    "Rue de Constantine", "Boulevard de la Republique", "Rue du 11 Decembre 1960",
]

REAL_CITIES = [
    "Algiers", "Oran", "Constantine", "Annaba", "Blida", "Setif",
    "Tizi Ouzou", "Bejaia", "Batna", "Sidi Bel Abbes", "Biskra", "Tebessa",
    "El Oued", "Ghardaia", "Tamanrasset", "Mostaganem", "Skikda", "Tipaza",
    "Boumerdes", "Relizane", "Saida", "M'sila", "Medea", "Tlemcen",
    "Chlef", "Bechar", "Adrar", "Laghouat", "Bouira", "Guelma",
]

SPECIALITIES = [
    "cardiology", "neurology", "pediatrics", "orthopedics", "general medicine",
    "dermatology", "ophthalmology", "oncology", "gynecology", "urology",
    "psychiatry", "radiology", "dentistry", "emergency medicine", "surgery",
    "nephrology", "gastroenterology", "pulmonology", "hematology", "immunology",
    "rheumatology", "endocrinology", "fertility", "audiology", "physiotherapy",
]

PROVIDER_TYPES = [
    "Medical", "Pharmacy", "Diagnostic", "Surgical",
    "Laboratory", "Dental", "Optical", "Therapeutic", "Rehabilitation",
]

BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

COUNTRIES = [
    "DZ", "MA", "TN", "EG", "SA", "AE",
    "US", "FR", "DE", "IT", "ES", "CA", "GB",
]

# Must match the DB enum on `payment.payment_method`.
PAYMENT_METHODS = ["wallet", "cash", "mobile_money", "bank_transfer"]

SERVICE_NAMES = [
    "General Consultation", "Follow-Up Visit", "Emergency Care",
    "Physical Therapy", "Blood Test", "X-Ray Imaging", "Vaccination",
    "Wound Care", "Health Screening", "Nutrition Counseling",
    "Chronic Care Management", "Pre-Surgical Assessment",
    "Post-Surgical Follow-Up", "Ultrasound", "ECG",
    "Physiotherapy Session", "Dental Cleaning", "Eye Exam",
    "Allergy Testing", "Minor Surgery",
]

# (name, type, unit) — the type is one of the enum values accepted
# by the resource_requirement schema; the unit only appears in notes.
RESOURCE_REQUIREMENTS = [
    ("Disposable gloves", "consumable", "pair"),
    ("Syringes", "consumable", "unit"),
    ("Bandages", "consumable", "roll"),
    ("Test tubes", "consumable", "unit"),
    ("X-ray film", "consumable", "sheet"),
    ("Ultrasound gel", "consumable", "bottle"),
    ("Surgical masks", "consumable", "unit"),
    ("IV fluids", "consumable", "bag"),
]

# These are ids, not names — the staff_role table is small and
# stable. Add to the list when new roles are seeded.
# ══════════════════════════════════════════════════════════════════
# Service pools and generators (moved from test_service_endpoints.py)
# ══════════════════════════════════════════════════════════════════

SERVICE_DISPLAY_NAMES = [
    "Premium Cleaning Service", "Professional Plumbing",
    "Electrical Installation", "HVAC Maintenance",
    "Landscaping Service", "Home Renovation",
    "Painting Service", "Carpentry Work",
    "Tile Installation", "Roofing Service",
    "Garden Design", "Pool Maintenance",
    "Security System Installation", "Home Automation",
    "Solar Panel Installation", "Water Heater Repair",
    "Appliance Repair", "Flooring Installation",
    "Window Replacement", "Insulation Service",
    "Deep Carpet Cleaning", "Duct Cleaning",
    "Pest Control", "Gutter Cleaning",
    "Pressure Washing", "Garage Door Repair",
    "Locksmith Service", "Moving Service",
]

SERVICE_DESCRIPTIONS = [
    "Professional service with certified staff",
    "Quality workmanship guaranteed",
    "Fast and reliable service",
    "Licensed and insured professionals",
    "Free consultation and estimate",
    "Emergency service available",
    "Competitive pricing",
    "High-quality materials used",
    "Expert technicians with years of experience",
    "Satisfaction guaranteed",
    "Eco-friendly solutions available",
    "Customized service plans",
]

SERVICE_QUANTIFIERS = ["unit", "hour", "session", "package", "job"]

SERVICE_DURATIONS_MINUTES = [15, 30, 45, 60, 90, 120, 180, 240, 300, 360]

RESOURCE_REQUIREMENT_NAMES = [
    "Cleaning supplies", "Electric drill set", "Piping materials",
    "HVAC equipment", "Landscaping tools", "Paint and brushes",
    "Wood materials", "Tile and grout", "Roofing materials",
    "Safety equipment", "Protective gear", "Cleaning chemicals",
    "Spare parts kit", "Measurement tools", "Power tools",
]

RESOURCE_REQUIREMENT_TYPES = [
    "consumable", "tool", "material", "equipment",
]

# Role IDs that exist in the `staff_role` table.
SERVICE_STAFF_ROLE_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# ══════════════════════════════════════════════════════════════════
# Response helpers
# ══════════════════════════════════════════════════════════════════

def unwrap(payload: Any) -> Dict[str, Any]:
    """Return the inner `data` dict of a wrapped backend response."""
    if isinstance(payload, dict):
        inner = payload.get("data")
        if isinstance(inner, dict):
            return inner
    return payload if isinstance(payload, dict) else {}


def short(text: Optional[str], n: int = 400) -> str:
    if not text:
        return ""
    return text if len(text) <= n else text[:n] + "..."


_ID_KEYS: List[str] = [
    "id_app_user", "id_product_provider", "provided_service_id","id_provider_organisation",
    "idprovider_organisation", "id_product", "id",
    "user_id", "supplier_id", "organisation_id",
    "rule_id", "staff_rule_id",
    "location_id", "person_id",
    "id_plan", "plan_id",
    "id_subscription", "subscription_id",
    "payment_id", "id_payment",
]


def extract_id(payload: Any) -> int:
    """Best-effort id extraction from an API response."""
    if not isinstance(payload, dict):
        return 0
    inner = payload.get("data")
    if isinstance(inner, dict):
        payload = inner

    for key in _ID_KEYS:
        if key in payload:
            try:
                return int(payload[key])
            except (ValueError, TypeError):
                pass

    for nested in [
        "user", "provider", "product", "payment", "rule", "staff",
        "organisation", "plan", "subscription", "invoice","service"
    ]:
        v = payload.get(nested)
        if isinstance(v, dict):
            found = extract_id(v)
            if found:
                return found
    return 0


# ══════════════════════════════════════════════════════════════════
# Generators
# ══════════════════════════════════════════════════════════════════

def get_random_item(lst: List) -> Any:
    return random.choice(lst) if lst else None


def random_date(start_year: int = 1950, end_year: int = 2005) -> str:
    return (
        f"{random.randint(start_year, end_year)}-"
        f"{random.randint(1, 12):02d}-"
        f"{random.randint(1, 28):02d}"
    )


def random_phone() -> str:
    return (
        f"+213-5{random.randint(10, 99):02d}"
        f"{random.randint(10, 99):02d}"
        f"{random.randint(10, 99):02d}"
    )


def random_price(min_price: float = 5.0, max_price: float = 200.0) -> float:
    return round(random.uniform(min_price, max_price), 2)


# ── Payload generators ─────────────────────────────────────────────

def generate_user_data(user_type: Optional[str] = None) -> Dict[str, Any]:
    first = get_random_item(REAL_FIRST_NAMES) or "Test"
    last = get_random_item(REAL_LAST_NAMES) or "User"
    all_types = ["provider", "customer", "patient", "guest", "admin"]
    return {
        "app_user_name": (
            f"{first.lower()}_{last.lower()}_{uuid.uuid4().hex[:4]}"
        ),
        "app_user_password": "Test123!@#",
        "app_user_email": (
            f"{first.lower()}.{last.lower()}."
            f"{uuid.uuid4().hex[:4]}@example.com"
        ),
        "app_user_type": user_type or random.choice(all_types),
        "app_user_preferences": json.dumps({
            "theme": random.choice(["dark", "light"]),
            "notifications": random.choice([True, False]),
            "language": random.choice(["en", "fr", "ar"]),
            "timezone": random.choice(["UTC+1", "UTC+2", "UTC+3"]),
            "currency": "DZD",
            "date_format": random.choice(
                ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"]
            ),
        }),
        "app_user_image_url": (
            f"https://example.com/avatars/"
            f"{uuid.uuid4().hex[:8]}.jpg"
        ),
    }


def generate_person_data(extended: bool = False) -> Dict[str, Any]:
    data = {
        "person_first_name": get_random_item(REAL_FIRST_NAMES) or "Test",
        "person_last_name": get_random_item(REAL_LAST_NAMES) or "User",
        "person_birth_date": random_date(1950, 2005),
        "person_gender": random.choice(["male", "female"]),
        "person_country_code": random.choice(COUNTRIES),
    }
    if extended:
        data.update({
            "blood_type": random.choice(BLOOD_TYPES),
            "person_email": (
                f"person_{uuid.uuid4().hex[:4]}@example.com"
            ),
            "person_phone": random_phone(),
            "person_id_number": (
                f"{random.randint(100000000, 999999999)}"
            ),
            "person_id_type": random.choice(
                ["Passport", "National ID", "Driver License"]
            ),
            "person_languages": random.choice([
                ["ar", "fr"], ["en", "ar"], ["fr", "en"],
                ["ar", "fr", "en"],
            ]),
            "person_job_title": random.choice([
                "Doctor", "Nurse", "Pharmacist",
                "Patient", "Administrator", "Specialist",
            ]),
            "person_job_ref": (
                f"JOB-{uuid.uuid4().hex[:6].upper()}"
            ),
        })
    return data


def generate_location_data(extended: bool = False) -> Dict[str, Any]:
    data = {
        "location_latitude": round(random.uniform(35.0, 37.0), 6),
        "location_longitude": round(random.uniform(-5.0, 8.0), 6),
        "location_name": get_random_item([
            "Home", "Work", "Clinic", "Office", "Shop",
            "Warehouse", "Distribution Center", "Hospital", "Pharmacy",
        ]) or "Office",
        "address_street": (
            f"{random.randint(1, 999)} "
            f"{get_random_item(REAL_STREETS) or 'Main St'}"
        ),
        "address_city": get_random_item(REAL_CITIES) or "Algiers",
        "address_postal_code": f"{random.randint(1000, 9999)}",
        "address_country": random.choice(COUNTRIES),
    }
    if extended:
        data.update({
            "address_building": (
                f"Building {random.choice(['A', 'B', 'C', 'D', 'E'])}"
            ),
            "address_floor": random.randint(1, 12),
            "address_apartment": f"APT {random.randint(1, 100)}",
            "address_landmark": get_random_item([
                "Near Hospital", "Next to Mall", "Opposite School",
                "Near Station", "Downtown",
            ]),
            "address_timezone": random.choice(
                ["UTC+1", "UTC+2", "UTC+3"]
            ),
        })
    return data


def generate_organisation_data(
    *, with_naming: bool = True,
) -> Dict[str, Any]:
    base = get_random_item(REAL_ORG_NAMES) or "HealthCare Plus"
    suffix = uuid.uuid4().hex[:4]
    flat_name = f"{base} {suffix}"

    payload: Dict[str, Any] = {
        "provider_organisation_name": flat_name,
        "provider_organisation_desc": (
            f"Leading healthcare provider specializing in "
            f"{get_random_item(SPECIALITIES) or 'medicine'}"
        ),
    }

    if with_naming:
        payload["naming"] = {
            "en": flat_name,
            "ar": f"مؤسسة {suffix}",
            "fr": f"Organisation {suffix}",
            "naming_contribution_type": "provider",
            "id_naming_contribution": 0,
        }

    return payload


def generate_supplier_data(
    org_id: int,
    owner_id: int,
    *,
    with_naming: bool = True,
) -> Dict[str, Any]:
    base = get_random_item(REAL_SUPPLIER_NAMES) or "Medical Center"
    suffix = uuid.uuid4().hex[:4]

    payload: Dict[str, Any] = {
        "id_provider_owner": owner_id,
        "id_provider_organisation": org_id,
        "id_product_provider_type": random.choice([1, 2, 3, 4, 5, 6]),
        "provider_name": f"Provider_{suffix}",
        "provider_contact_info": json.dumps({
            "phone": random_phone(),
            "email": f"contact_{uuid.uuid4().hex[:4]}@example.com",
            "website": f"https://{uuid.uuid4().hex[:8]}.com",
            "fax": (
                f"+213-5{random.randint(10, 99)}"
                f"{random.randint(10, 99)}"
                f"{random.randint(10, 99)}"
            ),
            "emergency_contact": random_phone(),
        }),
    }

    if with_naming:
        display_en = f"{base} {suffix}"
        payload["provider_name"] = display_en
        payload["naming"] = {
            "en": display_en,
            "ar": f"مزود {suffix}",
            "fr": f"Fournisseur {suffix}",
            "naming_contribution_type": "provider",
            "id_naming_contribution": 0,
        }

    return payload


def generate_product_data(
    provider_id: int,
    owner_id: int,
) -> Dict[str, Any]:
    name_en = get_random_item(REAL_PRODUCT_NAMES) or "Product"
    suffix = uuid.uuid4().hex[:4]
    flat_name = f"{name_en} {suffix}"

    return {
        "product_name": flat_name,
        "naming": {
            "en": flat_name,
            "ar": None,
            "fr": None,
            "naming_contribution_type": "product",
            "id_naming_contribution": 0,
        },
        "product_brand": get_random_item([
            "BrandA", "BrandB", "BrandC", "Generic",
            "Premium", "MedicalPro", "HealthPlus", "CareMed",
        ]) or "Generic",
        "product_provider_id": provider_id,
        "product_category_id": random.choice([1, 2, 3, 4, 5]),
        "product_barcode": (
            f"{random.randint(1000000000000, 9999999999999)}"
        ),
        "product_description": (
            f"High-quality "
            f"{get_random_item(['medication', 'device', 'supplement', 'supply', 'equipment', 'consumable'])} "
            f"product"
        ),
        "product_price": random_price(5.0, 200.0),
        "product_quantity": random.randint(10, 1000),
        "product_quantifier": get_random_item([
            "mg", "g", "ml", "pack", "unit",
            "tablet", "capsule", "bottle",
        ]) or "unit",
        "product_owner": owner_id,
        "product_sku": f"SKU-{uuid.uuid4().hex[:8].upper()}",
        "product_weight": round(random.uniform(0.1, 10.0), 2),
        "product_dimensions": (
            f"{random.randint(1, 30)}x"
            f"{random.randint(1, 30)}x"
            f"{random.randint(1, 30)} cm"
        ),
        "product_manufacturer": get_random_item([
            "Manufacturer A", "Manufacturer B",
            "Manufacturer C", "Generic Corp",
        ]),
        "product_gluten_status": random.choice([
            "gluten_free", "contains_gluten",
            "may_contain_gluten", "unknown",
        ]),
        "product_shelf_life_months": random.randint(6, 36),
        "product_requires_prescription": random.choice([True, False]),
        "product_tax_rate": round(random.uniform(5.0, 20.0), 1),
        "product_is_active": random.choice([True, False]),
    }


def generate_product_image_data() -> Dict[str, Any]:
    return {
        "product_image_url": (
            f"https://example.com/images/"
            f"product_{uuid.uuid4().hex[:8]}.jpg"
        ),
        "product_image_alt": (
            f"Product image {uuid.uuid4().hex[:4]}"
        ),
        "product_image_order": random.randint(1, 5),
        "product_image_primary": random.choice([True, False]),
    }


def generate_iproduct_data() -> Dict[str, Any]:
    name_en, name_ar, name_fr = random.choice(IPRODUCT_NAME_POOL)
    suffix = uuid.uuid4().hex[:4]
    flat_name = f"{name_en} {suffix}"

    return {
        "naming": {
            "en": flat_name,
            "ar": f"{name_ar} {suffix}",
            "fr": f"{name_fr} {suffix}",
            "naming_contribution_type": "product",
            "id_naming_contribution": 0,
        },
        "iproduct_name": flat_name,
        "iproduct_barcode": (
            f"{random.randint(1000000000000, 9999999999999)}"
        ),
        "iproduct_brand": get_random_item([
            "BrandA", "BrandB", "BrandC", "Generic", "Premium",
        ]) or "Generic",
        "iproduct_estimated_price": random_price(5.0, 200.0),
        "iproduct_price_currency": "DZD",
        "iproduct_gluten_status": random.choice([
            "gluten_free", "contains_gluten",
            "may_contain_gluten", "unknown",
        ]),
        "iproduct_info_source": random.choice([
            "openai", "manual", "csv_import", "api", "user_submitted",
        ]),
        "iproduct_info_confidence": round(random.uniform(0.5, 1.0), 2),
        "iproduct_category_id": random.choice([1, 2, 3, 4, 5]),
        "iproduct_verified": random.choice([True, False]),
        "iproduct_ingredients": random.choice([
            ["Active ingredient A", "Excipient B", "Preservative C"],
            ["Ingredient X", "Ingredient Y", "Ingredient Z"],
            ["Component 1", "Component 2", "Component 3"],
        ]),
        "iproduct_nutrition_facts": {
            "calories": random.randint(0, 500),
            "protein": round(random.uniform(0.0, 30.0), 1),
            "carbs": round(random.uniform(0.0, 50.0), 1),
            "fat": round(random.uniform(0.0, 20.0), 1),
            "fiber": round(random.uniform(0.0, 15.0), 1),
        },
    }


def generate_service_data(
    provider_id: int = 0,
    category_id: int = 0,
) -> Dict[str, Any]:
    """Generate a service payload.

    Returns the `service` sub-dict — not the full request body. The
    runner composes `{service, requirements, staff_requirements}`
    at the call site.
    """
    return {
        "provided_service_product_provider_id": provider_id,
        "provided_service_category_id": category_id,
        "provided_service_name": random.choice(SERVICE_DISPLAY_NAMES),
        "provided_service_description": random.choice(SERVICE_DESCRIPTIONS),
        "provided_service_base_price": round(
            random.uniform(50.00, 500.00), 2,
        ),
        "provided_service_final_price": round(
            random.uniform(60.00, 600.00), 2,
        ),
        "provided_service_actual_duration": random.choice(
            SERVICE_DURATIONS_MINUTES
        ),
        "provided_service_is_active": True,
        "provided_service_quantifier": random.choice(
            SERVICE_QUANTIFIERS
        ),
    }


def generate_resource_requirement(
    service_id: int = 0,
    product_id: int = 0,
) -> Dict[str, Any]:
    """Generate a resource requirement.

    `product_id` is the FK to the product this requirement consumes.
    If not supplied (or 0), defaults to 1 — the runner ensures at
    least one product exists before calling this.
    """
    product_ref = product_id if product_id > 0 else 1
    return {
        "resource_requirement_service_id": service_id,
        "resource_requirement_name": random.choice(
            RESOURCE_REQUIREMENT_NAMES
        ),
        "resource_requirement_type": random.choice(
            RESOURCE_REQUIREMENT_TYPES
        ),
        "resource_requirement_quantity": random.randint(1, 20),
        "resource_requirement_cost_per_unit": round(
            random.uniform(10.00, 200.00), 2,
        ),
        "resource_requirement_is_consumable": random.choice(
            [True, False]
        ),
        "resource_requirement_notes": (
            f"Test requirement {uuid.uuid4().hex[:6]}"
        ),
        "resource_requirement_product_ref": product_ref,
    }


def generate_staff_requirement(service_id: int = 0) -> Dict[str, Any]:
    """Generate a staff requirement.

    Role IDs come from `SERVICE_STAFF_ROLE_IDS` and must exist in
    the `staff_role` table. Add to that list when new roles are
    seeded.
    """
    return {
        "service_staff_requirement_service_id": service_id,
        "service_staff_requirement_role": random.choice(
            SERVICE_STAFF_ROLE_IDS
        ),
        "service_staff_requirement_notes": (
            f"Test staff req {uuid.uuid4().hex[:6]}"
        ),
        "service_staff_requirement_min_count": random.randint(1, 3),
        "service_staff_requirement_max_count": random.randint(3, 6),
        "service_staff_requirement_hourly_rate": round(
            random.uniform(20.00, 100.00), 2,
        ),
        "service_staff_requirement_allocated_hours": random.randint(2, 8),
    }


def generate_service_request(
    provider_id: int,
    category_id: int,
    product_ids: List[int],
    *,
    name_suffix: Optional[str] = None,
    n_resources: Optional[int] = None,
    n_staff: Optional[int] = None,
) -> Dict[str, Any]:
    """Compose the full service-creation body.

    Bundles the service, its resource requirements, and its staff
    requirements into the shape the router expects:

        {"service": {...}, "requirements": [...], "staff_requirements": [...]}

    Counts default to a random range. Pass explicit counts when a
    scenario needs to exercise a specific size.
    """
    service = generate_service_data(provider_id, category_id)
    suffix = name_suffix or uuid.uuid4().hex[:5]
    service["provided_service_name"] = (
        f"{service['provided_service_name']} {suffix}"
    )

    if n_resources is None:
        n_resources = random.randint(1, 4)
    if n_staff is None:
        n_staff = random.randint(0, 3)

    product_pool = product_ids or [1]
    requirements = [
        generate_resource_requirement(0, random.choice(product_pool))
        for _ in range(n_resources)
    ]
    staff_requirements = [
        generate_staff_requirement(0) for _ in range(n_staff)
    ]

    return {
        "service": service,
        "requirements": requirements,
        "staff_requirements": staff_requirements,
    }


def generate_subscription_purchase_data(
    plan_id: int,
    *,
    payment_method: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Query params for `POST /app_user/{user_id}/subscription/initiate`.

    The endpoint reads everything from query params, so this dict is
    meant to be passed as `params=` to httpx, not `json=`.

    Note: no `invoice_id` — the workflow composes the invoice itself
    as part of the purchase. There is nothing for the client to pass.
    """
    params: Dict[str, Any] = {
        "plan_id": plan_id,
        "payment_method": payment_method or random.choice(PAYMENT_METHODS),
    }
    if notes is not None:
        params["notes"] = notes
    return params