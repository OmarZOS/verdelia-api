# services/person_service.py
"""
Service for person-related operations including person CRUD, blood types, and location management.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.exceptions.specific.person_exceptions import *
from core.models.api_models import BloodType, Person_API, Location_API
from core.exceptions.handler import (
    DatabaseException
)
from core.models.models import Person, PersonDetails
from core.models.persistent_models import Location
from repositories.person_repository import PersonRepository
from services.location_service import LocationService

from core.logging_config import get_logger

from core.logging_config import get_logger

logger = get_logger(__name__)


# ==================== Person Service ====================

class PersonService:
    """Service for person-related operations"""
    
    def __init__(self):
        self.person_repo = PersonRepository()
        self.location_service = LocationService()
    
    # ==================== Person Operations ====================
    
    def get_person_by_id(self, person_id: str, full: bool = False) -> Person:
        """
        Get person by ID.
        
        Args:
            person_id: Person ID to retrieve
            full: Whether to load all related data eagerly
            
        Returns:
            Person object
            
        Raises:
            PersonNotFoundException: If person not found
        """
        person = self.person_repo.get_person_by_id(person_id, eager_load=full)
        if not person:
            logger.warning(f"Person not found with ID: {person_id}")
            raise PersonNotFoundException(
                person_id=person_id,
                details={"search_type": "by_id", "full_load": full}
            )
        
        logger.debug(f"Retrieved person with ID: {person_id}")
        return person
    
    def get_person_basic(self, person_id: str) -> Optional[Person]:
        """
        Get person with basic info only.
        
        Args:
            person_id: Person ID to retrieve
            
        Returns:
            Person object or None if not found
        """
        return self.person_repo.get_person_basic(person_id)
    
    def create_person_details(self, person_data: Person_API) -> PersonDetails:
        """
        Create person details record.
        
        Args:
            person_data: Person data containing details
            
        Returns:
            Created PersonDetails object
            
        Raises:
            PersonDetailsCreationException: If creation fails
        """
        person_detail = PersonDetails(
            person_first_name=person_data.person_first_name,
            person_last_name=person_data.person_last_name,
            person_birth_date=person_data.person_birth_date,
            person_gender=person_data.person_gender,
            person_country_code=person_data.person_country_code,
        )
        
        try:
            result = self.person_repo.create_person_details(person_detail)
            logger.info(f"Created person details for: {person_data.person_first_name} {person_data.person_last_name}")
            return result
        except Exception as e:
            logger.error(f"Failed to create person details: {e}")
            raise PersonDetailsCreationException(
                f"Failed to insert person details: {str(e)}"
            ) from e
    
    def generate_person_object(
        self,
        person_data: Person_API,
        location_data: Optional[Location_API] = None
    ) -> Person:
        """
        Generate a Person ORM object without inserting to DB.
        
        Args:
            person_data: Person data
            location_data: Optional location data
            
        Returns:
            Person ORM object (not persisted)
        """
        from core.models.models import Person, PersonDetails
        
        person = Person()
        
        # Create person details
        person_details = PersonDetails(
            person_first_name=person_data.person_first_name,
            person_last_name=person_data.person_last_name,
            person_birth_date=getattr(person_data, 'person_birth_date', None),
            person_gender=getattr(person_data, 'person_gender', None),
            person_country_code=getattr(person_data, 'person_country_code', None),
        )
        
        # Check if we should use existing details
        if hasattr(person_data, 'id_person_details') and person_data.id_person_details:
            existing_details = self.person_repo.get_person_details_by_id(
                person_data.id_person_details
            )
            if existing_details:
                person.person_details_id = existing_details.id_person_details
            else:
                person.person_details = person_details
        else:
            person.person_details = person_details
        
        # Set blood type
        if hasattr(person_data, 'blood_type') and person_data.blood_type.lower() != "unknown":
            person.person_blood_type = person_data.blood_type
        else:
            person.person_blood_type = None
        
        # Handle location
        if location_data:
            if location_data.id_location:
                location = self.location_service.get_location_object(location_data.id_location)
                if location:
                    person.person_location_id = location.id_location
                else:
                    person.person_location = self.location_service.build_location_model(location_data)
            else:
                person.person_location = self.location_service.build_location_model(location_data)
        
        logger.debug(f"Generated person object for: {person_data.person_first_name} {person_data.person_last_name}")
        return person

    
    def refresh_or_insert_person(
        self,
        person_data: Person_API,
        location_data: Location_API = None
    ) -> Person:
        """
        Insert a new person or update an existing one.
        
        Args:
            person_data: Person data
            location_data: Location data
            
        Returns:
            Created or updated Person object
            
        Raises:
            PersonNotFoundException: If person not found for update
            PersonInsertFailedException: If insertion fails
            PersonUpdateFailedException: If update fails
        """
        # Get existing person
        existing_person = self.person_repo.get_person_basic(person_data.id_person)
        
        
        # Handle person details
        existing_details = self.person_repo.get_person_details_by_id(
            person_data.id_person_details
        )
        
        if existing_person:
            # Update existing person
            logger.info(f"Updating existing person with ID: {person_data.id_person}")
            
            if existing_details:
                # Update existing details
                existing_details.person_gender = person_data.person_gender
                existing_details.person_first_name = person_data.person_first_name
                existing_details.person_last_name = person_data.person_last_name
                existing_person.person_details = existing_details
            else:
                # Create new details
                new_details = self.create_person_details(person_data)
                existing_person.person_details_id = new_details.id_person_details
            
            
            existing_person.person_details.person_country_code = person_data.person_country_code if person_data.person_country_code  else None
            existing_person.person_blood_type = person_data.blood_type if (person_data.blood_type != BloodType.UNKNOWN ) else None
            
            # Handle location
            if location_data:
                location = self.location_service.get_location_object(location_data.id_location)
                if location:
                    location = self.location_service.update_location(
                        location_data.id_location, 
                        location_data
                    )
                    existing_person.person_location_id = location.id_location
                else:
                    new_location = self.location_service.create_location(location_data)
                    existing_person.person_location_id = new_location.id_location
            
            try:
                updated_person = self.person_repo.update_person(existing_person)
                logger.info(f"Successfully updated person with ID: {person_data.id_person}")
                return updated_person
            except Exception as e:
                logger.error(f"Failed to update person {person_data.id_person}: {e}")
                raise PersonUpdateFailedException(
                    person_id=person_data.id_person,
                    error=str(e),
                    details={"operation": "refresh_or_insert_person"}
                )
        else:
            # Create new person
            logger.info(f"Creating new person: {person_data.person_first_name} {person_data.person_last_name}")
            
            person = Person()
            
            person.person_blood_type = person_data.blood_type if (person_data.blood_type != BloodType.UNKNOWN ) else None
            
            if existing_details:
                person.person_details_id = existing_details.id_person_details
            else:
                person.person_details_id = self.create_person_details(person_data).id_person_details
            
            # Handle location
            if location_data:
                location = self.location_service.get_location_object(location_data.id_location)
                if location:
                    person.person_location_id = location.id_location
                else:
                    person.person_location_id = self.location_service.create_location(location_data).id_location
            
            try:
                created_person = self.person_repo.create_person(person)
                logger.info(f"Successfully created person with ID: {created_person.id_person}")
                return created_person
            except Exception as e:
                logger.error(f"Failed to create person: {e}")
                raise PersonInsertFailedException(
                    error=str(e),
                    details={
                        "first_name": person_data.person_first_name,
                        "last_name": person_data.person_last_name
                    }
                )
    
    def delete_person(self, person_id: str) -> Dict[str, Any]:
        """
        Delete a person by ID.
        
        Args:
            person_id: ID of the person to delete
            
        Returns:
            Dictionary with success message
            
        Raises:
            PersonNotFoundException: If person not found
            PersonDeleteFailedException: If deletion fails
        """
        person = self.get_person_by_id(person_id)
        
        try:
            success = self.person_repo.delete_person(person)
            
            if not success:
                raise PersonDeleteFailedException(
                    person_id=person_id,
                    error="Repository returned False",
                    details={"operation": "delete_person"}
                )
            
            logger.info(f"Successfully deleted person with ID: {person_id}")
            return {
                "success": True,
                "message": "Person deleted successfully",
                "person_id": person_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except PersonNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete person {person_id}: {e}")
            raise PersonDeleteFailedException(
                person_id=person_id,
                error=str(e),
                details={"operation": "delete_person"}
            )
    
    
    # ==================== Person Details Operations ====================
    
    def get_person_details_by_id(self, details_id: int) -> Optional[PersonDetails]:
        """
        Get person details by ID.
        
        Args:
            details_id: Person details ID to retrieve
            
        Returns:
            PersonDetails object or None if not found
        """
        return self.person_repo.get_person_details_by_id(details_id)
    
    def update_person_details(
        self, 
        details_id: int, 
        person_data: Person_API
    ) -> PersonDetails:
        """
        Update person details.
        
        Args:
            details_id: ID of the details to update
            person_data: New person data
            
        Returns:
            Updated PersonDetails object
            
        Raises:
            PersonDetailsNotFoundException: If details not found
            DatabaseException: If update fails
        """
        details = self.get_person_details_by_id(details_id)
        if not details:
            logger.warning(f"Person details not found with ID: {details_id}")
            raise PersonDetailsNotFoundException(
                details_id=details_id,
                details={"operation": "update_person_details"}
            )
        
        try:
            details.person_first_name = person_data.person_first_name
            details.person_last_name = person_data.person_last_name
            details.person_birth_date = person_data.person_birth_date
            details.person_gender = person_data.person_gender
            details.person_country_code = person_data.person_country_code
            
            updated_details = self.person_repo.update_person_details(details)
            logger.info(f"Updated person details with ID: {details_id}")
            return updated_details
            
        except Exception as e:
            logger.error(f"Failed to update person details {details_id}: {e}")
            raise DatabaseException(
                message="Failed to update person details",
                details={
                    "details_id": details_id,
                    "error": str(e),
                    "operation": "update_person_details"
                }
            )
    
    # ==================== Utility Methods ====================
    
    def person_exists(self, person_id: str) -> bool:
        """
        Check if a person exists.
        
        Args:
            person_id: Person ID to check
            
        Returns:
            True if person exists, False otherwise
        """
        person = self.person_repo.get_person_basic(person_id)
        return person is not None
    
    def get_person_full_name(self, person_id: str) -> Optional[str]:
        """
        Get the full name of a person.
        
        Args:
            person_id: Person ID
            
        Returns:
            Full name string or None if person not found
        """
        person = self.get_person_basic(person_id)
        if not person or not person.person_details:
            return None
        
        details = person.person_details
        return f"{details.person_first_name} {details.person_last_name}".strip()
    
    def search_persons(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Person]:
        """
        Search persons by name.
        
        Args:
            first_name: First name to search for
            last_name: Last name to search for
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of matching Person objects
        """
        conditions = {}
        if first_name:
            conditions["person_first_name"] = first_name
        if last_name:
            conditions["person_last_name"] = last_name
        
        if not conditions:
            return []
        
        try:
            results = self.person_repo.get_persons_by_conditions(
                conditions, limit=limit, offset=offset
            )
            logger.debug(f"Found {len(results)} persons matching search criteria")
            return results
        except Exception as e:
            logger.error(f"Failed to search persons: {e}")
            return []