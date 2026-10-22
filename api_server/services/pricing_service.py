# services/pricing_service.py
from typing import Optional

class PricingService:
    """Service for price calculations"""
    
    @staticmethod
    def calculate_base_cost(purchase_price: float, logistics_costs: float) -> float:
        """Calculate base cost"""
        return purchase_price + logistics_costs
    
    @staticmethod
    def apply_margin_or_markup(
        subtotal: float,
        margin_rate: Optional[float] = None,
        markup_amount: Optional[float] = None
    ) -> float:
        """Apply broker's margin or markup"""
        if margin_rate:
            return subtotal * (1 + margin_rate)
        elif markup_amount:
            return subtotal + markup_amount
        return subtotal
    
    @staticmethod
    def apply_vat(subtotal: float, vat_rate: float) -> float:
        """Apply VAT to subtotal"""
        return subtotal * (1 + vat_rate)
    
    @staticmethod
    def add_additional_fees(
        subtotal: float,
        customs_duties: float = 0,
        brokerage_fees: float = 0
    ) -> float:
        """Add customs duties and brokerage fees"""
        return subtotal + customs_duties + brokerage_fees
    
    @staticmethod
    def add_overheads(
        subtotal: float,
        operational_costs: float = 0,
        finance_costs: float = 0
    ) -> float:
        """Add operational and finance overheads"""
        return subtotal + operational_costs + finance_costs
    
    @staticmethod
    def apply_discount(subtotal: float, discount: float = 0) -> float:
        """Apply discount to subtotal"""
        return subtotal - discount
    
    @staticmethod
    def add_currency_fluctuation(subtotal: float, buffer_percentage: float) -> float:
        """Add currency fluctuation buffer"""
        return subtotal * (1 + buffer_percentage)
    
    @classmethod
    def calculate_final_price(
        cls,
        purchase_price: float,
        logistics_costs: float,
        margin_rate: Optional[float] = None,
        markup_amount: Optional[float] = None,
        vat_rate: float = 0,
        customs_duties: float = 0,
        brokerage_fees: float = 0,
        operational_costs: float = 0,
        finance_costs: float = 0,
        discount: float = 0,
        currency_buffer: float = 0
    ) -> float:
        """
        Calculate final price using hierarchical calculation
        
        Steps:
        1. Base cost = purchase_price + logistics_costs
        2. Apply margin or markup
        3. Apply VAT
        4. Add additional fees
        5. Add overhead costs
        6. Apply discounts
        7. Add currency fluctuation buffer
        """
        # Step 1: Calculate base cost
        subtotal = cls.calculate_base_cost(purchase_price, logistics_costs)
        
        # Step 2: Apply broker's margin or markup
        subtotal = cls.apply_margin_or_markup(subtotal, margin_rate, markup_amount)
        
        # Step 3: Apply VAT
        subtotal = cls.apply_vat(subtotal, vat_rate)
        
        # Step 4: Add additional fees
        subtotal = cls.add_additional_fees(subtotal, customs_duties, brokerage_fees)
        
        # Step 5: Add overhead costs
        subtotal = cls.add_overheads(subtotal, operational_costs, finance_costs)
        
        # Step 6: Apply discounts
        subtotal = cls.apply_discount(subtotal, discount)
        
        # Step 7: Add currency fluctuation buffer
        final_price = cls.add_currency_fluctuation(subtotal, currency_buffer)
        
        return final_price
    
    @classmethod
    def calculate_order_total(
        cls,
        items: list,
        order_discount: float = 0,
        shipping_cost: float = 0
    ) -> float:
        """Calculate total price for an order"""
        subtotal = sum(
            item.ordered_quantity * item.unit_price * (1 + item.vat_rate)
            for item in items
        )
        
        subtotal += shipping_cost
        subtotal -= order_discount
        
        return max(0, subtotal)