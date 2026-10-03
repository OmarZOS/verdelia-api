# services/recipe_service.py
"""
Recipe service for managing recipes, ingredients, and recipe-related operations.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from core.models.api_models import Recipe_API, RecipeImage_API, Ingredient_API
from core.exceptions.specific.recipe_exceptions import (
    IngredientUpdateFailedException,
    RecipeNotFoundException,
    RecipeAlreadyExistsException,
    RecipeInsertFailedException,
    RecipePermissionException,
    RecipeUpdateFailedException,
    RecipeDeleteFailedException,
    RecipeCategoryNotFoundException,
    IngredientNotFoundException,
    IngredientAlreadyExistsException,
    IngredientInsertFailedException,
    IngredientDeleteFailedException
)
from core.models.models import Recipe, RecipeContainsIngredient, RecipeImage, Ingredient
from repositories.recipe_repository import RecipeRepository
from services.user_service import UserService

from core.logging_config import get_logger

logger = get_logger(__name__)



class RecipeService:
    """Service for recipe-related operations"""
    
    def __init__(self):
        self.recipe_repo = RecipeRepository()
        self.user_service = UserService()
    
    # ==================== Private Helper Methods ====================
    
    def _build_recipe_model(self, recipe_data: Recipe_API) -> Recipe:
        """
        Build Recipe model from API data.
        
        Args:
            recipe_data: API recipe data
            
        Returns:
            Recipe model instance
        """
        return Recipe(
            recipe_preparation_time=recipe_data.recipe_preparation_time,
            recipe_instructions=recipe_data.recipe_instructions,
            recipe_name=recipe_data.recipe_name,
            recipe_owner_id=recipe_data.recipe_owner_id,
            recipe_description=recipe_data.recipe_description,
            recipe_creation=datetime.now(),
            recipe_last_updated=datetime.now()
        )
    
    def _sync_recipe_ingredients(self, recipe_id: int, new_ingredients: Dict[int, float]):
        """
        Sync recipe ingredients (add, update, delete).
        
        Args:
            recipe_id: Recipe ID to sync ingredients for
            new_ingredients: Dictionary of ingredient IDs to quantities
        """
        # Get existing containments
        old_containments = self.recipe_repo.get_recipe_containments(recipe_id)
        old_map = {c.contained_ingredient_id: c for c in old_containments}
        
        for ingredient_id, quantity in new_ingredients.items():
            if ingredient_id in old_map:
                # Update existing
                containment = old_map[ingredient_id]
                containment.contained_quantity = quantity
                self.recipe_repo.update_containment(containment)
                del old_map[ingredient_id]
                logger.debug(f"Updated ingredient {ingredient_id} for recipe {recipe_id}")
            else:
                # Create new
                containment = RecipeContainsIngredient(
                    contained_ingredient_id=ingredient_id,
                    contained_quantity=quantity,
                    containing_recipe_id=recipe_id
                )
                self.recipe_repo.create_containment(containment)
                logger.debug(f"Added ingredient {ingredient_id} to recipe {recipe_id}")
        
        # Delete removed containments
        for containment in old_map.values():
            self.recipe_repo.delete_containment(containment)
            logger.debug(f"Removed ingredient {containment.contained_ingredient_id} from recipe {recipe_id}")
    
    def _handle_recipe_image(self, recipe_id: int, image_data: RecipeImage_API):
        """
        Handle recipe image creation or update.
        
        Args:
            recipe_id: Recipe ID
            image_data: Image data
        """
        if image_data.id_recipe_image == 0:
            new_image = RecipeImage(recipe_image_url=image_data.recipe_image_url)
            new_image.recipe_ref_id = recipe_id
            self.recipe_repo.create_recipe_image(new_image)
            logger.info(f"Created recipe image for recipe {recipe_id}")
        else:
            existing_images = self.recipe_repo.get_recipe_image_by_id(image_data.id_recipe_image)
            if existing_images:
                existing = existing_images[0]
                existing.recipe_image_url = image_data.recipe_image_url
                self.recipe_repo.update_recipe_image(existing)
                logger.info(f"Updated recipe image {image_data.id_recipe_image}")
    
    # ==================== Recipe Retrieval Methods ====================
    
    def get_recipe_by_id(self, recipe_id: int, full: bool = False) -> Recipe:
        """
        Get recipe by ID.
        
        Args:
            recipe_id: Recipe ID to retrieve
            full: Whether to load all related data
            
        Returns:
            Recipe object
            
        Raises:
            RecipeNotFoundException: If recipe not found
        """
        if full:
            recipe = self.recipe_repo.get_recipe_record_by_id(recipe_id)
        else:
            recipe = self.recipe_repo.get_recipe_by_id(recipe_id)
        
        if not recipe:
            logger.warning(f"Recipe not found with ID: {recipe_id}")
            raise RecipeNotFoundException(recipe_id=recipe_id)
        
        logger.debug(f"Retrieved recipe with ID: {recipe_id}")
        return recipe
    
    def get_recipes_by_user(self, user_id: int, offset: int = 0, limit: int = 100) -> List[Recipe]:
        """
        Get recipes by user.
        
        Args:
            user_id: User ID to filter by
            offset: Pagination offset
            limit: Maximum number of records
            
        Returns:
            List of Recipe objects
        """
        logger.debug(f"Fetching recipes for user {user_id}")
        return self.recipe_repo.get_recipes_by_user(user_id, offset, limit)
    
    def get_recipes_by_category(self, category_id: int, offset: int = 0, limit: int = 100) -> List[Recipe]:
        """
        Get recipes by category.
        
        Args:
            category_id: Category ID to filter by
            offset: Pagination offset
            limit: Maximum number of records
            
        Returns:
            List of Recipe objects
            
        Raises:
            RecipeCategoryNotFoundException: If category not found
        """
        # Validate category exists
        category = self.recipe_repo.get_recipe_category_by_id(category_id)
        if not category:
            logger.warning(f"Recipe category not found with ID: {category_id}")
            raise RecipeCategoryNotFoundException(category_id=category_id)
        
        logger.debug(f"Fetching recipes for category {category_id}")
        return self.recipe_repo.get_recipes_by_category(category_id, offset, limit)
    
    def get_all_recipes(self, offset: int = 0, limit: int = 100) -> List[Recipe]:
        """
        Get all recipes with pagination.
        
        Args:
            offset: Pagination offset
            limit: Maximum number of records
            
        Returns:
            List of Recipe objects
        """
        logger.debug(f"Fetching all recipes (offset={offset}, limit={limit})")
        return self.recipe_repo.get_all_recipes(offset, limit)
    
    def get_recipe_categories(self) -> List:
        """
        Get all recipe categories.
        
        Returns:
            List of recipe categories
        """
        logger.debug("Fetching all recipe categories")
        return self.recipe_repo.get_all_recipe_categories()
    
    # ==================== Recipe Creation Methods ====================
    
    async def create_recipe(
        self,
        recipe_data: Recipe_API,
        image_data: RecipeImage_API
    ) -> Recipe:
        """
        Create a new recipe.
        
        Args:
            recipe_data: Recipe details
            image_data: Recipe image data
            
        Returns:
            Created Recipe object
            
        Raises:
            RecipeAlreadyExistsException: If recipe name already exists
            RecipeCategoryNotFoundException: If category not found
            RecipeInsertFailedException: If creation fails
        """
        logger.info(f"Creating new recipe: {recipe_data.recipe_name}")
        
        # Check if recipe name exists
        existing = self.recipe_repo.get_recipe_by_name(recipe_data.recipe_name)
        if existing:
            logger.warning(f"Recipe already exists with name: {recipe_data.recipe_name}")
            raise RecipeAlreadyExistsException(recipe_name=recipe_data.recipe_name)
        
        # Validate category
        category = self.recipe_repo.get_recipe_category_by_id(recipe_data.recipe_category_id)
        if not category:
            logger.warning(f"Recipe category not found with ID: {recipe_data.recipe_category_id}")
            raise RecipeCategoryNotFoundException(category_id=recipe_data.recipe_category_id)
        
        # Validate user exists
        try:
            user = self.user_service.get_user_by_id(recipe_data.recipe_owner_id)
        except Exception as e:
            logger.error(f"User not found with ID: {recipe_data.recipe_owner_id}")
            raise
        
        # Build recipe
        recipe = self._build_recipe_model(recipe_data)
        recipe.recipe_category_id = category.id_recipe_category
        
        # Handle image
        if image_data and image_data.recipe_image_url:
            recipe_image = RecipeImage(recipe_image_url=image_data.recipe_image_url)
            recipe.recipe_image = [recipe_image]
        
        # Handle ingredients
        if recipe_data.recipe_ingredients:
            ingredient_list = []
            for ingredient_id, quantity in recipe_data.recipe_ingredients.items():
                containment = RecipeContainsIngredient(
                    contained_ingredient_id=ingredient_id,
                    contained_quantity=quantity
                )
                ingredient_list.append(containment)
            recipe.recipe_contains_ingredient = ingredient_list
        
        # Save recipe
        try:
            result = self.recipe_repo.create_recipe(recipe)
            logger.info(f"Recipe created successfully with ID: {result.id_recipe}")
            return result
        except Exception as e:
            logger.error(f"Failed to create recipe: {e}")
            raise RecipeInsertFailedException(
                error=str(e),
                recipe_name=recipe_data.recipe_name
            )
    
    # ==================== Recipe Update Methods ====================
    
    def update_recipe(
        self,
        recipe_id: int,
        recipe_data: Recipe_API,
        image_data: RecipeImage_API,
        user_id:int = None
    ) -> Recipe:
        """
        Update an existing recipe.
        
        Args:
            recipe_id: Recipe ID to update
            recipe_data: Updated recipe details
            image_data: Updated image data
            
        Returns:
            Updated Recipe object
            
        Raises:
            RecipeNotFoundException: If recipe not found
            RecipeAlreadyExistsException: If new name conflicts
            RecipeCategoryNotFoundException: If category not found
            RecipeUpdateFailedException: If update fails
        """
        logger.info(f"Updating recipe with ID: {recipe_id}")
        
        # Validate category
        category = self.recipe_repo.get_recipe_category_by_id(recipe_data.recipe_category_id)
        if not category:
            logger.warning(f"Recipe category not found with ID: {recipe_data.recipe_category_id}")
            raise RecipeCategoryNotFoundException(category_id=recipe_data.recipe_category_id)
        
        # Get existing recipe
        recipe = self.get_recipe_by_id(recipe_id, full=True)
        

        if user_id:
            if recipe.recipe_owner_id != user_id:
                logger.warning(f"User {user_id} is not the owner of recipe {recipe_id}")
                raise RecipePermissionException(f"User {user_id} is not authorized to update this recipe.")
        # Track changes for logging
        changes = []
        if recipe.recipe_name != recipe_data.recipe_name:
            changes.append(f"name: {recipe.recipe_name} -> {recipe_data.recipe_name}")
        if recipe.recipe_description != recipe_data.recipe_description:
            changes.append(f"description updated")
        if recipe.recipe_preparation_time != recipe_data.recipe_preparation_time:
            changes.append(f"prep time: {recipe.recipe_preparation_time} -> {recipe_data.recipe_preparation_time}")
        
        # Check name uniqueness if changed
        if recipe.recipe_name != recipe_data.recipe_name:
            other = self.recipe_repo.get_recipe_by_name(recipe_data.recipe_name)
            if other:
                logger.warning(f"Recipe name already exists: {recipe_data.recipe_name}")
                raise RecipeAlreadyExistsException(recipe_name=recipe_data.recipe_name)
        
        # Update basic fields
        recipe.recipe_preparation_time = recipe_data.recipe_preparation_time
        recipe.recipe_instructions = recipe_data.recipe_instructions
        recipe.recipe_name = recipe_data.recipe_name
        recipe.recipe_description = recipe_data.recipe_description
        recipe.recipe_last_updated = datetime.now()
        recipe.recipe_category_id = category.id_recipe_category
        
        # Update recipe
        try:
            recipe = self.recipe_repo.update_recipe(recipe)
            logger.info(f"Recipe {recipe_id} updated successfully. Changes: {changes if changes else 'none'}")
        except Exception as e:
            logger.error(f"Failed to update recipe {recipe_id}: {e}")
            raise RecipeUpdateFailedException(
                recipe_id=recipe_id,
                error=str(e)
            )
        
        # Update ingredients
        if recipe_data.recipe_ingredients:
            self._sync_recipe_ingredients(recipe.id_recipe, recipe_data.recipe_ingredients)
        
        # Update image
        if image_data and image_data.recipe_image_url:
            self._handle_recipe_image(recipe.id_recipe, image_data)
        
        return self.get_recipe_by_id(recipe_id, full=True)
    
    # ==================== Recipe Deletion Methods ====================
    
    def delete_recipe(self, recipe_id: int, force_delete: bool = False, user_id: int = None) -> Dict[str, Any]:
        """
        Delete a recipe and all associated data.
        
        Args:
            recipe_id: Recipe ID to delete
            force_delete: Force delete even if recipe has dependencies
            user_id: ID of the user attempting to delete the recipe
            
        Returns:
            Deletion confirmation
            
        Raises:
            RecipeNotFoundException: If recipe not found
            RecipeDeleteFailedException: If deletion fails
        """
        logger.info(f"Deleting recipe with ID: {recipe_id} (force={force_delete})")
        
        recipe = self.get_recipe_by_id(recipe_id,full=True)
        
        if user_id:
            if recipe.recipe_owner_id != user_id:
                logger.warning(f"User {user_id} is not the owner of recipe {recipe_id}")
                raise RecipePermissionException(f"User {user_id} is not authorized to delete this recipe.")

        # Check if recipe has dependencies (e.g., in orders, carts)
        if not force_delete:
            has_dependencies = self._check_recipe_dependencies(recipe_id)
            if has_dependencies:
                logger.warning(f"Recipe {recipe_id} has dependencies, use force_delete=true")
                raise RecipeDeleteFailedException(
                    recipe_id=recipe_id,
                    has_dependencies=True,
                    error="Recipe has existing dependencies (orders, carts)"
                )
        
        # Delete containments
        containments = self.recipe_repo.get_recipe_containments(recipe_id)
        for containment in containments:
            self.recipe_repo.delete_containment(containment)
            logger.debug(f"Deleted containment for recipe {recipe_id}")
        
        # Delete images
        images = self.recipe_repo.get_recipe_images(recipe_id)
        for image in images:
            self.recipe_repo.delete_recipe_image(image)
            logger.debug(f"Deleted image for recipe {recipe_id}")
        
        # Delete recipe
        try:
            success = self.recipe_repo.delete_recipe(recipe)
            
            if not success:
                raise RecipeDeleteFailedException(
                    recipe_id=recipe_id,
                    error="Repository returned False"
                )
            
            logger.info(f"Recipe {recipe_id} deleted successfully")
            return {
                "message": f"Recipe {recipe_id} deleted successfully",
                "recipe_id": recipe_id
            }
            
        except RecipeDeleteFailedException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete recipe {recipe_id}: {e}")
            raise RecipeDeleteFailedException(
                recipe_id=recipe_id,
                error=str(e)
            )
    
    def _check_recipe_dependencies(self, recipe_id: int) -> bool:
        """
        Check if recipe has dependencies.
        
        Args:
            recipe_id: Recipe ID to check
            
        Returns:
            True if recipe has dependencies
        """
        # Check if recipe is used in any orders
        order_items = self.recipe_repo.get_order_items_by_recipe(recipe_id)
        if order_items:
            logger.debug(f"Recipe {recipe_id} has {len(order_items)} order items")
            return True
        
        # Check if recipe is in any carts
        cart_items = self.recipe_repo.get_cart_items_by_recipe(recipe_id)
        if cart_items:
            logger.debug(f"Recipe {recipe_id} has {len(cart_items)} cart items")
            return True
        
        return False
    
    # ==================== Ingredient Operations ====================
    
    async def create_ingredient(self, ingredient_data: Ingredient_API,user_id:int) -> Ingredient:
        """
        Create a new ingredient.
        
        Args:
            ingredient_data: Ingredient details
            
        Returns:
            Created Ingredient object
            
        Raises:
            IngredientAlreadyExistsException: If ingredient name exists
            IngredientInsertFailedException: If creation fails
        """
        logger.info(f"Creating new ingredient: {ingredient_data.ingredient_name}")
        
        # Check if ingredient exists
        existing = self.recipe_repo.get_ingredient_by_name(ingredient_data.ingredient_name)
        if existing:
            logger.warning(f"Ingredient already exists with name: {ingredient_data.ingredient_name}")
            raise IngredientAlreadyExistsException(ingredient_name=ingredient_data.ingredient_name)
        
        ingredient = Ingredient(
            ingredient_name=ingredient_data.ingredient_name,
            ingredient_icon_url=ingredient_data.ingredient_icon_url,
            ingredient_quantifier=ingredient_data.ingredient_quantifier,
            ingredient_user_id = user_id
        )
        
        try:
            result = self.recipe_repo.create_ingredient(ingredient)
            logger.info(f"Ingredient created successfully with ID: {result.id_ingredient}")
            return result
        except Exception as e:
            logger.error(f"Failed to create ingredient: {e}")
            raise IngredientInsertFailedException(
                error=str(e),
                ingredient_name=ingredient_data.ingredient_name
            )
    
    def get_ingredient_by_id(self, ingredient_id: int) -> Ingredient:
        """
        Get ingredient by ID.
        
        Args:
            ingredient_id: Ingredient ID to retrieve
            
        Returns:
            Ingredient object
            
        Raises:
            IngredientNotFoundException: If ingredient not found
        """
        ingredient = self.recipe_repo.get_ingredient_by_id(ingredient_id)
        if not ingredient:
            logger.warning(f"Ingredient not found with ID: {ingredient_id}")
            raise IngredientNotFoundException(ingredient_id=ingredient_id)
        
        logger.debug(f"Retrieved ingredient with ID: {ingredient_id}")
        return ingredient
    
    def get_all_ingredients(self, offset: int = 0, limit: int = 100) -> List[Ingredient]:
        """
        Get all ingredients with pagination.
        
        Args:
            offset: Pagination offset
            limit: Maximum number of records
            
        Returns:
            List of Ingredient objects
        """
        logger.debug(f"Fetching all ingredients (offset={offset}, limit={limit})")
        return self.recipe_repo.get_all_ingredients(offset, limit)
    
    def delete_ingredient(self, ingredient_id: int, force_delete: bool = False, user_id: int = None) -> Dict[str, Any]:
        """
        Delete an ingredient.
        
        Args:
            ingredient_id: Ingredient ID to delete
            force_delete: Force delete even if ingredient is used in recipes
            user_id: ID of the user attempting to delete the ingredient
            
        Returns:
            Deletion confirmation
            
        Raises:
            IngredientNotFoundException: If ingredient not found
            IngredientDeleteFailedException: If deletion fails
        """
        logger.info(f"Deleting ingredient with ID: {ingredient_id} (force={force_delete})")
        
        ingredient = self.get_ingredient_by_id(ingredient_id)
        
        if user_id:
            if ingredient.ingredient_user_id != user_id:
                logger.warning(f"User {user_id} is not the owner of ingredient {ingredient_id}")
                raise RecipePermissionException(f"User {user_id} is not authorized to delete this ingredient.")

        # Check if ingredient is used in any recipes
        if not force_delete:
            recipe_usages = self.recipe_repo.get_recipes_by_ingredient(ingredient_id)
            if recipe_usages:
                logger.warning(f"Ingredient {ingredient_id} is used in {len(recipe_usages)} recipes")
                raise IngredientDeleteFailedException(
                    ingredient_id=ingredient_id,
                    has_dependencies=True,
                    error=f"Ingredient is used in {len(recipe_usages)} recipes"
                )
        
        try:
            success = self.recipe_repo.delete_ingredient(ingredient)
            
            if not success:
                raise IngredientDeleteFailedException(
                    ingredient_id=ingredient_id,
                    error="Repository returned False"
                )
            
            logger.info(f"Ingredient {ingredient_id} deleted successfully")
            return {
                "message": f"Ingredient {ingredient_id} deleted successfully",
                "ingredient_id": ingredient_id
            }
            
        except IngredientDeleteFailedException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete ingredient {ingredient_id}: {e}")
            raise IngredientDeleteFailedException(
                ingredient_id=ingredient_id,
                error=str(e)
            )
        

    def update_ingredient(self, ingredient_id: int, ingredient: Ingredient_API, user_id: int) -> Ingredient:
        """
        Update an existing ingredient.
        
        Args:
            ingredient_id: ID of the ingredient to update
            ingredient: Updated ingredient data
            
        Returns:
            Updated Ingredient object
            
        Raises:
            IngredientNotFoundException: If ingredient not found
            IngredientAlreadyExistsException: If ingredient name already exists
            IngredientUpdateFailedException: If update fails
        """
        logger.info(f"Updating ingredient with ID: {ingredient_id}")
        
        # Get existing ingredient
        existing_ingredient = self.recipe_repo.get_ingredient_by_id(ingredient_id)
        if not existing_ingredient:
            logger.warning(f"Ingredient not found with ID: {ingredient_id}")
            raise IngredientNotFoundException(ingredient_id=ingredient_id)
        
        if existing_ingredient.ingredient_user_id != user_id:
            logger.warning(f"User {user_id} is not the owner of ingredient {ingredient_id}")
            raise RecipePermissionException(f"User {user_id} is not authorized to update this ingredient.")


        # Check if name is being changed and if it already exists
        if ingredient.ingredient_name != existing_ingredient.ingredient_name:
            existing_by_name = self.recipe_repo.get_ingredient_by_name(ingredient.ingredient_name)
            if existing_by_name and existing_by_name.id_ingredient != ingredient_id:
                logger.warning(f"Ingredient name already exists: {ingredient.ingredient_name}")
                raise IngredientAlreadyExistsException(ingredient_name=ingredient.ingredient_name)
        
        # Update fields
        existing_ingredient.ingredient_name = ingredient.ingredient_name
        existing_ingredient.ingredient_icon_url = ingredient.ingredient_icon_url
        existing_ingredient.ingredient_quantifier = ingredient.ingredient_quantifier
        
        try:
            updated_ingredient = self.recipe_repo.update_ingredient(existing_ingredient)
            logger.info(f"Ingredient {ingredient_id} updated successfully")
            return updated_ingredient
        except Exception as e:
            logger.error(f"Failed to update ingredient {ingredient_id}: {e}")
            raise IngredientUpdateFailedException(
            ingredient_id=ingredient_id,
            error=str(e)
        )