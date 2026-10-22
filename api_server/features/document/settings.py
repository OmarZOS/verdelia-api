"""
Application settings - CAN BE CHANGED based on your preferences
These values control the appearance and behavior
"""

import os
from datetime import datetime
from pathlib import Path

# ============ PATHS & DIRECTORIES ============
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"
ARCHIVE_DIR = BASE_DIR / "archive"

# Create directories
for directory in [OUTPUT_DIR, LOG_DIR, ARCHIVE_DIR]:
    directory.mkdir(exist_ok=True)

# Output paths
INVOICE_OUTPUT_DIR = OUTPUT_DIR / "invoices"           # /output/invoices/
RECEIPT_OUTPUT_DIR = OUTPUT_DIR / "receipts"           # /output/receipts/
QUOTE_OUTPUT_DIR = OUTPUT_DIR / "quotes"               # /output/quotes/
QR_CACHE_DIR = OUTPUT_DIR / ".qr_cache"                # /output/.qr_cache/

# Create output directories
for directory in [INVOICE_OUTPUT_DIR, RECEIPT_OUTPUT_DIR, QUOTE_OUTPUT_DIR, QR_CACHE_DIR]:
    directory.mkdir(exist_ok=True)

# ============ PAGE LAYOUT SETTINGS ============
HEADER_HEIGHT_MM = 35                # Height of header section (35mm optimal)
FOOTER_HEIGHT_MM = 25                # Height of footer section (25mm optimal)
DEFAULT_MARGIN_MM = 15               # Page margins (15mm standard)
CONTENT_HEIGHT_MM = 210              # For A4 portrait (297mm total)

# ============ QR CODE SETTINGS ============
QR_ADD_TO_EVERY_PAGE = True         # Add QR to every page in multi-page docs
QR_INCLUDE_VERSION = True           # Include app version in QR data
QR_INCLUDE_TIMESTAMP = True         # Include generation timestamp
QR_INCLUDE_CHECKSUM = True          # Include document checksum
QR_STYLE = "professional"           # Options: professional, minimal, corporate, colorful
QR_SIZE = 120                       # QR code size in pixels
QR_INCLUDE_LOGO = True              # Embed company logo in QR center

# ============ DOCUMENT SETTINGS ============
ENABLE_QR = True                    # Enable QR code generation
ENABLE_WATERMARK = False            # Add watermark to documents
ENABLE_ENCRYPTION = False           # Encrypt PDF files (requires cryptography)
ENABLE_DIGITAL_SIGNATURE = False    # Add digital signature (requires certificates)
WATERMARK_TEXT = "CONFIDENTIAL"     # Watermark text
WATERMARK_OPACITY = 0.1             # Watermark opacity (0.0-1.0)

# ============ FONT SETTINGS ============
DEFAULT_FONT = "Inter"              # Primary font
FALLBACK_FONT = "Helvetica"         # Fallback font
MONOSPACE_FONT = "Roboto Mono"      # For numbers and codes
FONT_SIZE_BODY = 10                 # Base font size in points
FONT_SIZE_SMALL = 8                 # Small text
FONT_SIZE_LARGE = 12                # Large text
FONT_SIZE_TITLE = 16                # Title size

# ============ COLOR SCHEME ============
COMPANY_PRIMARY_COLOR = "#2C3E50"   # Dark blue-gray (professional)
COMPANY_SECONDARY_COLOR = "#3498DB" # Bright blue (accent)
COMPANY_ACCENT_COLOR = "#E74C3C"    # Red (for warnings/important)
COMPANY_SUCCESS_COLOR = "#27AE60"   # Green (for paid/success)
COMPANY_WARNING_COLOR = "#F39C12"   # Orange (for pending)
COMPANY_DANGER_COLOR = "#E74C3C"    # Red (for overdue)

# ============ LOGGING SETTINGS ============
LOG_FILE = LOG_DIR / f"invoices_{datetime.now().strftime('%Y%m')}.log"
LOG_LEVEL = "INFO"                  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_SIZE = 10485760             # 10MB max log file size
LOG_BACKUP_COUNT = 5                # Keep 5 backup logs

# ============ COMPANY BRANDING ============
COMPANY_LOGO_PATH = STATIC_DIR / "images" / "logo.png"
COMPANY_FAVICON_PATH = STATIC_DIR / "images" / "favicon.png"
COMPANY_STAMP_PATH = STATIC_DIR / "images" / "stamp.png"

# ============ EMAIL SETTINGS ============
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USE_TLS = True
EMAIL_FROM = "noreply@yourcompany.com"
EMAIL_SUBJECT_INVOICE = "Invoice {invoice_reference} from {company_name}"
EMAIL_SUBJECT_RECEIPT = "Payment Receipt {receipt_number}"
EMAIL_BODY_TEMPLATE = "email_template.html"

# ============ DATABASE SETTINGS ============
DATABASE_URI = "sqlite:///invoices.db"  # For production: "postgresql://user:pass@localhost/dbname"
DATABASE_POOL_SIZE = 5
DATABASE_MAX_OVERFLOW = 10

# ============ API SETTINGS ============
API_HOST = "0.0.0.0"
API_PORT = 8000
API_DEBUG = False
API_SECRET_KEY = "your-secret-key-here-change-in-production"
API_CORS_ORIGINS = ["http://localhost:3000", "https://yourdomain.com"]

# ============ PERFORMANCE SETTINGS ============
ENABLE_CACHING = True
CACHE_EXPIRY_SECONDS = 3600         # 1 hour
MAX_CACHE_SIZE = 100                # Max cached documents
WORKER_THREADS = 4                  # Number of worker threads

# ============ VALIDATION SETTINGS ============
VALIDATE_ON_GENERATE = True
ALLOW_CUSTOM_TAX_RATES = False
REQUIRE_CLIENT_EMAIL = True
ALLOW_PARTIAL_PAYMENTS = True

# ============ EXPORT SETTINGS ============
EXPORT_FORMATS = ["PDF", "HTML", "JSON"]
DEFAULT_EXPORT_FORMAT = "PDF"
COMPRESS_EXPORTS = True
EXPORT_ENCODING = "utf-8"

# ============ ARCHIVAL SETTINGS ============
AUTO_ARCHIVE_DAYS = 90              # Archive documents older than 90 days
KEEP_ARCHIVED_DAYS = 365            # Keep archived documents for 1 year
COMPRESS_ARCHIVES = True            # Compress archived files
ARCHIVE_FORMAT = "zip"              # Archive format

# ============ BACKUP SETTINGS ============
AUTO_BACKUP = True
BACKUP_FREQUENCY = "daily"          # daily, weekly, monthly
BACKUP_RETENTION_DAYS = 30
BACKUP_DIR = BASE_DIR / "backups"

# ============ SECURITY SETTINGS ============
REQUIRE_AUTHENTICATION = False
SESSION_TIMEOUT_MINUTES = 30
PASSWORD_MIN_LENGTH = 8
ALLOWED_FILE_TYPES = [".pdf", ".png", ".jpg", ".jpeg"]
MAX_FILE_SIZE_MB = 10

# ============ DEBUG SETTINGS ============
DEBUG_MODE = False                  # Set to True for development
SHOW_PAGE_BORDERS = False           # Show page borders for debugging
LOG_PDF_GENERATION_TIME = True      # Log time taken for PDF generation
VALIDATE_TEMPLATES_ON_LOAD = True   # Validate templates on application start

# ============ INTEGRATION SETTINGS ============
ENABLE_STRIPE = False               # Enable Stripe payment integration
ENABLE_PAYPAL = False               # Enable PayPal integration
ENABLE_QUICKBOOKS = False           # Enable QuickBooks integration
ENABLE_XERO = False                 # Enable Xero integration

# ============ LOCALIZATION SETTINGS ============
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "es", "fr", "de", "zh"]
TIMEZONE = "UTC"
DATE_LOCALE = "en_US.UTF-8"

# ============ MONITORING SETTINGS ============
ENABLE_METRICS = True
METRICS_PORT = 9090
HEALTH_CHECK_ENDPOINT = "/health"
PROMETHEUS_ENABLED = False

# Create backup directory
BACKUP_DIR.mkdir(exist_ok=True)

    