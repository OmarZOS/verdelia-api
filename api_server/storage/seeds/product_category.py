# storage/seeds/product_category.py
"""
Product category seed module using the storage broker.

Each category is backed by a NamingContribution row carrying the
Arabic / French / English names. Seeding is idempotent: re-running
inserts nothing.

The canonical identity of a category is its dotted key
(`domain.subdomain.key`, e.g. `food.alimentary.baked_goods`), stored
in `product_category_name`. Human-readable display names come from
the joined NamingContribution row — never from the name column.
"""

import logging
from typing import Any, Dict, List, Optional

from storage.storage_broker import insert_record, get
from core.models import models

logger = logging.getLogger(__name__)


# ==================== Seed Data ====================

# `key` is the immutable lookup anchor, stored in
# `product_category_name`. Treat it as frozen once shipped —
# downstream lookups and NamingContribution rows key on it.
SEED_PRODUCT_CATEGORIES: List[Dict[str, str]] = [
    # ══════════════════════════════════════════════════════════════
    # DOMAIN: food
    # ══════════════════════════════════════════════════════════════

    # ── food · alimentary ────────────────────────────────────────
    {"key": "food.alimentary.baked_goods",              "en": "Baked Goods",                  "fr": "Produits de boulangerie",           "ar": "المخبوزات"},
    {"key": "food.alimentary.spreads",                  "en": "Spreads",                      "fr": "Pâtes à tartiner",                  "ar": "المربى والدهون القابلة للدهن"},
    {"key": "food.alimentary.cereals",                  "en": "Cereals",                      "fr": "Céréales",                          "ar": "الحبوب"},
    {"key": "food.alimentary.pasta",                    "en": "Pasta",                        "fr": "Pâtes alimentaires",                "ar": "المعكرونة"},
    {"key": "food.alimentary.snacks",                   "en": "Snacks",                       "fr": "En-cas",                            "ar": "الوجبات الخفيفة"},
    {"key": "food.alimentary.desserts",                 "en": "Desserts",                     "fr": "Desserts",                          "ar": "الحلويات"},
    {"key": "food.alimentary.frozen_foods",             "en": "Frozen Foods",                 "fr": "Produits surgelés",                 "ar": "الأطعمة المجمدة"},
    {"key": "food.alimentary.flours_baking_ingredients","en": "Flours & Baking Ingredients",  "fr": "Farines et ingrédients de boulangerie","ar": "الطحين ومكونات الخبز"},
    {"key": "food.alimentary.canned_packaged_goods",    "en": "Canned & Packaged Goods",      "fr": "Conserves et produits emballés",    "ar": "المعلبات والأغذية المعبأة"},
    {"key": "food.alimentary.dairy",                    "en": "Dairy",                        "fr": "Produits laitiers",                 "ar": "منتجات الألبان"},
    {"key": "food.alimentary.cheese",                   "en": "Cheese",                       "fr": "Fromages",                          "ar": "الأجبان"},
    {"key": "food.alimentary.meat",                     "en": "Meat",                         "fr": "Viandes",                           "ar": "اللحوم"},
    {"key": "food.alimentary.poultry",                  "en": "Poultry",                      "fr": "Volaille",                          "ar": "الدواجن"},
    {"key": "food.alimentary.seafood",                  "en": "Seafood",                      "fr": "Produits de la mer",                "ar": "المأكولات البحرية"},
    {"key": "food.alimentary.eggs",                     "en": "Eggs",                         "fr": "Œufs",                              "ar": "البيض"},
    {"key": "food.alimentary.fruits",                   "en": "Fruits",                       "fr": "Fruits",                            "ar": "الفواكه"},
    {"key": "food.alimentary.vegetables",               "en": "Vegetables",                   "fr": "Légumes",                           "ar": "الخضروات"},
    {"key": "food.alimentary.legumes",                  "en": "Legumes & Pulses",             "fr": "Légumineuses",                      "ar": "البقوليات"},
    {"key": "food.alimentary.nuts_seeds",               "en": "Nuts & Seeds",                 "fr": "Noix et graines",                   "ar": "المكسرات والبذور"},
    {"key": "food.alimentary.condiments",               "en": "Condiments & Sauces",          "fr": "Condiments et sauces",              "ar": "التوابل والصلصات"},
    {"key": "food.alimentary.spices_herbs",             "en": "Spices & Herbs",               "fr": "Épices et herbes",                  "ar": "البهارات والأعشاب"},
    {"key": "food.alimentary.oils_fats",                "en": "Oils & Fats",                  "fr": "Huiles et matières grasses",        "ar": "الزيوت والدهون"},
    {"key": "food.alimentary.sweeteners",               "en": "Sweeteners & Sugars",          "fr": "Sucres et édulcorants",             "ar": "المحليات والسكريات"},
    {"key": "food.alimentary.baby_food",                "en": "Baby Food",                    "fr": "Alimentation infantile",            "ar": "أغذية الأطفال"},

    # ── food · beverages ─────────────────────────────────────────
    {"key": "food.beverages.water",                     "en": "Water",                        "fr": "Eaux",                              "ar": "المياه"},
    {"key": "food.beverages.soft_drinks",               "en": "Soft Drinks",                  "fr": "Sodas",                             "ar": "المشروبات الغازية"},
    {"key": "food.beverages.juices",                    "en": "Juices",                       "fr": "Jus",                               "ar": "العصائر"},
    {"key": "food.beverages.coffee_tea",                "en": "Coffee & Tea",                 "fr": "Café et thé",                       "ar": "القهوة والشاي"},
    {"key": "food.beverages.energy_drinks",             "en": "Energy & Sports Drinks",       "fr": "Boissons énergisantes et sportives","ar": "مشروبات الطاقة والرياضة"},
    {"key": "food.beverages.plant_based_milks",         "en": "Plant-Based Milks",            "fr": "Laits végétaux",                    "ar": "الحليب النباتي"},
    {"key": "food.beverages.syrups",                    "en": "Syrups & Concentrates",        "fr": "Sirops et concentrés",              "ar": "الشراب والمركزات"},
    {"key": "food.beverages.alcoholic",                 "en": "Alcoholic Beverages",          "fr": "Boissons alcoolisées",              "ar": "المشروبات الكحولية"},

    # ── food · prepared ──────────────────────────────────────────
    {"key": "food.prepared.ready_meals",                "en": "Ready Meals",                  "fr": "Plats préparés",                    "ar": "الوجبات الجاهزة"},
    {"key": "food.prepared.sandwiches_wraps",           "en": "Sandwiches & Wraps",           "fr": "Sandwichs et wraps",                "ar": "الساندويتشات والراب"},
    {"key": "food.prepared.pastries",                   "en": "Pastries",                     "fr": "Viennoiseries",                     "ar": "المعجنات"},
    {"key": "food.prepared.pizza",                      "en": "Pizza",                        "fr": "Pizzas",                            "ar": "البيتزا"},
    {"key": "food.prepared.salads",                     "en": "Salads",                       "fr": "Salades",                           "ar": "السلطات"},
    {"key": "food.prepared.soups",                      "en": "Soups",                        "fr": "Soupes",                            "ar": "الشوربات"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: health
    # ══════════════════════════════════════════════════════════════

    # ── health · pharma ──────────────────────────────────────────
    {"key": "health.pharma.pain_relief",                "en": "Pain Relief",                  "fr": "Antidouleurs",                      "ar": "مسكنات الألم"},
    {"key": "health.pharma.cold_flu",                   "en": "Cold & Flu",                   "fr": "Rhume et grippe",                   "ar": "البرد والإنفلونزا"},
    {"key": "health.pharma.digestive",                  "en": "Digestive Health",             "fr": "Santé digestive",                   "ar": "صحة الجهاز الهضمي"},
    {"key": "health.pharma.allergy",                    "en": "Allergy Relief",               "fr": "Antiallergiques",                   "ar": "مضادات الحساسية"},
    {"key": "health.pharma.first_aid",                  "en": "First Aid",                    "fr": "Premiers secours",                  "ar": "الإسعافات الأولية"},
    {"key": "health.pharma.prescription",               "en": "Prescription Medicine",        "fr": "Médicaments sur ordonnance",        "ar": "الأدوية الموصوفة"},

    # ── health · wellness ────────────────────────────────────────
    {"key": "health.wellness.vitamins",                 "en": "Vitamins",                     "fr": "Vitamines",                         "ar": "الفيتامينات"},
    {"key": "health.wellness.minerals",                 "en": "Minerals",                     "fr": "Minéraux",                          "ar": "المعادن"},
    {"key": "health.wellness.probiotics",               "en": "Probiotics",                   "fr": "Probiotiques",                      "ar": "البروبيوتيك"},
    {"key": "health.wellness.sports_nutrition",         "en": "Sports Nutrition",             "fr": "Nutrition sportive",                "ar": "تغذية الرياضيين"},
    {"key": "health.wellness.weight_management",        "en": "Weight Management",            "fr": "Gestion du poids",                  "ar": "إدارة الوزن"},
    {"key": "health.wellness.sleep_aids",               "en": "Sleep Aids",                   "fr": "Aides au sommeil",                  "ar": "مساعدات النوم"},

    # ── health · medical_devices ─────────────────────────────────
    {"key": "health.medical_devices.thermometers",      "en": "Thermometers",                 "fr": "Thermomètres",                      "ar": "مقاييس الحرارة"},
    {"key": "health.medical_devices.blood_pressure",    "en": "Blood Pressure Monitors",      "fr": "Tensiomètres",                      "ar": "أجهزة قياس ضغط الدم"},
    {"key": "health.medical_devices.glucose_meters",    "en": "Glucose Meters",               "fr": "Glucomètres",                       "ar": "أجهزة قياس السكر"},
    {"key": "health.medical_devices.oximeters",         "en": "Pulse Oximeters",              "fr": "Oxymètres de pouls",                "ar": "أجهزة قياس الأكسجين"},
    {"key": "health.medical_devices.mobility_aids",     "en": "Mobility Aids",                "fr": "Aides à la mobilité",               "ar": "أدوات المساعدة على الحركة"},

    # ── health · personal_care ───────────────────────────────────
    {"key": "health.personal_care.oral",                "en": "Oral Care",                    "fr": "Hygiène bucco-dentaire",            "ar": "العناية بالفم"},
    {"key": "health.personal_care.skin",                "en": "Skin Care",                    "fr": "Soins de la peau",                  "ar": "العناية بالبشرة"},
    {"key": "health.personal_care.hair",                "en": "Hair Care",                    "fr": "Soins capillaires",                 "ar": "العناية بالشعر"},
    {"key": "health.personal_care.hygiene",             "en": "Personal Hygiene",             "fr": "Hygiène personnelle",               "ar": "النظافة الشخصية"},
    {"key": "health.personal_care.feminine",            "en": "Feminine Care",                "fr": "Hygiène féminine",                  "ar": "العناية النسائية"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: retail
    # ══════════════════════════════════════════════════════════════

    # ── retail · household ───────────────────────────────────────
    {"key": "retail.household.cleaning",                "en": "Cleaning Supplies",            "fr": "Produits de nettoyage",             "ar": "مواد التنظيف"},
    {"key": "retail.household.laundry",                 "en": "Laundry",                      "fr": "Lessive",                           "ar": "الغسيل"},
    {"key": "retail.household.kitchen",                 "en": "Kitchen Supplies",             "fr": "Articles de cuisine",               "ar": "مستلزمات المطبخ"},
    {"key": "retail.household.paper",                   "en": "Paper Products",               "fr": "Produits en papier",                "ar": "المنتجات الورقية"},
    {"key": "retail.household.air_fresheners",          "en": "Air Fresheners",               "fr": "Désodorisants",                     "ar": "معطرات الجو"},

    # ── retail · electronics ─────────────────────────────────────
    {"key": "retail.electronics.phones",                "en": "Phones & Accessories",         "fr": "Téléphones et accessoires",         "ar": "الهواتف والملحقات"},
    {"key": "retail.electronics.computers",             "en": "Computers",                    "fr": "Ordinateurs",                       "ar": "الحواسيب"},
    {"key": "retail.electronics.audio",                 "en": "Audio",                        "fr": "Audio",                             "ar": "الصوتيات"},
    {"key": "retail.electronics.cables_chargers",       "en": "Cables & Chargers",            "fr": "Câbles et chargeurs",               "ar": "الكابلات والشواحن"},
    {"key": "retail.electronics.batteries",             "en": "Batteries",                    "fr": "Piles et batteries",                "ar": "البطاريات"},

    # ── retail · home ────────────────────────────────────────────
    {"key": "retail.home.furniture",                    "en": "Furniture",                    "fr": "Meubles",                           "ar": "الأثاث"},
    {"key": "retail.home.decor",                        "en": "Home Decor",                   "fr": "Décoration",                        "ar": "ديكور المنزل"},
    {"key": "retail.home.bedding",                      "en": "Bedding",                      "fr": "Literie",                           "ar": "مفروشات السرير"},
    {"key": "retail.home.lighting",                     "en": "Lighting",                     "fr": "Éclairage",                         "ar": "الإضاءة"},
    {"key": "retail.home.storage",                      "en": "Storage & Organization",       "fr": "Rangement et organisation",         "ar": "التخزين والتنظيم"},

    # ── retail · apparel ─────────────────────────────────────────
    {"key": "retail.apparel.men",                       "en": "Men's Clothing",               "fr": "Vêtements pour hommes",             "ar": "ملابس رجالية"},
    {"key": "retail.apparel.women",                     "en": "Women's Clothing",             "fr": "Vêtements pour femmes",             "ar": "ملابس نسائية"},
    {"key": "retail.apparel.kids",                      "en": "Kids' Clothing",               "fr": "Vêtements pour enfants",            "ar": "ملابس أطفال"},
    {"key": "retail.apparel.footwear",                  "en": "Footwear",                     "fr": "Chaussures",                        "ar": "الأحذية"},
    {"key": "retail.apparel.accessories",               "en": "Accessories",                  "fr": "Accessoires",                       "ar": "الإكسسوارات"},

    # ── retail · pet_supplies ────────────────────────────────────
    {"key": "retail.pet_supplies.food",                 "en": "Pet Food",                     "fr": "Alimentation pour animaux",         "ar": "طعام الحيوانات"},
    {"key": "retail.pet_supplies.toys",                 "en": "Pet Toys",                     "fr": "Jouets pour animaux",               "ar": "ألعاب الحيوانات"},
    {"key": "retail.pet_supplies.grooming",             "en": "Pet Grooming",                 "fr": "Toilettage",                        "ar": "العناية بالحيوانات"},
    {"key": "retail.pet_supplies.health",               "en": "Pet Health",                   "fr": "Santé animale",                     "ar": "صحة الحيوانات"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: services
    # ══════════════════════════════════════════════════════════════

    # ── services · beauty ────────────────────────────────────────
    {"key": "services.beauty.haircut",                  "en": "Haircut & Styling",            "fr": "Coupe et coiffure",                 "ar": "قص وتصفيف الشعر"},
    {"key": "services.beauty.nails",                    "en": "Nail Care",                    "fr": "Soins des ongles",                  "ar": "العناية بالأظافر"},
    {"key": "services.beauty.skin_treatments",          "en": "Skin Treatments",              "fr": "Soins de la peau",                  "ar": "علاجات البشرة"},
    {"key": "services.beauty.massage",                  "en": "Massage",                      "fr": "Massage",                           "ar": "التدليك"},
    {"key": "services.beauty.makeup",                   "en": "Makeup",                       "fr": "Maquillage",                        "ar": "المكياج"},

    # ── services · home_services ─────────────────────────────────
    {"key": "services.home_services.plumbing",          "en": "Plumbing",                     "fr": "Plomberie",                         "ar": "السباكة"},
    {"key": "services.home_services.electrical",        "en": "Electrical",                   "fr": "Électricité",                       "ar": "الكهرباء"},
    {"key": "services.home_services.cleaning",          "en": "Cleaning",                     "fr": "Nettoyage",                         "ar": "التنظيف"},
    {"key": "services.home_services.painting",          "en": "Painting",                     "fr": "Peinture",                          "ar": "الدهان"},
    {"key": "services.home_services.moving",            "en": "Moving",                       "fr": "Déménagement",                      "ar": "نقل الأثاث"},
    {"key": "services.home_services.gardening",         "en": "Gardening",                    "fr": "Jardinage",                         "ar": "البستنة"},

    # ── services · professional ──────────────────────────────────
    {"key": "services.professional.legal",              "en": "Legal Services",               "fr": "Services juridiques",               "ar": "الخدمات القانونية"},
    {"key": "services.professional.accounting",         "en": "Accounting",                   "fr": "Comptabilité",                      "ar": "المحاسبة"},
    {"key": "services.professional.consulting",         "en": "Consulting",                   "fr": "Conseil",                           "ar": "الاستشارات"},
    {"key": "services.professional.marketing",          "en": "Marketing",                    "fr": "Marketing",                         "ar": "التسويق"},
    {"key": "services.professional.translation",        "en": "Translation",                  "fr": "Traduction",                        "ar": "الترجمة"},

    # ── services · education ─────────────────────────────────────
    {"key": "services.education.tutoring",              "en": "Tutoring",                     "fr": "Cours particuliers",                "ar": "الدروس الخصوصية"},
    {"key": "services.education.language",              "en": "Language Lessons",             "fr": "Cours de langue",                   "ar": "دروس اللغة"},
    {"key": "services.education.music",                 "en": "Music Lessons",                "fr": "Cours de musique",                  "ar": "دروس الموسيقى"},
    {"key": "services.education.test_prep",             "en": "Test Preparation",             "fr": "Préparation aux examens",           "ar": "التحضير للاختبارات"},

    # ── services · health_services ───────────────────────────────
    {"key": "services.health_services.general_practice",   "en": "General Practice",          "fr": "Médecine générale",                 "ar": "الطب العام"},
    {"key": "services.health_services.dentistry",          "en": "Dentistry",                 "fr": "Dentisterie",                       "ar": "طب الأسنان"},
    {"key": "services.health_services.physiotherapy",      "en": "Physiotherapy",             "fr": "Kinésithérapie",                    "ar": "العلاج الطبيعي"},
    {"key": "services.health_services.psychology",         "en": "Psychology",                "fr": "Psychologie",                       "ar": "علم النفس"},
    {"key": "services.health_services.nutrition",          "en": "Nutrition",                 "fr": "Nutrition",                         "ar": "التغذية"},
    {"key": "services.health_services.optometry",          "en": "Optometry",                 "fr": "Optométrie",                        "ar": "قياس البصر"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: logistics
    # ══════════════════════════════════════════════════════════════

    # ── logistics · delivery ─────────────────────────────────────
    {"key": "logistics.delivery.same_day",              "en": "Same-Day Delivery",            "fr": "Livraison le jour même",            "ar": "توصيل في نفس اليوم"},
    {"key": "logistics.delivery.express",               "en": "Express Delivery",             "fr": "Livraison express",                 "ar": "توصيل سريع"},
    {"key": "logistics.delivery.freight",               "en": "Freight",                      "fr": "Fret",                              "ar": "الشحن الثقيل"},
    {"key": "logistics.delivery.international",         "en": "International Shipping",       "fr": "Expédition internationale",         "ar": "الشحن الدولي"},
    {"key": "logistics.delivery.last_mile",             "en": "Last-Mile",                    "fr": "Dernier kilomètre",                 "ar": "التوصيل النهائي"},

    # ── logistics · warehousing ──────────────────────────────────
    {"key": "logistics.warehousing.storage",            "en": "Storage",                      "fr": "Entreposage",                       "ar": "التخزين"},
    {"key": "logistics.warehousing.fulfillment",        "en": "Fulfillment",                  "fr": "Préparation de commandes",          "ar": "تنفيذ الطلبات"},
    {"key": "logistics.warehousing.cold_chain",         "en": "Cold Chain",                   "fr": "Chaîne du froid",                   "ar": "سلسلة التبريد"},
    {"key": "logistics.warehousing.inventory",          "en": "Inventory Management",         "fr": "Gestion des stocks",                "ar": "إدارة المخزون"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: automotive
    # ══════════════════════════════════════════════════════════════

    # ── automotive · parts ───────────────────────────────────────
    {"key": "automotive.parts.engine",                  "en": "Engine Parts",                 "fr": "Pièces moteur",                     "ar": "قطع المحرك"},
    {"key": "automotive.parts.brakes",                  "en": "Brakes",                       "fr": "Freins",                            "ar": "الفرامل"},
    {"key": "automotive.parts.suspension",              "en": "Suspension",                   "fr": "Suspension",                        "ar": "نظام التعليق"},
    {"key": "automotive.parts.electrical",              "en": "Electrical",                   "fr": "Électricité",                       "ar": "الكهرباء"},
    {"key": "automotive.parts.tires_wheels",            "en": "Tires & Wheels",               "fr": "Pneus et jantes",                   "ar": "الإطارات والعجلات"},
    {"key": "automotive.parts.body",                    "en": "Body & Exterior",              "fr": "Carrosserie et extérieur",          "ar": "الهيكل والخارج"},

    # ── automotive · fluids ──────────────────────────────────────
    {"key": "automotive.fluids.engine_oil",             "en": "Engine Oil",                   "fr": "Huile moteur",                      "ar": "زيت المحرك"},
    {"key": "automotive.fluids.coolant",                "en": "Coolant",                      "fr": "Liquide de refroidissement",        "ar": "سائل التبريد"},
    {"key": "automotive.fluids.brake_fluid",            "en": "Brake Fluid",                  "fr": "Liquide de frein",                  "ar": "سائل الفرامل"},
    {"key": "automotive.fluids.windshield",             "en": "Windshield Fluid",             "fr": "Liquide lave-glace",                "ar": "سائل الزجاج"},

    # ── automotive · services ────────────────────────────────────
    {"key": "automotive.services.maintenance",          "en": "Maintenance",                  "fr": "Entretien",                         "ar": "الصيانة"},
    {"key": "automotive.services.repair",               "en": "Repair",                       "fr": "Réparation",                        "ar": "الإصلاح"},
    {"key": "automotive.services.car_wash",             "en": "Car Wash",                     "fr": "Lavage auto",                       "ar": "غسيل السيارات"},
    {"key": "automotive.services.inspection",           "en": "Inspection",                   "fr": "Contrôle technique",                "ar": "الفحص الفني"},

    # ══════════════════════════════════════════════════════════════
    # DOMAIN: agriculture
    # ══════════════════════════════════════════════════════════════

    # ── agriculture · seeds ──────────────────────────────────────
    {"key": "agriculture.seeds.vegetables",             "en": "Vegetable Seeds",              "fr": "Graines de légumes",                "ar": "بذور الخضروات"},
    {"key": "agriculture.seeds.fruits",                 "en": "Fruit Seeds",                  "fr": "Graines de fruits",                 "ar": "بذور الفواكه"},
    {"key": "agriculture.seeds.herbs",                  "en": "Herb Seeds",                   "fr": "Graines d'herbes",                  "ar": "بذور الأعشاب"},
    {"key": "agriculture.seeds.flowers",                "en": "Flower Seeds",                 "fr": "Graines de fleurs",                 "ar": "بذور الزهور"},

    # ── agriculture · fertilizers ────────────────────────────────
    {"key": "agriculture.fertilizers.organic",          "en": "Organic Fertilizers",          "fr": "Engrais organiques",                "ar": "الأسمدة العضوية"},
    {"key": "agriculture.fertilizers.chemical",         "en": "Chemical Fertilizers",         "fr": "Engrais chimiques",                 "ar": "الأسمدة الكيماوية"},
    {"key": "agriculture.fertilizers.pesticides",       "en": "Pesticides",                   "fr": "Pesticides",                        "ar": "المبيدات"},
    {"key": "agriculture.fertilizers.herbicides",       "en": "Herbicides",                   "fr": "Herbicides",                        "ar": "مبيدات الأعشاب"},

    # ── agriculture · equipment ──────────────────────────────────
    {"key": "agriculture.equipment.tractors",           "en": "Tractors",                     "fr": "Tracteurs",                         "ar": "الجرارات"},
    {"key": "agriculture.equipment.irrigation",         "en": "Irrigation Systems",           "fr": "Systèmes d'irrigation",             "ar": "أنظمة الري"},
    {"key": "agriculture.equipment.greenhouses",        "en": "Greenhouses",                  "fr": "Serres",                            "ar": "البيوت المحمية"},
    {"key": "agriculture.equipment.harvesting",         "en": "Harvesting Equipment",         "fr": "Matériel de récolte",               "ar": "معدات الحصاد"},
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
    contribution_type: str = "product",
) -> Optional[Any]:
    """
    Return the existing NamingContribution for the given English name,
    or insert a new one. Returns the contribution row (with its id
    populated) on success, None on failure.

    The English name is used as the natural key, since
    `naming_contribution_en` is what downstream lookups key on.
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
        naming_contribution_icon_url=None,
        naming_contribution_by=None,
        naming_contribution_app_version=None,
    )
    result = insert_record(contribution)
    return _first_or_none(result)


def _get_or_create_product_category(
    *,
    key: str,
    naming_contribution_id: int,
) -> Optional[Any]:
    """
    Return the existing ProductCategory for the given dotted key, or
    insert a new one linked to `naming_contribution_id`.

    `product_category_name` stores the key verbatim.
    """
    existing = _first_or_none(
        get(
            table=models.ProductCategory,
            conditions={"product_category_name": key},
        )
    )
    if existing is not None:
        return existing

    category = models.ProductCategory(
        product_category_name=key,
        product_category_icon=None,
        product_category_naming_ref=naming_contribution_id,
    )
    result = insert_record(category)
    return _first_or_none(result)


# ==================== Seeding Function ====================

def seed_product_categories() -> int:
    """
    Seed product categories and their multilingual names.

    Returns:
        Number of product categories inserted (existing rows are not
        counted).
    """
    count_inserted = 0

    for entry in SEED_PRODUCT_CATEGORIES:
        key = entry["key"]
        name_en = entry["en"]

        contribution = _get_or_create_naming_contribution(
            name_en=name_en,
            name_ar=entry["ar"],
            name_fr=entry["fr"],
        )
        if contribution is None:
            logger.error(
                "Skipping category %r: could not resolve naming contribution",
                key,
            )
            continue

        existing_category = _first_or_none(
            get(
                table=models.ProductCategory,
                conditions={"product_category_name": key},
            )
        )
        if existing_category is not None:
            # Backfill the naming link if the row predates this seed.
            if (
                getattr(
                    existing_category, "product_category_naming_ref", None
                )
                is None
            ):
                existing_category.product_category_naming_ref = (
                    contribution.id_naming_contribution
                )
                logger.debug(
                    "Backfilled naming ref for existing category %r", key
                )
            continue

        category = _get_or_create_product_category(
            key=key,
            naming_contribution_id=contribution.id_naming_contribution,
        )
        if category:
            count_inserted += 1
            logger.debug("Seeded product category: %s", key)

    logger.info("Seeded %d new product categories", count_inserted)
    return count_inserted


# ==================== Main Execution ====================

def main():
    """Main entry point for seeding product categories."""
    print("Starting product category seeding...")

    try:
        count = seed_product_categories()
        print(f"Successfully seeded {count} product categories")
    except Exception as e:
        print(f"Failed to seed product categories: {e}")
        raise


if __name__ == "__main__":
    main()