# models/finance_models.py

from decimal import ROUND_HALF_UP, Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ==================== Request Models ====================

class PaymentCreate(BaseModel):
    """Request model for creating a payment"""
    invoice_id: Optional[int] = Field(default=None, description="ID of the invoice to pay")
    amount: float = Field(..., description="Payment amount", gt=0)
    payment_method: str = Field(..., description="Payment method: card, cash, bank_transfer, etc.")
    user_id: int = Field(..., description="ID of the user making the payment", gt=0)
    notes: Optional[str] = Field(None, description="Additional notes")
    payment_type: Optional[str] = Field('payment', description="Type of payment: payment, deposit, etc.")


    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return float(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    
    @field_validator('payment_method')
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        valid_methods = ['card', 'cash', 'bank_transfer', 'mobile_money', 'crypto', 'wallet']
        if v not in valid_methods:
            raise ValueError(f'Payment method must be one of: {", ".join(valid_methods)}')
        return v
    
    @field_validator('payment_type')
    @classmethod
    def validate_payment_type(cls, v: str) -> str:
        valid_types = ['payment', 'deposit', 'advance', 'partial']
        if v not in valid_types:
            raise ValueError(f'Payment type must be one of: {", ".join(valid_types)}')
        return v


class PaymentConfirm(BaseModel):
    """Request model for confirming a payment"""
    transaction_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Transaction details from payment gateway"
    )


class PaymentRefund(BaseModel):
    """Request model for refunding a payment"""
    amount: float = Field(..., description="Amount to refund", gt=0)
    reason: str = Field(..., description="Reason for refund", min_length=1)
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Refund amount must be greater than 0')
        return v


class PaymentReject(BaseModel):
    """Request model for rejecting a payment"""
    reason: str = Field(..., description="Reason for rejection", min_length=1)


# ==================== Response Models ====================

class TransactionResponse(BaseModel):
    """Transaction details in response"""
    id: int
    wallet_id: int
    amount: float
    transaction_type: str
    status: str
    reference: Optional[str] = None
    created_at: Optional[datetime] = None


class PaymentResponse(BaseModel):
    """Response model for payment operations"""
    id: int
    invoice_id: int
    user_id: Optional[int] = None
    amount: float
    payment_method: str
    status: str
    payment_type: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    transactions: List[TransactionResponse] = []
    refunds: List[Dict[str, Any]] = []
    
    @property
    def is_pending(self) -> bool:
        return self.status == 'pending'
    
    @property
    def is_completed(self) -> bool:
        return self.status == 'completed'
    
    @property
    def is_refunded(self) -> bool:
        return self.status == 'refunded'


class InvoicePaymentSummary(BaseModel):
    """Summary of payments for an invoice"""
    invoice_id: int
    total_amount: float
    total_paid: float
    remaining_amount: float
    status: str
    payments: List[PaymentResponse] = []
    
    @property
    def is_fully_paid(self) -> bool:
        return self.remaining_amount <= 0 and self.status == 'paid'
    
    @property
    def payment_percentage(self) -> float:
        if self.total_amount == 0:
            return 0
        return (self.total_paid / self.total_amount) * 100


class DailyPaymentStats(BaseModel):
    """Daily payment statistics"""
    date: str
    total_payments: int
    total_amount: float
    average_amount: float = 0.0
    by_status: Dict[str, int] = {}
    by_method: Dict[str, int] = {}


# ==================== Error Models ====================

class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    detail: str = Field(..., description="Main error message")
    status_code: int = Field(..., description="HTTP status code")
    error_code: Optional[str] = Field(None, description="Application error code")
    errors: Optional[List[ErrorDetail]] = Field(None, description="Detailed error list")
    timestamp: str = Field(..., description="Timestamp of the error")
    path: Optional[str] = Field(None, description="Request path")