import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.logging_config import get_logger
from core.models.api_models import Notification_API
from core.models.models import Notification
from services.notification_service import NotificationService

from core.logging_config import get_logger

logger = get_logger(__name__)



class NotificationBuilderService:
    """Builder pattern for creating different types of notifications"""
    
    def __init__(self):
        self.notification_service = NotificationService()
    


    def dump_notification(self, notification: Notification) -> Dict[str, Any]:
        """
        Convert a Notification model instance to a dictionary.
        
        This method serializes a Notification object into a dictionary format
        suitable for JSON serialization or API responses.
        
        Args:
            notification: Notification model instance to convert
            
        Returns:
            Dictionary containing all notification fields with proper formatting
        """
        if not notification:
            return {}
        
        result = {
            "id_notification": notification.id_notification,
            "notification_code": notification.notification_code,
            "notification_user_ref": notification.notification_user_ref,
        }
        
        # Handle notification_params (already stored as string, keep as is or parse)
        if notification.notification_params:
            # Try to parse as JSON, fallback to raw string
            try:
                result["notification_params"] = json.loads(notification.notification_params)
            except (json.JSONDecodeError, TypeError):
                result["notification_params"] = notification.notification_params
        else:
            result["notification_params"] = {}
        
        # Handle datetime fields (convert to ISO format strings)
        if notification.notification_created_at:
            result["notification_created_at"] = notification.notification_created_at.isoformat()
        else:
            result["notification_created_at"] = None
        
        if notification.notification_read_at:
            result["notification_read_at"] = notification.notification_read_at.isoformat()
        else:
            result["notification_read_at"] = None
        
        return result


    def dump_notification_list(self, notifications: List[Notification]) -> List[Dict[str, Any]]:
        """
        Convert a list of Notification model instances to a list of dictionaries.
        
        Args:
            notifications: List of Notification model instances to convert
            
        Returns:
            List of dictionaries containing notification fields
        """
        return [self.dump_notification(notification) for notification in notifications]


    def build_invitation_notification(
        self,
        rule_id: int = 0,
        role: int = 0,
        provider_id: int = 0,
        organization_id: int = 0,
        destination_user: int = 0,
        invited_by: int = 0
    ) -> Notification_API:
        """Build an invitation notification"""
        return Notification_API(
            notification_code="role_invitation",
            notification_params=json.dumps({
                "rule_id": rule_id,
                "role": role,
                "provider_id": provider_id,
                "organization_id": organization_id,
                "destination_user": destination_user,
                "invited_by": invited_by,
                "invitation_date": str(datetime.now())
            }),
            notification_user_ref=destination_user
        )
    
    def build_system_alert_notification(
        self,
        user_ref: int,
        alert_type: str,
        message: str
    ) -> Notification_API:
        """Build a system alert notification"""
        return Notification_API(
            notification_code="SYSTEM_ALERT",
            notification_params=json.dumps({
                "alert_type": alert_type,
                "message": message,
                "timestamp": str(datetime.now())
            }),
            notification_user_ref=user_ref
        )
    
    def build_reminder_notification(
        self,
        user_ref: int,
        reminder_type: str,
        due_date: str
    ) -> Notification_API:
        """Build a reminder notification"""
        return Notification_API(
            notification_code="REMINDER",
            notification_params=json.dumps({
                "reminder_type": reminder_type,
                "due_date": due_date,
                "created_at": str(datetime.now())
            }),
            notification_user_ref=user_ref
        )
    
    def create_invitation_notification(
        self,
        rule_id: int = 0,
        role: int = 0,
        provider_id: int = 0,
        organization_id: int = 0,
        destination_user: int = 0,
        invited_by: int = 0,
        notify_user: int = 0
    ) -> Notification:
        """Create and send an invitation notification"""
        # Build the notification API object
        notification_api = self.build_invitation_notification(
            rule_id=rule_id,
            role=role,
            provider_id=provider_id,
            organization_id=organization_id,
            destination_user=destination_user,
            invited_by=invited_by
        )
        
        # Use the notification service's send_invitation_notification method
        invitation_data = json.loads(notification_api.notification_params)
        
        notification = self.notification_service.send_invitation_notification(
            user_ref=notify_user,
            invitation_data=invitation_data
        )
        
        logger.info(f"Created invitation notification to user {notify_user} for rule {rule_id}")
        
        return notification
    
    def create_and_send_system_alert(
        self,
        user_ref: int,
        alert_type: str,
        message: str
    ) -> Notification:
        """Create and send a system alert notification"""
        notification_api = self.build_system_alert_notification(user_ref, alert_type, message)
        
        # Use the service's create_notification method
        notification = self.notification_service.create_notification(notification_api)
        
        logger.info(f"Created system alert notification for user {user_ref}")
        
        return notification
    
    def create_and_send_reminder(
        self,
        user_ref: int,
        reminder_type: str,
        due_date: str
    ) -> Notification:
        """Create and send a reminder notification"""
        notification_api = self.build_reminder_notification(user_ref, reminder_type, due_date)
        
        # Use the service's create_notification method
        notification = self.notification_service.create_notification(notification_api)
        
        logger.info(f"Created reminder notification for user {user_ref}")
        
        return notification
    
    def create_and_send_bulk_invitations(
        self,
        invitations: list[Dict[str, Any]]
    ) -> list[Notification]:
        """Create and send multiple invitations at once"""
        notifications_data = []
        
        for inv in invitations:
            notification_api = self.build_invitation_notification(
                rule_id=inv.get("rule_id", 0),
                role=inv.get("role", 0),
                provider_id=inv.get("provider_id", 0),
                organization_id=inv.get("organization_id", 0),
                destination_user=inv.get("destination_user", 0),
                invited_by=inv.get("invited_by", 0)
            )
            notifications_data.append(notification_api)
        
        # Use the service's bulk_create_notifications method
        notifications = self.notification_service.bulk_create_notifications(notifications_data)
        
        logger.info(f"Created {len(notifications)} bulk invitation notifications")
        
        return notifications