# storage/seed.py (main seed orchestrator with user seeding)
"""
Database seeding module for DEV environment.
Populates the database with initial test data including users.
"""

from sqlalchemy import inspect
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import random
import asyncio

from core.logging_config import get_logger
from core.models.api_models import AppUser_API, Location_API, Person_API, ProductProvider_API
from services.user_service import UserService
from storage.seeds.iproduct import seed_random_iproducts
import config
from storage.storage_broker import get_engine, session_scope, get, text
from storage.seeds.product_category import seed_product_categories
from storage.seeds.recipe_category import seed_recipe_categories
from storage.seeds.provider_type import seed_product_provider_types
from storage.seeds.provided_service_category import seed_service_categories
from storage.seeds.staff_role import seed_staff_roles
from storage.seeds.ingredient import seed_ingredients
from storage.seeds.plan import seed as seed_plans
from config import settings
from core.models import models
from core.exceptions.handler import APIException

from core.logging_config import get_logger

logger = get_logger(__name__)



# ==================== User Seeding Functions ====================

def generate_test_user_data(index: int = 0) -> Dict[str, Any]:
    """Generate test user data for seeding"""
    first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Maria", "Ahmed"]
    last_names = ["Smith", "Doe", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Benali", "Khan"]
    cities = ["Algiers", "Oran", "Constantine", "Annaba", "Blida", "Setif", "Tizi Ouzou", "Bejaia"]
    
    fn = first_names[index % len(first_names)]
    ln = last_names[index % len(last_names)]
    
    return {
        "user": {
            "app_user_name": f"seeduser_{fn.lower()}_{index}",
            "app_user_password": f"SeedTest{index}!@#",
            "app_user_email": f"seed_{fn.lower()}.{ln.lower()}_{index}@example.com",
            "app_user_type": "customer" if index % 3 != 0 else "provider",
            "app_user_preferences": {
                "theme": "light" if index % 2 == 0 else "dark",
                "notifications": True,
                "language": "en"
            },
            "app_user_image_url": f"https://example.com/avatars/seed_{index}.jpg"
        },
        "person": {
            "person_first_name": fn,
            "person_last_name": ln,
            "person_birth_date": f"{random.randint(1950, 2005)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "person_gender": "male" if index % 2 == 0 else "female",
            "person_country_code": "DZ",
            "blood_type": random.choice(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
        },
        "location": {
            "location_latitude": round(random.uniform(35.0, 37.0), 6),
            "location_longitude": round(random.uniform(-5.0, 8.0), 6),
            "location_name": "Home" if index % 2 == 0 else "Work",
            "address_street": f"{random.randint(1, 999)} Main St",
            "address_city": cities[index % len(cities)],
            "address_postal_code": f"{random.randint(1000, 9999)}",
            "address_country": "DZ"
        },
        "provider": {
            "provider_organisation_name": f"SeedOrg_{fn}_{ln}_{index}",
            "provider_organisation_desc": f"Seeded organisation for {fn} {ln}",
            "provider_organisation_icon_url": f"https://example.com/orgs/seed_{index}.png"
        } if index % 3 == 0 else None
    }




# ==================== Main Seed Functions ====================

async def seed_database(
    with_icons: bool = False,
    with_quantifiers: bool = False,
    seed_users: bool = True,
    user_count: int = 5,
    seed_specific: bool = True
) -> Dict[str, Any]:
    """
    Run all seed functions including users.
    
    Args:
        with_icons: Whether to seed with icon URLs
        with_quantifiers: Whether to seed ingredients with quantifiers
        seed_users: Whether to seed users
        user_count: Number of random users to create
        seed_specific: Whether to create specific test users
        
    Returns:
        Dictionary with seeding results
    """
    logger.info("🌱 Starting database seeding...")
    
    results = {
        "product_categories": 0,
        "recipe_categories": 0,
        "product_provider_types": 0,
        "service_categories": 0,
        "staff_roles": 0,
        "ingredients": 0,
        "iproducts": 0,
        "plans": 0,
        "users_created": 0,
        "user_ids": [],
        "specific_users_created": 0,
        "specific_user_ids": [],
        "total": 0,
    }
    
    try:
        # Seed product categories
        logger.info("Seeding product categories...")
        results["product_categories"] = seed_product_categories()
        
        # # Seed recipe categories
        # logger.info("Seeding recipe categories...")
        # results["recipe_categories"] = seed_recipe_categories(use_icons=with_icons)
        
        # Seed product provider types
        logger.info("Seeding product provider types...")
        results["product_provider_types"] = seed_product_provider_types(use_icons=with_icons)
        
        # Seed provided service categories
        logger.info("Seeding provided service categories...")
        results["service_categories"] = seed_service_categories()
        
        # Seed staff roles
        logger.info("Seeding staff roles...")
        results["staff_roles"] = seed_staff_roles()
        
        # Seed plans
        logger.info("Seeding plans...")
        results["plans"] = seed_plans()
        
        # # Seed ingredients
        # logger.info("Seeding ingredients...")
        # results["ingredients"] = seed_ingredients()
        
        # Seed iproducts
        logger.info("Seeding iproducts...")
        results["iproducts"] = seed_random_iproducts()
        
        
        # Calculate total
        results["total"] = sum([
            results["product_categories"],
            results["product_provider_types"],
            results["service_categories"],
            results["iproducts"],
            # results["plans"],
        ])
        
        logger.info(f"\n✅ Seeding complete! Total records inserted: {results['total']}")
        
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        raise




# ==================== Status and Helper Functions ====================

def get_seed_status() -> Dict[str, Any]:
    """
    Get the current seeding status including users.
    
    Returns:
        Dictionary with seeding status information
    """
    try:
        engine = get_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        status = {
            "has_tables": bool(tables),
            "has_product_categories": False,
            "has_recipe_categories": False,
            "has_product_provider_types": False,
            "has_service_categories": False,
            "has_staff_roles": False,
            "has_ingredients": False,
            "has_iproducts": False,
            "has_plans": False,
            "has_users": False,
            "product_category_count": 0,
            "recipe_category_count": 0,
            "product_provider_type_count": 0,
            "service_category_count": 0,
            "staff_role_count": 0,
            "ingredient_count": 0,
            "iproduct_count": 0,
            "plan_count": 0,
            "user_count": 0,
            "needs_seeding": True,
        }
        
        # Check each table
        table_checks = [
            ('product_category', 'has_product_categories', 'product_category_count'),
            ('recipe_category', 'has_recipe_categories', 'recipe_category_count'),
            ('product_provider_type', 'has_product_provider_types', 'product_provider_type_count'),
            ('provided_service_category', 'has_service_categories', 'service_category_count'),
            ('staff_role', 'has_staff_roles', 'staff_role_count'),
            ('ingredient', 'has_ingredients', 'ingredient_count'),
            ('iproduct', 'has_iproducts', 'iproduct_count'),
            ('plan', 'has_plans', 'plan_count'),
            ('app_user', 'has_users', 'user_count'),
        ]
        
        for table_name, has_flag, count_field in table_checks:
            if table_name in tables:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    status[has_flag] = count > 0
                    status[count_field] = count
        
        # Determine if seeding is needed (any table is empty)
        status["needs_seeding"] = not all([
            status["has_product_categories"],
            status["has_recipe_categories"],
            status["has_product_provider_types"],
            status["has_service_categories"],
            status["has_staff_roles"],
            status["has_ingredients"],
            status["has_iproducts"],
            status["has_plans"],
            status["has_users"],
        ])
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get seed status: {e}")
        return {
            "has_tables": False,
            "has_product_categories": False,
            "has_recipe_categories": False,
            "has_product_provider_types": False,
            "has_service_categories": False,
            "has_staff_roles": False,
            "has_ingredients": False,
            "has_iproducts": False,
            "has_plans": False,
            "has_users": False,
            "product_category_count": 0,
            "recipe_category_count": 0,
            "product_provider_type_count": 0,
            "service_category_count": 0,
            "staff_role_count": 0,
            "ingredient_count": 0,
            "iproduct_count": 0,
            "plan_count": 0,
            "user_count": 0,
            "needs_seeding": True,
            "error": str(e)
        }


def needs_seeding() -> bool:
    """
    Check if the database needs seeding including users.
    
    Returns:
        True if database is empty or needs seeding, False otherwise
    """
    try:
        engine = get_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # If no tables exist, we need seeding
        if not tables:
            logger.info("No tables found - seeding needed")
            return True
        
        # Check each table
        table_checks = [
            'product_category',
            'recipe_category',
            'product_provider_type',
            'provided_service_category',
            'staff_role',
            'ingredient',
            'plan',
            'app_user',
        ]
        
        all_have_data = True
        for table_name in table_checks:
            if table_name in tables:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    if count == 0:
                        logger.info(f"Table '{table_name}' is empty - seeding needed")
                        all_have_data = False
                        break
            else:
                logger.info(f"Table '{table_name}' doesn't exist - seeding needed")
                all_have_data = False
                break
        
        if all_have_data:
            logger.info("All tables have data - no seeding needed")
        
        return not all_have_data
        
    except Exception as e:
        logger.warning(f"Failed to check seeding need: {e}")
        return True


async def seed_database_if_needed():
    """
    Seed the database with initial data if in DEV mode and seeding is needed.
    This function is meant to be called during application startup.
    """
    # Check if we're in DEV mode
    is_dev = settings.DEBUG != "PRODUCTION"
    if not is_dev:
        logger.info("Not in DEV mode - skipping database seeding")
        return
    
    try:
        # Check if seeding is needed
        if not needs_seeding():
            logger.info("Database already has seed data - skipping seeding")
            return
        
        logger.info("🌱 Starting database seeding in DEV mode...")
        
        # Run the seed with users
        await seed_database(
            with_icons=True,
            with_quantifiers=True,
            seed_users=True,
            user_count=5,
            seed_specific=True
        )
        logger.info("✅ Database seeding completed successfully")
        
        # Log seed status
        status = get_seed_status()
        logger.info(f"📊 Seed status: {status}")
            
    except Exception as e:
        logger.error(f"❌ Failed to seed database: {e}")
        # Don't raise - let the application start anyway


# ==================== CLI Seeding Function ====================

def seed_database_cli():
    """
    Run database seeding from command line.
    Usage: python -m storage.seed
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed the database")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force seeding even if data already exists"
    )
    parser.add_argument(
        "--with-icons",
        action="store_true",
        help="Seed with icon URLs (for categories and provider types)"
    )
    parser.add_argument(
        "--with-quantifiers",
        action="store_true",
        help="Seed ingredients with quantifiers"
    )
    parser.add_argument(
        "--clear-all",
        action="store_true",
        help="Clear all seeded tables before seeding"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--users-only",
        action="store_true",
        help="Seed only users (skip other seed data)"
    )
    parser.add_argument(
        "--plans-only",
        action="store_true",
        help="Seed only plans (skip other seed data)"
    )
    parser.add_argument(
        "--user-count",
        type=int,
        default=5,
        help="Number of random users to create (default: 5)"
    )
    parser.add_argument(
        "--no-specific-users",
        action="store_true",
        help="Skip creating specific test users"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    print("🌱 Starting database seeding...")
    
    try:
        if args.clear_all:
            print("Clearing all seeded tables...")
            with session_scope() as db:
                # Delete in reverse order of dependencies
                db.query(models.StaffRole).delete()
                db.query(models.ProvidedServiceCategory).delete()
                db.query(models.Ingredient).delete()
                db.query(models.RecipeCategory).delete()
                db.query(models.ProductProviderType).delete()
                db.query(models.ProductCategory).delete()
                db.query(models.AppUser).delete()
                db.query(models.Person).delete()
                db.query(models.Wallet).delete()
                db.query(models.Plan).delete()
                db.commit()
            print("Cleared all seeded tables")
        elif args.force:
            print("Force seeding enabled - checking existing data...")
        
            
        elif args.plans_only:
            # Seed only plans
            count = seed_plans()
            print(f"\n✅ Plan seeding complete!")
            print(f"   Plans Created: {count}")
            
        else:
            # Full seed including users
            results = asyncio.run(seed_database(
                with_icons=args.with_icons,
                with_quantifiers=args.with_quantifiers,
                seed_users=True,
                user_count=args.user_count,
                seed_specific=not args.no_specific_users
            ))
            
            print(f"\n✅ Seeding complete!")
            print(f"   Product Categories: {results['product_categories']}")
            print(f"   Recipe Categories: {results['recipe_categories']}")
            print(f"   Product Provider Types: {results['product_provider_types']}")
            print(f"   Service Categories: {results['service_categories']}")
            print(f"   Staff Roles: {results['staff_roles']}")
            print(f"   Ingredients: {results['ingredients']}")
            print(f"   IProducts: {results['iproducts']}")
            print(f"   Plans: {results['plans']}")
            print(f"   Random Users: {results['users_created']}")
            print(f"   Specific Users: {results['specific_users_created']}")
            print(f"   Total: {results['total']}")
        
        # Show status
        status = get_seed_status()
        print(f"\n📊 Database Status:")
        print(f"   Product Categories: {status['product_category_count']}")
        print(f"   Recipe Categories: {status['recipe_category_count']}")
        print(f"   Product Provider Types: {status['product_provider_type_count']}")
        print(f"   Service Categories: {status['service_category_count']}")
        print(f"   Staff Roles: {status['staff_role_count']}")
        print(f"   Ingredients: {status['ingredient_count']}")
        print(f"   IProducts: {status['iproduct_count']}")
        print(f"   Plans: {status['plan_count']}")
        print(f"   Users: {status['user_count']}")
        
        if not args.users_only and not args.no_specific_users:
            print(f"\n📋 Specific Test Users Created:")
            print(f"   🔑 test_admin / Admin123!@#")
            print(f"   🔑 test_customer / Customer123!@#")
            print(f"   🔑 test_provider / Provider123!@#")
        
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        raise


# ==================== Module Export ====================

__all__ = [
    'seed_database',
    'seed_database_if_needed',
    'needs_seeding',
    'get_seed_status',
    'seed_database_cli',
    'seed_users',
    'seed_users_only',
    'seed_specific_users',
]


# ==================== CLI Entry Point ====================

if __name__ == "__main__":
    seed_database_cli()