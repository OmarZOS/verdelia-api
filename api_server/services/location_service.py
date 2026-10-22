# services/location_service.py
from typing import Optional, List, Dict, Any
from geoalchemy2.elements import WKTElement
from core.models.api_models import Location_API, Delivery_API
from core.models.models import Address
from core.models.persistent_models import Location
from core.exceptions.specific.location_exceptions import (
    
    LocationNotFoundError,
    AddressNotFoundError,
    LocationValidationError,
    LocationCreationError,
    LocationUpdateError
)
from core.exceptions.handler import APIException
from core.messages import *
from repositories.location_repository import LocationRepository
from repositories.address_repository import AddressRepository


class LocationService:
    """Service for location-related business logic"""
    
    def __init__(self):
        self.location_repo = LocationRepository()
        self.address_repo = AddressRepository()
    
    def build_address_from_location(self, location: Location_API) -> Address:
        """Build an Address from Location_API"""
        return Address(
            address_street=location.address_street,
            address_city=location.address_city,
            address_postal_code=location.address_postal_code,
            address_country=location.address_country,
        )
    
    def build_address_from_delivery(self, delivery: Delivery_API) -> Address:
        """Build an Address from Delivery_API"""
        address = Address()
        
        if delivery.delivery_address_id:
            address.id_address = delivery.delivery_address_id
        # if delivery.address_street:
        #     address.address_street = delivery.address_street
        # if delivery.address_city:
        #     address.address_city = delivery.address_city
        # if delivery.address_postal_code:
        #     address.address_postal_code = delivery.address_postal_code
        # if delivery.address_country:
        #     address.address_country = delivery.address_country
        
        return address
    
    def _validate_location_coordinates(self, latitude: Optional[float], longitude: Optional[float]) -> None:
        """Validate location coordinates"""
        if not latitude or not longitude:
            raise LocationValidationError(
                message="Latitude and longitude must be provided",
                details={"latitude": latitude, "longitude": longitude}
            )
        
        # Validate latitude range (-90 to 90)
        if latitude < -90 or latitude > 90:
            raise LocationValidationError(
                message="Invalid latitude value",
                details={"latitude": latitude, "valid_range": "-90 to 90"}
            )
        
        # Validate longitude range (-180 to 180)
        if longitude < -180 or longitude > 180:
            raise LocationValidationError(
                message="Invalid longitude value",
                details={"longitude": longitude, "valid_range": "-180 to 180"}
            )
    
    def build_location_model(self, location: Location_API) -> Location:
        """Build a Location ORM object from Location_API"""
        self._validate_location_coordinates(
            location.location_latitude, 
            location.location_longitude
        )
        
        # Create address if provided
        address = None
        if any([location.address_street, location.address_city, 
                location.address_postal_code, location.address_country]):
            address = Address(
                address_street=location.address_street,
                address_city=location.address_city,
                address_postal_code=location.address_postal_code,
                address_country=location.address_country,
            )
        
        # Create location
        loc = Location(
            location_position=WKTElement(
                f"POINT({location.location_longitude} {location.location_latitude})",
                srid=4326
            ),
            location_name=location.location_name,
        )
        
        if address:
            loc.location_address = address
        
        return loc
    
    def get_location_by_id(self, location_id: str, with_address: bool = True) -> Location:
        """Get location by ID"""
        location = self.location_repo.get_location_by_id(location_id, with_address)
        if not location:
            raise LocationNotFoundError(location_id)
        return location
    
    def get_location_object(self, location_id: str) -> Optional[Location]:
        """Get location object by ID (alias for get_location_by_id)"""
        return self.get_location_by_id(location_id, with_address=False)
    
    def get_address_by_id(self, address_id: str) -> Address:
        """Get address by ID"""
        address = self.address_repo.get_address_by_id(address_id)
        if not address:
            raise AddressNotFoundError(address_id)
        return address
    
    def create_location(self, location_data: Location_API) -> Location:
        """Create a new location"""
        try:
            # Validate coordinates before building
            self._validate_location_coordinates(
                location_data.location_latitude,
                location_data.location_longitude
            )
            
            # Build the location model
            location = self.build_location_model(location_data)
            
            # Create in repository
            created_location = self.location_repo.create_location(location)
            return created_location
            
        except (LocationValidationError, APIException):
            raise
            
        except Exception as e:
            raise LocationCreationError(
                message="Failed to create location",
                details={"error": str(e), "location_data": location_data.dict()}
            )
    
    def update_location(self, location_id: str, location_data: Location_API) -> Location:
        """Update an existing location"""
        try:
            # Get existing location
            existing_location = self.location_repo.get_location_by_id(location_id, with_address=True)
            if not existing_location:
                raise LocationNotFoundError(location_id)
            
            # Validate coordinates if provided
            if location_data.location_latitude and location_data.location_longitude:
                self._validate_location_coordinates(
                    location_data.location_latitude,
                    location_data.location_longitude
                )
            
            # Update address if it exists
            if existing_location.location_address:
                self._update_address_fields(existing_location.location_address, location_data)
            elif self._has_address_data(location_data):
                # Create new address if none exists but data provided
                existing_location.location_address = Address(
                    address_street=location_data.address_street,
                    address_city=location_data.address_city,
                    address_postal_code=location_data.address_postal_code,
                    address_country=location_data.address_country,
                )
            
            # Update location fields
            self._update_location_fields(existing_location, location_data)
            
            # Save changes
            updated_location = self.location_repo.update_location(existing_location)
            return updated_location
            
        except (LocationNotFoundError, LocationValidationError, APIException):
            raise
            
        except Exception as e:
            raise LocationUpdateError(
                location_id=location_id,
                message="Failed to update location",
                details={"error": str(e), "location_data": location_data.dict()}
            )
    
    def _update_address_fields(self, address: Address, location_data: Location_API) -> None:
        """Update address fields from location data"""
        if location_data.address_street is not None:
            address.address_street = location_data.address_street
        if location_data.address_city is not None:
            address.address_city = location_data.address_city
        if location_data.address_postal_code is not None:
            address.address_postal_code = location_data.address_postal_code
        if location_data.address_country is not None:
            address.address_country = location_data.address_country
    
    def _update_location_fields(self, location: Location, location_data: Location_API) -> None:
        """Update location fields from location data"""
        if location_data.location_name is not None:
            location.location_name = location_data.location_name
        
        if location_data.location_latitude and location_data.location_longitude:
            location.location_position = WKTElement(
                f"POINT({location_data.location_longitude} {location_data.location_latitude})",
                srid=4326
            )
    
    def _has_address_data(self, location_data: Location_API) -> bool:
        """Check if location data contains address information"""
        return any([
            location_data.address_street,
            location_data.address_city,
            location_data.address_postal_code,
            location_data.address_country
        ])
    
    def delete_location(self, location_id: str) -> Dict[str, Any]:
        """Delete a location"""
        # Verify location exists before deletion
        self.get_location_by_id(location_id, with_address=False)
        
        success = self.location_repo.delete_location(location_id)
        
        if not success:
            raise LocationUpdateError(
                location_id=location_id,
                message="Failed to delete location"
            )
        
        return {
            "message": "Location deleted successfully",
            "location_id": location_id
        }
    
    def get_nearby_locations(self, latitude: float, longitude: float, radius_km: float = 10) -> List[Location]:
        """Get locations within a radius (requires PostGIS)"""
        try:
            # Validate coordinates
            self._validate_location_coordinates(latitude, longitude)
            
            # Validate radius
            if radius_km <= 0:
                raise LocationValidationError(
                    message="Radius must be positive",
                    details={"radius_km": radius_km}
                )
            
            # This would use ST_DWithin for spatial queries
            # Implementation depends on your specific spatial query needs
            return []
            
        except LocationValidationError:
            raise
        except Exception as e:
            raise LocationValidationError(
                message="Failed to search nearby locations",
                details={"error": str(e), "latitude": latitude, "longitude": longitude, "radius_km": radius_km}
            )
    
    def create_address_from_location(self, location_data: Location_API) -> Address:
        """Create an address from location data"""
        try:
            address = self.build_address_from_location(location_data)
            return self.address_repo.create_address(address)
        except Exception as e:
            raise LocationCreationError(
                message="Failed to create address from location",
                details={"error": str(e), "location_data": location_data.dict()}
            )
    
    def update_address(self, address_id: str, address_data: Location_API) -> Address:
        """Update an existing address"""
        try:
            address = self.get_address_by_id(address_id)
            
            if address_data.address_street:
                address.address_street = address_data.address_street
            if address_data.address_city:
                address.address_city = address_data.address_city
            if address_data.address_postal_code:
                address.address_postal_code = address_data.address_postal_code
            if address_data.address_country:
                address.address_country = address_data.address_country
            
            return self.address_repo.update_address(address)
            
        except AddressNotFoundError:
            raise
        except Exception as e:
            raise LocationUpdateError(
                location_id=address_id,
                message="Failed to update address",
                details={"error": str(e), "address_data": address_data}
            )
    
    def get_location_with_address(self, location_id: str) -> Dict[str, Any]:
        """Get location with its associated address as a dictionary"""
        location = self.get_location_by_id(location_id, with_address=True)
        
        result = {
            "id_location": location.id_location,
            "location_name": location.location_name,
            "location_position": str(location.location_position) if location.location_position else None,
        }
        
        if location.location_address:
            result["address"] = {
                "id_address": location.location_address.id_address,
                "street": location.location_address.address_street,
                "city": location.location_address.address_city,
                "postal_code": location.location_address.address_postal_code,
                "country": location.location_address.address_country,
            }
        
        return result