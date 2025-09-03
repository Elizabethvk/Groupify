"""
Receipt Parser module for Groupify - FIXED VERSION
Parses OCR text to extract receipt items and totals with better Bulgarian support
"""

import re
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List
from difflib import SequenceMatcher

from data_models import Receipt, ReceiptItem
from constants import TOTAL_SUM_PATTERNS, SKIP_WORDS

class ReceiptParser:
    """Parses OCR text to extract receipt items and totals"""
    
    def __init__(self):
        self.receipt = Receipt()
        self.item_id_counter = 0
        self.debug = True
    
    def _generate_item_id(self) -> str:
        """Generate unique item ID (thread-safe)"""
        return f"item_{uuid.uuid4().hex}"
    
    def _clean_price(self, price_str: str) -> float:
        """Clean and convert price string to float"""
        if not price_str:
            return 0.0
        
        # Remove non-digit, non-decimal characters
        cleaned = re.sub(r'[^\d,\.]', '', str(price_str))
        
        # European format (comma as decimal separator)
        if ',' in cleaned and '.' in cleaned:
            cleaned = cleaned.replace('.', '').replace(',', '.')
        elif ',' in cleaned and cleaned.count(',') == 1:
            if len(cleaned.split(',')[1]) <= 2:
                cleaned = cleaned.replace(',', '.')
        
        try:
            price = float(cleaned)
            # prices be reasonable
            if 0.01 <= price <= 10000:
                return price
        except (ValueError, TypeError):
            pass
        
        return 0.0
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for better comparison"""
        normalized = ' '.join(text.lower().split())
        normalized = re.sub(r'[^\w\sа-я]', ' ', normalized)
        return normalized.strip()
    
    def _is_valid_item_name(self, name: str) -> bool:
        """Check if the name is likely a valid menu item"""
        if not name or len(name.strip()) < 2:
            return False
        
        normalized_name = self._normalize_text(name)
        
        for skip_word in SKIP_WORDS:
            if skip_word in normalized_name:
                return False
        
        if not re.search(r'[a-zA-Zа-яА-Я]', name):
            return False
        
        if len(re.sub(r'[\d\s\.\,\-]', '', name)) < 2:
            return False
        
        return True
    
    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity score between two strings (0-1)"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _deduplicate_by_line_similarity(self, text: str) -> str:
        """Remove duplicate lines that appear due to OCR overlapping regions"""
        lines = text.split('\n')
        unique_lines = []
        seen_exact = set()
        seen_similar = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line in seen_exact:
                if self.debug:
                    print(f"  Skipping exact duplicate: '{line}'")
                continue
            
            is_similar_duplicate = False
            for seen_line in seen_similar[-10:]:  # Check last 10 lines
                similarity = self._similarity_score(line, seen_line)
                if similarity > 0.95:
                    is_similar_duplicate = True
                    if self.debug:
                        print(f"  Skipping similar duplicate: '{line}' (similar to '{seen_line}', score: {similarity:.3f})")
                    break
            
            if not is_similar_duplicate:
                unique_lines.append(line)
                seen_exact.add(line)
                seen_similar.append(line)
        
        return '\n'.join(unique_lines)
    
    def _extract_items_from_line(self, line: str) -> List[ReceiptItem]:
        """Extract items from a single line using multiple patterns"""
        items = []
        line = line.strip()
        
        if not line:
            return items

        if self.debug:
            print(f"  Analyzing line: '{line}'")
        
        if any(word in line.upper() for word in ['ОБЩО:', 'TOTAL:', 'СУМА:', 'СМЕТКА']):
            return items
        
        # Pattern 1: Quantity x Price = Total
        qty_match = re.search(r'(.+?)\s*[xх×](\d+)\s*[-\s]*([\d,\.]+)\s*(?:лв|Г|Б|BGN|\$|USD|€|EUR)?', line, re.IGNORECASE)
        if qty_match:
            name = qty_match.group(1).strip()
            quantity = int(qty_match.group(2))
            total_price = self._clean_price(qty_match.group(3))
            unit_price = total_price / quantity if quantity > 0 else total_price
            
            if self._is_valid_item_name(name) and total_price > 0:
                item = ReceiptItem(
                    id=self._generate_item_id(),
                    name=name,
                    quantity=quantity,
                    unit_price=unit_price,
                    price=total_price
                )
                items.append(item)
                if self.debug:
                    print(f"    ✓ Found qty item (xN format): {name} {quantity}x{unit_price:.2f} = {total_price:.2f}")
                return items

        # Pattern 2: Number Item - Price
        num_item_match = re.search(r'^(\d+)\s+(.+?)\s*[-–]\s*([\d,\.]+)\s*(?:лв|Г|Б|BGN|\$|USD|€|EUR)?', line, re.IGNORECASE)
        if num_item_match:
            quantity = int(num_item_match.group(1))
            name = num_item_match.group(2).strip()
            total_price = self._clean_price(num_item_match.group(3))
            unit_price = total_price / quantity if quantity > 0 else total_price
            
            if self._is_valid_item_name(name) and total_price > 0:
                item = ReceiptItem(
                    id=self._generate_item_id(),
                    name=name,
                    quantity=quantity,
                    unit_price=unit_price,
                    price=total_price
                )
                items.append(item)
                if self.debug:
                    print(f"    ✓ Found numbered item: {name} {quantity}x{unit_price:.2f} = {total_price:.2f}")
                return items

        # Pattern 3: Item Qty x UnitPrice Total
        traditional_match = re.search(r'(.+?)\s+(\d+)\s*[xх×]\s*([\d,\.]+)\s+([\d,\.]+)', line, re.IGNORECASE)
        if traditional_match:
            name = traditional_match.group(1).strip()
            quantity = int(traditional_match.group(2))
            unit_price = self._clean_price(traditional_match.group(3))
            total_price = self._clean_price(traditional_match.group(4))
            
            if self._is_valid_item_name(name) and total_price > 0:
                expected_total = quantity * unit_price
                if abs(expected_total - total_price) < 0.5:
                    item = ReceiptItem(
                        id=self._generate_item_id(),
                        name=name,
                        quantity=quantity,
                        unit_price=unit_price,
                        price=total_price
                    )
                    items.append(item)
                    if self.debug:
                        print(f"    ✓ Found traditional item: {name} {quantity}x{unit_price:.2f} = {total_price:.2f}")
                    return items

        # Pattern 4: Item - Price
        simple_match = re.search(r'^(.+?)\s*[-–]\s*([\d,\.]+)\s*(?:лв|Г|Б|BGN|\$|USD|€|EUR)?', line, re.IGNORECASE)
        if simple_match:
            name = simple_match.group(1).strip()
            price = self._clean_price(simple_match.group(2))
            
            if self._is_valid_item_name(name) and price > 0:
                item = ReceiptItem(
                    id=self._generate_item_id(),
                    name=name,
                    quantity=1,
                    unit_price=price,
                    price=price
                )
                items.append(item)
                if self.debug:
                    print(f"    ✓ Found simple item: {name} = {price:.2f}")
                return items

        # Pattern 5: Simple Item Price
        no_dash_match = re.search(r'^(.+?)\s+([\d,\.]+)\s*(?:лв|Г|Б|BGN|\$|USD|€|EUR)?\s*$', line, re.IGNORECASE)
        if no_dash_match:
            name = no_dash_match.group(1).strip()
            price = self._clean_price(no_dash_match.group(2))
            
            if self._is_valid_item_name(name) and price > 0:
                item = ReceiptItem(
                    id=self._generate_item_id(),
                    name=name,
                    quantity=1,
                    unit_price=price,
                    price=price
                )
                items.append(item)
                if self.debug:
                    print(f"    ✓ Found no-dash item: {name} = {price:.2f}")
                return items

        return items
    
    def _find_total(self, text: str) -> float:
        """Find the total amount in the receipt"""
        for pattern in TOTAL_SUM_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                total = self._clean_price(match.group(1))
                if total > 0:
                    if self.debug:
                        print(f"  Found total: {total:.2f}")
                    return total
        return 0.0
    
    def _detect_currency(self, text: str) -> str:
        """Detect currency used in receipt"""
        bg_indicators = len(re.findall(r'лв|Г|Б|BGN', text, re.IGNORECASE))
        usd_indicators = len(re.findall(r'\$|USD', text, re.IGNORECASE))
        eur_indicators = len(re.findall(r'€|EUR', text, re.IGNORECASE))
        
        if bg_indicators > max(usd_indicators, eur_indicators):
            return 'BGN'
        elif usd_indicators > eur_indicators:
            return 'USD'
        elif eur_indicators > 0:
            return 'EUR'
        else:
            return 'BGN'
    
    def parse(self, ocr_text: str) -> Receipt:
        """Parse OCR text to extract receipt items and total"""
        if self.debug:
            print("\n🔍 Starting receipt parsing...")
            print(f"OCR text length: {len(ocr_text)} characters")
        
        self.receipt = Receipt()
        self.item_id_counter = 0
        
        cleaned_text = self._deduplicate_by_line_similarity(ocr_text)
        if self.debug:
            lines_before = len([l for l in ocr_text.split('\n') if l.strip()])
            lines_after = len([l for l in cleaned_text.split('\n') if l.strip()])
            if lines_before != lines_after:
                print(f"Deduplicated lines: {lines_before} → {lines_after}")
        
        self.receipt.currency = self._detect_currency(cleaned_text)
        if self.debug:
            print(f"Detected currency: {self.receipt.currency}")
        
        lines = [l for l in cleaned_text.split('\n') if l.strip()]
        all_items: List[ReceiptItem] = []
        
        # Parallel line parsing
        max_workers = max(1, min(8, (os.cpu_count() or 4)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for result in executor.map(self._extract_items_from_line, lines):
                if result:
                    all_items.extend(result)
        
        self.receipt.items = all_items
        
        if not self.receipt.items:
            if self.debug:
                print("  ⚠ No items found with current patterns")
                print("  💡 Trying fallback extraction...")
            
            for line in lines:
                line = line.strip()
                if not line or any(word in line.upper() for word in ['ОБЩО:', 'TOTAL:', 'СУМА:', 'СМЕТКА']):
                    continue
                
                price_match = re.search(r'([\d,\.]+)\s*(?:лв|Г|Б|BGN|\$|USD|€|EUR)?\s*$', line, re.IGNORECASE)
                if price_match:
                    price = self._clean_price(price_match.group(1))
                    if 1.0 <= price <= 500:
                        name_part = line[:price_match.start()].strip()
                        name_part = re.sub(r'^[\d\s\-\*]+', '', name_part).strip()  # Remove leading numbers
                        name_part = re.sub(r'\s*[-–]\s*$', '', name_part).strip()  # Remove trailing dash
                        
                        if len(name_part) > 2 and self._is_valid_item_name(name_part):
                            item = ReceiptItem(
                                id=self._generate_item_id(),
                                name=name_part,
                                quantity=1,
                                unit_price=price,
                                price=price
                            )
                            self.receipt.items.append(item)
                            if self.debug:
                                print(f"    ⚡ Fallback item: {name_part} = {price:.2f}")
        
        self.receipt.total = self._find_total(cleaned_text)
        self.receipt.original_total = self.receipt.total
        
        if self.receipt.total == 0 and self.receipt.items:
            self.receipt.calculate_total()
            if self.debug:
                print(f"  Calculated total from items: {self.receipt.total:.2f}")
        
        if self.receipt.items and self.receipt.total > 0:
            calculated_total = sum(item.price for item in self.receipt.items)
            if abs(calculated_total - self.receipt.total) > 1.0:
                if self.debug:
                    print(f"  ⚠ Total mismatch: calculated {calculated_total:.2f} vs found {self.receipt.total:.2f}")
                    print(f"  This suggests possible duplicate items or parsing errors")
        
        if self.debug:
            print(f"\n📊 Parsing Results:")
            print(f"  Items found: {len(self.receipt.items)}")
            print(f"  Total: {self.receipt.total:.2f} {self.receipt.currency}")
            
            if self.receipt.items:
                print("  Items:")
                for item in self.receipt.items:
                    print(f"    • {item.name}: {item.quantity}x{item.unit_price:.2f} = {item.price:.2f}")
        
        return self.receipt