# 🍽️ Groupify - Smart Bill Splitter

Parallel receipt processing and bill splitting with OCR.

## Features

- **Parallel OCR**: Multi-worker OCR for faster receipt scanning
- **Multi-language**: Bulgarian and English receipt recognition
- **Smart parsing**: Item detection and deduplication
- **Optimized settlements**: Minimize transactions between people
- **Analytics**: Breakdown of who owes what
- **Export**: JSON export with settlement details

## Installation

1. Install Tesseract OCR
   - Windows: see `https://github.com/UB-Mannheim/tesseract/wiki`
   - macOS: `brew install tesseract`
   - Ubuntu/Debian: `sudo apt install tesseract-ocr tesseract-ocr-bul`
2. Install Python dependencies
   - Create a venv and install requirements:
```bash
git clone <repository-url>
cd Groupify
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then run:
```bash
cd Source
python main.py --help
```

## Usage

```bash
# Interactive mode
python main.py

# Process image and start interactive mode
python main.py receipt.jpg

# Quick processing - just show results
python main.py receipt.jpg --quick

# Use more workers for faster processing
python main.py receipt.jpg --workers 8
```

### Interactive commands

1. **Process Receipt Image**: Upload and OCR a receipt photo
2. **Manage People**: Add/remove people splitting the bill
3. **Assign Items**: Assign specific items to specific people
4. **Add Tip**: Include service charges or tips
5. **Calculate Settlements**: Optimize who pays whom
6. **Export Results**: Save complete analysis to JSON

## File Structure

```
Groupify/
├── Source/
│   ├── main.py              # Main entry point
│   ├── data_models.py       # Data structures
│   ├── ocr_processor.py     # Parallel OCR processing
│   ├── receipt_parser.py    # Text parsing and item extraction
│   ├── bill_splitter.py     # Settlement optimization algorithms
│   ├── cli_interface.py     # Interactive CLI
│   ├── utils.py             # Validation and helpers
│   └── constants.py         # Regex and parser constants
│   └── config.py            # Configuration of constants
├── Images/                  # Sample images
├── README.md
└── requirements.txt         # Py dependencies
```

## Architecture Notes

- **Separation of concerns**: OCR, parsing, settlement, and CLI are isolated.
- **Parallelization**: OCR is region-parallel; parser parses lines in parallel.
- **Input safety**: Centralized in `utils.py` and in CLI/main/OCR loader.

## Supported Receipt Formats
- .jpg
- .jpeg
- .png
- .bmp
- .tiff
- .gif
- .webp'

### Languages
- **Bulgarian**: Cyrillic text recognition
- **English**: Latin text recognition
- **Mixed**: Bilingual receipts

### Currencies
- Bulgarian Lev (лв, BGN)
- Euro (€, EUR)
- US Dollar ($, USD)

### Receipt Types
- Restaurant receipts
- Grocery store receipts
- Retail receipts with itemized lists
- Mixed quantity items (2x item @ price)

## Example Workflow

1. **Get Receipt Photo**: Clear image of itemized receipt
2. **Run Groupify**: `python main.py receipt.jpg`
3. **Add People**: Ivan, Georgi, Maria
4. **Auto-Processing**: OCR extracts items automatically
5. **Assign Items**: 
   - Appetizer → Everyone
   - Ivan's meal → Ivan only
   - Shared dessert → Georgi & Maria
6. **Add Tip**: 10% service charge (optional)
7. **Calculate**: Optimal payment plan generated
8. **Export**: Complete JSON with all details

## Advanced Features

### Parallel OCR Processing
- Splits images into regions for concurrent processing
- Automatic deduplication of overlapping text
- Speedup metrics and performance monitoring

### Smart Item Detection
- Pattern matching for different receipt formats
- Price validation and currency detection
- Automatic quantity and unit price calculation
- Duplicate item merging

### Settlement Optimization
- Minimizes the number of transactions needed
- Balances creditors and debtors efficiently
- Handles unequal consumption scenarios
- Includes proportional tip distribution

### Export Format
```json
{
  "export_info": {
    "timestamp": "2025-01-01T12:00:00",
    "version": "1.0",
    "currency": "BGN"
  },
  "receipt": {
    "items": [
      {"id": "item_abc", "name": "Salad", "quantity": 1, "unit_price": 7.50, "price": 7.50, "assigned_to": ["Ivan", "Maria"]}
    ],
    "total": 127.00,
    "original_total": 112.00,
    "tip_amount": 15.00,
    "currency": "BGN"
  },
  "settlement_analysis": {
    "individual_shares": {"Ivan": 40.50, "Georgi": 35.20, "Maria": 51.30},
    "equal_share_per_person": 42.33,
    "total_amount": 127.00,
    "transactions": 2,
    "settlements": [
      {"from_person": "Georgi", "to_person": "Maria", "amount": 7.00, "currency": "BGN"}
    ],
    "payment_instructions": [
      {"instruction": "Georgi pays Maria 7.00 BGN", "from": "Georgi", "to": "Maria", "amount": 7.00, "currency": "BGN"}
    ],
    "detailed_breakdown": {
      "Ivan": {"subtotal_from_items": 35.50, "tip_share": 5.00, "total_consumed": 40.50, "equal_share_owed": 42.33, "difference": -1.83, "status": "debtor"}
    }
  }
}
```

## Troubleshooting

### OCR Issues
- **Poor Recognition**: Ensure good lighting and image quality
- **Missing Languages**: Install Tesseract language packs
- **Windows Path Issues**: Check Tesseract installation path

### Performance
- **Slow Processing**: Reduce worker count or image size
- **Memory Issues**: Use fewer parallel workers
- **Accuracy Problems**: Try image preprocessing

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Tesseract OCR for text recognition
- OpenCV for image processing