# services/search_service.py
from typing import List, Dict, Any, Optional, Tuple
from core.models.models import  Product, Recipe, AppUser, Person, ProviderDetails, ProductProvider
from core.models.persistent_models import Location
from core.models.models import PersonDetails
from storage.storage_broker import search_records
from repositories.supplier_repository import SupplierRepository

class SearchService:
    """Service for search operations across different entities"""
    
    def __init__(self):
        self.supplier_repo = SupplierRepository()
    
    def search_products(
        self,
        token: str,
        offset: int = 0,
        limit: int = 100
    ) -> List[Product]:
        """
        Search products by token in name, brand, and description.
        
        Args:
            token: Search query string
            offset: Pagination offset
            limit: Pagination limit
        
        Returns:
            List of matching products
        """
        if not token or token.strip() == "":
            return []
        
        return search_records(
            Product,
            search_query=token,
            search_fields=[
                'product_brand',
                'product_name',
                'product_description'
            ],
            offset=offset,
            limit=limit
        )
    
    def search_recipes(
        self,
        token: str,
        offset: int = 0,
        limit: int = 100
    ) -> List[Recipe]:
        """
        Search recipes by token in name, description, and instructions.
        
        Args:
            token: Search query string
            offset: Pagination offset
            limit: Pagination limit
        
        Returns:
            List of matching recipes
        """
        if not token or token.strip() == "":
            return []
        
        return search_records(
            Recipe,
            search_query=token,
            search_fields=[
                'recipe_name',
                'recipe_description',
                'recipe_instructions'
            ],
            offset=offset,
            limit=limit
        )
    
    def search_users(
        self,
        token: str,
        offset: int = 0,
        limit: int = 100
    ) -> List[AppUser]:
        """
        Search users by token in person details and username.
        
        Args:
            token: Search query string
            offset: Pagination offset
            limit: Pagination limit
        
        Returns:
            List of matching users
        """
        if not token or token.strip() == "":
            return []
        
        return search_records(
            table=AppUser,
            search_query=token,
            search_fields=[
                'app_user_person.person_details.person_first_name',
                'app_user_person.person_details.person_last_name', 
                'app_user_name'
            ],
            join_tables=[AppUser.app_user_person,AppUser.app_user_person],
            eager_load_depth=[{AppUser.app_user_person: [{Person.person_details:[]}]}],
            offset=offset,
            limit=limit

        )
    
    def search_people(
        self,
        token: str,
        offset: int = 0,
        limit: int = 100
    ) -> List[Person]:
        """
        Search people by token in person details.
        
        Args:
            token: Search query string
            offset: Pagination offset
            limit: Pagination limit
        
        Returns:
            List of matching people
        """
        if not token or token.strip() == "":
            return []
        data = search_records(
            Person,
            search_query=token,
            search_fields=[
                'person_details.person_first_name',
                'person_details.person_last_name',
                # 'person_details.person_nationality'
            ],
            join_tables= [],
            eager_load_depth=[Person.person_details,Person.person_blood_type],
            offset=offset,
            limit=limit,
            
        )
        return data
    
    def search_suppliers(
        self,
        token: str,
        offset: int = 0,
        limit: int = 100
    ) -> List[ProviderDetails]:
        """
        Search suppliers by token in provider name and contact info.
        
        Args:
            token: Search query string
            offset: Pagination offset
            limit: Pagination limit
        
        Returns:
            List of matching suppliers
        """
        if not token or token.strip() == "":
            return []
        
        return search_records(
            ProviderDetails,
            [ProviderDetails.product_provider],
            search_fields=[
                'provider_name',
                'provider_contact_info'
            ],
            search_query=token,
            eager_load_depth=[{
                ProviderDetails.product_provider: [
                    ProductProvider.product_provider_org,
                    {
                        ProductProvider.product_provider_location: [
                            Location.location_name,
                            Location.position_wkt,
                            Location.location_address
                        ]
                    }
                ]
            }],
            offset=offset,
            limit=limit
        )
    
    def search_suppliers_by_location(
        self,
        longitude: float,
        latitude: float,
        distance_km: float,
        offset: int = 0,
        limit: int = 100
    ) :
        """
        Search suppliers by geographic location.
        
        Args:
            longitude: Longitude coordinate
            latitude: Latitude coordinate
            distance_km: Search radius in kilometers
            offset: Pagination offset
            limit: Pagination limit
        
        Returns:
            List of matching suppliers with distance information
        """
        return self.supplier_repo.search_by_filter(
            (longitude, latitude),
            distance_km,
            offset,
            limit
        )
    
    def search_suppliers_by_position(
        self,
        longitude: float,
        latitude: float,
        distance_km: float,
        offset: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Alias for search_suppliers_by_location.
        Search suppliers by geographic position.
        
        Args:
            longitude: Longitude coordinate
            latitude: Latitude coordinate
            distance_km: Search radius in kilometers
            offset: Pagination offset
            limit: Pagination limit
        
        Returns:
            List of matching suppliers with distance information
        """
        return self.search_suppliers_by_location(longitude, latitude, distance_km, offset, limit)
    
    def multi_search(
        self,
        token: str,
        entity_types: List[str],
        offset: int = 0,
        limit: int = 20
    ) -> Dict[str, List]:
        """
        Search across multiple entity types.
        
        Args:
            token: Search query string
            entity_types: List of entity types to search 
                         ('products', 'recipes', 'users', 'people', 'suppliers')
            offset: Pagination offset
            limit: Pagination limit per entity
        
        Returns:
            Dictionary with results grouped by entity type
        """
        if not token or token.strip() == "":
            return {
                'products': [],
                'recipes': [],
                'users': [],
                'people': [],
                'suppliers': []
            }
        
        results = {}
        
        if 'products' in entity_types:
            results['products'] = self.search_products(token, offset, limit)
        
        if 'recipes' in entity_types:
            results['recipes'] = self.search_recipes(token, offset, limit)
        
        if 'users' in entity_types:
            results['users'] = self.search_users(token, offset, limit)
        
        if 'people' in entity_types:
            results['people'] = self.search_people(token, offset, limit)
        
        if 'suppliers' in entity_types:
            results['suppliers'] = self.search_suppliers(token, offset, limit)
        
        return results
    
    def quick_search(
        self,
        token: str,
        limit: int = 5
    ) -> Dict[str, List]:
        """
        Quick search across all entity types with small result sets.
        Useful for autocomplete or quick lookup features.
        
        Args:
            token: Search query string
            limit: Maximum results per entity type
        
        Returns:
            Dictionary with limited results from all entity types
        """
        return self.multi_search(
            token,
            ['products', 'recipes', 'users', 'people', 'suppliers'],
            0,
            limit
        )
    
    def search_by_field(
        self,
        entity_type: str,
        field_name: str,
        value: str,
        offset: int = 0,
        limit: int = 100
    ) -> List:
        """
        Generic search by specific field.
        
        Args:
            entity_type: Type of entity to search ('product', 'recipe', 'user', 'person', 'supplier')
            field_name: Name of the field to search on
            value: Value to search for
            offset: Pagination offset
            limit: Pagination limit
        
        Returns:
            List of matching entities
        """
        entity_map = {
            'product': Product,
            'recipe': Recipe,
            'user': AppUser,
            'person': Person,
            'supplier': ProviderDetails
        }
        
        if entity_type not in entity_map:
            raise ValueError(f"Unsupported entity type: {entity_type}")
        
        entity_class = entity_map[entity_type]
        
        # Validate field exists
        if not hasattr(entity_class, field_name):
            raise ValueError(f"Field '{field_name}' does not exist on {entity_type}")
        
        return search_records(
            entity_class,
            search_query=value,
            search_fields=[field_name],
            offset=offset,
            limit=limit
        )
    
    def get_search_suggestions(
        self,
        token: str,
        limit: int = 10
    ) -> Dict[str, List[str]]:
        """
        Get search suggestions for autocomplete.
        
        Args:
            token: Search query string
            limit: Maximum suggestions per category
        
        Returns:
            Dictionary with suggestion lists by category
        """
        suggestions = {
            'products': [],
            'recipes': [],
            'suppliers': []
        }
        
        if not token or len(token) < 2:
            return suggestions
        
        # Get product name suggestions
        products = self.search_products(token, 0, limit)
        suggestions['products'] = [p.product_name for p in products if p.product_name]
        
        # Get recipe name suggestions
        recipes = self.search_recipes(token, 0, limit)
        suggestions['recipes'] = [r.recipe_name for r in recipes if r.recipe_name]
        
        # Get supplier name suggestions
        suppliers = self.search_suppliers(token, 0, limit)
        suggestions['suppliers'] = [s.provider_name for s in suppliers if s.provider_name]
        
        return suggestions
    
    def count_search_results(
        self,
        token: str,
        entity_types: List[str]
    ) -> Dict[str, int]:
        """
        Get count of search results for each entity type.
        Useful for pagination and search results preview.
        
        Args:
            token: Search query string
            entity_types: List of entity types to count
        
        Returns:
            Dictionary with counts by entity type
        """
        counts = {}
        
        # Use large limit to get all results, but we only need count
        # This could be optimized with a count query
        if 'products' in entity_types:
            products = self.search_products(token, 0, 10000)
            counts['products'] = len(products)
        
        if 'recipes' in entity_types:
            recipes = self.search_recipes(token, 0, 10000)
            counts['recipes'] = len(recipes)
        
        if 'users' in entity_types:
            users = self.search_users(token, 0, 10000)
            counts['users'] = len(users)
        
        if 'people' in entity_types:
            people = self.search_people(token, 0, 10000)
            counts['people'] = len(people)
        
        if 'suppliers' in entity_types:
            suppliers = self.search_suppliers(token, 0, 10000)
            counts['suppliers'] = len(suppliers)
        
        return counts