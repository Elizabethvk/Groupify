"""
Bill Splitter module for Groupify
Handles bill splitting calculations and optimizations
"""

from typing import List, Dict
from data_models import Receipt, Settlement
from decimal import Decimal, ROUND_HALF_UP
from constants import SETTLEMENT_EPSILON, DECIMAL_QUANTIZE


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
    
    def calculate_balances(self) -> Dict[str, Decimal]:
        """Calculate how much each person owes"""
        for person in self.people:
            self.balances[person] = Decimal("0.00")
        
        # item costs per person
        for item in self.receipt.items:
            if item.assigned_to:
                share_per_person = Decimal(str(item.price)) / Decimal(len(item.assigned_to))
                
                for person in item.assigned_to:
                    if person in self.balances:
                        self.balances[person] += share_per_person
        
        # tip proportionally
        if self.receipt.tip_amount > 0:
            tip_per_person = Decimal(str(self.receipt.tip_amount)) / Decimal(len(self.people))
            for person in self.people:
                self.balances[person] += tip_per_person
        
        for person in self.people:
            self.balances[person] = self.balances[person].quantize(DECIMAL_QUANTIZE, rounding=ROUND_HALF_UP)

        return self.balances
    
    def optimize_settlements(self) -> List[Settlement]:
        """Optimize settlements to minimize transactions"""
        if not self.balances:
            self.calculate_balances()
        
        # equal split of total
        equal_share = Decimal(str(self.receipt.total)) / Decimal(len(self.people))
        
        creditors = []
        debtors = []
        
        for person in self.people:
            difference = self.balances[person] - equal_share
            if difference > SETTLEMENT_EPSILON:
                creditors.append({'name': person, 'amount': difference})
            elif difference < -SETTLEMENT_EPSILON:
                debtors.append({'name': person, 'amount': -difference})
        
        creditors.sort(key=lambda x: x['amount'], reverse=True)
        debtors.sort(key=lambda x: x['amount'], reverse=True)
        
        settlements = []
        i, j = 0, 0
        
        while i < len(creditors) and j < len(debtors):
            amount = min(creditors[i]['amount'], debtors[j]['amount'])
            
            if amount > SETTLEMENT_EPSILON:
                settlements.append(Settlement(
                    from_person=debtors[j]['name'],
                    to_person=creditors[i]['name'],
                    amount=float(amount.quantize(DECIMAL_QUANTIZE, rounding=ROUND_HALF_UP)),
                    currency=self.receipt.currency
                ))
            
            creditors[i]['amount'] -= amount
            debtors[j]['amount'] -= amount
            
            if creditors[i]['amount'] < SETTLEMENT_EPSILON:
                i += 1
            if debtors[j]['amount'] < SETTLEMENT_EPSILON:
                j += 1
        
        self.settlements = settlements
        return settlements