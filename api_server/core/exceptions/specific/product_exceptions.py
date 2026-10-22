
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


# ==================== Base Product Exception ====================

class ProductException(APIException):
    """Base exception for all product-related errors"""
    
    def __init__(
        self,
        message: str = "Product service error",
        error_code: ErrorCode = ErrorCode.PRODUCT_NOT_EXISTS,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details or {}
        )


# ==================== Product Exceptions ====================

class ProductNotFoundException(ProductException):
    """Exception when a product is not found"""
    
    def __init__(
        self,
        product_id: int = None,
        product_name: str = None,
        barcode: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if product_id:
            error_details["product_id"] = product_id
        if product_name:
            error_details["product_name"] = product_name
        if barcode:
            error_details["barcode"] = barcode
        
        message = "Product not found"
        if product_id:
            message = f"Product with ID '{product_id}' not found"
        elif product_name:
            message = f"Product '{product_name}' not found"
        elif barcode:
            message = f"Product with barcode '{barcode}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_NOT_EXISTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class ProductAlreadyExistsException(ProductException):
    """Exception when trying to create a duplicate product"""
    
    def __init__(
        self,
        product_id: int = None,
        product_name: str = None,
        barcode: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if product_id:
            error_details["product_id"] = product_id
        if product_name:
            error_details["product_name"] = product_name
        if barcode:
            error_details["barcode"] = barcode
        
        message = "Product already exists"
        if product_id:
            message = f"Product with ID '{product_id}' already exists"
        elif product_name:
            message = f"Product '{product_name}' already exists"
        elif barcode:
            message = f"Product with barcode '{barcode}' already exists"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_ALREADY_EXISTS,
            status_code=HTTP_409_CONFLICT,
            details=error_details
        )


class ProductInsertFailedException(ProductException):
    """Exception when product insertion fails"""
    
    def __init__(
        self,
        error: str = None,
        product_id: int = None,
        product_name: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if error:
            error_details["insert_error"] = error
        if product_id:
            error_details["product_id"] = product_id
        if product_name:
            error_details["product_name"] = product_name
        
        message = "Failed to create product"
        if product_name:
            message = f"Failed to create product '{product_name}'"
        elif product_id:
            message = f"Failed to create product with ID '{product_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_INSERT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class ProductUpdateFailedException(ProductException):
    """Exception when product update fails"""
    
    def __init__(
        self,
        product_id: int = None,
        error: str = None,
        fields_attempted: List[str] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if product_id:
            error_details["product_id"] = product_id
        if error:
            error_details["update_error"] = error
        if fields_attempted:
            error_details["fields_attempted"] = fields_attempted
        
        message = "Failed to update product"
        if product_id:
            message = f"Failed to update product with ID '{product_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_UPDATE_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class ProductDeleteFailedException(ProductException):
    """Exception when product deletion fails"""
    
    def __init__(
        self,
        product_id: int = None,
        error: str = None,
        has_dependencies: bool = False,
        has_orders: bool = False,
        has_cart_items: bool = False,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if product_id:
            error_details["product_id"] = product_id
        if error:
            error_details["delete_error"] = error
        if has_dependencies:
            error_details["has_dependencies"] = has_dependencies
        if has_orders:
            error_details["has_orders"] = has_orders
        if has_cart_items:
            error_details["has_cart_items"] = has_cart_items
        
        message = "Failed to delete product"
        if product_id:
            message = f"Failed to delete product with ID '{product_id}'"
        
        reasons = []
        if has_orders:
            reasons.append("has existing orders")
        if has_cart_items:
            reasons.append("is in active carts")
        if reasons:
            message += f" - Product {', '.join(reasons)}. Use force_delete=true to delete anyway."
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_DELETE_FAILED,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


class ProductFetchNotFoundException(ProductException):
    """Exception when product fetch returns no results"""
    
    def __init__(
        self,
        identifier: str = None,
        search_type: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if identifier:
            error_details["identifier"] = identifier
        if search_type:
            error_details["search_type"] = search_type
        
        message = "Unable to retrieve product information"
        if search_type == "barcode":
            message = f"Product with barcode '{identifier}' not found"
        elif search_type == "barcode_ai":
            message = f"Product with barcode '{identifier}' not found in database or AI"
        elif search_type == "image_recognition":
            message = "Unable to recognize product from image"
        elif search_type == "barcode_database":
            message = f"Product with barcode '{identifier}' not found in database"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_FETCH_NOT_FOUND,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class ProductQuantityNotEnoughException(ProductException):
    """Exception when product quantity is insufficient"""
    available=0
    requested= 0
    def __init__(
        self,
        product_id: int = None,
        product_name: str = None,
        requested_quantity: int = None,
        available_quantity: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if product_id:
            self.product_id = product_id
            error_details["product_id"] = product_id
        if product_name:
            error_details["product_name"] = product_name
        if requested_quantity:
            self.requested = requested_quantity
            error_details["requested_quantity"] = requested_quantity
        if available_quantity:
            self.available = available_quantity
            error_details["available_quantity"] = available_quantity
        
        message = "Insufficient product quantity"
        if product_name:
            message = f"Insufficient stock for '{product_name}'. Requested: {requested_quantity}, Available: {available_quantity}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_QUANTITY_NOT_ENOUGH,
            status_code=HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            details=error_details
        )


class ProductQuantityRestoreFailedException(ProductException):
    """Exception when restoring product quantity fails"""
    
    def __init__(
        self,
        product_id: int = None,
        quantity_to_restore: int = None,
        error: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if product_id:
            error_details["product_id"] = product_id
        if quantity_to_restore:
            error_details["quantity_to_restore"] = quantity_to_restore
        if error:
            error_details["restore_error"] = error
        
        message = "Failed to restore product quantity"
        if product_id:
            message = f"Failed to restore quantity for product ID '{product_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_QUANTITY_RESTORE_FAILED,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


# ==================== Product Category Exceptions ====================

class ProductCategoryException(ProductException):
    """Base exception for product category errors"""
    
    def __init__(
        self,
        message: str = "Product category error",
        error_code: ErrorCode = ErrorCode.PRODUCT_CATEGORY_NOT_EXISTS,
        status_code: int = HTTP_404_NOT_FOUND,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details or {}
        )


class ProductCategoryNotFoundException(ProductCategoryException):
    """Exception when a product category is not found"""
    
    def __init__(
        self,
        category_id: int = None,
        category_name: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if category_id:
            error_details["category_id"] = category_id
        if category_name:
            error_details["category_name"] = category_name
        
        message = "Product category not found"
        if category_id:
            message = f"Product category with ID '{category_id}' not found"
        elif category_name:
            message = f"Product category '{category_name}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_CATEGORY_NOT_EXISTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class ProductCategoryAlreadyExistsException(ProductCategoryException):
    """Exception when trying to create a duplicate category"""
    
    def __init__(
        self,
        category_name: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if category_name:
            error_details["category_name"] = category_name
        
        message = "Product category already exists"
        if category_name:
            message = f"Product category '{category_name}' already exists"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_ALREADY_EXISTS,
            status_code=HTTP_409_CONFLICT,
            details=error_details
        )


class ProductCategoryInsertFailedException(ProductCategoryException):
    """Exception when category insertion fails"""
    
    def __init__(
        self,
        error: str = None,
        category_name: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if error:
            error_details["insert_error"] = error
        if category_name:
            error_details["category_name"] = category_name
        
        message = "Failed to create product category"
        if category_name:
            message = f"Failed to create product category '{category_name}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_INSERT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


# ==================== Product Image Exceptions ====================

class ProductImageException(ProductException):
    """Base exception for product image errors"""
    
    def __init__(
        self,
        message: str = "Product image error",
        error_code: ErrorCode = ErrorCode.PRODUCT_IMAGE_NOT_FOUND,
        status_code: int = HTTP_404_NOT_FOUND,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details or {}
        )


class ProductImageNotFoundException(ProductImageException):
    """Exception when a product image is not found"""
    
    def __init__(
        self,
        image_id: int = None,
        product_id: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if image_id:
            error_details["image_id"] = image_id
        if product_id:
            error_details["product_id"] = product_id
        
        message = "Product image not found"
        if image_id:
            message = f"Product image with ID '{image_id}' not found"
        elif product_id:
            message = f"Image for product '{product_id}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_IMAGE_NOT_FOUND,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class ProductImageInsertFailedException(ProductImageException):
    """Exception when product image insertion fails"""
    
    def __init__(
        self,
        error: str = None,
        product_id: int = None,
        image_url: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if error:
            error_details["insert_error"] = error
        if product_id:
            error_details["product_id"] = product_id
        if image_url:
            error_details["image_url"] = image_url[:100]  # Truncate long URLs
        
        message = "Failed to upload product image"
        if product_id:
            message = f"Failed to upload image for product '{product_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.IMAGE_INSERT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class ProductImageUpdateFailedException(ProductImageException):
    """Exception when product image update fails"""
    
    def __init__(
        self,
        image_id: int = None,
        error: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if image_id:
            error_details["image_id"] = image_id
        if error:
            error_details["update_error"] = error
        
        message = "Failed to update product image"
        if image_id:
            message = f"Failed to update product image with ID '{image_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.IMAGE_UPDATE_FAILED,
            status_code=HTTP_409_CONFLICT,
            details=error_details
        )


class ProductImageDeleteFailedException(ProductImageException):
    """Exception when product image deletion fails"""
    
    def __init__(
        self,
        image_id: int = None,
        error: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if image_id:
            error_details["image_id"] = image_id
        if error:
            error_details["delete_error"] = error
        
        message = "Failed to delete product image"
        if image_id:
            message = f"Failed to delete product image with ID '{image_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.IMAGE_INSERT_FAILED,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


# ==================== Product Search Exceptions ====================

class ProductSearchException(ProductException):
    """Exception for product search errors"""
    
    def __init__(
        self,
        message: str = "Product search failed",
        search_term: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if search_term:
            error_details["search_term"] = search_term
        
        message = "Product search failed"
        if search_term:
            message = f"Product search failed for term '{search_term}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_SEARCH_NOT_FOUND,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


# ==================== IProduct Exceptions ====================

class IProductException(ProductException):
    """Base exception for IProduct errors"""
    
    def __init__(
        self,
        message: str = "IProduct service error",
        error_code: ErrorCode = ErrorCode.PRODUCT_NOT_EXISTS,
        status_code: int = HTTP_404_NOT_FOUND,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details or {}
        )


class IProductNotFoundException(IProductException):
    """Exception when an IProduct is not found"""
    
    def __init__(
        self,
        iproduct_id: int = None,
        barcode: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if iproduct_id:
            error_details["iproduct_id"] = iproduct_id
        if barcode:
            error_details["barcode"] = barcode
        
        message = "IProduct not found"
        if iproduct_id:
            message = f"IProduct with ID '{iproduct_id}' not found"
        elif barcode:
            message = f"IProduct with barcode '{barcode}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_NOT_EXISTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class IProductInsertFailedException(IProductException):
    """Exception when IProduct insertion fails"""
    
    def __init__(
        self,
        error: str = None,
        barcode: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if error:
            error_details["insert_error"] = error
        if barcode:
            error_details["barcode"] = barcode
        
        message = "Failed to create IProduct"
        if barcode:
            message = f"Failed to create IProduct for barcode '{barcode}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_INSERT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


# ==================== Supplier Product Exceptions ====================

class ProductSupplierNotFoundException(ProductException):
    """Exception when product supplier is not found"""
    
    def __init__(
        self,
        supplier_id: int = None,
        product_id: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if supplier_id:
            error_details["supplier_id"] = supplier_id
        if product_id:
            error_details["product_id"] = product_id
        
        message = "Product supplier not found"
        if supplier_id and product_id:
            message = f"Supplier '{supplier_id}' not found for product '{product_id}'"
        elif supplier_id:
            message = f"Supplier with ID '{supplier_id}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_SUPPLIER_NOT_EXISTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class ProductSupplierAlreadyExistsException(ProductException):
    """Exception when product supplier already exists"""
    
    def __init__(
        self,
        supplier_id: int = None,
        product_id: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if supplier_id:
            error_details["supplier_id"] = supplier_id
        if product_id:
            error_details["product_id"] = product_id
        
        message = "Product supplier association already exists"
        if supplier_id and product_id:
            message = f"Supplier '{supplier_id}' is already associated with product '{product_id}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.PRODUCT_SUPPLIER_ALREADY_EXISTS,
            status_code=HTTP_409_CONFLICT,
            details=error_details
        )


# ==================== Validation Exceptions ====================

class ProductValidationException(ProductException):
    """Exception for product data validation errors"""
    
    def __init__(
        self,
        message: str = "Product validation failed",
        errors: Dict[str, List[str]] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if errors:
            error_details["validation_errors"] = errors
        
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            details=error_details
        )


class ProductPriceInvalidException(ProductValidationException):
    """Exception when product price is invalid"""
    
    def __init__(
        self,
        product_id: int = None,
        price: float = None,
        reason: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if product_id:
            error_details["product_id"] = product_id
        if price is not None:
            error_details["price"] = price
        if reason:
            error_details["reason"] = reason
        
        message = "Invalid product price"
        if price is not None and price < 0:
            message = "Product price cannot be negative"
        elif reason:
            message = reason
        
        super().__init__(
            message=message,
            errors={"price": [message]},
            details=error_details
        )


class ProductQuantityInvalidException(ProductValidationException):
    """Exception when product quantity is invalid"""
    
    def __init__(
        self,
        product_id: int = None,
        quantity: int = None,
        reason: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if product_id:
            error_details["product_id"] = product_id
        if quantity is not None:
            error_details["quantity"] = quantity
        if reason:
            error_details["reason"] = reason
        
        message = "Invalid product quantity"
        if quantity is not None and quantity < 0:
            message = "Product quantity cannot be negative"
        elif reason:
            message = reason
        
        super().__init__(
            message=message,
            errors={"quantity": [message]},
            details=error_details
        )