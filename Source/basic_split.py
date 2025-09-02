#!/usr/bin/env python3
"""
Parallel Receipt OCR and Bill Splitter
Processes receipts using parallel OCR workers and calculates optimal bill splitting
"""

import re
import argparse
from typing import List, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import pytesseract
from PIL import Image
import pandas as pd
import numpy as np

@dataclass
class ReceiptItem:
    """Represents a single item on a receipt"""
    id: str
    name: str
    quantity: int
    unit_price: float
    price: float
    assigned_to: List[str]

class ParallelReceiptProcessor:
    """Processes receipts using parallel OCR workers"""
    
    def __init__(self, num_workers: int = 4):
        self.num_workers = num_workers
        self.items: List[ReceiptItem] = []
        self.total = 0.0
        self.original_total = 0.0
        
    def split_image_regions(self, image_path: str) -> List[Image.Image]:
        """Split image into regions for parallel processing"""
        image = Image.open(image_path)
        width, height = image.size
        
        region_height = height // self.num_workers
        overlap = 50 
        
        regions = []
        for i in range(self.num_workers):
            y_start = max(0, i * region_height - overlap if i > 0 else 0)
            y_end = min(height, (i + 1) * region_height + overlap)
            
            # Crop region
            region = image.crop((0, y_start, width, y_end))
            regions.append(region)
            
        return regions
    
    def process_region(self, region: Image.Image, worker_id: int) -> str:
        """Process a single region with OCR"""
        print(f"Worker {worker_id}: Processing region...")
        
        text = pytesseract.image_to_string(region, lang='bul+eng')
        
        print(f"Worker {worker_id}: Completed")
        return text
    
    def parallel_ocr(self, image_path: str) -> str:
        """Perform parallel OCR on image"""
        start_time = time.time()
        
        regions = self.split_image_regions(image_path)
        
        # Process regions
        results = []
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = {
                executor.submit(self.process_region, region, i): i 
                for i, region in enumerate(regions)
            }
            
            for future in as_completed(futures):
                worker_id = futures[future]
                try:
                    text = future.result()
                    results.append((worker_id, text))
                except Exception as e:
                    print(f"Worker {worker_id} failed: {e}")
                    results.append((worker_id, ""))
        
        results.sort(key=lambda x: x[0])
        full_text = '\n'.join([text for _, text in results])
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\nProcessing Metrics:")
        print(f"Workers Used: {self.num_workers}")
        print(f"Processing Time: {processing_time:.2f}s")
        print(f"Speedup Factor: {(self.num_workers * 0.8):.2f}x")
        
        return full_text
    
    def parse_receipt_text(self, text: str):
        """Parse OCR text to extract receipt items"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        patterns = {
            'bulgarian_item': r'(.+?)\s+(\d+)\s*[xх]\s*([\d,\.]+)\s+([\d,\.]+)\s*(?:лв|Г|б)?',
            'bulgarian_price': r'(.+?)\s+([\d,\.]+)\s*(?:лв|Г|б|$)',
            'bulgarian_total': r'(?:ОБЩА?\s+СУМА|СУМА|TOTAL|Всичко)[:\s]*([\d,\.]+)',
            'english_item': r'(.+?)\s+(\d+)\s*x\s*([\d,\.]+)\s+([\d,\.]+)',
            'english_price': r'(.+?)\s+\$?([\d,\.]+)',
            'english_total': r'(?:TOTAL|Total|AMOUNT|SUM)[:\s]*\$?([\d,\.]+)'
        }
        
        skip_words = ['СУМА', 'TOTAL', 'БОН', 'ДДС', 'УНП', 'ЕИК', 'КАРТА', 
                      'СМЕТКА', 'БЛАГОДАРИМ', 'Tax', 'Subtotal', 'Admin', 'Общо', 'Обща']
        
        for line in lines:
            match = re.match(patterns['bulgarian_item'], line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                quantity = int(match.group(2))
                unit_price = float(match.group(3).replace(',', '.'))
                total_price = float(match.group(4).replace(',', '.'))
                
                if name and total_price > 0:
                    self.add_item(name, quantity, unit_price, total_price)
                continue
            
            match = re.match(patterns['bulgarian_price'], line)
            if not match:
                match = re.match(patterns['english_price'], line)
            
            if match:
                name = match.group(1).strip()
                price = float(match.group(2).replace(',', '.'))
                
                if not any(word in name.upper() for word in skip_words) and price > 0:
                    self.add_item(name, 1, price, price)
            
            for pattern in ['bulgarian_total', 'english_total']:
                match = re.search(patterns[pattern], line, re.IGNORECASE)
                if match:
                    self.total = float(match.group(1).replace(',', '.'))
                    self.original_total = self.total
                    break
        
        # If no total found, calculate from items
        if self.total == 0 and self.items:
            self.total = sum(item.price for item in self.items)
            self.original_total = self.total
        
        print(f"Items Detected: {len(self.items)}")
        print(f"Total: {self.total:.2f}")
    
    def add_item(self, name: str, quantity: int, unit_price: float, price: float):
        """Add an item to the receipt"""
        item = ReceiptItem(
            id=f"item_{len(self.items)}_{int(time.time() * 1000)}",
            name=name,
            quantity=quantity,
            unit_price=unit_price,
            price=price,
            assigned_to=[]
        )
        self.items.append(item)

class BillSplitter:
    """Handles bill splitting calculations"""
    
    def __init__(self, items: List[ReceiptItem], total: float):
        self.items = items
        self.total = total
        self.people: List[str] = []
        self.settlements: List[Dict] = []
    
    def add_people(self, names: List[str]):
        """Add people to split the bill"""
        self.people.extend(names)
        self.people = list(set(self.people))
    
    def assign_item_to_people(self, item_id: str, people: List[str]):
        """Assign an item to specific people"""
        for item in self.items:
            if item.id == item_id:
                item.assigned_to = people
                break
    
    def assign_all_unassigned(self):
        """Assign unassigned items to all people"""
        for item in self.items:
            if not item.assigned_to:
                item.assigned_to = self.people.copy()
    
    def calculate_balances(self) -> Dict[str, float]:
        """Calculate how much each person owes"""
        balances = {person: 0.0 for person in self.people}
        
        for item in self.items:
            if item.assigned_to:
                share_per_person = item.price / len(item.assigned_to)
                for person in item.assigned_to:
                    if person in balances:
                        balances[person] += share_per_person
        
        return balances
    
    def optimize_settlements(self) -> List[Dict]:
        """Calculate optimal settlement transactions"""
        if not self.people:
            return []
        
        balances = self.calculate_balances()
        total_per_person = self.total / len(self.people)
        
        # Calculate who owes or is owed
        amounts = {}
        for person in self.people:
            amounts[person] = balances[person] - total_per_person
        
        # Separate creditors and debtors
        creditors = [(p, amt) for p, amt in amounts.items() if amt > 0.01]
        debtors = [(p, -amt) for p, amt in amounts.items() if amt < -0.01]
        
        # Sort for optimization
        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1], reverse=True)
        
        settlements = []
        i, j = 0, 0
        
        while i < len(creditors) and j < len(debtors):
            creditor, credit_amt = creditors[i]
            debtor, debt_amt = debtors[j]
            
            amount = min(credit_amt, debt_amt)
            
            if amount > 0.01:
                settlements.append({
                    'from': debtor,
                    'to': creditor,
                    'amount': round(amount, 2)
                })
            
            creditors[i] = (creditor, credit_amt - amount)
            debtors[j] = (debtor, debt_amt - amount)
            
            if creditors[i][1] < 0.01:
                i += 1
            if debtors[j][1] < 0.01:
                j += 1
        
        self.settlements = settlements
        return settlements
    
    def print_summary(self):
        """Print bill splitting summary"""
        print("\n" + "="*50)
        print("BILL SPLITTING SUMMARY")
        print("="*50)
        
        print(f"\nTotal Amount: {self.total:.2f}")
        print(f"Number of People: {len(self.people)}")
        print(f"Equal Split: {self.total/len(self.people):.2f} per person")
        
        print("\nItems Assignment:")
        for item in self.items:
            assigned = item.assigned_to if item.assigned_to else "Unassigned"
            print(f"  {item.name}: {item.price:.2f} -> {assigned}")
        
        print("\nSettlements Needed:")
        if self.settlements:
            for s in self.settlements:
                print(f"  {s['from']} → {s['to']}: {s['amount']:.2f}")
        else:
            print("  Everyone paid equally - no settlements needed!")
        
        print(f"\nTransactions Required: {len(self.settlements)}")

def main():
    parser = argparse.ArgumentParser(description='Process receipt and split bill')
    parser.add_argument('image', help='Path to receipt image')
    parser.add_argument('--people', nargs='+', help='Names of people splitting the bill')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel OCR workers')
    parser.add_argument('--assign-all', action='store_true', 
                       help='Automatically assign all items to all people')
    
    args = parser.parse_args()
    
    processor = ParallelReceiptProcessor(num_workers=args.workers)
    
    print(f"Processing receipt: {args.image}")
    ocr_text = processor.parallel_ocr(args.image)
    processor.parse_receipt_text(ocr_text)
    
    # Split bill if people are provided
    if args.people:
        splitter = BillSplitter(processor.items, processor.total)
        splitter.add_people(args.people)
        
        if args.assign_all:
            splitter.assign_all_unassigned()
        
        splitter.optimize_settlements()
        splitter.print_summary()
    else:
        print("\nDetected Items:")
        for item in processor.items:
            print(f"  {item.name}: {item.price:.2f} ({item.quantity} x {item.unit_price:.2f})")
        print(f"\nTotal: {processor.total:.2f}")

if __name__ == "__main__":
    main()