"""
Notification handling for management rules.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from core.models.api_models import Notification_API
from services.notification_service import NotificationService
from services.helpers.notification_builder_service import NotificationBuilderService
from repositories.supplier_repository import SupplierRepository
from communication.publisher import notify_invitation_to_role_received, notify_rule_to_role_received

from core.logging_config import get_logger

logger = get_logger(__name__)



class RuleNotification:
    """Notification handler for management rule operations"""
    
    def __init__(self):
        self.notification_service = NotificationService()
        self.notification_builder = NotificationBuilderService()
        self.supplier_repo = SupplierRepository()
    
    def create_invitation_notification(self, rule, destinations):
        """
        Create invitation notifications for a rule.

        Filters out None/invalid destinations up front. Raises if no valid
        destination remains — an invitation with no recipient is a bug, not
        a no-op.
        """
        valid = [d for d in destinations if isinstance(d, int) and d > 0]
        if not valid:
            raise ValueError(
                f"No valid destination users for rule {rule.id_management_rule}; "
                f"provider={rule.rule_provider_id} org={rule.rule_org_id}"
            )

        result: Optional[Notification_API] = None
        try:
            for user_id in valid:
                notification = self.notification_builder.create_invitation_notification(
                    rule_id=rule.id_management_rule,
                    role=rule.management_rule_code,
                    provider_id=rule.rule_provider_id,
                    organization_id=rule.rule_org_id,
                    destination_user=rule.rule_user_id,
                    invited_by=rule.rule_provider_id,  # still wrong; see earlier note
                    notify_user=user_id,
                )
                if rule.rule_user_id == user_id:
                    result = notification
                logger.info(
                    "Created invitation notification to user %s for rule %s",
                    user_id, rule.id_management_rule,
                )

            try:
                notify_invitation_to_role_received({
                    "rule_id": rule.id_management_rule,
                    "role": rule.management_rule_code,
                    "provider_id": rule.rule_provider_id,
                    "organization_id": rule.rule_org_id,
                    "destination_user": rule.rule_user_id,
                    "invited_by": rule.rule_provider_id,
                }, rule.rule_user_id)
            except Exception as e:
                logger.warning("Failed to send real-time notification: %s", e)

            return result
        except Exception as e:
            logger.exception("Failed to create invitation notification")
            raise
    
    def create_rule_update_notification(self, rule,destinations) -> None:
        """
        Create notification for rule update.
        
        Args:
            rule: Updated rule
        """
        try:
            notification_data = {
                "rule_id": rule.id_management_rule,
                "role": rule.management_rule_code,
                "rule_type": rule.management_rule_status,
                "user_id": rule.rule_user_id,
                "provider_id": rule.rule_provider_id,
                "organization_id": rule.rule_org_id,
                "invited_by": rule.rule_user_id,
                "notification_date": str(datetime.now())
            }
            for id in destinations:
                notification_api = Notification_API(
                    notification_code="role_updated",
                    notification_params=json.dumps(notification_data),
                    notification_user_ref=id,
                )
                
                self.notification_service.create_notification(notification_api)
                logger.info(f"Created rule update notification to user {id} for rule {rule.id_management_rule}")
            
                
        except Exception as e:
            logger.error(f"Failed to create rule update notification: {e}")
    
    def create_invitation_response_notification(self, rule, accepted: bool,destinations) -> None:
        """
        Create notification for invitation response.
        
        Args:
            rule: Rule being responded to
            accepted: Whether invitation was accepted
        """
        try:
            notification_code = "role_invitation_accepted" if accepted else "role_invitation_rejected"
            message = "accepted" if accepted else "rejected"
            
            notification_data = {
                "rule_id": rule.id_management_rule,
                "user_id": rule.rule_user_id,
                "organization_id": rule.rule_org_id,
                "provider_id": rule.rule_provider_id,
                "role": rule.management_rule_code,
                "status": rule.management_rule_status,
                "response_date": str(datetime.now())
            }

            for id in destinations:
            
                notification_api = Notification_API(
                    notification_code=notification_code,
                    notification_params=json.dumps(notification_data),
                    notification_user_ref=id,
                )
                
                self.notification_service.create_notification(notification_api)
                logger.info(f"Created invitation {message} notification for rule {rule.id_management_rule}")
            
                        
        except Exception as e:
            logger.error(f"Failed to create invitation response notification: {e}")