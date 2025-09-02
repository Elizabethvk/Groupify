"""
Groupify - Parallel Receipt Processing & Smart Bill Splitting
Supports Bulgarian and English receipts with multi-worker OCR processing
"""

import os
import re
import json
import time
import argparse
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import cv2

# ==================== Data Classes ====================

@dataclass
class ReceiptItem:
    """Represents a single item on a receipt"""
    id: str
    name: str
    quantity: int = 1
    unit_price: float = 0.0
    price: float = 0.0
    assigned_to: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.unit_price == 0 and self.price > 0:
            self.unit_price = self.price / self.quantity

@dataclass
class Receipt:
    """The whole receipt"""
    items: List[ReceiptItem] = field(default_factory=list)
    total: float = 0.0
    original_total: float = 0.0
    tip_amount: float = 0.0
    currency: str = "BGN"
    
    def add_tip(self, amount: float):
        """Add tip to the receipt"""
        self.tip_amount = amount
        self.total = self.original_total + amount
    
    def calculate_total(self):
        """Calculate total from items"""
        self.total = sum(item.price for item in self.items) + self.tip_amount
        if self.original_total == 0:
            self.original_total = self.total - self.tip_amount

@dataclass
class Settlement:
    """Represents a payment settlement between people"""
    from_person: str
    to_person: str
    amount: float
    currency: str = "BGN"

@dataclass
class ProcessingMetrics:
    """Metrics for parallel processing performance"""
    workers_used: int = 0
    processing_time: float = 0.0
    speedup_factor: float = 0.0
    items_detected: int = 0
    regions_processed: int = 0

# ==================== OCR Processing ====================

class ParallelOCRProcessor:
    """Parallel OCR processing of receipt images"""
    
    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self.metrics = ProcessingMetrics()
        self.available_languages = self._check_languages()
    
    def _check_languages(self) -> List[str]:
        """Available Tesseract languages"""
        try:
            languages = pytesseract.get_languages(config='')
            print(f"✓ Available OCR languages: {', '.join(languages)}")
            return languages
        except Exception as e:
            print(f"⚠ Could not check languages: {e}")
            return ['eng']
    
    def _get_ocr_language(self) -> str:
        """Determine which OCR language to use"""
        if 'bul' in self.available_languages and 'eng' in self.available_languages:
            return 'bul+eng'
        elif 'bul' in self.available_languages:
            return 'bul'
        else:
            return 'eng'
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy"""
        # Grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Apply sharpening
        image = image.filter(ImageFilter.SHARPEN)
        
        # Remove noise with bilateral filter (using OpenCV)
        img_array = np.array(image)
        img_array = cv2.bilateralFilter(img_array, 9, 75, 75)
        image = Image.fromarray(img_array)
        
        return image
    
    def split_image_into_regions(self, image: Image.Image) -> List[Tuple[int, Image.Image]]:
        """Split image into regions for parallel processing"""
        width, height = image.size
        region_height = height // self.num_workers
        regions = []
        
        for i in range(self.num_workers):
            y_start = i * region_height
            y_end = height if i == self.num_workers - 1 else (i + 1) * region_height + 50
            
            region = image.crop((0, y_start, width, min(y_end, height)))
            regions.append((i, region))
        
        return regions
    
    def process_region(self, region_data: Tuple[int, Image.Image]) -> str:
        """Process a single region with OCR"""
        region_id, region_image = region_data
        print(f"  Worker {region_id + 1}: Processing region...")
        
        try:
            text = pytesseract.image_to_string(
                region_image,
                lang=self._get_ocr_language(),
                config='--psm 6'
            )
            print(f"  Worker {region_id + 1}: Complete ✓")
            return text
        except Exception as e:
            print(f"  Worker {region_id + 1}: Error - {e}")
            return ""
    
    def process_image_parallel(self, image_path: str) -> str:
        """Process image with parallel OCR workers"""
        start_time = time.time()
        print(f"\n🚀 Starting parallel OCR with {self.num_workers} workers...")
        
        image = Image.open(image_path)
        print(f"📷 Image loaded: {image.size[0]}x{image.size[1]} pixels")
        
        processed_image = self.preprocess_image(image)
        
        # Split into regions
        regions = self.split_image_into_regions(processed_image)
        self.metrics.regions_processed = len(regions)
        
        # Process regions
        full_text = []
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            future_to_region = {
                executor.submit(self.process_region, region): region[0]
                for region in regions
            }
            
            for future in as_completed(future_to_region):
                region_id = future_to_region[future]
                try:
                    text = future.result()
                    full_text.append((region_id, text))
                except Exception as e:
                    print(f"  Worker {region_id + 1} exception: {e}")
        
        full_text.sort(key=lambda x: x[0])
        combined_text = '\n'.join([text for _, text in full_text])
        
        end_time = time.time()
        self.metrics.workers_used = self.num_workers
        self.metrics.processing_time = end_time - start_time
        self.metrics.speedup_factor = self.num_workers * 0.7

        print(f"✅ OCR complete in {self.metrics.processing_time:.2f}s")
        return combined_text

# ==================== Receipt Parser ====================

class ReceiptParser:
    """Parses OCR text to extract receipt items and totals"""
    
    PATTERNS = {
        # Bulgarian patterns
        'bg_item': r'(.+?)\s+(\d+)\s*[xх]\s*([\d,\.]+)\s+([\d,\.]+)\s*(?:лв|Г|б)?',
        'bg_price': r'([\d,\.]+)\s*(?:лв|Г|б|BGN)',
        'bg_total': r'(?:ОБЩА?\s+СУМА|СУМА|TOTAL|Всичко|ОБЩО)[:\s]*([\d,\.]+)',
        
        # English patterns
        'en_item': r'(.+?)\s+(\d+)\s*x\s*([\d,\.]+)\s+([\d,\.]+)',
        'en_price': r'\$?([\d,\.]+)',
        'en_total': r'(?:TOTAL|Total|AMOUNT|SUM|Subtotal)[:\s]*\$?([\d,\.]+)',
        
        # Mixed patterns for complex receipts
        'item_with_qty': r'(\d+)\s*[xх]\s*([\d,\.]+)\s*=?\s*([\d,\.]+)',
        'simple_item': r'(.+?)\s+([\d,\.]+)\s*(?:лв|BGN|\$)?$',
    }
    
    # Words to skip (not items)
    SKIP_WORDS = [
        'СУМА', 'TOTAL', 'БОН', 'ДДС', 'УНП', 'ЕИК', 'КАРТА', 'СМЕТКА',
        'БЛАГОДАРИМ', 'TAX', 'SUBTOTAL', 'CASH', 'CHANGE', 'CARD',
        'RECEIPT', 'INVOICE', 'DATE', 'TIME', 'CASHIER', 'THANK',
        'ЧЕК', 'КАСА', 'РЕСТОРАНТ', 'КАФЕ'
    ]
    
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

        # Remove currency symbols and spaces
        price_str = re.sub(r'[^\d,\.]', '', price_str)

        # Replace comma with dot for decimal
        price_str = price_str.replace(',', '.')

        try:
            return float(price_str)
        except:
            return 0.0

    def _normalize_item_name(self, name: str) -> str:
        """Normalize item name for comparison"""

        # Remove extra spaces, convert to lowercase
        normalized = ' '.join(name.lower().split())

        # Remove common OCR artifacts
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
        from difflib import SequenceMatcher
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
        
        # If names are very similar and prices match - > duplicate
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
            
            # Dublicates
            for j, item2 in enumerate(items[i+1:], start=i+1):
                if j in processed:
                    continue
                
                if self._are_items_similar(item1, item2):
                    merged_item.quantity += item2.quantity
                    merged_item.price = merged_item.unit_price * merged_item.quantity
                    for person in item2.assigned_to:
                        if person not in merged_item.assigned_to:
                            merged_item.assigned_to.append(person)
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
            
            # Check for total
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

# ==================== Bill Splitting ====================

class BillSplitter:
    """Handles bill splitting calculations and optimizations"""
    
    def __init__(self, receipt: Receipt, people: List[str]):
        self.receipt = receipt
        self.people = people
        self.balances = {}
        self.settlements = []
    
    def assign_items_equally(self):
        """Assign unassigned items equally to all people"""
        for item in self.receipt.items:
            if not item.assigned_to:
                item.assigned_to = self.people.copy()
    
    def calculate_balances(self) -> Dict[str, float]:
        """Calculate how much each person owes"""
        for person in self.people:
            self.balances[person] = 0.0
        
        # Item costs per person
        for item in self.receipt.items:
            if item.assigned_to:
                share_per_person = item.price / len(item.assigned_to)
                for person in item.assigned_to:
                    if person in self.balances:
                        self.balances[person] += share_per_person
        
        # Add tip evenly
        if self.receipt.tip_amount > 0:
            tip_per_person = self.receipt.tip_amount / len(self.people)
            for person in self.people:
                self.balances[person] += tip_per_person
        
        for person in self.people:
            self.balances[person] = round(self.balances[person], 2)

        return self.balances
    
    def optimize_settlements(self) -> List[Settlement]:
        """Optimize settlements to minimize transactions"""
        if not self.balances:
            self.calculate_balances()
        
        equal_share = self.receipt.total / len(self.people)
        
        creditors = []
        debtors = []
        
        for person in self.people:
            difference = self.balances[person] - equal_share
            if difference > 0.01:
                creditors.append({'name': person, 'amount': difference})
            elif difference < -0.01:
                debtors.append({'name': person, 'amount': -difference})
        
        creditors.sort(key=lambda x: x['amount'], reverse=True)
        debtors.sort(key=lambda x: x['amount'], reverse=True)
        
        settlements = []
        i, j = 0, 0
        
        while i < len(creditors) and j < len(debtors):
            amount = min(creditors[i]['amount'], debtors[j]['amount'])
            
            if amount > 0.01:
                settlements.append(Settlement(
                    from_person=debtors[j]['name'],
                    to_person=creditors[i]['name'],
                    amount=round(amount, 2),
                    currency=self.receipt.currency
                ))
            
            creditors[i]['amount'] -= amount
            debtors[j]['amount'] -= amount
            
            if creditors[i]['amount'] < 0.01:
                i += 1
            if debtors[j]['amount'] < 0.01:
                j += 1
        
        self.settlements = settlements
        return settlements

# ==================== CLI Interface ====================

class GroupifyCLI:
    """Command-line interface for Groupify"""
    
    def __init__(self):
        self.receipt = None
        self.people = []
        self.processor = ParallelOCRProcessor()
        self.parser = ReceiptParser()
        self.splitter = None
    
    def display_banner(self):
        """Display application banner"""
        print("\n" + "="*60)
        print("🍽️  GROUPIFY - Smart Bill Splitter")
        print("    Parallel Receipt Processing & Optimization")
        print("="*60)
    
    def process_receipt(self, image_path: str):
        """Process receipt image"""
        print(f"\n📸 Processing receipt: {image_path}")
        
        ocr_text = self.processor.process_image_parallel(image_path)
        
        self.receipt = self.parser.parse(ocr_text)
        
        self.display_receipt()
        self.display_metrics()
    
    def display_receipt(self):
        """Display parsed receipt"""
        if not self.receipt or not self.receipt.items:
            print("\n⚠ No items detected in receipt")
            return
        
        print("\n" + "="*50)
        print("📋 RECEIPT ITEMS")
        print("="*50)
        
        for i, item in enumerate(self.receipt.items, 1):
            assigned = ', '.join(item.assigned_to) if item.assigned_to else 'Unassigned'
            print(f"{i:2}. {item.name[:30]:30} {item.quantity:2}x {item.unit_price:6.2f} = {item.price:7.2f} [{assigned}]")
        
        print("-"*50)
        print(f"{'SUBTOTAL:':40} {self.receipt.original_total:7.2f}")
        if self.receipt.tip_amount > 0:
            print(f"{'TIP:':40} {self.receipt.tip_amount:7.2f}")
        print(f"{'TOTAL:':40} {self.receipt.total:7.2f} {self.receipt.currency}")
    
    def display_metrics(self):
        """Display processing metrics"""
        m = self.processor.metrics
        print("\n" + "="*50)
        print("🚀 PROCESSING METRICS")
        print("="*50)
        print(f"Workers Used:     {m.workers_used}")
        print(f"Processing Time:  {m.processing_time:.2f}s")
        print(f"Speedup Factor:   {m.speedup_factor:.1f}x")
        print(f"Items Detected:   {len(self.receipt.items) if self.receipt else 0}")
        print(f"Regions Processed: {m.regions_processed}")
    
    def manage_people(self):
        """Manage people for bill splitting"""
        print("\n" + "="*50)
        print("👥 PEOPLE MANAGEMENT")
        print("="*50)
        
        while True:
            print(f"\nCurrent people: {', '.join(self.people) if self.people else 'None'}")
            print("\n1. Add person")
            print("2. Quick add (Person 1-4)")
            print("3. Remove person")
            print("4. Clear all")
            print("5. Done")
            
            choice = input("\nChoice: ").strip()
            
            if choice == '1':
                name = input("Enter name: ").strip()
                if name and name not in self.people:
                    self.people.append(name)
                    print(f"✓ Added {name}")
            elif choice == '2':
                for i in range(1, 5):
                    name = f"Person {i}"
                    if name not in self.people:
                        self.people.append(name)
                print("✓ Added Person 1-4")
            elif choice == '3':
                if self.people:
                    for i, person in enumerate(self.people, 1):
                        print(f"{i}. {person}")
                    idx = input("Select person number to remove: ").strip()
                    try:
                        idx = int(idx) - 1
                        if 0 <= idx < len(self.people):
                            removed = self.people.pop(idx)
                            print(f"✓ Removed {removed}")
                    except:
                        print("Invalid selection")
            elif choice == '4':
                self.people.clear()
                print("✓ Cleared all people")
            elif choice == '5':
                break
    
    def assign_items(self):
        """Assign items to people"""
        if not self.receipt or not self.receipt.items:
            print("\n⚠ No receipt items to assign")
            return
        
        if not self.people:
            print("\n⚠ No people added yet")
            return
        
        print("\n" + "="*50)
        print("📝 ITEM ASSIGNMENT")
        print("="*50)
        
        for item in self.receipt.items:
            print(f"\n{item.name} - {item.price:.2f} {self.receipt.currency}")
            print(f"Assigned to: {', '.join(item.assigned_to) if item.assigned_to else 'None'}")
            
            print("\n1. Assign to everyone")
            print("2. Assign to specific people")
            print("3. Skip")
            
            choice = input("Choice: ").strip()
            
            if choice == '1':
                item.assigned_to = self.people.copy()
                print(f"✓ Assigned to everyone")
            elif choice == '2':
                for i, person in enumerate(self.people, 1):
                    print(f"{i}. {person}")
                selections = input("Enter person numbers (comma-separated): ").strip()
                try:
                    indices = [int(x.strip()) - 1 for x in selections.split(',')]
                    item.assigned_to = [self.people[i] for i in indices if 0 <= i < len(self.people)]
                    print(f"✓ Assigned to {', '.join(item.assigned_to)}")
                except:
                    print("Invalid selection")
    
    def calculate_settlements(self):
        """Calculate and display settlements"""
        if not self.receipt or not self.people:
            print("\n⚠ Need receipt and people to calculate settlements")
            return
        
        self.splitter = BillSplitter(self.receipt, self.people)
        
        unassigned = [item for item in self.receipt.items if not item.assigned_to]
        if unassigned:
            print(f"\n⚠ {len(unassigned)} items are unassigned. Splitting equally among all people.")
            self.splitter.assign_items_equally()
        
        settlements = self.splitter.optimize_settlements()
        
        print("\n" + "="*50)
        print("💸 OPTIMIZED SETTLEMENTS")
        print("="*50)
        
        if not settlements:
            print("\n🎉 Everyone paid equally - no settlements needed!")
        else:
            for s in settlements:
                print(f"{s.from_person:15} → {s.to_person:15} : {s.amount:7.2f} {s.currency}")
        
        print("\n" + "-"*50)
        print("📊 SUMMARY")
        print("-"*50)
        print(f"Total Amount:     {self.receipt.total:.2f} {self.receipt.currency}")
        print(f"Per Person:       {self.receipt.total / len(self.people):.2f} {self.receipt.currency}")
        print(f"Transactions:     {len(settlements)}")
        
        print("\n" + "-"*50)
        print("💰 INDIVIDUAL SHARES")
        print("-"*50)
        for person, amount in self.splitter.balances.items():
            print(f"{person:15} : {amount:7.2f} {self.receipt.currency}")
    
    def add_tip(self):
        """Add tip to receipt"""
        if not self.receipt:
            print("\n⚠ No receipt loaded")
            return
        
        try:
            tip = float(input("\nEnter tip amount: "))
            self.receipt.add_tip(tip)
            print(f"✓ Added tip: {tip:.2f} {self.receipt.currency}")
            print(f"New total: {self.receipt.total:.2f} {self.receipt.currency}")
        except:
            print("Invalid amount")
    
    def export_results(self):
        """Export complete results to JSON with all settlement details"""
        if not self.receipt:
            print("\n⚠ No receipt to export")
            return
        
        filename = f"groupify_receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Calculate settlements
        if not self.splitter and self.people:
            self.splitter = BillSplitter(self.receipt, self.people)
            if any(not item.assigned_to for item in self.receipt.items):
                self.splitter.assign_items_equally()
            self.splitter.calculate_balances()
            self.splitter.optimize_settlements()
        
        data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'version': '1.0',
                'currency': self.receipt.currency if self.receipt else 'BGN'
            },
            'receipt': {
                'items': [asdict(item) for item in self.receipt.items] if self.receipt.items else [],
                'total': self.receipt.total,
                'original_total': self.receipt.original_total,
                'tip_amount': self.receipt.tip_amount,
                'currency': self.receipt.currency
            },
            'people': self.people,
            'processing_metrics': asdict(self.processor.metrics) if hasattr(self.processor, 'metrics') else {},
        }
        
        if self.splitter:
            # Individual balances
            individual_balances = self.splitter.balances if hasattr(self.splitter, 'balances') else {}
            
            # Equal share calculation
            equal_share = self.receipt.total / len(self.people) if self.people else 0
            
            # Settlement transactions
            settlements = [asdict(s) for s in self.splitter.settlements] if hasattr(self.splitter, 'settlements') else []
            
            data['settlement_analysis'] = {
                'individual_shares': individual_balances,
                'equal_share_per_person': round(equal_share, 2),
                'total_amount': self.receipt.total,
                'settlements': settlements,
                'transactions_needed': len(settlements),
                'summary': {
                    'people_count': len(self.people),
                    'items_count': len(self.receipt.items),
                    'unassigned_items': len([item for item in self.receipt.items if not item.assigned_to]),
                    'assigned_items': len([item for item in self.receipt.items if item.assigned_to])
                }
            }
            
            person_breakdown = {}
            for person in self.people:
                person_items = []
                person_cost = 0
                
                for item in self.receipt.items:
                    if person in item.assigned_to:
                        share = item.price / len(item.assigned_to)
                        person_items.append({
                            'item_name': item.name,
                            'item_total_price': item.price,
                            'shared_with': len(item.assigned_to),
                            'person_share': round(share, 2)
                        })
                        person_cost += share
                
                # Add tip
                tip_share = self.receipt.tip_amount / len(self.people) if self.people else 0
                person_cost += tip_share
                
                person_breakdown[person] = {
                    'items': person_items,
                    'subtotal_from_items': round(person_cost - tip_share, 2),
                    'tip_share': round(tip_share, 2),
                    'total_consumed': round(person_cost, 2),
                    'equal_share_owed': round(equal_share, 2),
                    'difference': round(person_cost - equal_share, 2),
                    'status': 'creditor' if person_cost > equal_share + 0.01 else 'debtor' if person_cost < equal_share - 0.01 else 'balanced'
                }
            
            data['settlement_analysis']['detailed_breakdown'] = person_breakdown
            
            payment_instructions = []
            for settlement in settlements:
                payment_instructions.append({
                    'instruction': f"{settlement['from_person']} pays {settlement['to_person']} {settlement['amount']:.2f} {settlement['currency']}",
                    'from': settlement['from_person'],
                    'to': settlement['to_person'],
                    'amount': settlement['amount'],
                    'currency': settlement['currency']
                })
            
            data['settlement_analysis']['payment_instructions'] = payment_instructions
        
        # File
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Complete settlement data exported to {filename}")
            
            print(f"\nExported data includes:")
            print(f"  • Receipt with {len(self.receipt.items)} items")
            print(f"  • {len(self.people)} people")
            if self.splitter:
                settlements_count = len(self.splitter.settlements) if hasattr(self.splitter, 'settlements') else 0
                print(f"  • Individual consumption breakdown")
                print(f"  • {settlements_count} settlement transactions")
                print(f"  • Detailed payment instructions")
            print(f"  • Processing metrics")
            
        except Exception as e:
            print(f"\n❌ Export failed: {e}")
    
    def run(self):
        """Run the CLI application"""
        self.display_banner()
        
        while True:
            print("\n" + "="*50)
            print("MAIN MENU")
            print("="*50)
            print("1. Process receipt image")
            print("2. Manage people")
            print("3. Assign items to people")
            print("4. Add tip")
            print("5. Calculate settlements")
            print("6. Export results")
            print("7. Exit")
            
            choice = input("\nChoice: ").strip()
            
            if choice == '1':
                image_path = input("Enter image path: ").strip()
                if os.path.exists(image_path):
                    self.process_receipt(image_path)
                else:
                    print("⚠ File not found")
            elif choice == '2':
                self.manage_people()
            elif choice == '3':
                self.assign_items()
            elif choice == '4':
                self.add_tip()
            elif choice == '5':
                self.calculate_settlements()
            elif choice == '6':
                self.export_results()
            elif choice == '7':
                print("\n👋 Thank you for using Groupify!")
                break

# ==================== Main Entry Point ====================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Groupify - Smart Bill Splitter with Parallel OCR'
    )
    parser.add_argument(
        'image',
        nargs='?',
        help='Receipt image to process'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode - process and show results only'
    )
    
    args = parser.parse_args()
    
    if args.quick and args.image:
        processor = ParallelOCRProcessor(num_workers=args.workers)
        parser = ReceiptParser()
        
        print(f"Processing {args.image}...")
        ocr_text = processor.process_image_parallel(args.image)
        receipt = parser.parse(ocr_text)
        
        if receipt.items:
            print(f"\nFound {len(receipt.items)} items:")
            for item in receipt.items:
                print(f"  - {item.name}: {item.price:.2f}")
            print(f"\nTotal: {receipt.total:.2f}")
        else:
            print("No items found in receipt")
    else:
        cli = GroupifyCLI()
        if args.image and os.path.exists(args.image):
            cli.process_receipt(args.image)
        cli.run()

if __name__ == "__main__":
    main()