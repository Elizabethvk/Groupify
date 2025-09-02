"""
Data models for Groupify - Receipt processing and bill splitting
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


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