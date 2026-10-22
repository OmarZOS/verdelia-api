import os


"""
Application constants - DO NOT CHANGE unless necessary
These values are optimized for professional A4 documents
"""

# Application Metadata
APP_NAME = "ProInvoice Suite"
APP_VERSION = "2.1.0"
APP_RELEASE_DATE = "2024-01-15"

# Document Layout Constants
PAGE_SIZE = "A4"                    # Standard business paper size
PAGE_ORIENTATION = "portrait"       # Portrait for invoices/receipts
DEFAULT_MARGIN_MM = 15              # 15mm margin (standard for A4)
MAX_ITEMS_PER_PAGE = 10             # Optimal: 8-12 items per page (10 is safe)
MAX_PAGES = 10                      # Maximum pages per document

# Currency Settings (ISO Standards)
CURRENCY = "USD"                    # ISO 4217 currency code
CURRENCY_SYMBOL = "$"               # Currency symbol
DECIMAL_PLACES = 2                  # Standard decimal places

# QR Code Configuration
QR_VERSION = 7                      # QR version 7 (supports up to 456 chars)
QR_ERROR_CORRECTION = 'H'           # High error correction (30%)
QR_BOX_SIZE = 6                     # Pixel size per module
QR_BORDER = 2                       # Quiet zone border
QR_FILL_COLOR = "#000000"           # Black
QR_BACK_COLOR = "#FFFFFF"           # White

# Document Security
SIGNATURE_ALGORITHM = "SHA-256"
ENCRYPTION_KEY_LENGTH = 32
DOCUMENT_EXPIRY_DAYS = 365          # Documents valid for 1 year

# Validation Rules
MIN_AMOUNT = 0.01                   # Minimum transaction amount
MAX_AMOUNT = 9999999.99             # Maximum amount (9,999,999.99)
VALID_TAX_RATES = [0, 5, 8, 10, 15, 18, 20]  # Common global tax rates
VALID_CURRENCIES = [
    "USD", "EUR", "GBP", "JPY",     # Major currencies
    "CAD", "AUD", "CHF", "CNY",     # Secondary currencies
    "INR", "BRL", "MXN"             # Emerging market currencies
]

# Company Defaults (Update with your company info)
COMPANY_INFO = {
    "name": "Your Company Name",
    "address": "123 Business Street\nCity, State ZIP\nCountry",
    "phone": "+1 (555) 123-4567",
    "email": "invoices@yourcompany.com",
    "website": "www.yourcompany.com",
    "tax_id": "TAX-ID-123456789",
    "registration_number": "REG-7890123",
    "bank_details": {
        "bank_name": "Global Bank",
        "account_number": "**** **** **** 1234",
        "routing_number": "123456789",
        "swift_code": "GBANKUS33",
        "iban": "GB33BUKB20201555555555"  # For international
    }
}

# Invoice/Receipt Settings
TAX_RATE_DEFAULT = 10.0              # Default tax rate percentage
PAYMENT_TERMS = "Net 30"             # Standard payment terms
LATE_FEE_PERCENTAGE = 1.5           # Monthly late fee (industry standard)
EARLY_PAYMENT_DISCOUNT = 2.0        # Early payment discount percentage

# Document Numbering Patterns
invoice_reference_PATTERN = "INV-{year}{month}{day}-{seq:03d}"
RECEIPT_NUMBER_PATTERN = "RCPT-{year}{month}{day}-{seq:03d}"
QUOTE_NUMBER_PATTERN = "QTE-{year}{month}{day}-{seq:03d}"

# Date Formats
DATE_FORMAT = "%Y-%m-%d"             # ISO 8601 format
DISPLAY_DATE_FORMAT = "%d %b %Y"     # Display format: 15 Jan 2024
TIME_FORMAT = "%H:%M:%S"

# PDF Compression Settings
PDF_COMPRESSION_LEVEL = 6           # 0-9 (higher = more compression)
IMAGE_COMPRESSION_QUALITY = 85      # 0-100 (higher = better quality)

# Performance Settings
CACHE_ENABLED = True
CACHE_EXPIRY_HOURS = 24
MAX_CONCURRENT_GENERATIONS = 5
ENABLE_WATERMARK = False
ENABLE_ENCRYPTION = (False,{})


BASE_URL = os.getenv("BASE_URL", "http://localhost:9000/api")
