#!/usr/bin/env python3
"""
Utility functions for Groupify
"""

import re
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
import mimetypes
from config import MAX_IMAGE_SIZE_BYTES, PROGRESS_BAR_LENGTH

def validate_image_path(image_path: str) -> bool:
    """Comprehensive image path validation with security checks"""
    if not isinstance(image_path, str):
        print("Image path must be a string")
        return False
    
    try:
        # Convert to Path object for better handling
        path = Path(image_path)
        
        # Security: Basic directory traversal check
        if '..' in str(path):
            print(f"Security risk: Invalid path pattern: {image_path}")
            return False
        
        # Check if file exists
        if not path.exists():
            print(f"File not found: {image_path}")
            return False
        
        # Check if it's a file (not a directory)
        if not path.is_file():
            print(f"Path is not a file: {image_path}")
            return False
        
        # File size validation configure
        if path.stat().st_size > MAX_IMAGE_SIZE_BYTES:
            print(f"File too large: {path.stat().st_size} bytes (max: {MAX_IMAGE_SIZE_BYTES})")
            return False
        
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp'}
        if path.suffix.lower() not in allowed_extensions:
            print(f"Unsupported file extension: {path.suffix}")
            return False
        
        # MIME type validation
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type and not mime_type.startswith('image/'):
            print(f"Invalid MIME type: {mime_type}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Path validation error: {e}")
        return False


def get_image_files(directory: str) -> List[str]:
    """Get all image files from a directory with validation"""
    if not isinstance(directory, str):
        return []
    
    try:
        directory_path = Path(directory)
        
        if not directory_path.exists() or not directory_path.is_dir():
            print(f"Invalid directory: {directory}")
            return []
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp'}
        image_files = []
        
        # Search for image files
        for file_path in directory_path.iterdir():
            if (file_path.is_file() and 
                file_path.suffix.lower() in image_extensions and
                validate_image_path(str(file_path))):
                image_files.append(str(file_path))
        
        # Sort files naturally
        image_files.sort()
        
        print(f"Found {len(image_files)} valid image files in {directory}")
        return image_files
        
    except Exception as e:
        print(f"Error scanning directory {directory}: {e}")
        return []


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    if not isinstance(filename, str):
        return "unnamed_file"
    
    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    # Ensure it's not empty
    if not filename.strip():
        filename = "unnamed_file"
    
    return filename


def calculate_file_hash(filepath: str, algorithm: str = 'md5') -> Optional[str]:
    """Calculate hash of a file for caching and deduplication"""
    try:
        hash_obj = hashlib.new(algorithm)
        
        with open(filepath, 'rb') as f:
            # Read file in chunks to handle large files
            while chunk := f.read(8192):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
        
    except Exception as e:
        print(f"Error calculating hash for {filepath}: {e}")
        return None


def format_currency(amount: float, currency: str = 'BGN') -> str:
    """Format currency amount with proper symbols"""
    if not isinstance(amount, (int, float)):
        return "0.00"
    
    currency_symbols = {
        'BGN': 'лв',
        'USD': '$',
        'EUR': '€',
        'GBP': '£'
    }
    
    symbol = currency_symbols.get(currency, currency)
    
    if currency in ['USD', 'EUR', 'GBP']:
        return f"{symbol}{amount:.2f}"
    else:
        return f"{amount:.2f} {symbol}"


def parse_currency_amount(amount_str: str) -> tuple[float, str]:
    """Parse currency amount string and return (amount, currency)"""
    if not isinstance(amount_str, str):
        return 0.0, 'BGN'
    
    # Clean the string
    amount_str = amount_str.strip()
    
    # Currency patterns
    patterns = [
        (r'\$(\d+(?:\.\d{2})?)', 'USD'),
        (r'€(\d+(?:\.\d{2})?)', 'EUR'),
        (r'£(\d+(?:\.\d{2})?)', 'GBP'),
        (r'(\d+(?:[,\.]\d{2})?)\s*(?:лв|Г|б|BGN)', 'BGN'),
        (r'(\d+(?:[,\.]\d{2})?)', 'BGN')  # Default
    ]
    
    for pattern, currency in patterns:
        match = re.search(pattern, amount_str, re.IGNORECASE)
        if match:
            try:
                amount = float(match.group(1).replace(',', '.'))
                return amount, currency
            except ValueError:
                continue
    
    return 0.0, 'BGN'


def try_parse_int(value: str) -> Optional[int]:
    """Safely parse integer from string"""
    try:
        return int(value.strip())
    except Exception:
        return None


def try_parse_float(value: str) -> Optional[float]:
    """Safely parse float from string"""
    try:
        return float(value.strip().replace(',', '.'))
    except Exception:
        return None


def validate_menu_choice(choice: str, valid_choices: list[str]) -> Optional[str]:
    """Validate a menu choice against allowed options"""
    if not isinstance(choice, str):
        return None
    choice = choice.strip()
    return choice if choice in set(valid_choices) else None


def create_progress_callback(total_steps: int, description: str = "Processing"):
    """Create a progress callback function for long operations"""
    def progress_callback(step: int, status: str = ""):
        percentage = (step / total_steps) * 100
        bar_length = PROGRESS_BAR_LENGTH
        filled_length = int(bar_length * step // total_steps)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        status_text = f" - {status}" if status else ""
        print(f"\r{description}: [{bar}] {percentage:.1f}%{status_text}", end='', flush=True)
        
        if step >= total_steps:
            print()
    
    return progress_callback


def ensure_directory_exists(directory: str) -> bool:
    """Ensure a directory exists, create it if it doesn't"""
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Failed to create directory {directory}: {e}")
        return False

def clean_text_for_display(text: str, max_length: int = 100) -> str:
    """Clean text for safe display in UI"""
    if not isinstance(text, str):
        return ""
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # If too long
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    return text


def detect_language(text: str) -> str:
    """Simple language detection for Bulgarian vs English"""
    if not isinstance(text, str) or not text.strip():
        return 'unknown'
    
    # Count Cyrillic characters
    cyrillic_count = len(re.findall(r'[а-яё]', text.lower()))
    total_letters = len(re.findall(r'[a-zа-яё]', text.lower()))
    
    if total_letters == 0:
        return 'unknown'
    
    cyrillic_ratio = cyrillic_count / total_letters
    
    if cyrillic_ratio > 0.5:
        return 'bulgarian'
    elif cyrillic_ratio < 0.1:
        return 'english'
    else:
        return 'mixed'


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str, log_result: bool = True):
        self.operation_name = operation_name
        self.log_result = log_result
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = __import__('time').time()
        return self
    
    def __exit__(self):
        self.end_time = __import__('time').time()
        execution_time = self.end_time - self.start_time
        if self.log_result:
            print(f"{self.operation_name} completed in {execution_time:.3f}s")
        return False
    
    @property
    def elapsed_time(self) -> Optional[float]:
        """Get elapsed time if timing is complete"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None