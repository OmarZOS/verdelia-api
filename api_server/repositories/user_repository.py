# repositories/user_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import joinedload, selectinload
from core.models.persistent_models import Location
from core.models.models import Address, AppUser,  Person, PersonDetails
import storage.storage_broker as storage_broker

class UserRepository:
    """Repository for User-related database operations"""
    
    def get_all(self) -> List[AppUser]:
        """Get all users"""
        return storage_broker.get(AppUser)
    
    def get_by_id(self, user_id: int, eager_load: bool = False) -> Optional[AppUser]:
        """Get user by ID with optional eager loading"""
        conditions = {AppUser.id_app_user: user_id}
        
        if eager_load:
            eager_load_depth = [
                {AppUser.subscription:[]},
                {AppUser.app_user_wallet:[]},
                {
                    AppUser.app_user_person: [

                        Person.person_blood_type,
                        
                        {Person.person_location: [
                            Location.location_address_id,
                            Location.location_name,
                            Location.position_wkt,
                            {Location.location_address:[Address.address_city,Address.address_country,Address.address_postal_code,Address.address_street,Address.address_street]},
                        ]},
                                            {
                        Person.person_details: [
                        ]
                    },
                    ]
                }
            ]
        else:
            eager_load_depth = [ {AppUser.app_user_person: []}]
        
        users = storage_broker.get(
            table=AppUser,

            conditions=conditions,
            join_tables=[],
            eager_load_depth=eager_load_depth,
            offset=0,
            limit=1
        )

        
        
        return users[0] if users else None
    
    def get_by_name(self, username: str) -> List[AppUser]:
        """Get user by username"""
        return storage_broker.get(table= AppUser, conditions={AppUser.app_user_name: username})
    
    def get_by_email(self, email: str) -> List[AppUser]:
        """Get user by email"""
        return storage_broker.get(AppUser, {AppUser.app_user_email: email})
    
    def create(self, user: AppUser) -> AppUser:
        """Create a new user"""
        from features.insertion import insert_or_complete_or_raise
        return insert_or_complete_or_raise(user)
    
    def update(self, user: AppUser) -> AppUser:
        """Update an existing user"""
        from features.insertion import update_record_in_api
        return update_record_in_api(user)
    
    def delete(self, user: AppUser) -> bool:
        """Delete a user"""
        from features.insertion import delete_record_from_api
        return delete_record_from_api(user)
    
