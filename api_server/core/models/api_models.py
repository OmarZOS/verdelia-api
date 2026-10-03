# api_models.py
"""
API Models for Verdelia System
All models include proper types, default values, and validation.
"""

from datetime import datetime, date
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator, validator
from enum import Enum
from constants import ReactionType

# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    COMPLETED = "completed"

class CartStatus(str, Enum):
    PENDING = "PENDING"
    CHECKED_OUT = "CHECKED_OUT"
    ABANDONED = "ABANDONED"


class GlutenStatus(str, Enum):
    GLUTEN_FREE = "gluten_free"
    CONTAINS_GLUTEN = "contains_gluten"
    MAY_CONTAIN = "may_contain"
    UNKNOWN = "unknown"

# ============================================================================
# RESPONSE MODELS
# ============================================================================

class API_Resolution(BaseModel):
    """Standard API response wrapper"""
    status: int = Field(..., description="HTTP status code")
    error_code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human readable message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "error_code": "SUCCESS",
                "message": "Operation completed successfully"
            }
        }

# ============================================================================
# PERSON & LOCATION MODELS
# ============================================================================

class Gender(str, Enum):
    """Gender enum"""
    MALE = "male"
    FEMALE = "female"
    
    @classmethod
    def from_db(cls, value: str) -> "Gender":
        """Convert database value to enum"""
        try:
            return cls(value)
        except ValueError:
            return cls.MALE
    
    def to_db(self) -> str:
        """Convert enum to database value"""
        return self.value

class BloodType(str, Enum):
    """Blood type enum with Rh factor"""
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"
    UNKNOWN = "Unknown"
    
    @classmethod
    def to_list(cls) -> List[str]:
        """Convert database value to enum"""
        try:
            return [v for v in [cls.A_POSITIVE,cls.A_NEGATIVE
,cls.B_POSITIVE
,cls.B_NEGATIVE
,cls.AB_POSITIVE
,cls.AB_NEGATIVE
,cls.O_POSITIVE
,cls.O_NEGATIVE
,cls.UNKNOWN]]
        except ValueError:
            return cls.UNKNOWN
    

    @classmethod
    def from_db(cls, value: str) -> "BloodType":
        """Convert database value to enum"""
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN
    
    def to_db(self) -> str:
        """Convert enum to database value"""
        return self.value
    
    @property
    def is_positive(self) -> bool:
        """Check if blood type is Rh positive"""
        return '+' in self.value
    
    @property
    def is_negative(self) -> bool:
        """Check if blood type is Rh negative"""
        return '-' in self.value
    
    @property
    def is_universal_donor(self) -> bool:
        """O- is universal donor"""
        return self == BloodType.O_NEGATIVE
    
    @property
    def is_universal_recipient(self) -> bool:
        """AB+ is universal recipient"""
        return self == BloodType.AB_POSITIVE

# ============ API MODELS ============

class CountryCode(str, Enum):
    """ISO 3166-1 alpha-2 country codes"""
    AF = "AF"  # Afghanistan
    AL = "AL"  # Albania
    DZ = "DZ"  # Algeria
    AD = "AD"  # Andorra
    AO = "AO"  # Angola
    AR = "AR"  # Argentina
    AM = "AM"  # Armenia
    AU = "AU"  # Australia
    AT = "AT"  # Austria
    AZ = "AZ"  # Azerbaijan
    BS = "BS"  # Bahamas
    BH = "BH"  # Bahrain
    BD = "BD"  # Bangladesh
    BB = "BB"  # Barbados
    BY = "BY"  # Belarus
    BE = "BE"  # Belgium
    BZ = "BZ"  # Belize
    BJ = "BJ"  # Benin
    BT = "BT"  # Bhutan
    BO = "BO"  # Bolivia
    BA = "BA"  # Bosnia and Herzegovina
    BW = "BW"  # Botswana
    BR = "BR"  # Brazil
    BN = "BN"  # Brunei
    BG = "BG"  # Bulgaria
    BF = "BF"  # Burkina Faso
    BI = "BI"  # Burundi
    KH = "KH"  # Cambodia
    CM = "CM"  # Cameroon
    CA = "CA"  # Canada
    CV = "CV"  # Cape Verde
    CF = "CF"  # Central African Republic
    TD = "TD"  # Chad
    CL = "CL"  # Chile
    CN = "CN"  # China
    CO = "CO"  # Colombia
    KM = "KM"  # Comoros
    CG = "CG"  # Congo
    CD = "CD"  # Congo (DRC)
    CR = "CR"  # Costa Rica
    HR = "HR"  # Croatia
    CU = "CU"  # Cuba
    CY = "CY"  # Cyprus
    CZ = "CZ"  # Czech Republic
    DK = "DK"  # Denmark
    DJ = "DJ"  # Djibouti
    DM = "DM"  # Dominica
    DO = "DO"  # Dominican Republic
    EC = "EC"  # Ecuador
    EG = "EG"  # Egypt
    SV = "SV"  # El Salvador
    GQ = "GQ"  # Equatorial Guinea
    ER = "ER"  # Eritrea
    EE = "EE"  # Estonia
    SZ = "SZ"  # Eswatini
    ET = "ET"  # Ethiopia
    FJ = "FJ"  # Fiji
    FI = "FI"  # Finland
    FR = "FR"  # France
    GA = "GA"  # Gabon
    GM = "GM"  # Gambia
    GE = "GE"  # Georgia
    DE = "DE"  # Germany
    GH = "GH"  # Ghana
    GR = "GR"  # Greece
    GD = "GD"  # Grenada
    GT = "GT"  # Guatemala
    GN = "GN"  # Guinea
    GW = "GW"  # Guinea-Bissau
    GY = "GY"  # Guyana
    HT = "HT"  # Haiti
    HN = "HN"  # Honduras
    HU = "HU"  # Hungary
    IS = "IS"  # Iceland
    IN = "IN"  # India
    ID = "ID"  # Indonesia
    IR = "IR"  # Iran
    IQ = "IQ"  # Iraq
    IE = "IE"  # Ireland
    IL = "IL"  # Israel
    IT = "IT"  # Italy
    JM = "JM"  # Jamaica
    JP = "JP"  # Japan
    JO = "JO"  # Jordan
    KZ = "KZ"  # Kazakhstan
    KE = "KE"  # Kenya
    KI = "KI"  # Kiribati
    KP = "KP"  # North Korea
    KR = "KR"  # South Korea
    KW = "KW"  # Kuwait
    KG = "KG"  # Kyrgyzstan
    LA = "LA"  # Laos
    LV = "LV"  # Latvia
    LB = "LB"  # Lebanon
    LS = "LS"  # Lesotho
    LR = "LR"  # Liberia
    LY = "LY"  # Libya
    LI = "LI"  # Liechtenstein
    LT = "LT"  # Lithuania
    LU = "LU"  # Luxembourg
    MG = "MG"  # Madagascar
    MW = "MW"  # Malawi
    MY = "MY"  # Malaysia
    MV = "MV"  # Maldives
    ML = "ML"  # Mali
    MT = "MT"  # Malta
    MH = "MH"  # Marshall Islands
    MR = "MR"  # Mauritania
    MU = "MU"  # Mauritius
    MX = "MX"  # Mexico
    FM = "FM"  # Micronesia
    MD = "MD"  # Moldova
    MC = "MC"  # Monaco
    MN = "MN"  # Mongolia
    ME = "ME"  # Montenegro
    MA = "MA"  # Morocco
    MZ = "MZ"  # Mozambique
    MM = "MM"  # Myanmar
    NA = "NA"  # Namibia
    NR = "NR"  # Nauru
    NP = "NP"  # Nepal
    NL = "NL"  # Netherlands
    NZ = "NZ"  # New Zealand
    NI = "NI"  # Nicaragua
    NE = "NE"  # Niger
    NG = "NG"  # Nigeria
    MK = "MK"  # North Macedonia
    NO = "NO"  # Norway
    OM = "OM"  # Oman
    PK = "PK"  # Pakistan
    PW = "PW"  # Palau
    PA = "PA"  # Panama
    PG = "PG"  # Papua New Guinea
    PY = "PY"  # Paraguay
    PE = "PE"  # Peru
    PH = "PH"  # Philippines
    PL = "PL"  # Poland
    PT = "PT"  # Portugal
    QA = "QA"  # Qatar
    RO = "RO"  # Romania
    RU = "RU"  # Russia
    RW = "RW"  # Rwanda
    KN = "KN"  # Saint Kitts and Nevis
    LC = "LC"  # Saint Lucia
    VC = "VC"  # Saint Vincent and the Grenadines
    WS = "WS"  # Samoa
    SM = "SM"  # San Marino
    ST = "ST"  # Sao Tome and Principe
    SA = "SA"  # Saudi Arabia
    SN = "SN"  # Senegal
    RS = "RS"  # Serbia
    SC = "SC"  # Seychelles
    SL = "SL"  # Sierra Leone
    SG = "SG"  # Singapore
    SK = "SK"  # Slovakia
    SI = "SI"  # Slovenia
    SB = "SB"  # Solomon Islands
    SO = "SO"  # Somalia
    ZA = "ZA"  # South Africa
    SS = "SS"  # South Sudan
    ES = "ES"  # Spain
    LK = "LK"  # Sri Lanka
    SD = "SD"  # Sudan
    SR = "SR"  # Suriname
    SE = "SE"  # Sweden
    CH = "CH"  # Switzerland
    SY = "SY"  # Syria
    TW = "TW"  # Taiwan
    TJ = "TJ"  # Tajikistan
    TZ = "TZ"  # Tanzania
    TH = "TH"  # Thailand
    TL = "TL"  # Timor-Leste
    TG = "TG"  # Togo
    TO = "TO"  # Tonga
    TT = "TT"  # Trinidad and Tobago
    TN = "TN"  # Tunisia
    TR = "TR"  # Turkey
    TM = "TM"  # Turkmenistan
    TV = "TV"  # Tuvalu
    UG = "UG"  # Uganda
    UA = "UA"  # Ukraine
    AE = "AE"  # United Arab Emirates
    GB = "GB"  # United Kingdom
    US = "US"  # United States
    UY = "UY"  # Uruguay
    UZ = "UZ"  # Uzbekistan
    VU = "VU"  # Vanuatu
    VA = "VA"  # Vatican City
    VE = "VE"  # Venezuela
    VN = "VN"  # Vietnam
    YE = "YE"  # Yemen
    ZM = "ZM"  # Zambia
    ZW = "ZW"  # Zimbabwe
    XK = "XK"  # Kosovo

class Person_API(BaseModel):
    """Person information model"""
    id_person: int = Field(default=0, ge=0, description="Person ID")
    person_details_id: Optional[int] = Field(default=None, description="Reference to person details")
    
    # PersonDetails
    id_person_details: int = Field(default=0, description="Person details ID")
    person_first_name: Optional[str] = Field(default=None, max_length=100, description="First name")
    person_last_name: Optional[str] = Field(default=None, max_length=100, description="Last name")
    person_birth_date: Optional[date] = Field(default=None, description="Birth date (YYYY-MM-DD)")
    person_gender: Optional[Gender] = Field(default=None, description="Gender")
    person_country_code: Optional[CountryCode] = Field(default=CountryCode.DZ, description="Nationality")
    
    # Blood type
    blood_type: BloodType = Field(default=BloodType.UNKNOWN, description="Blood type")
    
    @property
    def full_name(self) -> str:
        """Get full name"""
        parts = []
        if self.person_first_name:
            parts.append(self.person_first_name)
        if self.person_last_name:
            parts.append(self.person_last_name)
        return " ".join(parts) if parts else "Unknown"
    
    # --- FIXED VALIDATORS ---
    
    @field_validator('person_birth_date')
    @classmethod
    def validate_birth_date(cls, v: Optional[date]) -> Optional[date]:
        """Validate birth date is not in the future"""
        if v and v > date.today():
            raise ValueError('Birth date cannot be in the future')
        return v
    
    @field_validator('person_gender')
    @classmethod
    def validate_gender(cls, v: Optional[Gender]) -> Optional[Gender]:
        """Validate gender is valid"""
        if v is not None:
            # Get all valid gender values
            valid_genders = [g.value.lower() for g in Gender]
            if v not in valid_genders:
                raise ValueError(f'Invalid gender. Must be one of: {", ".join(valid_genders)}')
        return v
    
    @field_validator('blood_type')
    @classmethod
    def validate_blood_type(cls, v: BloodType) -> BloodType:
        """Validate blood type is valid"""
        if v is not None:
            # Get all valid blood type values
            valid_blood_types = [b.value for b in BloodType]
            if v not in valid_blood_types:
                raise ValueError(f'Invalid blood type. Must be one of: {", ".join(valid_blood_types)}')
        return v
    
    @field_validator('person_country_code')
    @classmethod
    def validate_country_code(cls, v: Optional[CountryCode]) -> Optional[CountryCode]:
        """Validate country code is valid"""
        if v is not None:
            valid_codes = [c.value for c in CountryCode]
            if v not in valid_codes:
                raise ValueError(f'Invalid country code. Must be a valid ISO 3166-1 alpha-2 code')
        return v
    
    class Config:
        use_enum_values = True
        json_encoders = {
            Gender: lambda v: v.value if v else None,
            BloodType: lambda v: v.value if v else None,
            CountryCode: lambda v: v.value if v else None
        }
    
    def to_db_dict(self) -> dict:
        """Convert to database dictionary"""
        data = self.model_dump()
        if 'person_gender' in data and data['person_gender']:
            data['person_gender'] = data['person_gender'].value
        if 'blood_type' in data and data['blood_type']:
            data['blood_type'] = data['blood_type'].value
        if 'person_country_code' in data and data['person_country_code']:
            data['person_country_code'] = data['person_country_code'].value
        return data

class Location_API(BaseModel):
    """Location and address model"""
    id_location: int = Field(default=0, ge=0, description="Location ID")
    location_latitude: Optional[float] = Field(default=None, ge=-90, le=90, description="Latitude")
    location_longitude: Optional[float] = Field(default=None, ge=-180, le=180, description="Longitude")
    location_name: Optional[str] = Field(default=None, max_length=200, description="Location name")
    location_address_id: Optional[int] = Field(default=None, description="Address reference")
    
    # Address
    id_address: int = Field(default=0, description="Address ID")
    address_street: Optional[str] = Field(default=None, max_length=255, description="Street address")
    address_city: Optional[str] = Field(default=None, max_length=100, description="City")
    address_postal_code: Optional[str] = Field(default=None, max_length=20, description="Postal code")
    address_country: Optional[str] = Field(default=None, max_length=100, description="Country")

# ============================================================================
# USER MODELS
# ============================================================================

class AppUserType(str, Enum):
    """Application user types"""
    PROVIDER = "provider"
    CUSTOMER = "customer"
    PATIENT = "patient"
    GUEST = "guest"
    
    @classmethod
    def get_default(cls) -> "AppUserType":
        return cls.GUEST
    
    @classmethod
    def from_db(cls, value: str) -> "AppUserType":
        """Convert database value (string) to enum"""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.GUEST
    
    def to_db(self) -> str:
        """Convert enum to database value"""
        return self.value

# ============ API MODELS ============

class AppUser_API(BaseModel):
    """Application user model"""
    id_app_user: int = Field(default=0, ge=0, description="User ID")
    app_user_name: Optional[str] = Field(default=None, min_length=3, max_length=50, description="Username")
    app_user_password: Optional[str] = Field(default=None, min_length=6, description="Password (hashed)")
    
    
    app_user_person_id: Optional[int] = Field(default=None, description="Person reference")
    app_user_preferences: Optional[str] = Field(default=None, description="User preferences (JSON)")
    app_user_email: Optional[str] = Field(default=None, max_length=100, description="Email address")
    app_user_image_url: Optional[str] = Field(default=None, max_length=500, description="Profile image URL")
    app_user_type: AppUserType = Field(
        default=AppUserType.GUEST,
        description="User type: provider, customer, patient, guest"
    )


class AppUserUpdate_API(AppUser_API):
    """User update model with password change"""
    username: str = Field(..., min_length=3, max_length=50, description="New username")
    new_password: Optional[str] = Field(default=None, min_length=6, description="New password (optional)")

class AuthData_API(BaseModel):
    """Authentication data model"""
    id_app_user: int = Field(default=0, description="User ID")
    app_user_name: Optional[str] = Field(default=None, description="Username")
    app_user_password: Optional[str] = Field(default=None, description="Password")

# ============================================================================
# PATIENT MODELS
# ============================================================================

class Patient_API(BaseModel):
    """Patient information model"""
    id_patient: int = Field(default=0, ge=0, description="Patient ID")
    patient_person_id: Optional[int] = Field(default=None, description="Person reference")
    patient_disease_severity_id: Optional[int] = Field(default=None, description="Disease severity ID")

class Serology_API(BaseModel):
    """Serology test results"""
    id_patient: int = Field(..., gt=0, description="Patient ID")
    serology_indicator_id: int = Field(..., gt=0, description="Indicator ID")
    serology_indicator_value: str = Field(..., max_length=50, description="Indicator value")
    serology_date: date = Field(..., description="Test date")

class Symptoms_API(BaseModel):
    """Patient symptoms model"""
    id_patient: int = Field(..., gt=0, description="Patient ID")
    symptom_ids: List[int] = Field(default_factory=list, description="List of symptom IDs")
    symptoms_occurence_reason: Optional[str] = Field(default=None, max_length=500, description="Reason for symptoms")
    reason_date: Optional[date] = Field(default=None, description="Date of symptoms")

# ============================================================================
# PRODUCT & IPRODUCT MODELS
# ============================================================================

class GlutenStatus(str, Enum):
    UNKNOWN = "unknown"
    GLUTEN_FREE = "gluten_free"
    CONTAINS_GLUTEN = "contains_gluten"
    MAY_CONTAIN_GLUTEN = "may_contain_gluten"


class NamingContributionType(str, Enum):
    """Mirror of the DB enum on `naming_contribution.naming_contribution_type`.
    Kept here so the API contract declares every allowed value explicitly."""
    PRODUCT = "product"
    PROVIDER = "provider"
    INGREDIENT = "ingredient"
    RECIPE = "recipe"
    SERVICE = "service"
    SYMPTOM = "symptom"
    ROLE = "role"


# ==================== Nested naming object ====================

class NamingContribution_API(BaseModel):
    """Trilingual name payload.

    Maps to a row in `naming_contribution`. Carried as a nested object
    on every entity that has translatable names (products, categories,
    providers, ingredients, ...).

    `en` is required: it is the canonical anchor that seeds use as the
    idempotency key. `ar` and `fr` are optional at the API level but
    the seeding convention is to fill them; missing translations fall
    back to `en` on the client.
    """
    id_naming_contribution: Optional[int] = Field(
        default=0, ge=0, description="Naming contribution ID",
    )
    en: str = Field(
        ..., min_length=1, max_length=255,
        description="English name — the canonical anchor",
    )
    ar: Optional[str] = Field(
        default=None, max_length=255, description="Arabic name",
    )
    fr: Optional[str] = Field(
        default=None, max_length=255, description="French name",
    )

    naming_contribution_status: Optional[str] = Field(
        default="PENDING",
        description=(
            "PENDING | ACCEPTED | APP_TRANSLATED | REJECTED. "
            "Seed data uses APP_TRANSLATED."
        ),
    )
    naming_contribution_icon_url: Optional[str] = Field(
        default=None, max_length=255,
        description="Optional icon URL attached to the contribution",
    )
    naming_contribution_type: Optional[NamingContributionType] = Field(
        default=None,
        description="Discriminator: product / provider / ingredient / ...",
    )

    class Config:
        use_enum_values = True
        populate_by_name = True
        from_attributes = True


# ==================== Iproduct API ====================

class Iproduct_API(BaseModel):
    """External / imported product.

    Two ways to supply the name:

    1. **Flat.** Set `iproduct_name` (English). The server creates or
       reuses a NamingContribution whose `en` is that string and whose
       `ar` / `fr` default to it.

    2. **Nested.** Set `naming` with all three languages. The server
       creates or reuses a NamingContribution from those values and
       copies `naming.en` into `iproduct_name` for backward
       compatibility with code that reads the flat column.

    When both are supplied, `naming.en` wins and `iproduct_name` is
    overwritten server-side. That keeps `iproduct_name` and
    `naming.en` from ever drifting.
    """

    # ---------- Identity ----------
    id_iproduct: Optional[int] = Field(
        default=0, ge=0, description="IProduct ID",
    )

    # ---------- Name (flat form) ----------
    iproduct_name: Optional[str] = Field(
        default="",
        max_length=200,
        description=(
            "English product name. Kept for backward compatibility. "
            "When `naming` is provided, this is set from `naming.en`."
        ),
    )

    # ---------- Name (trilingual form) ----------
    naming: Optional[NamingContribution_API] = Field(
        default=None,
        description=(
            "Trilingual name contribution. When provided, drives the "
            "NamingContribution row and sets `iproduct_name`."
        ),
    )

    # ---------- Barcode ----------
    iproduct_barcode: Optional[str] = Field(
        default="", max_length=100, description="Barcode",
    )

    # ---------- Brand ----------
    iproduct_brand: Optional[str] = Field(
        default="", max_length=100, description="Brand name",
    )

    # ---------- Pricing ----------
    iproduct_estimated_price: Optional[float] = Field(
        default=0.0, ge=0, description="Estimated price",
    )
    iproduct_price_currency: Optional[str] = Field(
        default="DZD", max_length=3, description="Currency code",
    )
    iproduct_last_price_update: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="Last price update",
    )

    # ---------- Classification ----------
    iproduct_gluten_status: Optional[GlutenStatus] = Field(
        default=GlutenStatus.UNKNOWN, description="Gluten status",
    )

    # ---------- Provenance ----------
    iproduct_info_source: Optional[str] = Field(
        default="openai", max_length=50,
        description="Information source",
    )
    iproduct_info_confidence: Optional[float] = Field(
        default=0.0, ge=0, le=1, description="Confidence score",
    )
    iproduct_model_name: Optional[str] = Field(
        default="None", max_length=100, description="AI model used",
    )

    # ---------- Media ----------
    iproduct_image_url: Optional[str] = Field(
        default="", max_length=500, description="Product image URL",
    )

    # ---------- Timestamps ----------
    iproduct_created_at: Optional[datetime] = Field(
        default_factory=datetime.now, description="Creation timestamp",
    )
    iproduct_last_update: Optional[datetime] = Field(
        default_factory=datetime.now, description="Last update timestamp",
    )

    # ==================== Validators ====================

    @field_validator("iproduct_barcode")
    @classmethod
    def _barcode_shape(cls, v: Optional[str]) -> Optional[str]:
        """Barcodes are digits-only when non-empty; empty normalises to
        the empty string to match the model's default."""
        if v is None or v == "":
            return ""
        if not v.isdigit():
            raise ValueError("iproduct_barcode must contain digits only")
        return v

    @field_validator("iproduct_price_currency")
    @classmethod
    def _currency_shape(cls, v: Optional[str]) -> str:
        """Upper-case three-letter currency code."""
        if not v:
            return "DZD"
        upper = v.strip().upper()
        if len(upper) != 3 or not upper.isalpha():
            raise ValueError(
                "iproduct_price_currency must be a 3-letter ISO code"
            )
        return upper

    @field_validator("naming")
    @classmethod
    def _naming_shape(
        cls, v: Optional[NamingContribution_API],
    ) -> Optional[NamingContribution_API]:
        """Reject a naming object whose `en` is missing or whitespace."""
        if v is None:
            return None
        if not v.en or not v.en.strip():
            raise ValueError("naming.en must not be blank")
        return v

    # ==================== Serialisation helpers ====================

    def resolved_naming(self) -> NamingContribution_API:
        """
        Return the naming object to persist, synthesising one from the
        flat `iproduct_name` when `naming` is absent.

        Guarantees the returned object has a non-empty `en`. Falls back
        to a placeholder when both inputs are empty, so the caller
        never has to handle a "no name at all" case downstream — the
        DB has a NOT NULL-ish expectation on the English column.
        """
        if self.naming is not None:
            return self.naming
        flat = (self.iproduct_name or "").strip() or "Unnamed product"
        return NamingContribution_API(
            en=flat,
            ar=None,
            fr=None,
            naming_contribution_type=NamingContributionType.PRODUCT,
        )

    class Config:
        use_enum_values = True
        populate_by_name = True
        from_attributes = True

class ProductVisibility(str, Enum):
    """Canonical visibility values. Must stay in sync with the
    `Product.product_visibility` string on the Dart side."""
    VISIBLE = "VISIBLE"
    HIDDEN = "HIDDEN"
    DELETED = "DELETED"


class Product_API(BaseModel):
    """Main product model.

    Field names mirror the JSON keys the Dart `Product.toJson()` emits
    under the top-level `"product"` object, and the keys
    `Product.fromJson` reads back from `getAllProducts` /
    `focusOnProduct` responses. Keep the two in sync.
    """

    # ==================== Identity ====================

    id_product: Optional[int] = Field(
        default=0, ge=0, description="Product ID",
    )
    product_provider_id: Optional[int] = Field(
        default=None, description="Provider ID",
    )
    product_category_id: Optional[int] = Field(
        default=None, description="Category ID",
    )

    # Alias kept for backwards compatibility. The Dart side sends both
    # `product_category_id` and `id_product_category` on writes and
    # tolerates either on reads.
    id_product_category: Optional[int] = Field(
        default=None, description="Category ID (legacy alias)",
    )

    id_product_image: Optional[int] = Field(
        default=None, description="Primary product image ID",
    )

    # Legacy reference; not the same as `product_origin_id`.
    product_ref_id: Optional[int] = Field(
        default=None, description="Legacy product reference ID",
    )

    product_owner: Optional[int] = Field(
        default=None, description="Owner user ID",
    )

    # ==================== Descriptive ====================

    product_name: Optional[str] = Field(
        default=None, max_length=200, description="Product name",
    )
    product_brand: Optional[str] = Field(
        default=None, max_length=100, description="Brand name",
    )
    product_barcode: Optional[str] = Field(
        default=None, max_length=100, description="Barcode",
    )
    product_quantifier: Optional[str] = Field(
        default="unit", max_length=50, description="Unit of measurement",
    )
    product_description: Optional[str] = Field(
        default=None, max_length=1000, description="Product description",
    )

    # Category display name. Read-only on the server side; the Dart
    # client sends it as `product_category_desc` inside `toJson()` for
    # historical reasons.
    product_category_desc: Optional[str] = Field(
        default=None, max_length=200,
        description="Category display name (echoed on read)",
    )

    # ==================== Pricing & stock ====================

    product_price: Optional[float] = Field(
        default=0.0, ge=0, description="Customer-facing price (VAT-inclusive)",
    )
    product_base_price: Optional[float] = Field(
        default=0.0, ge=0, description="Supplier-side cost",
    )
    product_quantity: Optional[float] = Field(
        default=0.0, ge=0, description="Available quantity",
    )
    product_reserved_quantity: Optional[float] = Field(
        default=0.0, ge=0,
        description="Quantity reserved by carts and pending orders",
    )

    # ==================== Status ====================

    product_visibility: Optional[ProductVisibility] = Field(
        default=ProductVisibility.VISIBLE,
        description='"VISIBLE" | "HIDDEN". Defaults to VISIBLE.',
    )

    # ==================== Timestamps ====================

    created: Optional[datetime] = Field(
        default=None, description="Creation timestamp",
    )
    last_updated: Optional[datetime] = Field(
        default=None, description="Last modification timestamp",
    )

    # ==================== Image (flattened convenience) ====================

    product_image_url: Optional[str] = Field(
        default=None, max_length=500,
        description="Primary image URL (denormalised for reads)",
    )

    # ==================== Validators ====================

    @field_validator("product_visibility", mode="before")
    @classmethod
    def _normalise_visibility(cls, v):
        """Accept the canonical values case-insensitively, plus None.
        Anything else is rejected so the DB never stores junk."""
        if v is None:
            return ProductVisibility.VISIBLE
        if isinstance(v, ProductVisibility):
            return v
        if isinstance(v, str):
            upper = v.upper().strip()
            if upper in ("VISIBLE", "HIDDEN","DELETED"):
                return ProductVisibility(upper)
        raise ValueError(
            f"product_visibility must be 'VISIBLE' or 'HIDDEN', got {v!r}"
        )

    # ==================== Serialisation helpers ====================

    class Config:
        # Emit enum values as their string form ("VISIBLE", not
        # "ProductVisibility.VISIBLE") so the Dart client's
        # `_asString(map['product_visibility'])` reads them cleanly.
        use_enum_values = True
        populate_by_name = True
        from_attributes = True


# ==================== Request wrapper ====================

class ProductWritePayload(BaseModel):
    """Shape the Dart client sends for create / update.

    Matches `Product.toJson()`:

        {
          "product": { ...Product_API fields... },
          "image":   { id_product_image, product_image_url, product_ref_id }
        }
    """
    product: Product_API
    image: Optional["ProductImagePayload"] = None


class ProductImagePayload(BaseModel):
    id_product_image: Optional[int] = Field(default=0, ge=0)
    product_image_url: Optional[str] = Field(default="", max_length=500)
    product_ref_id: Optional[int] = Field(default=0)


ProductWritePayload.model_rebuild()


# ==================== Read wrapper ====================

class ProductImageRead(BaseModel):
    """Shape of each entry in the `product_image` list on read. The Dart
    side reads `.last` and pulls `id_product_image` / `product_image_url`
    out of it."""
    id_product_image: Optional[int] = Field(default=0, ge=0)
    product_image_url: Optional[str] = Field(default="", max_length=500)
    product_ref_id: Optional[int] = Field(default=None)


class ProductRead(BaseModel):
    """Shape returned by `getAllProducts` / `focusOnProduct`.

    Superset of `Product_API` with the nested `product_category`,
    `product_provider`, and `product_image` objects the Dart
    `Product.fromJson` looks for.
    """
    # Everything from the write model…
    id_product: Optional[int] = 0
    product_provider_id: Optional[int] = None
    product_category_id: Optional[int] = None
    id_product_category: Optional[int] = None
    id_product_image: Optional[int] = None
    product_ref_id: Optional[int] = None
    product_owner: Optional[int] = None
    product_origin_id: Optional[int] = None

    product_name: Optional[str] = None
    product_brand: Optional[str] = None
    product_barcode: Optional[str] = None
    product_quantifier: Optional[str] = "unit"
    product_description: Optional[str] = None
    product_category_name: Optional[str] = None

    product_price: Optional[float] = 0.0
    product_base_price: Optional[float] = 0.0
    product_quantity: Optional[float] = 0.0
    product_reserved_quantity: Optional[float] = 0.0

    product_visibility: Optional[ProductVisibility] = ProductVisibility.VISIBLE

    created: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    product_image_url: Optional[str] = None

    # …plus the nested snapshots the Dart parser prefers when present.
    product_category: Optional[dict] = None
    product_provider: Optional[dict] = None
    product_image: Optional[list[ProductImageRead]] = None

    class Config:
        use_enum_values = True
        populate_by_name = True
        from_attributes = True

class ProductImage_API(BaseModel):
    """Product image model"""
    id_product_image: int = Field(default=0, ge=0, description="Product image ID")
    product_image_url: Optional[str] = Field(default=None, max_length=500, description="Image URL")
    product_ref_id: Optional[int] = Field(default=None, description="Product reference")

# ============================================================================
# SERVICE MODELS
# ============================================================================

class ProvidedService_API(BaseModel):
    """Service offered by provider"""
    provided_service_product_provider_id: int = Field(..., gt=0, description="Provider ID")
    provided_service_id: Optional[int] = Field(default=0, ge=0, description="Service ID")
    provided_service_name: Optional[str] = Field(default="", max_length=200, description="Service name")
    provided_service_description: Optional[str] = Field(default="", max_length=1000, description="Service description")
    provided_service_category_id: Optional[int] = Field(default=0, description="Service category ID")
    provided_service_base_price: Optional[float] = Field(default=0.0, ge=0, description="Base price")
    provided_service_final_price: Optional[float] = Field(default=0.0, ge=0, description="Final price")
    provided_service_actual_duration: Optional[float] = Field(default=0.0, ge=0, description="Duration in minutes")
    provided_service_is_active: Optional[bool] = Field(default=True, description="Is service active")
    provided_service_pricing_config: Optional[str] = Field(default="", description="Pricing configuration (JSON)")

class OrderedService_API(BaseModel):
    """Service ordered by customer"""
    ordered_service_service_id: Optional[int] = Field(default=0, description="Service ID")
    ordered_service_quantity: Optional[float] = Field(default=1.0, gt=0, description="Quantity")
    ordered_service_unit_price: Optional[float] = Field(default=0.0, ge=0, description="Unit price")
    ordered_service_total_price: Optional[float] = Field(default=0.0, ge=0, description="Total price")
    ordered_service_scheduled_at: Optional[datetime] = Field(default=None, description="Scheduled date/time")
    ordered_service_notes: Optional[str] = Field(default="", max_length=500, description="Order notes")
    resource_requirement_id: Optional[int] = Field(default=0, description="Resource requirement ID")

class ServiceResourceRequirement_API(BaseModel):
    """Resource requirements for a service"""
    resource_requirement_id: Optional[int] = Field(default=0, description="Requirement ID")
    resource_requirement_service_id: Optional[int] = Field(default=0, description="Service ID")
    resource_requirement_name: Optional[str] = Field(default="", max_length=200, description="Resource name")
    resource_requirement_type: Optional[str] = Field(default="", max_length=50, description="Resource type")
    resource_requirement_quantity: Optional[float] = Field(default=0.0, ge=0, description="Quantity needed")
    resource_requirement_cost_per_unit: Optional[float] = Field(default=0.0, ge=0, description="Cost per unit")
    resource_requirement_is_consumable: Optional[bool] = Field(default=True, description="Is consumable")
    resource_requirement_notes: Optional[str] = Field(default="", max_length=500, description="Notes")
    resource_requirement_product_ref: Optional[int] = Field(default=0, description="Product reference")

class ServiceStaffRequirement_API(BaseModel):
    """Staff requirements for a service"""
    service_staff_requirement_id: Optional[int] = Field(default=0, description="Requirement ID")
    service_staff_requirement_service_id: Optional[int] = Field(default=0, description="Service ID")
    service_staff_requirement_role: Optional[int] = Field(default=0, description="Staff role ID (foreign key to staff_role)")
    service_staff_requirement_notes: Optional[str] = Field(default="", max_length=500, description="Notes")
    service_staff_requirement_min_count: Optional[float] = Field(default=0.0, ge=0, description="Minimum staff count")
    service_staff_requirement_max_count: Optional[float] = Field(default=0.0, ge=0, description="Maximum staff count")
    service_staff_requirement_hourly_rate: Optional[float] = Field(default=0.0, ge=0, description="Hourly rate")
    service_staff_requirement_allocated_hours: Optional[float] = Field(default=0.0, ge=0, description="Allocated hours")
    
    @field_validator('service_staff_requirement_role')
    @classmethod
    def validate_role(cls, v: Optional[int]) -> Optional[int]:
        """Validate role ID is provided and positive"""
        if v is None or v <= 0:
            raise ValueError('Staff role ID must be a positive integer')
        return v


# ============================================================================
# DELIVERY MODELS
# ============================================================================

class DeliveryShippingMethod(str, Enum):
    """Delivery shipping methods"""
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"
    PICKUP = "pickup"
    COURIER = "courier"
    SAME_DAY = "same_day"
    INTERNATIONAL = "international"


class DeliveryStatus(str, Enum):
    """Delivery status values"""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"


class DeliverySourceType(str, Enum):
    """Delivery source types"""
    CART = "cart"
    PLACED_ORDER = "placed_order"


# ============================================================================
# DELIVERY API MODEL
# ============================================================================

class OrderedItem_API(BaseModel):
    """Ordered item model"""
    id_ordered_item: Optional[int] = Field(default=0, description="Ordered item ID")
    ordered_product_id: Optional[int] = Field(default=None, description="Product ID")
    order_ref: Optional[int] = Field(default=None, description="Order reference")
    
    product_discount: Optional[float] = Field(default=0.0, ge=0, le=100, description="Product discount percentage")
    ordered_quantity: Optional[int] = Field(default=1, gt=0, description="Quantity ordered")
    unit_price: Optional[float] = Field(default=0.0, ge=0, description="Unit price")
    applied_vat: Optional[float] = Field(default=0.0, ge=0, le=100, description="VAT percentage")
    
    @field_validator('ordered_quantity')
    @classmethod
    def validate_quantity(cls, v: Optional[int]) -> int:
        """Validate quantity is positive"""
        if v is None:
            return 1
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v
    
    @field_validator('product_discount', 'applied_vat')
    @classmethod
    def validate_percentage(cls, v: Optional[float]) -> Optional[float]:
        """Validate percentage values are between 0 and 100"""
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Value must be between 0 and 100')
        return v
    
    @model_validator(mode='after')
    def validate_total_price_consistency(self) -> 'OrderedItem_API':
        """Validate that unit_price * ordered_quantity makes sense with discount"""
        # This is a cross-field validation
        if self.ordered_quantity and self.unit_price:
            # You could add additional validation here if needed
            pass
        return self

class Delivery_API(BaseModel):
    """Delivery information model matching the database schema"""
    
    # Primary key
    id_delivery: Optional[int] = Field(default=0, ge=0, description="Delivery ID")
    
    # Recipient information
    recipient_person: Optional[int] = Field(default=None, description="Recipient person ID")
    recipient_provider: Optional[int] = Field(default=None, description="Recipient provider ID")
    
    # Cargo details
    delivery_package_count: Optional[int] = Field(default=0, description="Number of packages")
    delivery_total_weight: Optional[float] = Field(default=None, ge=0, description="Total weight (kg)")
    delivery_cargo_dimensions: Optional[str] = Field(default=None, max_length=255, description="Cargo dimensions (LxWxH)")
    delivery_goods_description: Optional[str] = Field(default=None, description="Goods description")
    hs_code: Optional[str] = Field(default=None, max_length=255, description="HS code")
    delivery_merchant_name: Optional[str] = Field(default=None, max_length=255, description="Merchant name")

    delivery_ordered_items: Optional[List[OrderedItem_API]] = Field(default=[], description="Ordered items to confirm reservations")
    
    # Shipping details
    delivery_shipping_method: DeliveryShippingMethod = Field(
        default=DeliveryShippingMethod.STANDARD,
        description="Shipping method"
    )
    delivery_special_instructions: Optional[str] = Field(
        default=None, 
        max_length=45,
        description="Special instructions for delivery"
    )
    
    # Status and tracking
    delivery_status: DeliveryStatus = Field(
        default=DeliveryStatus.PENDING,
        description="Current delivery status"
    )
    delivery_fee: Optional[float] = Field(default=0.0, ge=0, description="Delivery fee")
    
    # Address references
    delivery_address_id: Optional[int] = Field(default=None, description="Delivery address ID")
    delivery_current_address_id: Optional[int] = Field(default=None, description="Current tracking address ID")
    
    # Relationships
    delivery_provider_id: Optional[int] = Field(default=None, description="Provider ID")
    delivery_broker_id: Optional[int] = Field(default=None, description="Broker ID")
    delivery_invoice_ref: Optional[int] = Field(default=None, description="Invoice reference")
    
    # Source tracking
    delivery_source_type: Optional[DeliverySourceType] = Field(
        default=None,
        description="Source type (cart or placed_order)"
    )
    delivery_source_id: Optional[int] = Field(
        default=None,
        description="Source ID (cart_id or placed_order_id)"
    )
    
    # Timestamps (read-only, populated by database)
    delivery_created_at: Optional[datetime] = Field(
        default=None,
        description="Creation timestamp (auto-generated)"
    )
    delivery_updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp (auto-generated)"
    )
    
    # ==================== VALIDATORS ====================
    
    @field_validator('delivery_total_weight')
    @classmethod
    def validate_weight(cls, v: Optional[float]) -> Optional[float]:
        """Validate total weight is positive"""
        if v is not None and v < 0:
            raise ValueError('Total weight must be greater than or equal to 0')
        return v
    
    @field_validator('delivery_fee')
    @classmethod
    def validate_fee(cls, v: Optional[float]) -> Optional[float]:
        """Validate delivery fee is positive"""
        if v is not None and v < 0:
            raise ValueError('Delivery fee must be greater than or equal to 0')
        return v
    
    @field_validator('delivery_package_count')
    @classmethod
    def validate_package_count(cls, v: Optional[str]) -> Optional[str]:
        """Validate package count is a positive integer string"""
        if v is not None:
            if v <= 0:
                raise ValueError('Package count must be greater than 0')
        return v
    
    @field_validator('delivery_source_type')
    @classmethod
    def validate_source_type(cls, v: Optional[DeliverySourceType]) -> Optional[DeliverySourceType]:
        """Validate source type is valid"""
        if v is not None and v not in [DeliverySourceType.CART, DeliverySourceType.PLACED_ORDER]:
            raise ValueError('Source type must be either "cart" or "placed_order"')
        return v
    
    @field_validator('delivery_status')
    @classmethod
    def validate_status(cls, v: Optional[DeliveryStatus]) -> Optional[DeliveryStatus]:
        """Validate delivery status is valid"""
        valid_statuses = [s.value for s in DeliveryStatus]
        if v is not None and v.value not in valid_statuses:
            raise ValueError(f'Invalid delivery status. Must be one of: {", ".join(valid_statuses)}')
        return v
    
    @field_validator('delivery_shipping_method')
    @classmethod
    def validate_shipping_method(cls, v: Optional[DeliveryShippingMethod]) -> Optional[DeliveryShippingMethod]:
        """Validate shipping method is valid"""
        valid_methods = [m.value for m in DeliveryShippingMethod]
        if v is not None and v.value not in valid_methods:
            raise ValueError(f'Invalid shipping method. Must be one of: {", ".join(valid_methods)}')
        return v
    
    # ==================== HELPER METHODS ====================
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database dictionary, excluding None values and read-only fields"""
        data = self.model_dump(exclude_none=True)
        # Remove read-only fields that are auto-generated
        data.pop('delivery_created_at', None)
        data.pop('delivery_updated_at', None)
        # Convert enums to strings
        if 'delivery_status' in data and data['delivery_status']:
            data['delivery_status'] = data['delivery_status'].value
        if 'delivery_shipping_method' in data and data['delivery_shipping_method']:
            data['delivery_shipping_method'] = data['delivery_shipping_method'].value
        if 'delivery_source_type' in data and data['delivery_source_type']:
            data['delivery_source_type'] = data['delivery_source_type'].value
        return data
    
    @classmethod
    def from_db_model(cls, db_delivery) -> 'Delivery_API':
        """Create Delivery_API from database model"""
        return cls(
            id_delivery=db_delivery.id_delivery,
            recipient_person=db_delivery.recipient_person,
            recipient_provider=db_delivery.recipient_provider,
            delivery_package_count=db_delivery.delivery_package_count,
            delivery_total_weight=float(db_delivery.delivery_total_weight) if db_delivery.delivery_total_weight else None,
            delivery_cargo_dimensions=db_delivery.delivery_cargo_dimensions,
            delivery_goods_description=db_delivery.delivery_goods_description,
            hs_code=db_delivery.hs_code,
            delivery_merchant_name=db_delivery.delivery_merchant_name,
            delivery_shipping_method=db_delivery.delivery_shipping_method,
            delivery_special_instructions=db_delivery.delivery_special_instructions,
            delivery_status=db_delivery.delivery_status,
            delivery_fee=float(db_delivery.delivery_fee) if db_delivery.delivery_fee else 0.0,
            delivery_address_id=db_delivery.delivery_address_id,
            delivery_current_address_id=db_delivery.delivery_current_address_id,
            delivery_provider_id=db_delivery.delivery_provider_id,
            delivery_broker_id=db_delivery.delivery_broker_id,
            delivery_invoice_ref=db_delivery.delivery_invoice_ref,
            delivery_source_type=db_delivery.delivery_source_type,
            delivery_source_id=db_delivery.delivery_source_id,
            delivery_created_at=db_delivery.delivery_created_at,
            delivery_updated_at=db_delivery.delivery_updated_at
        )
        


# ============================================================================
# DELIVERY UPDATE MODEL (for partial updates)
# ============================================================================

class DeliveryUpdate_API(BaseModel):
    """Model for partial delivery updates"""
    
    recipient_person: Optional[int] = Field(default=None, description="Recipient person ID")
    recipient_provider: Optional[int] = Field(default=None, description="Recipient provider ID")
    delivery_package_count: Optional[int] = Field(default=1, ge=0)
    delivery_total_weight: Optional[float] = Field(default=None, ge=0)
    delivery_cargo_dimensions: Optional[str] = Field(default=None, max_length=255)
    delivery_goods_description: Optional[str] = Field(default=None)
    hs_code: Optional[str] = Field(default=None, max_length=255)
    delivery_merchant_name: Optional[str] = Field(default=None, max_length=255)
    delivery_shipping_method: Optional[DeliveryShippingMethod] = Field(default=None)
    delivery_special_instructions: Optional[str] = Field(default=None, max_length=45)
    delivery_status: Optional[DeliveryStatus] = Field(default=None)
    delivery_fee: Optional[float] = Field(default=None, ge=0)
    delivery_address_id: Optional[int] = Field(default=None)
    delivery_current_address_id: Optional[int] = Field(default=None)
    delivery_provider_id: Optional[int] = Field(default=None)
    delivery_broker_id: Optional[int] = Field(default=None)
    delivery_invoice_ref: Optional[int] = Field(default=None)
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database dictionary, excluding None values"""
        data = self.model_dump(exclude_none=True)
        # Convert enums to strings
        if 'delivery_status' in data and data['delivery_status']:
            data['delivery_status'] = data['delivery_status'].value
        if 'delivery_shipping_method' in data and data['delivery_shipping_method']:
            data['delivery_shipping_method'] = data['delivery_shipping_method'].value
        return data


class Delivery_Info_API(BaseModel):
    """Location and address model"""
    destination_address : Location_API = Field(..., description="Destination address")
    delivery_fee: Optional[float] = Field(default=0.0, description="Delivery fee")
    


# ============================================================================
# DELIVERY RESPONSE MODEL (with additional details)
# ============================================================================

class DeliveryResponse_API(Delivery_API):
    """Extended delivery response with related data"""
    
    provider_name: Optional[str] = Field(default=None, description="Provider name")
    broker_name: Optional[str] = Field(default=None, description="Broker name")
    invoice_number: Optional[str] = Field(default=None, description="Invoice number")
    address_details: Optional[Dict[str, Any]] = Field(default=None, description="Address details")
    current_address_details: Optional[Dict[str, Any]] = Field(default=None, description="Current address details")
    
    class Config:
        from_attributes = True

# ============================================================================
# CART & PAYMENT MODELS
# ============================================================================

class CartStatus(str, Enum):
    """Cart status enum matching database exactly"""
    OPEN = 'open'
    PENDING = 'pending'
    COMPLETED = 'completed'
    CANCELED = 'canceled'
    PARTIAL = 'partial'
    CHECKOUT = 'checkout'
    ABANDONED = 'abandoned'
    
    @classmethod
    def get_valid_statuses(cls) -> List[str]:
        """Get list of all valid status values"""
        return [status.value for status in cls]

class Cart_API(BaseModel):
    """Cart API model matching database structure"""
    cart_status: Optional[CartStatus] = Field(default=CartStatus.OPEN)
    cart_total_amount: Optional[float] = Field(None, ge=0)
    cart_notes: Optional[str] = Field(None, max_length=65535)  # TEXT field
    cart_due_date: Optional[date] = None
    cart_invoice: Optional[int] = Field(None, ge=1)

    # ── Payment intent fields ───────────────────────────────────────────
    # These four are read by CartService._detect_payment_intent() to decide
    # whether to create a payment inline during cart creation:
    #
    #   cart_deposit = true          → DEPOSIT intent (partial amount now)
    #   cart_payment = true          → FULL intent    (entire total now)
    #   cart_due_date set, no flags  → DUE_DATE intent (no payment now)
    #   none of the above            → NONE          (no payment now)
    #
    # cart_paid_money is how much to charge *right now*:
    #   - for FULL:   typically cart_total_amount
    #   - for DEPOSIT: the deposit amount
    cart_payment: Optional[bool] = Field(
        default=False,
        description="Client intent: charge the full amount now",
    )
    cart_deposit: Optional[bool] = Field(
        default=False,
        description="Client intent: charge a deposit now",
    )
    cart_paid_money: Optional[float] = Field(
        default=0.0,
        ge=0,
        description="Amount being charged right now (0 if nothing is paid now)",
    )
    cart_payment_method: Optional[str] = Field(
        default=None,
        max_length=32,
        description="cash | card | bank_transfer | mobile_money | wallet",
    )

    # ── Validators ──────────────────────────────────────────────────────

    @field_validator('cart_status')
    @classmethod
    def validate_cart_status(cls, v):
        """Validate cart status is valid"""
        if v is not None:
            valid_statuses = CartStatus.get_valid_statuses()
            if v not in valid_statuses:
                raise ValueError(f"cart_status must be one of: {', '.join(valid_statuses)}")
        return v

    @field_validator('cart_total_amount')
    @classmethod
    def validate_amount(cls, v):
        """Validate total amount is not negative"""
        if v is not None and v < 0:
            raise ValueError("cart_total_amount cannot be negative")
        return v

    # ── Cross-field validation ──────────────────────────────────────────

    @model_validator(mode="after")
    def validate_payment_intent(self):
        """
        Enforce the intent contract:
          - cart_payment and cart_deposit are mutually exclusive
          - if either intent flag is set, cart_paid_money must be > 0
            and cart_payment_method must be provided
          - if neither intent flag is set, cart_paid_money should be 0
        """
        wants_full = bool(self.cart_payment)
        wants_deposit = bool(self.cart_deposit)

        if wants_full and wants_deposit:
            raise ValueError(
                "cart_payment and cart_deposit are mutually exclusive"
            )

        if wants_full or wants_deposit:
            if not self.cart_paid_money or self.cart_paid_money <= 0:
                raise ValueError(
                    "cart_paid_money must be > 0 when cart_payment or "
                    "cart_deposit is set"
                )
            if not self.cart_payment_method:
                raise ValueError(
                    "cart_payment_method is required when cart_payment or "
                    "cart_deposit is set"
                )

        if not wants_full and not wants_deposit:
            # A due date can coexist with no payment (DUE_DATE intent) but
            # paid-money must be zero because nothing is being charged now.
            if self.cart_paid_money and self.cart_paid_money > 0:
                raise ValueError(
                    "cart_paid_money must be 0 when neither cart_payment "
                    "nor cart_deposit is set"
                )

        return self
    

class Payment_API(BaseModel):
    """Payment information"""
    payment_id: Optional[int] = Field(default=0, ge=0, description="Payment ID")
    payment_invoice_id: Optional[int] = Field(default=None, description="Invoice ID")
    payment_amount: Optional[float] = Field(default=0.0, ge=0, description="Payment amount")
    payment_method: Optional[str] = Field(default="cash", max_length=50, description="Payment method")
    payment_status: Optional[PaymentStatus] = Field(default=PaymentStatus.PENDING, description="Payment status")
    payment_reference: Optional[str] = Field(default="", max_length=100, description="Payment reference")
    payment_notes: Optional[str] = Field(default="", max_length=500, description="Payment notes")

class Deposit_API(BaseModel):
    """Deposit information"""
    deposit_id: Optional[int] = Field(default=0, ge=0, description="Deposit ID")
    deposit_amount: Optional[float] = Field(default=0.0, ge=0, description="Deposit amount")
    deposit_method: Optional[str] = Field(default="cash", max_length=50, description="Deposit method")
    deposit_cart_id: Optional[int] = Field(default=None, description="Cart ID")
    deposit_invoice_id: Optional[int] = Field(default=None, description="Invoice ID")
    deposit_reference: Optional[str] = Field(default="", max_length=100, description="Deposit reference")
    deposit_notes: Optional[str] = Field(default="", max_length=500, description="Deposit notes")
    deposit_receipt_id: Optional[int] = Field(default=None, description="Receipt ID")

class AdditionalFee_API(BaseModel):
    """Additional fees"""
    additional_fee_id: Optional[int] = Field(default=0, description="Fee ID")
    additional_fee_payment_id: Optional[int] = Field(default=None, description="Payment ID")
    additional_fee_name: Optional[str] = Field(default="", max_length=200, description="Fee name")
    additional_fee_amount: Optional[float] = Field(default=0.0, ge=0, description="Fee amount")
    additional_fee_description: Optional[str] = Field(default="", max_length=500, description="Fee description")
    additional_fee_document_url: Optional[str] = Field(default=None, max_length=500, description="Document URL")
    additional_fee_user_id: int = Field(..., gt=0, description="User ID")
    additional_fee_on_provider_id: int = Field(..., gt=0, description="Provider ID")

# ============================================================================
# PROVIDER MODELS
# ============================================================================

class ProductProvider_API(BaseModel):
    """Product provider (supplier) model.

    Two ways to supply the name:

    1. **Flat.** Set `provider_name` (English). The service creates or
       reuses a NamingContribution whose `en` is that string and whose
       `ar` / `fr` default to it.

    2. **Nested.** Set `naming` with all three languages. The service
       creates or reuses a NamingContribution from those values and
       links it via `provider_naming_ref`.

    When both are supplied, `naming.en` wins for the naming row, but
    the flat `provider_name` is still stored on the provider details
    row for backward compatibility with code that reads it directly.
    """
    id_product_provider: int = Field(default=0, ge=0, description="Provider ID")
    id_provider_owner: int = Field(default=0, ge=0, description="Owner ID")
    idprovider_details_id: int = Field(default=0, ge=0, description="Provider details ID")
    id_product_provider_type: int = Field(default=0, ge=0, description="Provider type ID")
    id_provider_organisation: int = Field(default=0, ge=0, description="Organization ID")

    # Provider type
    product_provider_type_desc: Optional[str] = Field(default="", max_length=200, description="Provider type description")
    provider_organisation_name: Optional[str] = Field(default="", max_length=200, description="Organization name")
    provider_organisation_desc: Optional[str] = Field(default="", max_length=500, description="Organization description")

    # Provider details
    provider_name: Optional[str] = Field(default="", max_length=200, description="Provider name")
    provider_contact_info: Optional[str] = Field(default="", max_length=500, description="Contact information (JSON)")

    # ---------- Name (trilingual form) ----------
    naming: Optional[NamingContribution_API] = Field(
        default=None,
        description=(
            "Trilingual name contribution. When provided, drives the "
            "NamingContribution row and sets the provider's "
            "`provider_naming_ref`."
        ),
    )

    # ==================== Validators ====================

    @field_validator("naming")
    @classmethod
    def _naming_shape(
        cls, v: Optional[NamingContribution_API],
    ) -> Optional[NamingContribution_API]:
        """Reject a naming object whose `en` is missing or whitespace."""
        if v is None:
            return None
        if not v.en or not v.en.strip():
            raise ValueError("naming.en must not be blank")
        return v

    # ==================== Serialisation helpers ====================

    def resolved_naming(self) -> NamingContribution_API:
        """
        Return the naming object to persist, synthesising one from the
        flat `provider_name` when `naming` is absent.

        Guarantees the returned object has a non-empty `en`. Falls back
        to a placeholder when both inputs are empty, so the caller
        never has to handle a "no name at all" case downstream — the
        DB has a NOT NULL-ish expectation on the English column.
        """
        if self.naming is not None:
            return self.naming
        flat = (self.provider_name or "").strip() or "Unnamed provider"
        return NamingContribution_API(
            en=flat,
            ar=None,
            fr=None,
            naming_contribution_type=NamingContributionType.PROVIDER,
        )

    class Config:
        use_enum_values = True
        populate_by_name = True
        from_attributes = True

class ProviderOrganisation_API(BaseModel):
    """Provider organization model.

    Same two-form name handling as `ProductProvider_API`: the flat
    `provider_organisation_name` is the fallback, the nested `naming`
    block is the preferred source when present.
    """
    id_provider_organisation: int = Field(default=0, ge=0, description="Organization ID")
    app_user_id: Optional[int] = Field(default=0, description="User ID")
    provider_organisation_name: Optional[str] = Field(default="", max_length=200, description="Organization name")
    provider_organisation_desc: Optional[str] = Field(default="", max_length=500, description="Organization description")

    # ---------- Name (trilingual form) ----------
    naming: Optional[NamingContribution_API] = Field(
        default=None,
        description=(
            "Trilingual name contribution. When provided, drives the "
            "NamingContribution row and sets the organisation's "
            "`provider_organisation_naming_ref`."
        ),
    )

    # ==================== Validators ====================

    @field_validator("naming")
    @classmethod
    def _naming_shape(
        cls, v: Optional[NamingContribution_API],
    ) -> Optional[NamingContribution_API]:
        """Reject a naming object whose `en` is missing or whitespace."""
        if v is None:
            return None
        if not v.en or not v.en.strip():
            raise ValueError("naming.en must not be blank")
        return v

    # ==================== Serialisation helpers ====================

    def resolved_naming(self) -> NamingContribution_API:
        """
        Return the naming object to persist, synthesising one from the
        flat `provider_organisation_name` when `naming` is absent.
        """
        if self.naming is not None:
            return self.naming
        flat = (
            self.provider_organisation_name or ""
        ).strip() or "Unnamed organisation"
        return NamingContribution_API(
            en=flat,
            ar=None,
            fr=None,
            naming_contribution_type=NamingContributionType.PROVIDER,
        )

    class Config:
        use_enum_values = True
        populate_by_name = True
        from_attributes = True

class OrganisationImage_API(BaseModel):
    """Organization image model"""
    id_org_image: int = Field(default=0, ge=0, description="Organization image ID")
    org_image_url: Optional[str] = Field(default=None, max_length=500, description="Image URL")
    org_ref_id: Optional[int] = Field(default=None, description="Organization reference")

class ProviderImage_API(BaseModel):
    """Provider image model"""
    id_provider_image: int = Field(default=0, ge=0, description="Provider image ID")
    provider_image_url: Optional[str] = Field(default=None, max_length=500, description="Image URL")
    provider_ref_id: Optional[int] = Field(default=None, description="Provider reference")

# ============================================================================
# RULES & NOTIFICATIONS
# ============================================================================

class ManagementRule_API(BaseModel):
    """Management rule model"""
    id_management_rule: Optional[int] = Field(default=0, description="Rule ID")
    rule_ref_org: Optional[int] = Field(default=None, description="Organization reference")
    rule_ref_provider: Optional[int] = Field(default=None, description="Provider reference")
    rule_ref_user: Optional[int] = Field(default=None, description="User reference")
    management_rule_code: Optional[int] = Field(default=None, description="Rule code")
    management_rule_status: Optional[str] = Field(default=None, max_length=50, description="Rule status")
    management_rule_expiry: Optional[datetime] = Field(default=None, description="Expiry date")

class Notification_API(BaseModel):
    """Notification model"""
    id_notification: Optional[int] = Field(default=0, description="Notification ID")
    notification_code: Optional[str] = Field(default=None, max_length=100, description="Notification code")
    notification_params: Optional[str] = Field(default=None, description="Parameters (JSON)")
    notification_user_ref: Optional[int] = Field(default=None, description="User reference")
    notification_created_at: Optional[datetime] = Field(default_factory=datetime.now, description="Creation timestamp")
    notification_read_at: Optional[datetime] = Field(default=None, description="Read timestamp")

# ============================================================================
# REACTION MODELS
# ============================================================================

# ============================================================================
# REACTION ENUMS
# ============================================================================

class ReactionType(str, Enum):
    """Types of reactions available in the system"""
    PRODUCT = "product"
    RECIPE = "recipe"
    PROVIDER = "provider"    
    COMMENT = "comment"

class ReactionValue(str, Enum):
    """Possible reaction values"""
    LIKE = "like"
    DISLIKE = "dislike"
    LOVE = "love"
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    STAR = "star"

class ProviderReactionValue(str, Enum):
    """Provider reaction values (rating)"""
    ONE_STAR = "1"
    TWO_STARS = "2"
    THREE_STARS = "3"
    FOUR_STARS = "4"
    FIVE_STARS = "5"

class ReactionBase(BaseModel):
    """Base reaction model for API requests"""
    user_id: int = Field(..., gt=0, description="User ID")
    reaction_type: ReactionType = Field(..., description="Type of reaction (product, recipe, provider, comment)")
    target_id: int = Field(..., gt=0, description="Target ID (product/recipe/provider/comment ID)")
    reaction_value: Optional[ReactionValue] = Field(default=None, description="Reaction value (like, dislike, love, etc.)")
    rating_value: Optional[float] = Field(default=None, ge=0, le=5, description="Rating value (1-5) for provider reactions")
    
    @field_validator('rating_value')
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        """Validate rating is between 1 and 5"""
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Rating must be between 1 and 5')
        return v

class CommentReaction_API(BaseModel):
    """Comment reaction model"""
    id_comment_reaction: Optional[int] = Field(default=0, description="Comment reaction ID")
    comment_reacting_user: int = Field(..., gt=0, description="User ID")
    reacted_on_comment: int = Field(..., gt=0, description="Comment ID")
    comment_reaction: ReactionValue = Field(default=ReactionValue.LIKE, description="Reaction value")

class Config:
    from_attributes = True

class CommentReactionResponse(CommentReaction_API):
    """Comment reaction response with user and comment details"""
    user_name: Optional[str] = Field(default=None, description="Username")
    user_image: Optional[str] = Field(default=None, description="User profile image")
    comment_content: Optional[str] = Field(default=None, description="Comment content")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

# ============================================================================
# REACTION STATISTICS
# ============================================================================

class ReactionStatistics(BaseModel):
    """Reaction statistics for a target"""
    target_id: int = Field(..., description="Target ID")
    target_type: ReactionType = Field(..., description="Target type")
    total_reactions: int = Field(default=0, description="Total number of reactions")
    like_count: int = Field(default=0, description="Number of likes")
    dislike_count: int = Field(default=0, description="Number of dislikes")
    love_count: int = Field(default=0, description="Number of loves")
    helpful_count: int = Field(default=0, description="Number of helpful ratings")
    average_rating: Optional[float] = Field(default=None, description="Average rating (for providers)")
    total_ratings: int = Field(default=0, description="Total number of ratings (for providers)")
    
    class Config:
        from_attributes = True

# ============================================================================
# API REQUEST/RESPONSE WRAPPERS
# ============================================================================

class ReactionRequest(BaseModel):
    """Request model for adding/updating a reaction"""
    reaction: ReactionBase = Field(..., description="Reaction details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reaction": {
                    "user_id": 123,
                    "reaction_type": "product",
                    "target_id": 456,
                    "reaction_value": "like",
                    "rating_value": 4.5
                }
            }
        }

class ReactionBulkRequest(BaseModel):
    """Request model for bulk reactions"""
    reactions: List[ReactionBase] = Field(..., description="List of reactions")
    
    @field_validator('reactions')
    @classmethod
    def validate_reactions(cls, v: List[ReactionBase]) -> List[ReactionBase]:
        """Validate at least one reaction is provided"""
        if not v:
            raise ValueError('At least one reaction is required')
        if len(v) > 100:
            raise ValueError('Maximum 100 reactions per request')
        return v

class ReactionBulkResponse(BaseModel):
    """Response model for bulk reactions"""
    success: bool = Field(..., description="Indicates if all reactions were processed")
    processed_count: int = Field(..., description="Number of reactions processed")
    failed_count: int = Field(..., description="Number of reactions that failed")
    errors: Optional[List[Dict[str, Any]]] = Field(default=None, description="Error details for failed reactions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "processed_count": 5,
                "failed_count": 0,
                "errors": None
            }
        }


class Reaction_API(BaseModel):
    """Reaction model"""
    id_reaction: Optional[int] = Field(default=0, description="Reaction ID")
    
    recipe_reaction_ref: Optional[int] = Field(default=0, description="Recipe reaction reference")
    product_reaction_ref: Optional[int] = Field(default=0, description="Product reaction reference")
    comment_reaction_ref: Optional[int] = Field(default=0, description="Comment reaction reference")
    
    id_product_reaction: Optional[int] = Field(default=0, description="Product reaction ID")
    id_recipe_reaction: Optional[int] = Field(default=0, description="Recipe reaction ID")
    id_comment_reaction: Optional[int] = Field(default=0, description="Comment reaction ID")
    
    reacted_on_product: Optional[int] = Field(default=0, description="Reacted product ID")
    reacted_on_provider: Optional[int] = Field(default=0, description="Reacted provider ID")
    reacted_on_recipe: Optional[int] = Field(default=0, description="Reacted recipe ID")
    reacted_on_comment: Optional[int] = Field(default=0, description="Reacted comment ID")
    
    recipe_reacting_user: Optional[int] = Field(default=0, description="Recipe reacting user ID")
    product_reacting_user: Optional[int] = Field(default=0, description="Product reacting user ID")
    comment_reacting_user: Optional[int] = Field(default=0, description="Comment reacting user ID")
    
    provider_reaction_value: Optional[float] = Field(default=0.0, description="Provider rating value")
    product_reaction_value: Optional[float] = Field(default=0.0, description="Product rating value")

# ============================================================================
# RECIPE MODELS
# ============================================================================

class Ingredient_API(BaseModel):
    """Ingredient model"""
    id_ingredient: int = Field(default=0, ge=0, description="Ingredient ID")
    ingredient_name: Optional[str] = Field(default=None, max_length=200, description="Ingredient name")
    ingredient_icon_url: Optional[str] = Field(default=None, max_length=500, description="Icon URL")
    ingredient_quantifier: Optional[str] = Field(default="unit", max_length=50, description="Unit of measurement")

class Recipe_API(BaseModel):
    """Recipe model"""
    id_recipe: int = Field(default=0, ge=0, description="Recipe ID")
    recipe_category_id: int = Field(..., gt=0, description="Recipe category ID")
    recipe_name: str = Field(..., max_length=200, description="Recipe name")
    recipe_owner_id: Optional[int] = Field(default=None, description="Owner user ID")
    recipe_preparation_time: Optional[str] = Field(default=None, max_length=50, description="Preparation time (ISO duration)")
    recipe_instructions: Optional[str] = Field(default=None, max_length=5000, description="Instructions")
    recipe_description: Optional[str] = Field(default=None, max_length=1000, description="Description")
    recipe_ingredients: Optional[Dict[int, str]] = Field(default_factory=dict, description="Ingredients mapping (ID -> quantity)")

class RecipeContainsIngredient_API(BaseModel):
    """Recipe-Ingredient association model"""
    idrecipe_contains_ingredient_id: int = Field(default=0, description="Association ID")
    containing_recipe_id: Optional[int] = Field(default=None, description="Recipe ID")
    contained_ingredient_id: Optional[int] = Field(default=None, description="Ingredient ID")
    contained_quantity: Optional[str] = Field(default=None, max_length=50, description="Quantity")

class RecipeImage_API(BaseModel):
    """Recipe image model"""
    id_recipe_image: int = Field(default=0, description="Recipe image ID")
    recipe_image_url: Optional[str] = Field(default=None, max_length=500, description="Image URL")
    recipe_ref_id: Optional[int] = Field(default=None, description="Recipe reference")

# ============================================================================
# ORDER MODELS
# ============================================================================

class PlacedOrder_API(BaseModel):
    """Placed order model"""
    id_placed_order: Optional[int] = Field(default=0, description="Order ID")
    ordered_timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Order timestamp")
    order_discount: Optional[float] = Field(default=0.0, ge=0, description="Order discount")
    placed_order_last_mod: Optional[datetime] = Field(default_factory=datetime.now, description="Last modification")
    payment_status: Optional[PaymentStatus] = Field(default=PaymentStatus.PENDING, description="Payment status")
    payment_ref: Optional[str] = Field(default="", max_length=100, description="Payment reference")
    placed_order_state: Optional[OrderStatus] = Field(default=OrderStatus.PENDING, description="Order status")
    payment_method: Optional[str] = Field(default="cash", max_length=50, description="Payment method")
    ordering_user_id: Optional[int] = Field(default=None, description="Ordering user ID")




class InvoiceStatus(str, Enum):
    """Invoice status enum matching database"""
    UNPAID = "unpaid"
    PAID = "paid"
    CANCELED = "canceled"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    REFUNDED = "refunded"
    
    @classmethod
    def get_valid_statuses(cls) -> List[str]:
        """Get list of all valid status values"""
        return [status.value for status in cls]

class InvoiceType(str, Enum):
    """Invoice type enum matching database"""
    RECEIPT = "receipt"
    INVOICE = "invoice"
    PROFORMA = "proforma"
    
    @classmethod
    def get_valid_types(cls) -> List[str]:
        """Get list of all valid type values"""
        return [type_.value for type_ in cls]

class Invoice_API(BaseModel):
    """Invoice API model"""
    invoice_id: Optional[int] = Field(default=0, ge=0, description="Invoice ID")
    invoice_number: Optional[str] = Field(default="", max_length=100, description="Invoice number")
    invoice_total_amount: Optional[float] = Field(default=0.0, ge=0, description="Total amount")
    invoice_status: InvoiceStatus = Field(default=InvoiceStatus.UNPAID, description="Invoice status")
    invoice_type: InvoiceType = Field(default=InvoiceType.INVOICE, description="Invoice type")
    invoice_issue_date: Optional[date] = Field(default_factory=date.today, description="Issue date")
    invoice_due_date: Optional[date] = Field(default=None, description="Due date")
    invoice_notes: Optional[str] = Field(default="", max_length=65535, description="Notes")
    invoice_tax_applied: Optional[bool] = Field(default=False, description="Tax applied")
    
    # Relationships
    invoice_cart_id: Optional[int] = Field(default=None, description="Cart ID")
    invoice_order_id: Optional[int] = Field(default=None, description="Order ID")
    
    @field_validator('invoice_total_amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Validate total amount is not negative"""
        if v < 0:
            raise ValueError('Invoice total amount cannot be negative')
        return v
    
    @model_validator(mode='after')
    def validate_dates(self) -> 'Invoice_API':
        """Validate due date is after issue date"""
        if self.invoice_due_date and self.invoice_issue_date:
            if self.invoice_due_date < self.invoice_issue_date:
                raise ValueError('Due date must be after issue date')
        return self

class InvoiceUpdate_API(BaseModel):
    """Invoice update model - all fields optional"""
    invoice_number: Optional[str] = Field(default=None, max_length=100, description="Invoice number")
    invoice_total_amount: Optional[float] = Field(default=None, ge=0, description="Total amount")
    invoice_status: Optional[InvoiceStatus] = Field(default=None, description="Invoice status")
    invoice_type: Optional[InvoiceType] = Field(default=None, description="Invoice type")
    invoice_issue_date: Optional[date] = Field(default=None, description="Issue date")
    invoice_due_date: Optional[date] = Field(default=None, description="Due date")
    invoice_notes: Optional[str] = Field(default=None, max_length=65535, description="Notes")
    invoice_tax_applied: Optional[bool] = Field(default=None, description="Tax applied")
    invoice_cart_id: Optional[int] = Field(default=None, description="Cart ID")
    invoice_order_id: Optional[int] = Field(default=None, description="Order ID")

class InvoiceResponse_API(Invoice_API):
    """Invoice response with related data"""
    # Related data
    cart: Optional[Cart_API] = Field(default=None, description="Cart details")
    order: Optional[PlacedOrder_API] = Field(default=None, description="Order details")
    payments: Optional[List[Payment_API]] = Field(default=None, description="Payments")
    deliveries: Optional[List[Delivery_API]] = Field(default=None, description="Deliveries")
    additional_fees: Optional[List[AdditionalFee_API]] = Field(default=None, description="Additional fees")
    
    # Computed fields
    total_paid: Optional[float] = Field(default=0.0, description="Total amount paid")
    remaining_balance: Optional[float] = Field(default=0.0, description="Remaining balance")
    is_overdue: Optional[bool] = Field(default=False, description="Is invoice overdue")
    
    class Config:
        from_attributes = True

class InvoiceFilterParams(BaseModel):
    """Invoice filter parameters"""
    invoice_status: Optional[InvoiceStatus] = Field(default=None, description="Filter by status")
    invoice_type: Optional[InvoiceType] = Field(default=None, description="Filter by type")
    date_from: Optional[date] = Field(default=None, description="Filter from date")
    date_to: Optional[date] = Field(default=None, description="Filter to date")
    cart_id: Optional[int] = Field(default=None, description="Filter by cart ID")
    provider_id: Optional[int] = Field(default=None, description="Filter by provider ID")
    order_id: Optional[int] = Field(default=None, description="Filter by order ID")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    limit: int = Field(default=100, ge=1, le=1000, description="Limit")