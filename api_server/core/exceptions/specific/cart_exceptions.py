
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

class CartServiceException(APIException):
    """Base exception for cart service errors"""
    
    def __init__(
        self,
        message: str = "Cart service error",
        error_code: ErrorCode = ErrorCode.CART_NOT_EXISTS,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: dict = None
    ):
        super().__init__(
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details or {}
        )


class CartNotFoundException(CartServiceException):
    """Exception when a cart is not found"""
    
    def __init__(
        self,
        cart_id: int = None,
        user_id: int = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if user_id:
            error_details["user_id"] = user_id
        
        message = "Cart not found"
        if cart_id:
            message = f"Cart with ID '{cart_id}' not found"
        elif user_id:
            message = f"No carts found for user ID '{user_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CART_NOT_EXISTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class CartCreationFailedException(CartServiceException):
    """Exception when cart creation fails"""
    
    def __init__(
        self,
        error: str = None,
        provider_id: int = None,
        seller_id: int = None,
        buyer_id: int = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if error:
            error_details["creation_error"] = error
        if provider_id:
            error_details["provider_id"] = provider_id
        if seller_id:
            error_details["seller_id"] = seller_id
        if buyer_id:
            error_details["buyer_id"] = buyer_id
        
        message = "Failed to create cart"
        if provider_id and seller_id:
            message = f"Failed to create cart for provider {provider_id} and seller {seller_id}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CART_INSERT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class CartUpdateFailedException(CartServiceException):
    """Exception when cart update fails"""
    
    def __init__(
        self,
        cart_id: int = None,
        error: str = None,
        fields_attempted: list = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if error:
            error_details["update_error"] = error
        if fields_attempted:
            error_details["fields_attempted"] = fields_attempted
        
        message = "Failed to update cart"
        if cart_id:
            message = f"Failed to update cart with ID '{cart_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CART_INSERT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class CartDeleteFailedException(CartServiceException):
    """Exception when cart deletion fails"""
    
    def __init__(
        self,
        cart_id: int = None,
        error: str = None,
        has_items: bool = False,
        has_services: bool = False,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if error:
            error_details["delete_error"] = error
        if has_items:
            error_details["has_items"] = has_items
        if has_services:
            error_details["has_services"] = has_services
        
        message = "Failed to delete cart"
        if cart_id:
            message = f"Failed to delete cart with ID '{cart_id}'"
        
        if has_items or has_services:
            message += " - Cart has existing items or services"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CART_INSERT_FAILED,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


class CartFilterRequiredException(CartServiceException):
    """Exception when no filter is provided for cart listing"""
    
    def __init__(
        self,
        details: dict = None
    ):
        error_details = details or {}
        
        message = "At least one filter is required to list carts"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


class CartInvalidStatusException(CartServiceException):
    """Exception for invalid cart status transitions"""
    
    def __init__(
        self,
        cart_id: int = None,
        current_status: str = None,
        requested_status: str = None,
        allowed_statuses: list = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if current_status:
            error_details["current_status"] = current_status
        if requested_status:
            error_details["requested_status"] = requested_status
        if allowed_statuses:
            error_details["allowed_statuses"] = allowed_statuses
        
        message = "Invalid cart status transition"
        if current_status and requested_status:
            message = f"Cannot change cart status from '{current_status}' to '{requested_status}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_ORDER_STATUS,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )


class CartItemNotFoundException(CartServiceException):
    """Exception when cart items are not found"""
    
    def __init__(
        self,
        cart_id: int = None,
        item_id: int = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if item_id:
            error_details["item_id"] = item_id
        
        message = "Cart items not found"
        if cart_id:
            message = f"Items for cart ID '{cart_id}' not found"
        elif item_id:
            message = f"Cart item with ID '{item_id}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.CART_NOT_EXISTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class CartServiceNotFoundException(CartServiceException):
    """Exception when cart services are not found"""
    
    def __init__(
        self,
        cart_id: int = None,
        service_id: int = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if service_id:
            error_details["service_id"] = service_id
        
        message = "Cart services not found"
        if cart_id:
            message = f"Services for cart ID '{cart_id}' not found"
        elif service_id:
            message = f"Service with ID '{service_id}' not found in cart"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SERVICE_NOT_FOUND,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class CartPaymentRequiredException(CartServiceException):
    """Exception when payment is required but not provided"""
    
    def __init__(
        self,
        cart_id: int = None,
        amount_due: float = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if amount_due:
            error_details["amount_due"] = amount_due
        
        message = "Payment required to complete cart"
        if amount_due:
            message = f"Payment of {amount_due} required to complete cart"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_402_PAYMENT_REQUIRED,
            details=error_details
        )


class CartSupplierNotFoundException(CartServiceException):
    """Exception when supplier/provider is not found for cart"""
    
    def __init__(
        self,
        provider_id: int = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if provider_id:
            error_details["provider_id"] = provider_id
        
        message = "Supplier not found"
        if provider_id:
            message = f"Supplier with ID '{provider_id}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.SUPPLIER_NOT_EXISTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class CartSellerNotFoundException(CartServiceException):
    """Exception when seller user is not found for cart"""
    
    def __init__(
        self,
        seller_id: int = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if seller_id:
            error_details["seller_id"] = seller_id
        
        message = "Seller not found"
        if seller_id:
            message = f"Seller with ID '{seller_id}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.APPUSER_NOT_EXISTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class CartBuyerNotFoundException(CartServiceException):
    """Exception when buyer user is not found for cart"""
    
    def __init__(
        self,
        buyer_id: int = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if buyer_id:
            error_details["buyer_id"] = buyer_id
        
        message = "Buyer not found"
        if buyer_id:
            message = f"Buyer with ID '{buyer_id}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.APPUSER_NOT_EXISTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class CartProductNotFoundException(CartServiceException):
    """Exception when a product in cart is not found"""
    
    def __init__(
        self,
        product_id: int = None,
        product_name: str = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if product_id:
            error_details["product_id"] = product_id
        if product_name:
            error_details["product_name"] = product_name
        
        message = f"Product {product_id} not found in cart"
        if product_id:
            message = f"Product with ID '{product_id}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_NOT_EXISTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class CartStockRollbackException(CartServiceException):
    """Exception when rolling back product stock fails"""
    
    def __init__(
        self,
        cart_id: int = None,
        product_id: int = None,
        error: str = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if product_id:
            error_details["product_id"] = product_id
        if error:
            error_details["rollback_error"] = error
        
        message = "Failed to rollback product stock"
        if cart_id:
            message = f"Failed to rollback stock for cart {cart_id}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_QUANTITY_RESTORE_FAILED,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


class CartInvoiceCreationException(CartServiceException):
    """Exception when creating invoice for cart fails"""
    
    def __init__(
        self,
        cart_id: int = None,
        error: str = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if error:
            error_details["invoice_error"] = error
        
        message = "Failed to create invoice for cart"
        if cart_id:
            message = f"Failed to create invoice for cart {cart_id}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.INVOICE_CREATION_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class CartPaymentCreationException(CartServiceException):
    """Exception when creating payment for cart fails"""
    
    def __init__(
        self,
        cart_id: int = None,
        amount: float = None,
        error: str = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if amount:
            error_details["amount"] = amount
        if error:
            error_details["payment_error"] = error
        
        message = "Failed to create payment for cart"
        if cart_id:
            message = f"Failed to create payment for cart {cart_id}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PAYMENT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class CartReceiptCreationException(CartServiceException):
    """Exception when creating receipt for cart fails"""
    
    def __init__(
        self,
        cart_id: int = None,
        payment_id: int = None,
        error: str = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if payment_id:
            error_details["payment_id"] = payment_id
        if error:
            error_details["receipt_error"] = error
        
        message = "Failed to create receipt for cart"
        if cart_id:
            message = f"Failed to create receipt for cart {cart_id}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.RECEIPT_CREATION_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class CartDepositCreationException(CartServiceException):
    """Exception when creating deposit for cart fails"""
    
    def __init__(
        self,
        cart_id: int = None,
        amount: float = None,
        error: str = None,
        details: dict = None
    ):
        error_details = details or {}
        
        if cart_id:
            error_details["cart_id"] = cart_id
        if amount:
            error_details["amount"] = amount
        if error:
            error_details["deposit_error"] = error
        
        message = "Failed to create deposit for cart"
        if cart_id:
            message = f"Failed to create deposit for cart {cart_id}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DEPOSIT_CREATION_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )



class CartInsufficientStockException(CartServiceException):
    """Stock is not available to confirm/reserve for a cart."""
    def __init__(
        self,
        cart_id: int = None,
        product_id: int = None,
        requested: int = None,
        available: int = None,
        detail: str = None,
        details: dict = None,
    ):
        error_details = details or {}
        if cart_id: error_details["cart_id"] = cart_id
        if product_id: error_details["product_id"] = product_id
        if requested is not None: error_details["requested"] = requested
        if available is not None: error_details["available"] = available
        if detail: error_details["inventory_detail"] = detail

        message = "Insufficient stock to confirm cart"
        if product_id is not None:
            message = f"Insufficient stock for product {product_id}"
        if requested is not None and available is not None:
            message += f" (requested {requested}, available {available})"

        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_QUANTITY_INSUFFICIENT,  # add this code
            status_code=HTTP_409_CONFLICT,
            details=error_details,
        )