# services/user_service.py
import json
import logging
import datetime
from typing import Optional

from features.auth_manager import AuthManager
from core.models.api_models import AppUser_API, Person_API, Location_API, AppUserUpdate_API
from core.exceptions.handler import (
    APIException,
    UserNotFoundException,
    # Add these specific exceptions to your core/exceptions.py
)
from core.models.models import AppUser, Subscription, Wallet
from repositories.user_repository import UserRepository
from repositories.person_repository import PersonRepository
from repositories.location_repository import LocationRepository
from services.person_service import PersonService

# Import from your new structure
from core.messages.error_codes import ErrorCode
from core.messages.http_status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_410_GONE,
    HTTP_417_EXPECTATION_FAILED
)

from core.logging_config import get_logger

from core.logging_config import get_logger

logger = get_logger(__name__)


class UserService:
    """Service for user-related business logic"""
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.person_repo = PersonRepository()
        self.location_repo = LocationRepository()
        self.person_service = PersonService()
        self.auth_manager = AuthManager()
    
    def get_all_users(self):
        """Get all users"""
        return self.user_repo.get_all()
    
    def get_user_by_id(self, user_id: int, full: bool = False):
        """Get user by ID with optional full details"""
        user = self.user_repo.get_by_id(user_id, eager_load=full)
        if not user:
            raise UserNotFoundException(user_id=user_id)
        return user
    
    def create_user_record(
        self,
        user_data: AppUser_API,
        person_data: Optional[Person_API] = None,
        location_data: Optional[Location_API] = None,
    ) -> AppUser:
        """Persist a new AppUser row plus its person/location, if any.

        Does not touch auth. Does not check uniqueness — the workflow
        checks that before calling. This method is purely the storage
        step.
        """
        now = datetime.datetime.now()
        app_user = AppUser(
            app_user_name=user_data.app_user_name,
            app_user_password="",
            app_user_preferences=json.dumps(user_data.app_user_preferences),
            app_user_email=user_data.app_user_email,
            app_user_image_url=user_data.app_user_image_url,
            app_user_type=user_data.app_user_type.value,
            app_user_last_active=str(now),
            app_user_last_updated=str(now),
            app_user_creation=str(now),
        )
        app_user.app_user_wallet = Wallet(
            wallet_balance= 0.00,wallet_status= 'active'
        )

        app_user.subscription = Subscription(
                    subscription_quota= 100,subscription_plan_id = 1
        )

        if person_data:
            existing_person = self.person_repo.get_person_by_id(person_data.id_person)
            if existing_person:
                app_user.app_user_person_id = existing_person.id_person
            else:
                app_user.app_user_person = self.person_service.generate_person_object(
                    person_data, location_data
                )

        try:
            return self.user_repo.create(app_user)
        except Exception as e:
            logger.error(f"Failed to insert AppUser: {e}")
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.USER_INSERT_FAILED,
                details={"error": str(e)},
            )


    def update_user_record_raw(self,user: AppUser):
        try:
            return self.user_repo.update(user)
        except Exception as e:
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.USER_UPDATE_FAILED,
                details={"user_id": user.id_app_user, "error": str(e)},
            )

    def update_user_record(
        self,
        user: AppUser,
        user_data: AppUser_API,
        person_id: int,
    ) -> AppUser:
        """Apply updates to an existing AppUser row.

        Caller supplies the resolved person id — the workflow is
        responsible for inserting or refreshing the person first.
        """
        updatable_fields = [
            "app_user_preferences",
            "app_user_last_active",
            "app_user_image_url",
            "app_user_email",
            "app_user_type",
        ]
        for field in updatable_fields:
            if hasattr(user_data, field):
                setattr(user, field, getattr(user_data, field))

        user.app_user_person_id = person_id
        user.app_user_last_updated = datetime.datetime.now()

        try:
            return self.user_repo.update(user)
        except Exception as e:
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.USER_UPDATE_FAILED,
                details={"user_id": user.id_app_user, "error": str(e)},
            )


    def delete_user_record(self, user: AppUser) -> bool:
        """Delete an AppUser row. Auth deletion is the workflow's job."""
        return self.user_repo.delete(user)
    
    def update_user(
        self,
        user_data: AppUser_API,
        person_data: Person_API,
        location_data: Location_API
    ):
        """Update user information"""
        
        user = self.get_user_by_id(user_data.id_app_user)
        
        # Update person information
        person = self.person_service.refresh_or_insert_person(person_data, location_data)
        
        
        # Update allowed fields
        updatable_fields = [
            "app_user_preferences",
            "app_user_last_active",
            "app_user_image_url",
            "app_user_email",
            "app_user_type",
        ]
        
        for field in updatable_fields:
            if hasattr(user_data, field):
                setattr(user, field, getattr(user_data, field))
        
        user.app_user_person_id = person.id_person
        user.app_user_last_updated = datetime.datetime.now()
        
        try:
            return self.user_repo.update(user)
        except Exception as e:
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.USER_UPDATE_FAILED,
                details={"user_id": user.id_app_user, "error": str(e)}
            )
    
    def update_user_password(self, user_record, hashed_password: str):
        """Update user's password hash"""
        user = self.get_user_by_id(user_record.id_app_user)
        user.app_user_password = hashed_password
        
        try:
            return self.user_repo.update(user)
        except Exception as e:
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.USER_UPDATE_FAILED,
                details={"user_id": user.id_app_user, "error": str(e)}
            )
    
    def update_user_image_url(self, user_record, image_url: str):
        """Update user's image URL"""
        user = self.get_user_by_id(user_record.id_app_user)
        user.app_user_image_url = image_url
        
        try:
            return self.user_repo.update(user)
        except Exception as e:
            raise APIException(
                status_code=HTTP_417_EXPECTATION_FAILED,
                error_code=ErrorCode.USER_UPDATE_FAILED,
                details={"user_id": user.id_app_user, "error": str(e)}
            )
    
    def delete_user(self, user_data: AppUser_API):
        """Delete a user"""
        user = self.get_user_by_id(user_data.id_app_user)
        return self.user_repo.delete(user)
    

    