"""
Receipt Parser module for Groupify
Parses OCR text to extract receipt items and totals
"""

import re
import time
from typing import List
from difflib import SequenceMatcher
from data_models import Receipt, ReceiptItem
from constants import PATTERNS, SKIP_WORDS

class ReceiptParser:
    """Parses OCR text to extract receipt items and totals"""
    
    def __init__(self):
        self.receipt = Receipt()
        self.item_id_counter = 0
        self.raw_items = []
    
    def _generate_item_id(self) -> str:
        """Generate unique item ID"""
        self.item_id_counter += 1
        return f"item_{self.item_id_counter}_{int(time.time() * 1000)}"
    
    def _clean_price(self, price_str: str) -> float:
        """Clean and convert price string to float"""
        price_str = re.sub(r'[^\d,\.]', '', price_str)
        price_str = price_str.replace(',', '.')
        try:
            return float(price_str)
        except:
            return 0.0

    def _normalize_item_name(self, name: str) -> str:
        """Normalize item name for comparison"""
        normalized = ' '.join(name.lower().split())
        normalized = re.sub(r'[^\w\s\-а-я]', '', normalized)
        return normalized.strip()
    
    def _is_valid_item_name(self, name: str) -> bool:
        """Check if the name is likely a valid item"""
        if not name or len(name) < 2:
            return False
        
        name_upper = name.upper()
        for skip_word in self.SKIP_WORDS:
            if skip_word in name_upper:
                return False
        
        if not re.search(r'[a-zA-Zа-яА-Я]', name):
            return False
        
        return True
    
    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity score between two strings (0-1)"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def _are_items_similar(self, item1: ReceiptItem, item2: ReceiptItem, 
                           name_threshold: float = 0.85, 
                           price_threshold: float = 0.01) -> bool:
        """Check if two items are likely duplicates"""
        
        name1 = self._normalize_item_name(item1.name)
        name2 = self._normalize_item_name(item2.name)
        
        # Check exact match first
        if name1 == name2 and abs(item1.price - item2.price) < price_threshold:
            return True
        
        # Check similarity for near-matches (OCR errors)
        name_similarity = self._similarity_score(name1, name2)
        price_match = abs(item1.price - item2.price) < price_threshold
        
        # If names are very similar and prices match, likely duplicate
        if name_similarity >= name_threshold and price_match:
            return True
        
        # Check if one name contains the other (partial OCR reads)
        if len(name1) > 3 and len(name2) > 3:
            if (name1 in name2 or name2 in name1) and price_match:
                return True
        
        return False
    
    def _merge_duplicate_items(self, items: List[ReceiptItem]) -> List[ReceiptItem]:
        """Merge duplicate items by increasing quantity"""
        if not items:
            return []
        
        merged = []
        processed = set()
        
        for i, item1 in enumerate(items):
            if i in processed:
                continue
            
            merged_item = ReceiptItem(
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
                
                if self._are_items_similar(item1, item2):
                    merged_item.quantity = item2.quantity
                    processed.add(j)
            
            merged.append(merged_item)
            processed.add(i)
        
        return merged
    
    def _deduplicate_by_position(self, text: str) -> str:
        """Remove duplicate lines that appear close together (from overlapping regions)"""
        lines = text.split('\n')
        cleaned_lines = []
        previous_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            is_duplicate = False
            for prev_line in previous_lines[-3:]:
                if self._similarity_score(line, prev_line) > 0.9:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                cleaned_lines.append(line)
                previous_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def parse(self, ocr_text: str) -> Receipt:
        """Parse OCR text to extract receipt items"""
        ocr_text = self._deduplicate_by_position(ocr_text)
        
        lines = ocr_text.split('\n')
        self.raw_items = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            for pattern_name in ['bg_item', 'en_item']:
                match = re.search(self.PATTERNS[pattern_name], line, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    quantity = int(match.group(2)) if match.group(2) else 1
                    unit_price = self._clean_price(match.group(3))
                    total_price = self._clean_price(match.group(4))
                    
                    if self._is_valid_item_name(name) and total_price > 0:
                        item = ReceiptItem(
                            id=self._generate_item_id(),
                            name=name,
                            quantity=quantity,
                            unit_price=unit_price or (total_price / quantity),
                            price=total_price
                        )
                        self.raw_items.append(item)
                        break
            else:
                match = re.search(self.PATTERNS['simple_item'], line, re.IGNORECASE)
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
                        self.raw_items.append(item)
            
            for pattern_name in ['bg_total', 'en_total']:
                match = re.search(self.PATTERNS[pattern_name], line, re.IGNORECASE)
                if match:
                    total = self._clean_price(match.group(1))
                    if total > 0:
                        self.receipt.total = total
                        self.receipt.original_total = total
                        break
        
        self.receipt.items = self._merge_duplicate_items(self.raw_items)
        
        if self.receipt.total == 0 and self.receipt.items:
            self.receipt.calculate_total()
        
        if len(self.raw_items) > len(self.receipt.items):
            print(f"  Deduplication: {len(self.raw_items)} raw items → {len(self.receipt.items)} unique items")
        
        return self.receipt