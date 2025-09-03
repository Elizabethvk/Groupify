"""
CLI Interface module for Groupify
Command-line interface for receipt processing and bill splitting
"""

import json
from datetime import datetime
from dataclasses import asdict
from ocr_processor import ParallelOCRProcessor
from receipt_parser import ReceiptParser
from bill_splitter import BillSplitter
from utils import validate_image_path, try_parse_float, validate_menu_choice

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
        print("🍽️  GROUPIFY - Bill Splitter")
        print("Parallel Receipt Processing & Optimization")
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
            print("-"*50)
            choice = validate_menu_choice(choice, ['1','2','3','4','5']) or ''
            
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
        print("🔍 ITEM ASSIGNMENT")
        print("="*50)
        
        for item in self.receipt.items:
            print(f"\n{item.name} - {item.price:.2f} {self.receipt.currency}")
            print(f"Assigned to: {', '.join(item.assigned_to) if item.assigned_to else 'None'}")
            
            print("\n1. Assign to everyone")
            print("2. Assign to specific people")
            print("3. Skip")
            
            choice = input("Choice: ").strip()
            print("-"*50)
            choice = validate_menu_choice(choice, ['1','2','3']) or ''
            
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
            tip_input = input("\nEnter tip amount: ")
            tip_val = try_parse_float(tip_input)
            if tip_val is None or tip_val < 0:
                raise ValueError("Invalid tip")
            tip = tip_val
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
            individual_balances = self.splitter.balances if hasattr(self.splitter, 'balances') else {}
            
            equal_share = self.receipt.total / len(self.people) if self.people else 0
            
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
            
            # detailed breakdown
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
                
                # tip share
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
            
            # payment instructions
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
            print(f"\nExport failed: {e}")
    
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
                if validate_image_path(image_path):
                    self.process_receipt(image_path)
                else:
                    print("⚠ Invalid or unsupported image")
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