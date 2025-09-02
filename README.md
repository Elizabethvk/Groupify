# 🍽️ Groupify - Smart Bill Splitter

Parallel Receipt Processing & Smart Bill Splitting with advanced OCR technology.

## Features

- **🚀 Parallel OCR Processing**: Multi-worker OCR for faster receipt scanning
- **🌍 Multi-language Support**: Bulgarian and English receipt recognition
- **🧠 Smart Parsing**: Intelligent item detection and deduplication
- **💰 Optimized Settlements**: Minimize transactions between people
- **📊 Detailed Analytics**: Complete breakdown of who owes what
- **💾 Export Capabilities**: JSON export with full settlement details
- **🎯 Interactive CLI**: User-friendly command-line interface

## Installation

### Prerequisites

1. **Install Tesseract OCR**:
   - **Windows**: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS**: `brew install tesseract`
   - **Ubuntu/Debian**: `sudo apt install tesseract-ocr tesseract-ocr-bul`

<!-- 2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ``` -->

### Quick Setup

```bash
git clone <repository-url>
cd groupify
pip install -r requirements.txt
python main.py --help
```

## Usage

### Basic Usage

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

### Interactive Commands

1. **Process Receipt Image**: Upload and OCR a receipt photo
2. **Manage People**: Add/remove people splitting the bill
3. **Assign Items**: Assign specific items to specific people
4. **Add Tip**: Include service charges or tips
5. **Calculate Settlements**: Optimize who pays whom
6. **Export Results**: Save complete analysis to JSON

## File Structure

```
groupify/
├── main.py              # Main entry point
├── data_models.py       # Data structures (Receipt, Item, Settlement)
├── ocr_processor.py     # Parallel OCR processing
├── receipt_parser.py    # Text parsing and item extraction
├── bill_splitter.py     # Settlement optimization algorithms
├── cli_interface.py     # Interactive command-line interface
<!-- ├── requirements.txt     # Python dependencies -->
└── README.md
```

## Supported Receipt Formats

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
6. **Add Tip**: 10% service charge
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
    "items": [...],
    "total": 127.00,
    "tip_amount": 15.00
  },
  "settlement_analysis": {
    "individual_shares": {...},
    "settlements": [...],
    "payment_instructions": [...],
    "detailed_breakdown": {...}
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