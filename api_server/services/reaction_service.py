# services/reaction_service.py
import logging
from typing import Union, Optional, Dict, Any, List
from core.logging_config import get_logger
from core.messages.http_status import *
from constants import ReactionType
from core.models.api_models import ReactionBase, ReactionValue
from core.exceptions.handler import APIException, UserNotFoundException
from core.messages import *
from core.messages.error_codes import ErrorCode
from core.models.models import (
    ProductReaction, RecipeReaction, ProviderReaction, 
    CommentReaction, AppUser, Product, Recipe, 
    ProductProvider, Comment
)
from repositories.reaction_repository import ReactionRepository

from core.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# EXCEPTION CLASSES
# ============================================================================

class ReactionNotFoundException(APIException):
    """Exception raised when a reaction is not found."""
    
    def __init__(self, user_id: int = None, target_id: int = None, reaction_type: str = None):
        details = {}
        if user_id:
            details["user_id"] = user_id
        if target_id:
            details["target_id"] = target_id
        if reaction_type:
            details["reaction_type"] = reaction_type
        
        message = "Reaction not found"
        if user_id and target_id and reaction_type:
            message = f"Reaction for user {user_id} on {reaction_type} {target_id} not found"
        elif user_id and reaction_type:
            message = f"Reaction for user {user_id} of type {reaction_type} not found"
        
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.REACTION_NOT_FOUND,
            message=message,
            details=details
        )


class TargetNotFoundException(APIException):
    """Exception raised when a target (product, recipe, provider, comment) is not found."""
    
    def __init__(self, target_type: str, target_id: int):
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            error_code=ErrorCode.TARGET_NOT_FOUND,
            message=f"{target_type.capitalize()} with ID '{target_id}' not found",
            details={
                "target_type": target_type,
                "target_id": target_id
            }
        )


class ReactionValidationException(APIException):
    """Exception raised when reaction validation fails."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.REACTION_VALIDATION_ERROR,
            message=message,
            details=details or {}
        )


# ============================================================================
# SERVICE CLASS
# ============================================================================

class ReactionService:
    """Service for reaction-related business logic"""
    
    def __init__(self):
        self.reaction_repo = ReactionRepository()
    
    def _validate_reaction_value(self, reaction_value: Optional[ReactionValue], rating_value: Optional[float]) -> None:
        """Validate reaction value based on type"""
        if reaction_value is None and rating_value is None:
            raise ReactionValidationException(
                message="Either reaction_value or rating_value must be provided"
            )
        
        if rating_value is not None and (rating_value < 0 or rating_value > 5):
            raise ReactionValidationException(
                message="Rating must be between 0 and 5",
                details={"rating_value": rating_value, "min": 0, "max": 5}
            )
    
    def _validate_target_exists(self, reaction_type: ReactionType, target_id: int) -> None:
        """Validate that the target exists"""
        target_exists = False
        
        if reaction_type == ReactionType.PRODUCT:
            target_exists = self.reaction_repo.product_exists(target_id)
        elif reaction_type == ReactionType.RECIPE:
            target_exists = self.reaction_repo.recipe_exists(target_id)
        elif reaction_type == ReactionType.PROVIDER:
            target_exists = self.reaction_repo.provider_exists(target_id)
        elif reaction_type == ReactionType.COMMENT:
            target_exists = self.reaction_repo.comment_exists(target_id)
        
        if not target_exists:
            raise TargetNotFoundException(
                target_type=reaction_type.value,
                target_id=target_id
            )
    
    def _validate_user_exists(self, user_id: int) -> None:
        """Validate that the user exists"""
        user_exists = self.reaction_repo.user_exists(user_id)
        if not user_exists:
            raise UserNotFoundException(user_id=user_id)
    
    def _build_reaction_model(self, reaction: ReactionBase) -> Union[ProductReaction, RecipeReaction, ProviderReaction, CommentReaction]:
        """Build the appropriate reaction model based on type"""
        reaction_type = reaction.reaction_type
        
        # Validate reaction value
        self._validate_reaction_value(reaction.reaction_value, reaction.rating_value)
        
        if reaction_type == ReactionType.PRODUCT:
            return ProductReaction(
                product_reacting_user=reaction.user_id,
                reacted_on_product=reaction.target_id,
                product_reaction=reaction.reaction_value.value if reaction.reaction_value else None,
                product_reaction_value=reaction.rating_value if reaction.rating_value is not None else 0.0,
            )
        
        elif reaction_type == ReactionType.RECIPE:
            return RecipeReaction(
                recipe_reacting_user=reaction.user_id,
                reacted_on_recipe=reaction.target_id,
                recipe_reaction=reaction.reaction_value.value if reaction.reaction_value else None,
            )
        
        elif reaction_type == ReactionType.PROVIDER:
            return ProviderReaction(
                provider_reacting_user=reaction.user_id,
                reacted_on_provider=reaction.target_id,
                provider_reaction=reaction.reaction_value.value if reaction.reaction_value else None,
                provider_reaction_value=reaction.rating_value if reaction.rating_value is not None else 0.0,
            )
        
        elif reaction_type == ReactionType.COMMENT:
            return CommentReaction(
                comment_reacting_user=reaction.user_id,
                reacted_on_comment=reaction.target_id,
                comment_reaction=reaction.reaction_value.value if reaction.reaction_value else None,
            )
        
        else:
            raise ReactionValidationException(
                message=f"Unknown reaction type: {reaction_type}",
                details={"reaction_type": reaction_type}
            )
    
    def _update_existing_reaction(self, existing_reaction: Union[ProductReaction, RecipeReaction, ProviderReaction, CommentReaction], reaction: ReactionBase) -> Union[ProductReaction, RecipeReaction, ProviderReaction, CommentReaction]:
        """Update an existing reaction with new values"""
        reaction_type = reaction.reaction_type
        
        if reaction_type == ReactionType.PRODUCT:
            if reaction.reaction_value:
                existing_reaction.product_reaction = reaction.reaction_value.value
            if reaction.rating_value is not None:
                existing_reaction.product_reaction_value = reaction.rating_value
        
        elif reaction_type == ReactionType.RECIPE:
            if reaction.reaction_value:
                existing_reaction.recipe_reaction = reaction.reaction_value.value
        
        elif reaction_type == ReactionType.PROVIDER:
            if reaction.reaction_value:
                existing_reaction.provider_reaction = reaction.reaction_value.value
            if reaction.rating_value is not None:
                existing_reaction.provider_reaction_value = reaction.rating_value
        
        elif reaction_type == ReactionType.COMMENT:
            if reaction.reaction_value:
                existing_reaction.comment_reaction = reaction.reaction_value.value
        
        return existing_reaction
    
    def _get_existing_reaction(self, reaction: ReactionBase) -> Optional[Union[ProductReaction, RecipeReaction, ProviderReaction, CommentReaction]]:
        """Get existing reaction if it exists"""
        reaction_type = reaction.reaction_type
        
        if reaction_type == ReactionType.PRODUCT:
            return self.reaction_repo.get_product_reaction_by_user(
                reaction.user_id, reaction.target_id
            )
        elif reaction_type == ReactionType.RECIPE:
            return self.reaction_repo.get_recipe_reaction_by_user(
                reaction.user_id, reaction.target_id
            )
        elif reaction_type == ReactionType.PROVIDER:
            return self.reaction_repo.get_provider_reaction_by_user(
                reaction.user_id, reaction.target_id
            )
        elif reaction_type == ReactionType.COMMENT:
            return self.reaction_repo.get_comment_reaction_by_user(
                reaction.user_id, reaction.target_id
            )
        return None
    
    def _create_new_reaction(self, reaction: ReactionBase) -> Union[ProductReaction, RecipeReaction, ProviderReaction, CommentReaction]:
        """Create a new reaction"""
        built_reaction = self._build_reaction_model(reaction)
        reaction_type = reaction.reaction_type
        
        if reaction_type == ReactionType.PRODUCT:
            return self.reaction_repo.create_product_reaction(built_reaction)
        elif reaction_type == ReactionType.RECIPE:
            return self.reaction_repo.create_recipe_reaction(built_reaction)
        elif reaction_type == ReactionType.PROVIDER:
            return self.reaction_repo.create_provider_reaction(built_reaction)
        elif reaction_type == ReactionType.COMMENT:
            return self.reaction_repo.create_comment_reaction(built_reaction)
        
        raise APIException(
            status=HTTP_500_INTERNAL_SERVER_ERROR,
            code=ErrorCode.REACTION_CREATION_FAILED,
            message=f"Failed to create reaction of type {reaction_type}",
            details={"reaction_type": reaction_type}
        )
    
    def handle_reaction(self, reaction: ReactionBase) -> Union[ProductReaction, RecipeReaction, ProviderReaction, CommentReaction]:
        """
        Handle reaction creation or update
        
        Args:
            reaction: Reaction data
            
        Returns:
            Created or updated reaction
            
        Raises:
            APIException: If validation fails
        """
        # Validate user exists
        self._validate_user_exists(reaction.user_id)
        
        # Validate target exists
        self._validate_target_exists(reaction.reaction_type, reaction.target_id)
        
        # Check if reaction already exists
        existing_reaction = self._get_existing_reaction(reaction)
        
        if existing_reaction:
            # Update existing reaction
            updated_reaction = self._update_existing_reaction(existing_reaction, reaction)
            return self.reaction_repo.update_reaction(updated_reaction)
        
        # Create new reaction
        return self._create_new_reaction(reaction)
    
    def get_user_reaction_on_target(
        self, 
        user_id: int, 
        target_id: int, 
        reaction_type: ReactionType
    ) -> Optional[Union[ProductReaction, RecipeReaction, ProviderReaction, CommentReaction]]:
        """Get a user's reaction on a specific target"""
        reaction = None
        
        if reaction_type == ReactionType.PRODUCT:
            reaction = self.reaction_repo.get_product_reaction_by_user(user_id, target_id)
        elif reaction_type == ReactionType.RECIPE:
            reaction = self.reaction_repo.get_recipe_reaction_by_user(user_id, target_id)
        elif reaction_type == ReactionType.PROVIDER:
            reaction = self.reaction_repo.get_provider_reaction_by_user(user_id, target_id)
        elif reaction_type == ReactionType.COMMENT:
            reaction = self.reaction_repo.get_comment_reaction_by_user(user_id, target_id)
        
        if not reaction:
            raise ReactionNotFoundException(
                user_id=user_id,
                target_id=target_id,
                reaction_type=reaction_type.value if hasattr(reaction_type, 'value') else str(reaction_type)
            )
        
        return reaction
    
    def delete_user_reaction(
        self, 
        user_id: int, 
        target_id: int, 
        reaction_type: ReactionType
    ) -> bool:
        """Delete a user's reaction on a target"""
        reaction = None
        
        if reaction_type == ReactionType.PRODUCT:
            reaction = self.reaction_repo.get_product_reaction_by_user(user_id, target_id)
        elif reaction_type == ReactionType.RECIPE:
            reaction = self.reaction_repo.get_recipe_reaction_by_user(user_id, target_id)
        elif reaction_type == ReactionType.PROVIDER:
            reaction = self.reaction_repo.get_provider_reaction_by_user(user_id, target_id)
        elif reaction_type == ReactionType.COMMENT:
            reaction = self.reaction_repo.get_comment_reaction_by_user(user_id, target_id)
        
        if not reaction:
            raise ReactionNotFoundException(
                user_id=user_id,
                target_id=target_id,
                reaction_type=reaction_type.value if hasattr(reaction_type, 'value') else str(reaction_type)
            )
        
        return self.reaction_repo.delete_reaction(reaction)
    
    def get_reaction_summary(
        self, 
        target_type: ReactionType, 
        target_id: int
    ) -> Dict[str, Any]:
        """Get summary of reactions for a target"""
        # Validate target exists
        self._validate_target_exists(target_type, target_id)
        
        if target_type == ReactionType.PRODUCT:
            return self._get_product_reaction_summary(target_id)
        elif target_type == ReactionType.RECIPE:
            return self._get_recipe_reaction_summary(target_id)
        elif target_type == ReactionType.PROVIDER:
            return self._get_provider_reaction_summary(target_id)
        elif target_type == ReactionType.COMMENT:
            return self._get_comment_reaction_summary(target_id)
        else:
            raise ReactionValidationException(
                message=f"Unknown target type: {target_type}",
                details={"target_type": target_type}
            )
    
    def _get_product_reaction_summary(self, product_id: int) -> Dict[str, Any]:
        """Get reaction summary for a product"""
        reactions = self.reaction_repo.get_product_reactions_by_target(product_id)
        
        summary = {
            "target_id": product_id,
            "target_type": "product",
            "total_reactions": len(reactions),
            "reaction_counts": {},
            "average_rating": 0.0,
            "total_ratings": 0
        }
        
        # Count reactions
        for reaction in reactions:
            if reaction.product_reaction:
                summary["reaction_counts"][reaction.product_reaction] = \
                    summary["reaction_counts"].get(reaction.product_reaction, 0) + 1
            
            if reaction.product_reaction_value and reaction.product_reaction_value > 0:
                summary["total_ratings"] += 1
                summary["average_rating"] = (summary.get("average_rating", 0) + reaction.product_reaction_value)
        
        if summary["total_ratings"] > 0:
            summary["average_rating"] = summary["average_rating"] / summary["total_ratings"]
        
        return summary
    
    def _get_recipe_reaction_summary(self, recipe_id: int) -> Dict[str, Any]:
        """Get reaction summary for a recipe"""
        reactions = self.reaction_repo.get_recipe_reactions_by_target(recipe_id)
        
        summary = {
            "target_id": recipe_id,
            "target_type": "recipe",
            "total_reactions": len(reactions),
            "reaction_counts": {}
        }
        
        # Count reactions
        for reaction in reactions:
            if reaction.recipe_reaction:
                summary["reaction_counts"][reaction.recipe_reaction] = \
                    summary["reaction_counts"].get(reaction.recipe_reaction, 0) + 1
        
        return summary
    
    def _get_provider_reaction_summary(self, provider_id: int) -> Dict[str, Any]:
        """Get reaction summary for a provider"""
        reactions = self.reaction_repo.get_provider_reactions_by_target(provider_id)
        
        summary = {
            "target_id": provider_id,
            "target_type": "provider",
            "total_reactions": len(reactions),
            "reaction_counts": {},
            "average_rating": 0.0,
            "total_ratings": 0
        }
        
        # Count reactions
        for reaction in reactions:
            if reaction.provider_reaction:
                summary["reaction_counts"][reaction.provider_reaction] = \
                    summary["reaction_counts"].get(reaction.provider_reaction, 0) + 1
            
            if reaction.provider_reaction_value and reaction.provider_reaction_value > 0:
                summary["total_ratings"] += 1
                summary["average_rating"] = (summary.get("average_rating", 0) + reaction.provider_reaction_value)
        
        if summary["total_ratings"] > 0:
            summary["average_rating"] = summary["average_rating"] / summary["total_ratings"]
        
        return summary
    
    def _get_comment_reaction_summary(self, comment_id: int) -> Dict[str, Any]:
        """Get reaction summary for a comment"""
        reactions = self.reaction_repo.get_comment_reactions_by_target(comment_id)
        
        summary = {
            "target_id": comment_id,
            "target_type": "comment",
            "total_reactions": len(reactions),
            "reaction_counts": {}
        }
        
        # Count reactions
        for reaction in reactions:
            if reaction.comment_reaction:
                summary["reaction_counts"][reaction.comment_reaction] = \
                    summary["reaction_counts"].get(reaction.comment_reaction, 0) + 1
        
        return summary
    
    def get_reactions_by_user(self, user_id: int, reaction_type: Optional[ReactionType] = None) -> Dict[str, Any]:
        """Get all reactions by a user"""
        # Validate user exists
        self._validate_user_exists(user_id)
        
        if reaction_type == ReactionType.PRODUCT:
            reactions = self.reaction_repo.get_product_reactions_by_user(user_id)
        elif reaction_type == ReactionType.RECIPE:
            reactions = self.reaction_repo.get_recipe_reactions_by_user(user_id)
        elif reaction_type == ReactionType.PROVIDER:
            reactions = self.reaction_repo.get_provider_reactions_by_user(user_id)
        elif reaction_type == ReactionType.COMMENT:
            reactions = self.reaction_repo.get_comment_reactions_by_user(user_id)
        else:
            reactions = self.reaction_repo.get_all_reactions_by_user(user_id)
        
        return {
            "user_id": user_id,
            "total_reactions": len(reactions),
            "reactions": reactions
        }