
from typing import Optional, Dict, Any, List
from enum import Enum

from core.messages.error_codes import ErrorCode
from core.messages.error_messages import get_error_message
from core.messages.http_status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_402_PAYMENT_REQUIRED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_410_GONE,
    HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
    HTTP_417_EXPECTATION_FAILED,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_502_BAD_GATEWAY,
    HTTP_503_SERVICE_UNAVAILABLE,
    HTTP_504_GATEWAY_TIMEOUT,
    HTTP_511_NETWORK_AUTHENTICATION_REQUIRED
)
from core.exceptions.handler import APIException


# core/exceptions/specific/product_exceptions.py
"""
Product specific exceptions for product management, barcode search, and AI recognition.
"""

from core.exceptions.handler import APIException
from core.messages.error_codes import ErrorCode
from typing import Optional, Dict, Any, List


# core/exceptions/specific/order_exceptions.py
"""
Order specific exceptions for order management, items, and status transitions.
"""

from core.messages.error_codes import ErrorCode
from typing import Optional, Dict, Any, List


# ==================== Base Order Exception ====================

# core/exceptions/specific/financial_exceptions.py
"""
Financial specific exceptions for payments, deposits, fees, and invoices.
"""



# ==================== Base Financial Exception ====================

class FinancialException(APIException):
    """Base exception for all financial-related errors"""
    
    def __init__(
        self,
        message: str = "Financial service error",
        error_code: ErrorCode = ErrorCode.PAYMENT_FAILED,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details or {}
        )


# ==================== Payment Exceptions ====================

class PaymentException(FinancialException):
    """Base exception for payment-related errors"""
    
    def __init__(
        self,
        message: str = "Payment error",
        error_code: ErrorCode = ErrorCode.PAYMENT_FAILED,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details or {}
        )


class PaymentNotFoundException(PaymentException):
    """Exception when a payment is not found"""
    
    def __init__(
        self,
        payment_id: int = None,
        invoice_id: int = None,
        reference: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if payment_id:
            error_details["payment_id"] = payment_id
        if invoice_id:
            error_details["invoice_id"] = invoice_id
        if reference:
            error_details["reference"] = reference
        
        message = "Payment not found"
        if payment_id:
            message = f"Payment with ID '{payment_id}' not found"
        elif invoice_id:
            message = f"Payment for invoice ID '{invoice_id}' not found"
        elif reference:
            message = f"Payment with reference '{reference}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class PaymentCreationFailedException(PaymentException):
    """Exception when payment creation fails"""
    
    def __init__(
        self,
        error: str = None,
        payment_id: int = None,
        invoice_id: int = None,
        amount: float = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if error:
            error_details["creation_error"] = error
        if payment_id:
            error_details["payment_id"] = payment_id
        if invoice_id:
            error_details["invoice_id"] = invoice_id
        if amount is not None:
            error_details["amount"] = amount
        
        message = "Failed to create payment"
        if invoice_id:
            message = f"Failed to create payment for invoice '{invoice_id}'"
        elif payment_id:
            message = f"Failed to create payment with ID '{payment_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class PaymentUpdateFailedException(PaymentException):
    """Exception when payment update fails"""
    
    def __init__(
        self,
        payment_id: int = None,
        error: str = None,
        fields_attempted: List[str] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if payment_id:
            error_details["payment_id"] = payment_id
        if error:
            error_details["update_error"] = error
        if fields_attempted:
            error_details["fields_attempted"] = fields_attempted
        
        message = "Failed to update payment"
        if payment_id:
            message = f"Failed to update payment with ID '{payment_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class PaymentAlreadyExistsException(PaymentException):
    """Exception when a payment already exists for an invoice"""
    
    def __init__(
        self,
        invoice_id: int = None,
        payment_id: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if invoice_id:
            error_details["invoice_id"] = invoice_id
        if payment_id:
            error_details["existing_payment_id"] = payment_id
        
        message = "Payment already exists"
        if invoice_id:
            message = f"Payment already exists for invoice '{invoice_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_409_CONFLICT,
            details=error_details
        )


class PaymentStatusInvalidException(PaymentException):
    """Exception when payment status is invalid"""
    
    def __init__(
        self,
        payment_id: int = None,
        current_status: str = None,
        requested_status: str = None,
        allowed_statuses: List[str] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if payment_id:
            error_details["payment_id"] = payment_id
        if current_status:
            error_details["current_status"] = current_status
        if requested_status:
            error_details["requested_status"] = requested_status
        if allowed_statuses:
            error_details["allowed_statuses"] = allowed_statuses
        
        message = "Invalid payment status transition"
        if current_status and requested_status:
            message = f"Cannot change payment status from '{current_status}' to '{requested_status}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


# ==================== Deposit Exceptions ====================

class DepositException(FinancialException):
    """Base exception for deposit-related errors"""
    
    def __init__(
        self,
        message: str = "Deposit error",
        error_code: ErrorCode = ErrorCode.DEPOSIT_CREATION_FAILED,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details or {}
        )


class DepositNotFoundException(DepositException):
    """Exception when a deposit is not found"""
    
    def __init__(
        self,
        deposit_id: int = None,
        cart_id: int = None,
        reference: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if deposit_id:
            error_details["deposit_id"] = deposit_id
        if cart_id:
            error_details["cart_id"] = cart_id
        if reference:
            error_details["reference"] = reference
        
        message = "Deposit not found"
        if deposit_id:
            message = f"Deposit with ID '{deposit_id}' not found"
        elif cart_id:
            message = f"Deposit for cart ID '{cart_id}' not found"
        elif reference:
            message = f"Deposit with reference '{reference}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DEPOSIT_CREATION_FAILED,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class DepositCreationFailedException(DepositException):
    """Exception when deposit creation fails"""
    
    def __init__(
        self,
        error: str = None,
        deposit_id: int = None,
        cart_id: int = None,
        amount: float = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if error:
            error_details["creation_error"] = error
        if deposit_id:
            error_details["deposit_id"] = deposit_id
        if cart_id:
            error_details["cart_id"] = cart_id
        if amount is not None:
            error_details["amount"] = amount
        
        message = "Failed to create deposit"
        if cart_id:
            message = f"Failed to create deposit for cart '{cart_id}'"
        elif deposit_id:
            message = f"Failed to create deposit with ID '{deposit_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DEPOSIT_CREATION_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class DepositUpdateFailedException(DepositException):
    """Exception when deposit update fails"""
    
    def __init__(
        self,
        deposit_id: int = None,
        error: str = None,
        fields_attempted: List[str] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if deposit_id:
            error_details["deposit_id"] = deposit_id
        if error:
            error_details["update_error"] = error
        if fields_attempted:
            error_details["fields_attempted"] = fields_attempted
        
        message = "Failed to update deposit"
        if deposit_id:
            message = f"Failed to update deposit with ID '{deposit_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DEPOSIT_CREATION_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class DepositAlreadyExistsException(DepositException):
    """Exception when a deposit already exists for a cart"""
    
    def __init__(
        self,
        cart_id: int = None,
        deposit_id: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if deposit_id:
            error_details["existing_deposit_id"] = deposit_id
        
        message = "Deposit already exists"
        if cart_id:
            message = f"Deposit already exists for cart '{cart_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DEPOSIT_CREATION_FAILED,
            status_code=HTTP_409_CONFLICT,
            details=error_details
        )


# ==================== Fee Exceptions ====================

class FeeException(FinancialException):
    """Base exception for fee-related errors"""
    
    def __init__(
        self,
        message: str = "Fee error",
        error_code: ErrorCode = ErrorCode.PAYMENT_FAILED,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details or {}
        )


class FeeNotFoundException(FeeException):
    """Exception when a fee is not found"""
    
    def __init__(
        self,
        fee_id: int = None,
        provider_id: int = None,
        name: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if fee_id:
            error_details["fee_id"] = fee_id
        if provider_id:
            error_details["provider_id"] = provider_id
        if name:
            error_details["fee_name"] = name
        
        message = "Fee not found"
        if fee_id:
            message = f"Fee with ID '{fee_id}' not found"
        elif provider_id:
            message = f"Fee for provider ID '{provider_id}' not found"
        elif name:
            message = f"Fee '{name}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class FeeCreationFailedException(FeeException):
    """Exception when fee creation fails"""
    
    def __init__(
        self,
        error: str = None,
        fee_id: int = None,
        provider_id: int = None,
        name: str = None,
        amount: float = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if error:
            error_details["creation_error"] = error
        if fee_id:
            error_details["fee_id"] = fee_id
        if provider_id:
            error_details["provider_id"] = provider_id
        if name:
            error_details["fee_name"] = name
        if amount is not None:
            error_details["amount"] = amount
        
        message = "Failed to create fee"
        if name:
            message = f"Failed to create fee '{name}'"
        elif provider_id:
            message = f"Failed to create fee for provider '{provider_id}'"
        elif fee_id:
            message = f"Failed to create fee with ID '{fee_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class FeeUpdateFailedException(FeeException):
    """Exception when fee update fails"""
    
    def __init__(
        self,
        fee_id: int = None,
        error: str = None,
        fields_attempted: List[str] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if fee_id:
            error_details["fee_id"] = fee_id
        if error:
            error_details["update_error"] = error
        if fields_attempted:
            error_details["fields_attempted"] = fields_attempted
        
        message = "Failed to update fee"
        if fee_id:
            message = f"Failed to update fee with ID '{fee_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )



class PaymentNotConfirmedException(PaymentException):
    """
    Raised when the finance service returns a payment whose status is
    not a confirmed/completed/paid state.

    Used by `OrderWorkflow.process_payment` after `confirm_payment`
    returns: the payment exists, the remote call succeeded, but the
    status on the returned row is not one of the terminal-success
    statuses, so the workflow must not mark the invoice paid.
    """

    def __init__(
        self,
        payment_id: int = None,
        status: str = None,
        invoice_id: int = None,
        details: Dict[str, Any] = None,
    ):
        error_details = details or {}

        if payment_id:
            error_details["payment_id"] = payment_id
        if status is not None:
            error_details["status"] = status
        if invoice_id:
            error_details["invoice_id"] = invoice_id

        message = "Payment could not be confirmed"
        if payment_id and status is not None:
            message = (
                f"Payment '{payment_id}' was not confirmed "
                f"(status='{status}')"
            )
        elif payment_id:
            message = f"Payment '{payment_id}' was not confirmed"
        elif status is not None:
            message = f"Payment confirmation failed (status='{status}')"

        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_409_CONFLICT,
            details=error_details,
        )

        
class FeeAlreadyExistsException(FeeException):
    """Exception when a fee already exists for a provider"""
    
    def __init__(
        self,
        provider_id: int = None,
        fee_name: str = None,
        fee_id: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if provider_id:
            error_details["provider_id"] = provider_id
        if fee_name:
            error_details["fee_name"] = fee_name
        if fee_id:
            error_details["existing_fee_id"] = fee_id
        
        message = "Fee already exists"
        if provider_id and fee_name:
            message = f"Fee '{fee_name}' already exists for provider '{provider_id}'"
        elif fee_name:
            message = f"Fee '{fee_name}' already exists"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_409_CONFLICT,
            details=error_details
        )


class FeeAmountInvalidException(FeeException):
    """Exception when fee amount is invalid"""
    
    def __init__(
        self,
        fee_id: int = None,
        amount: float = None,
        reason: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if fee_id:
            error_details["fee_id"] = fee_id
        if amount is not None:
            error_details["amount"] = amount
        if reason:
            error_details["reason"] = reason
        
        message = "Invalid fee amount"
        if amount is not None and amount < 0:
            message = "Fee amount cannot be negative"
        elif reason:
            message = reason
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            details=error_details
        )


# ==================== Invoice Exceptions ====================

class InvoiceException(FinancialException):
    """Base exception for invoice-related errors"""
    
    def __init__(
        self,
        message: str = "Invoice error",
        error_code: ErrorCode = ErrorCode.PAYMENT_FAILED,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details or {}
        )


class InvoiceNotFoundException(InvoiceException):
    """Exception when an invoice is not found"""
    
    def __init__(
        self,
        invoice_id: int = None,
        invoice_reference: str = None,
        cart_id: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if invoice_id:
            error_details["invoice_id"] = invoice_id
        if invoice_reference:
            error_details["invoice_reference"] = invoice_reference
        if cart_id:
            error_details["cart_id"] = cart_id
        
        message = "Invoice not found"
        if invoice_id:
            message = f"Invoice with ID '{invoice_id}' not found"
        elif invoice_reference:
            message = f"Invoice number '{invoice_reference}' not found"
        elif cart_id:
            message = f"Invoice for cart ID '{cart_id}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class InvoiceCreationFailedException(InvoiceException):
    """Exception when invoice creation fails"""
    
    def __init__(
        self,
        error: str = None,
        invoice_id: int = None,
        cart_id: int = None,
        amount: float = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if error:
            error_details["creation_error"] = error
        if invoice_id:
            error_details["invoice_id"] = invoice_id
        if cart_id:
            error_details["cart_id"] = cart_id
        if amount is not None:
            error_details["amount"] = amount
        
        message = "Failed to create invoice"
        if cart_id:
            message = f"Failed to create invoice for cart '{cart_id}'"
        elif invoice_id:
            message = f"Failed to create invoice with ID '{invoice_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class InvoiceUpdateFailedException(InvoiceException):
    """Exception when invoice update fails"""
    
    def __init__(
        self,
        invoice_id: int = None,
        error: str = None,
        fields_attempted: List[str] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if invoice_id:
            error_details["invoice_id"] = invoice_id
        if error:
            error_details["update_error"] = error
        if fields_attempted:
            error_details["fields_attempted"] = fields_attempted
        
        message = "Failed to update invoice"
        if invoice_id:
            message = f"Failed to update invoice with ID '{invoice_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class InvoiceAlreadyPaidException(InvoiceException):
    """Exception when trying to modify a paid invoice"""
    
    def __init__(
        self,
        invoice_id: int = None,
        invoice_reference: str = None,
        action: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if invoice_id:
            error_details["invoice_id"] = invoice_id
        if invoice_reference:
            error_details["invoice_reference"] = invoice_reference
        if action:
            error_details["attempted_action"] = action
        
        message = "Cannot modify paid invoice"
        if invoice_id:
            message = f"Invoice '{invoice_id}' has already been paid and cannot be modified"
        elif invoice_reference:
            message = f"Invoice '{invoice_reference}' has already been paid and cannot be modified"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


class InvoiceStatusInvalidException(InvoiceException):
    """Exception when invoice status is invalid"""
    
    def __init__(
        self,
        invoice_id: int = None,
        current_status: str = None,
        requested_status: str = None,
        allowed_statuses: List[str] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if invoice_id:
            error_details["invoice_id"] = invoice_id
        if current_status:
            error_details["current_status"] = current_status
        if requested_status:
            error_details["requested_status"] = requested_status
        if allowed_statuses:
            error_details["allowed_statuses"] = allowed_statuses
        
        message = "Invalid invoice status transition"
        if current_status and requested_status:
            message = f"Cannot change invoice status from '{current_status}' to '{requested_status}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


# ==================== Receipt Exceptions ====================

class ReceiptException(FinancialException):
    """Base exception for receipt-related errors"""
    
    def __init__(
        self,
        message: str = "Receipt error",
        error_code: ErrorCode = ErrorCode.PAYMENT_FAILED,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details or {}
        )


class ReceiptNotFoundException(ReceiptException):
    """Exception when a receipt is not found"""
    
    def __init__(
        self,
        receipt_id: int = None,
        payment_id: int = None,
        receipt_number: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if receipt_id:
            error_details["receipt_id"] = receipt_id
        if payment_id:
            error_details["payment_id"] = payment_id
        if receipt_number:
            error_details["receipt_number"] = receipt_number
        
        message = "Receipt not found"
        if receipt_id:
            message = f"Receipt with ID '{receipt_id}' not found"
        elif payment_id:
            message = f"Receipt for payment '{payment_id}' not found"
        elif receipt_number:
            message = f"Receipt number '{receipt_number}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class ReceiptCreationFailedException(ReceiptException):
    """Exception when receipt creation fails"""
    
    def __init__(
        self,
        error: str = None,
        receipt_id: int = None,
        payment_id: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if error:
            error_details["creation_error"] = error
        if receipt_id:
            error_details["receipt_id"] = receipt_id
        if payment_id:
            error_details["payment_id"] = payment_id
        
        message = "Failed to create receipt"
        if payment_id:
            message = f"Failed to create receipt for payment '{payment_id}'"
        elif receipt_id:
            message = f"Failed to create receipt with ID '{receipt_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class FinancialItemNotFoundException(FinancialException):
    """Exception when financial items are not found"""
    
    def __init__(
        self,
        supplier_id: int = None,
        person_id: int = None,
        client_id: int = None,
        seller_id: int = None,
        cart_id: int = None,
        order_id: int = None,
        deposit_id: int = None,
        invoice_id: int = None,
        payment_id: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        # Track which filters were provided
        filters = {}
        if supplier_id:
            filters["supplier_id"] = supplier_id
            error_details["supplier_id"] = supplier_id
        if person_id:
            filters["person_id"] = person_id
            error_details["person_id"] = person_id
        if client_id:
            filters["client_id"] = client_id
            error_details["client_id"] = client_id
        if seller_id:
            filters["seller_id"] = seller_id
            error_details["seller_id"] = seller_id
        if cart_id:
            filters["cart_id"] = cart_id
            error_details["cart_id"] = cart_id
        if order_id:
            filters["order_id"] = order_id
            error_details["order_id"] = order_id
        if deposit_id:
            filters["deposit_id"] = deposit_id
            error_details["deposit_id"] = deposit_id
        if invoice_id:
            filters["invoice_id"] = invoice_id
            error_details["invoice_id"] = invoice_id
        if payment_id:
            filters["payment_id"] = payment_id
            error_details["payment_id"] = payment_id
        
        # Build message based on provided filters
        message = "Financial items not found"
        
        if payment_id:
            message = f"Payment with ID '{payment_id}' not found"
        elif invoice_id:
            message = f"Invoice with ID '{invoice_id}' not found"
        elif deposit_id:
            message = f"Deposit with ID '{deposit_id}' not found"
        elif cart_id:
            message = f"No financial items found for cart ID '{cart_id}'"
        elif order_id:
            message = f"No financial items found for order ID '{order_id}'"
        elif supplier_id:
            message = f"No financial items found for supplier ID '{supplier_id}'"
        elif client_id:
            message = f"No financial items found for client ID '{client_id}'"
        elif seller_id:
            message = f"No financial items found for seller ID '{seller_id}'"
        elif person_id:
            message = f"No financial items found for person ID '{person_id}'"
        elif filters:
            filter_str = ", ".join([f"{k}={v}" for k, v in filters.items()])
            message = f"No financial items found with filters: {filter_str}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.FINANCIAL_ITEM_NOT_FOUND,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )

class FinanceClientError(Exception):
    """
    Base class for every finance-client failure.

    Attributes:
        action:  Human label for the operation that failed, e.g.
                 "create payment" or "confirm payment 42".
        status:  HTTP status code returned by the finance server,
                 or None when the failure was at the transport
                 layer (DNS, TCP, timeout) and no response
                 arrived.
        detail:  The finance server's own error message, when it
                 sent one. Falls back to a generic string.
        error_code: Optional application error code, mirroring
                 `ErrorCode` from the finance server when it's
                 present in the response body. Nullable.
    """

    def __init__(
        self,
        action: str = "finance request",
        status: Optional[int] = None,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.action = action
        self.status = status
        self.detail = detail or "unknown error"
        self.error_code = error_code
        self.details = details or {}

        # Build a readable default message. Subclasses may override
        # it but the base already carries enough context for a log.
        if status is not None:
            super().__init__(
                f"{action} failed (HTTP {status}): {self.detail}"
            )
        else:
            super().__init__(f"{action} failed: {self.detail}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialise for structured logging."""
        return {
            "error_type": type(self).__name__,
            "action": self.action,
            "status": self.status,
            "detail": self.detail,
            "error_code": self.error_code,
            **({"details": self.details} if self.details else {}),
        }


# ==================== Subclasses ====================

class FinanceValidationError(FinanceClientError):
    """
    400 / 422 — the finance server rejected the payload.

    The client sent a well-formed request but the server considered
    the values invalid: a non-positive amount, a missing required
    field, a malformed reference.

    Maps to HTTP 422 (or 400) at the boundary.
    """

    def __init__(
        self,
        action: str = "finance request",
        status: int = 422,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            action=action,
            status=status,
            detail=detail or "The finance server rejected the request",
            error_code=error_code,
            details=details,
        )


class FinanceNotFoundError(FinanceClientError):
    """
    404 — the referenced entity doesn't exist on the finance side.

    Most often: an invoice referenced by `PaymentCreate` that the
    finance service has never seen, or a payment id that has no row.
    """

    def __init__(
        self,
        action: str = "finance request",
        status: int = 404,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            action=action,
            status=status,
            detail=detail or "The referenced resource was not found",
            error_code=error_code,
            details=details,
        )


class FinanceConflictError(FinanceClientError):
    """
    409 — the finance server rejected the operation because of the
    current state of the resource.

    The classic case is confirming a payment that has already been
    confirmed, or creating a payment for an invoice that is already
    marked `paid`. The request was well-formed and the resource
    existed; the operation just doesn't apply in that state.
    """

    def __init__(
        self,
        action: str = "finance request",
        status: int = 409,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            action=action,
            status=status,
            detail=detail or "The operation conflicts with current state",
            error_code=error_code,
            details=details,
        )


class FinanceServerError(FinanceClientError):
    """
    5xx — the finance server faulted; the client's request was fine.

    Distinct from `FinanceUnavailableError` because the server did
    respond. A 5xx carries the server's own error message in
    `detail`, which is often the only clue about what went wrong.
    """

    def __init__(
        self,
        action: str = "finance request",
        status: int = 500,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            action=action,
            status=status,
            detail=detail or "The finance server returned an error",
            error_code=error_code,
            details=details,
        )


class FinanceUnavailableError(FinanceClientError):
    """
    Transport-level failure — no HTTP response was received.

    DNS resolution failed, the TCP connection was refused, the
    request timed out, or TLS negotiation failed. `status` is
    always None because there was no status code to record.

    The distinction from `FinanceServerError` matters: a 5xx means
    the server is running but broken; an unavailable error means
    we couldn't reach it at all. The retry policy is different
    (backoff vs. fix-the-server).
    """

    def __init__(
        self,
        action: str = "finance request",
        status: Optional[int] = None,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            action=action,
            status=status,
            detail=detail or "The finance service is unreachable",
            error_code=error_code,
            details=details,
        )

    def __init_subclass__(cls, **kwargs):
        # Prevent accidental subclassing that would silently drop
        # the transport-only semantics.
        raise TypeError(
            "FinanceUnavailableError is terminal; subclassing would "
            "lose the 'no HTTP response' guarantee."
        )