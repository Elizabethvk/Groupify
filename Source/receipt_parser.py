#!/usr/bin/env python3
"""
Receipt Parser module for Groupify - FIXED VERSION
Parses OCR text to extract receipt items and totals with better Bulgarian support
"""

import re
import time
from typing import List, Tuple
from difflib import SequenceMatcher
from data_models import Receipt, ReceiptItem
from constants import PATTERNS, SKIP_WORDS

class ReceiptParser:
    """Parses OCR text to extract receipt items and totals"""
    
    def __init__(self):
        self.receipt = Receipt()
        self.item_id_counter = 0
        self.debug = True
    
    def _generate_item_id(self) -> str:
        """Generate unique item ID"""
        self.item_id_counter += 1
        return f"item_{self.item_id_counter}_{int(time.time() * 1000)}"
    
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
        
        for skip_word in self.SKIP_WORDS:
            if skip_word in normalized_name:
                return False
        
        if not re.search(r'[a-zA-Zа-яА-Я]', name):
            return False
        
        if len(re.sub(r'[\d\s\.\,\-]', '', name)) < 2:
            return False
        
        return True
    
    def _extract_items_from_line(self, line: str) -> List[ReceiptItem]:
        """Extract items from a single line using multiple patterns"""
        items = []
        original_line = line
        line = line.strip()
        
        if not line:
            return items
        
        if self.debug:
            print(f"  Analyzing line: '{line}'")
        
        for pattern_name in ['bg_item_qty', 'en_item_qty']:
            match = re.search(self.PATTERNS[pattern_name], line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                quantity = int(match.group(2))
                unit_price = self._clean_price(match.group(3))
                total_price = self._clean_price(match.group(4))
                
                if self._is_valid_item_name(name) and total_price > 0:
                    # Validate that quantity * unit_price ≈ total_price
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
                            print(f"    ✓ Found qty item: {name} {quantity}x{unit_price:.2f} = {total_price:.2f}")
                        return items
        
        for pattern_name in ['bg_item_simple', 'en_item_simple']:
            match = re.search(self.PATTERNS[pattern_name], line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                price = self._clean_price(match.group(2))
                
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
        
        price_matches = re.findall(r'[\d,\.]+', line)
        if len(price_matches) >= 3:
            try:
                qty_part = line.split()[0]
                if qty_part.isdigit():
                    quantity = int(qty_part)
                    prices = [self._clean_price(p) for p in price_matches[-2:]]  # Last two numbers
                    if all(p > 0 for p in prices):
                        unit_price, total_price = prices
                        if abs(quantity * unit_price - total_price) < 0.5:
                            name_part = re.sub(r'^\d+\s*[xх×]?\s*', '', line)
                            name_part = re.sub(r'[\d,\.]+\s*(?:лв|Г|Б|BGN|\$|USD|€|EUR)?\s*$', '', name_part).strip()
                            
                            if self._is_valid_item_name(name_part):
                                item = ReceiptItem(
                                    id=self._generate_item_id(),
                                    name=name_part,
                                    quantity=quantity,
                                    unit_price=unit_price,
                                    price=total_price
                                )
                                items.append(item)
                                if self.debug:
                                    print(f"    ✓ Found multi-price item: {name_part} {quantity}x{unit_price:.2f} = {total_price:.2f}")
            except:
                pass
        
        return items
    
    def _find_total(self, text: str) -> float:
        """Find the total amount in the receipt"""
        for pattern in self.PATTERNS['total_patterns']:
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
    
    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity score between two strings (0-1)"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _merge_similar_items(self, items: List[ReceiptItem]) -> List[ReceiptItem]:
        """Merge items that are likely duplicates (from OCR errors or overlapping regions)"""
        if len(items) <= 1:
            return items
        
        merged = []
        processed = set()
        
        for i, item1 in enumerate(items):
            if i in processed:
                continue
            
            current_item = ReceiptItem(
                id=item1.id,
                name=item1.name,
                quantity=item1.quantity,
                unit_price=item1.unit_price,
                price=item1.price,
                assigned_to=item1.assigned_to.copy()
            )
            
            # Look for duplicates
            for j, item2 in enumerate(items[i+1:], start=i+1):
                if j in processed:
                    continue
                
                name_similarity = self._similarity_score(item1.name, item2.name)
                price_similarity = abs(item1.price - item2.price) < 0.5
                
                if name_similarity > 0.85 and price_similarity:
                    current_item.quantity += item2.quantity
                    current_item.price = current_item.unit_price * current_item.quantity
                    processed.add(j)
                    if self.debug:
                        print(f"  Merged similar items: '{item1.name}' + '{item2.name}'")
            
            merged.append(current_item)
            processed.add(i)
        
        return merged
    
    def parse(self, ocr_text: str) -> Receipt:
        """Parse OCR text to extract receipt items and total"""
        if self.debug:
            print("\n🔍 Starting receipt parsing...")
            print(f"OCR text length: {len(ocr_text)} characters")
        
        self.receipt = Receipt()
        self.item_id_counter = 0
        
        self.receipt.currency = self._detect_currency(ocr_text)
        if self.debug:
            print(f"Detected currency: {self.receipt.currency}")
        
        lines = ocr_text.split('\n')
        all_items = []
        
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                continue
            
            items = self._extract_items_from_line(line)
            all_items.extend(items)
        
        if all_items:
            self.receipt.items = self._merge_similar_items(all_items)
        else:
            if self.debug:
                print("  ⚠ No items found with current patterns")
                print("  💡 Trying fallback extraction...")
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                price_matches = re.findall(r'([\d,\.]+)', line)
                for price_str in price_matches:
                    price = self._clean_price(price_str)
                    if 1.0 <= price <= 500:
                        name_part = line.split(price_str)[0].strip()
                        name_part = re.sub(r'^[\d\s\-\*]+', '', name_part).strip()  # Remove leading numbers
                        
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
                            break
        
        # Find total
        self.receipt.total = self._find_total(ocr_text)
        self.receipt.original_total = self.receipt.total
        
        if self.receipt.total == 0 and self.receipt.items:
            self.receipt.calculate_total()
            if self.debug:
                print(f"  Calculated total from items: {self.receipt.total:.2f}")
        
        if self.debug:
            print(f"\n📊 Parsing Results:")
            print(f"  Items found: {len(self.receipt.items)}")
            print(f"  Total: {self.receipt.total:.2f} {self.receipt.currency}")
            
            if self.receipt.items:
                print("  Items:")
                for item in self.receipt.items:
                    print(f"    • {item.name}: {item.price:.2f}")
        
        return self.receipt