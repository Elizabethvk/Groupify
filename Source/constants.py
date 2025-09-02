PATTERNS = {
        'bg_item': r'(.+?)\s+(\d+)\s*[xх]\s*([\d,\.]+)\s+([\d,\.]+)\s*(?:лв|Г|б)?',
        'bg_price': r'([\d,\.]+)\s*(?:лв|Г|б|BGN)',
        'bg_total': r'(?:ОБЩA?\s+СУМА|СУМА|TOTAL|Всичко|ОБЩО)[:\s]*([\d,\.]+)',
        
        'en_item': r'(.+?)\s+(\d+)\s*x\s*([\d,\.]+)\s+([\d,\.]+)',
        'en_price': r'\$?([\d,\.]+)',
        'en_total': r'(?:TOTAL|Total|AMOUNT|SUM|Subtotal)[:\s]*\$?([\d,\.]+)',
        
        'item_with_qty': r'(\d+)\s*[xх]\s*([\d,\.]+)\s*=?\s*([\d,\.]+)',
        'simple_item': r'(.+?)\s+([\d,\.]+)\s*(?:лв|BGN|\$)?$',
    }

# Words to skip
SKIP_WORDS = [
    'СУМА', 'TOTAL', 'БОН', 'ДДС', 'УНП', 'ЕИК', 'КАРТА', 'СМЕТКА',
    'БЛАГОДАРИМ', 'TAX', 'SUBTOTAL', 'CASH', 'CHANGE', 'CARD',
    'RECEIPT', 'INVOICE', 'DATE', 'TIME', 'CASHIER', 'THANK',
    'ЧЕК', 'КАСА', 'РЕСТОРАНТ', 'КАФЕ',
    'сума', 'total', 'бон', 'ддс', 'унп', 'еик', 'карта', 'сметка',
    'благодарим', 'tax', 'subtotal', 'cash', 'change', 'card',
    'receipt', 'invoice', 'date', 'time', 'cashier', 'thank',
    'чек', 'каса', 'ресторант',
    'Сума', 'Total', 'Бон', 'Ддс', 'Унп', 'Еик', 'Карта', 'Сметка',
    'Благодарим', 'Tax', 'Subtotal', 'Cash', 'Change', 'Card',
    'Receipt', 'Invoice', 'Date', 'Time', 'Cashier', 'Thank',
    'Чек', 'Каса', 'Ресторант', 'Общо', 'ОБЩО'
]