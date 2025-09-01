SKIP_WORDS = {
    # Bulgarian skip words
    'сума', 'общо', 'общa', 'бон', 'чек', 'ддс', 'унп', 'еик', 
    'карта', 'сметка', 'благодарим', 'ресторант', 'кафе', 'касa',
    'дата', 'време', 'час', 'минута',
    
    # English skip words
    'total', 'subtotal', 'tax', 'receipt', 'bill', 'check', 'cash', 
    'card', 'change', 'date', 'time', 'server', 'table', 'thank',
    'admin', 'fee', 'service'
}

TOTAL_SUM_PATTERNS = [
    r'(?:ОБЩО|ОБЩА\s+СУМА|СУМА|TOTAL|Total|Общо)[\s:]*?([\d,\.]+)',
    r'(?:ИТОГО|Итого|ВСИЧКО|Всичко)[\s:]*?([\d,\.]+)',
    r'(?:SUBTOTAL|Subtotal)[\s:]*?([\d,\.]+)',
]

# General numeric and parsing constants
PROGRESS_BAR_LENGTH = 30
MAX_IMAGE_SIZE_BYTES = 50 * 1024 * 1024
IMAGE_REGION_OVERLAP_PX = 50

# Parsing thresholds
DUPLICATE_SIMILARITY_THRESHOLD = 0.95
ITEM_PRICE_MIN = 0.01
ITEM_PRICE_MAX = 10000.0
FALLBACK_PRICE_MIN = 1.0
FALLBACK_PRICE_MAX = 500.0
TOTAL_MISMATCH_TOLERANCE = 1.0

# Settlement and currency handling
from decimal import Decimal
SETTLEMENT_EPSILON = Decimal("0.01")
DECIMAL_QUANTIZE = Decimal("0.01")

# OCR configuration defaults
DEFAULT_OCR_PSM = 6
DEFAULT_OCR_LANGUAGES = "bul+eng"
WORKERS_MIN = 1
WORKERS_MAX = 16