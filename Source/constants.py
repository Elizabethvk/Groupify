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