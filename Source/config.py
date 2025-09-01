"""
Centralized configuration for Groupify with environment
"""

import os
from decimal import Decimal

# OCR settings
OCR_PSM = int(os.getenv("GROUPIFY_OCR_PSM", "6"))
OCR_LANGUAGES = os.getenv("GROUPIFY_OCR_LANGUAGES", "bul+eng")

# Runtime settings
DEFAULT_MAX_WORKERS = int(os.getenv("GROUPIFY_MAX_WORKERS", "4"))
CURRENCY_DEFAULT = os.getenv("GROUPIFY_DEFAULT_CURRENCY", "BGN")

# Thresholds
SETTLEMENT_EPSILON = Decimal(os.getenv("GROUPIFY_SETTLEMENT_EPSILON", "0.01"))
DUPLICATE_SIMILARITY_THRESHOLD = float(os.getenv("GROUPIFY_DUP_SIMILARITY", "0.95"))
IMAGE_REGION_OVERLAP_PX = int(os.getenv("GROUPIFY_IMAGE_OVERLAP", "50"))
MAX_IMAGE_SIZE_BYTES = int(os.getenv("GROUPIFY_MAX_IMAGE_SIZE_BYTES", str(50 * 1024 * 1024)))
PROGRESS_BAR_LENGTH = int(os.getenv("GROUPIFY_PROGRESS_BAR_LENGTH", "30"))

# Price normalization
ITEM_PRICE_MIN = float(os.getenv("GROUPIFY_ITEM_PRICE_MIN", "0.01"))
ITEM_PRICE_MAX = float(os.getenv("GROUPIFY_ITEM_PRICE_MAX", "10000"))
FALLBACK_PRICE_MIN = float(os.getenv("GROUPIFY_FALLBACK_PRICE_MIN", "1.0"))
FALLBACK_PRICE_MAX = float(os.getenv("GROUPIFY_FALLBACK_PRICE_MAX", "500.0"))
TOTAL_MISMATCH_TOLERANCE = float(os.getenv("GROUPIFY_TOTAL_MISMATCH_TOLERANCE", "1.0"))

# Workers bounds
WORKERS_MIN = int(os.getenv("GROUPIFY_WORKERS_MIN", "1"))
WORKERS_MAX = int(os.getenv("GROUPIFY_WORKERS_MAX", "16"))