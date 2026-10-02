# core/exceptions/specific/notification_exceptions.py
"""
Notification-specific exceptions for the Verdelia system.
"""

from typing import Optional, Dict, Any, List
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_417_EXPECTATION_FAILED,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR
)
from core.exceptions.handler import APIException


# ==================== Base Notification Exception ====================

class NotificationException(APIException):
    """Base exception for all notification-related errors"""
    
    def __init__(
        self,
        message: str = "Notification service error",
        error_code: ErrorCode = ErrorCode.NOTIFICATION_ERROR,
        status_code: int = HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        super().__init__(
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details or {}
        )


# ==================== Notification Exceptions ====================

class NotificationNotFoundException(NotificationException):
    """Exception when a notification is not found"""
    
    def __init__(
        self,
        notification_id: int = None,
        user_ref: int = None,
        notification_code: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if notification_id:
            error_details["notification_id"] = notification_id
        if user_ref:
            error_details["user_ref"] = user_ref
        if notification_code:
            error_details["notification_code"] = notification_code
        
        message = "Notification not found"
        if notification_id:
            message = f"Notification with ID '{notification_id}' not found"
        elif user_ref:
            message = f"No notifications found for user '{user_ref}'"
        elif notification_code:
            message = f"Notification with code '{notification_code}' not found"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.NOTIFICATION_NOT_EXISTS,
            status_code=HTTP_404_NOT_FOUND,
            details=error_details
        )


class NotificationAlreadyExistsException(NotificationException):
    """Exception when a notification already exists"""
    
    def __init__(
        self,
        notification_id: int = None,
        notification_code: str = None,
        user_ref: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if notification_id:
            error_details["notification_id"] = notification_id
        if notification_code:
            error_details["notification_code"] = notification_code
        if user_ref:
            error_details["user_ref"] = user_ref
        
        message = "Notification already exists"
        if notification_id:
            message = f"Notification with ID '{notification_id}' already exists"
        elif notification_code and user_ref:
            message = f"Notification with code '{notification_code}' already exists for user '{user_ref}'"
        elif notification_code:
            message = f"Notification with code '{notification_code}' already exists"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.NOTIFICATION_ALREADY_EXISTS,
            status_code=HTTP_409_CONFLICT,
            details=error_details
        )


class NotificationCreationFailedException(NotificationException):
    """Exception when notification creation fails"""
    
    def __init__(
        self,
        error: str = None,
        user_ref: int = None,
        notification_code: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if error:
            error_details["creation_error"] = error
        if user_ref:
            error_details["user_ref"] = user_ref
        if notification_code:
            error_details["notification_code"] = notification_code
        
        message = "Failed to create notification"
        if user_ref:
            message = f"Failed to create notification for user '{user_ref}'"
        if notification_code:
            message = f"Failed to create notification with code '{notification_code}'"
        if error:
            message += f": {error}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.NOTIFICATION_INSERT_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class NotificationUpdateFailedException(NotificationException):
    """Exception when notification update fails"""
    
    def __init__(
        self,
        notification_id: int = None,
        error: str = None,
        attempted_action: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if notification_id:
            error_details["notification_id"] = notification_id
        if error:
            error_details["update_error"] = error
        if attempted_action:
            error_details["attempted_action"] = attempted_action
        
        message = "Failed to update notification"
        if notification_id:
            message = f"Failed to update notification with ID '{notification_id}'"
        if attempted_action:
            message = f"Failed to {attempted_action} notification"
        if error:
            message += f": {error}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.NOTIFICATION_UPDATE_FAILED,
            status_code=HTTP_417_EXPECTATION_FAILED,
            details=error_details
        )


class NotificationDeleteFailedException(NotificationException):
    """Exception when notification deletion fails"""
    
    def __init__(
        self,
        notification_id: int = None,
        user_ref: int = None,
        error: str = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if notification_id:
            error_details["notification_id"] = notification_id
        if user_ref:
            error_details["user_ref"] = user_ref
        if error:
            error_details["delete_error"] = error
        
        message = "Failed to delete notification"
        if notification_id:
            message = f"Failed to delete notification with ID '{notification_id}'"
        elif user_ref:
            message = f"Failed to delete notifications for user '{user_ref}'"
        if error:
            message += f": {error}"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.NOTIFICATION_DELETE_FAILED,
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            details=error_details
        )


class NotificationValidationException(NotificationException):
    """Exception when notification data validation fails"""
    
    def __init__(
        self,
        field: str = None,
        value: Any = None,
        reason: str = None,
        validation_errors: Dict[str, List[str]] = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["provided_value"] = value
        if reason:
            error_details["reason"] = reason
        if validation_errors:
            error_details["validation_errors"] = validation_errors
        
        message = "Notification validation failed"
        if field and reason:
            message = f"Validation failed for field '{field}': {reason}"
        elif reason:
            message = reason
        elif field:
            message = f"Validation failed for field '{field}'"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.NOTIFICATION_VALIDATION_FAILED,
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            details=error_details
        )


# ==================== Bulk Notification Exceptions ====================

class NotificationBulkOperationException(NotificationException):
    """Exception for bulk notification operations"""
    
    def __init__(
        self,
        operation: str,
        success_count: int = None,
        failed_count: int = None,
        errors: List[Dict[str, Any]] = None,
        user_ref: int = None,
        details: Dict[str, Any] = None
    ):
        error_details = details or {}
        
        error_details["operation"] = operation
        if success_count is not None:
            error_details["success_count"] = success_count
        if failed_count is not None:
            error_details["failed_count"] = failed_count
        if errors:
            error_details["errors"] = errors
        if user_ref:
            error_details["user_ref"] = user_ref
        
        message = f"Bulk notification {operation} failed"
        if success_count is not None and failed_count is not None:
            message = f"Bulk notification {operation} completed with {success_count} successes and {failed_count} failures"
        elif operation:
            message = f"Bulk notification {operation} operation failed"
        
        super().__init__(
            message=message,
            error_code=ErrorCode.NOTIFICATION_BULK_INSERT_FAILED,
            status_code=HTTP_400_BAD_REQUEST,
            details=error_details
        )