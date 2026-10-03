# services/notification_service.py
import json
import logging
import datetime
from typing import List, Optional, Dict, Any
from core.logging_config import get_logger
from core.models.api_models import Notification_API
from core.exceptions.specific.notification_exceptions import (
    NotificationException,
    NotificationNotFoundException,
    NotificationAlreadyExistsException,
    NotificationCreationFailedException,
    NotificationUpdateFailedException,
    NotificationDeleteFailedException,
    NotificationBulkOperationException,
    NotificationValidationException
)
from core.models.models import Notification
from repositories.notification_repository import NotificationRepository

from core.logging_config import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Service for notification-related business logic"""
    
    def __init__(self):
        self.notification_repo = NotificationRepository()
    
    def _parse_expiry(self, value: str | None) -> datetime.datetime | None:
        """
        Parse management_notification_expiry without external libraries.
        Returns datetime or None.
        """
        if not value or str(value).lower() == "null":
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S",      # ISO no timezone
            "%Y-%m-%d %H:%M:%S",      # "YYYY-MM-DD HH:MM:SS"
            "%Y-%m-%d",               # Date only
            "%Y/%m/%d %H:%M:%S",      # Slash format
            "%d/%m/%Y %H:%M:%S",      # 01/02/2025 10:20:30
            "%d/%m/%Y",               # 01/02/2025
        ]

        for fmt in formats:
            try:
                return datetime.datetime.strptime(value, fmt)
            except ValueError:
                continue

        return None
    
    def _build_notification_model(self, notification_data: Notification_API) -> Notification:
        """Convert API model to database model"""
        new_notification = Notification(
            notification_code=notification_data.notification_code,
            notification_params=notification_data.notification_params,
            notification_user_ref=notification_data.notification_user_ref,
        )
        
        # Set created at if not provided
        if not notification_data.notification_created_at:
            new_notification.notification_created_at = datetime.datetime.now()
        else:
            new_notification.notification_created_at = notification_data.notification_created_at
        
        # Set read at if provided
        if notification_data.notification_read_at:
            new_notification.notification_read_at = notification_data.notification_read_at
        
        return new_notification
    
    def _validate_notification_data(self, notification_data: Notification_API) -> None:
        """Validate notification data before creation"""
        errors = []
        
        if not notification_data.notification_code:
            errors.append("notification_code is required")
        
        if not notification_data.notification_user_ref or notification_data.notification_user_ref <= 0:
            errors.append("notification_user_ref must be a positive integer")
        
        if errors:
            raise NotificationValidationException(
                field="notification_data",
                value=notification_data.dict(),
                reason="; ".join(errors)
            )
    
    def create_notification(
        self, 
        notification_data: Notification_API
    ) -> Notification:
        """Create a new notification"""
        
        # Validate notification data
        self._validate_notification_data(notification_data)
        
        # Check if notification already exists
        if notification_data.id_notification and notification_data.id_notification > 0:
            existing = self.notification_repo.get_by_id(
                notification_data.id_notification
            )
            if existing:
                raise NotificationAlreadyExistsException(
                    notification_id=notification_data.id_notification
                )
        
        # Build notification model
        new_notification = self._build_notification_model(notification_data)
        
        try:
            return self.notification_repo.create(new_notification)
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            raise NotificationCreationFailedException(
                error=str(e),
                user_ref=notification_data.notification_user_ref,
                notification_code=notification_data.notification_code
            )
    
    def get_notification_by_id(self, notification_id: int) -> Notification:
        """Get notification by ID"""
        notification = self.notification_repo.get_by_id(notification_id)
        if not notification:
            raise NotificationNotFoundException(
                notification_id=notification_id
            )
        return notification
    
    def get_user_notifications(
        self, 
        user_ref: int, 
        offset: int = 0, 
        limit: int = 100
    ) -> List[Notification]:
        """Get all notifications for a user"""
        if user_ref <= 0:
            raise NotificationValidationException(
                field="user_ref",
                value=user_ref,
                reason="User reference must be a positive integer"
            )
        
        if offset < 0:
            raise NotificationValidationException(
                field="offset",
                value=offset,
                reason="Offset cannot be negative"
            )
        
        if limit < 1 or limit > 500:
            raise NotificationValidationException(
                field="limit",
                value=limit,
                reason="Limit must be between 1 and 500"
            )
        
        return self.notification_repo.get_by_user_ref(user_ref, offset, limit)
    
    def mark_notification_as_read(self, notification_id: int) -> Notification:
        """Mark a single notification as read"""
        notification = self.get_notification_by_id(notification_id)
        
        if notification.notification_read_at:
            # Already read, return as is
            return notification
        
        try:
            updated = self.notification_repo.mark_as_read(notification_id)
            if not updated:
                raise NotificationNotFoundException(
                    notification_id=notification_id
                )
            return updated
        except NotificationNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            raise NotificationUpdateFailedException(
                notification_id=notification_id,
                error=str(e),
                attempted_action="mark_as_read"
            )
    
    def mark_all_notifications_as_read(self, user_ref: int) -> int:
        """Mark all notifications for a user as read"""
        if user_ref <= 0:
            raise NotificationValidationException(
                field="user_ref",
                value=user_ref,
                reason="User reference must be a positive integer"
            )
        
        notifications = self.get_user_notifications(user_ref)
        unread_count = 0
        errors = []
        
        for notification in notifications:
            if not notification.notification_read_at:
                try:
                    self.mark_notification_as_read(notification.id_notification)
                    unread_count += 1
                except Exception as e:
                    errors.append({
                        "notification_id": notification.id_notification,
                        "error": str(e)
                    })
                    logger.warning(f"Failed to mark notification {notification.id_notification}: {e}")
        
        if errors and unread_count == 0:
            raise NotificationBulkOperationException(
                operation="mark_as_read",
                success_count=unread_count,
                failed_count=len(errors),
                errors=errors,
                user_ref=user_ref
            )
        
        return unread_count
    
    def delete_notification(self, notification_id: int) -> bool:
        """Delete a notification"""
        notification = self.get_notification_by_id(notification_id)
        
        try:
            return self.notification_repo.delete(notification_id)
        except Exception as e:
            logger.error(f"Failed to delete notification: {e}")
            raise NotificationDeleteFailedException(
                notification_id=notification_id,
                error=str(e)
            )
    
    def delete_all_user_notifications(self, user_ref: int) -> int:
        """Delete all notifications for a user"""
        if user_ref <= 0:
            raise NotificationValidationException(
                field="user_ref",
                value=user_ref,
                reason="User reference must be a positive integer"
            )
        
        notifications = self.get_user_notifications(user_ref)
        deleted_count = 0
        errors = []
        
        for notification in notifications:
            try:
                if self.notification_repo.delete(notification.id_notification):
                    deleted_count += 1
            except Exception as e:
                errors.append({
                    "notification_id": notification.id_notification,
                    "error": str(e)
                })
                logger.warning(f"Failed to delete notification {notification.id_notification}: {e}")
        
        if errors and deleted_count == 0:
            raise NotificationBulkOperationException(
                operation="delete",
                success_count=deleted_count,
                failed_count=len(errors),
                errors=errors,
                user_ref=user_ref
            )
        
        return deleted_count
    
    def get_unread_notification_count(self, user_ref: int) -> Dict[str, Any]:
        """Get count of unread notifications for a user"""
        if user_ref <= 0:
            raise NotificationValidationException(
                field="user_ref",
                value=user_ref,
                reason="User reference must be a positive integer"
            )
        
        count = self.notification_repo.get_unread_count(user_ref)
        
        return {
            "user_ref": user_ref,
            "unread_count": count,
            "has_unread": count > 0
        }
    
    def send_invitation_notification(
        self, 
        user_ref: int, 
        invitation_data: Dict[str, Any]
    ) -> Notification:
        """Send an invitation notification to a user"""
        
        if user_ref <= 0:
            raise NotificationValidationException(
                field="user_ref",
                value=user_ref,
                reason="User reference must be a positive integer"
            )
        
        if not invitation_data:
            raise NotificationValidationException(
                field="invitation_data",
                value=invitation_data,
                reason="Invitation data cannot be empty"
            )
        
        # Create notification
        notification_data = Notification_API(
            notification_code="role_invitation",
            notification_params=json.dumps(invitation_data),
            notification_user_ref=user_ref,
        )
        
        notification = self.create_notification(notification_data)
        
        
        return notification
    
    def bulk_create_notifications(
        self, 
        notifications_data: List[Notification_API]
    ) -> List[Notification]:
        """Create multiple notifications at once"""
        if not notifications_data:
            raise NotificationValidationException(
                field="notifications_data",
                value=notifications_data,
                reason="Notifications list cannot be empty"
            )
        
        if len(notifications_data) > 100:
            raise NotificationValidationException(
                field="notifications_data",
                value=len(notifications_data),
                reason="Cannot create more than 100 notifications at once"
            )
        
        created = []
        errors = []
        
        for idx, notification_data in enumerate(notifications_data):
            try:
                notification = self.create_notification(notification_data)
                created.append(notification)
            except Exception as e:
                errors.append({
                    "index": idx,
                    "data": notification_data.dict(),
                    "error": str(e)
                })
                logger.warning(f"Failed to create notification at index {idx}: {e}")
        
        if errors and not created:
            raise NotificationBulkOperationException(
                operation="create",
                success_count=len(created),
                failed_count=len(errors),
                errors=errors
            )
        
        return created