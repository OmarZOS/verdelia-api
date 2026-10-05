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


async def seed_users_now(count: int = 5) -> Dict[str, Any]:
    """
    Seed users using the user service.
    
    Args:
        count: Number of users to create
        
    Returns:
        Dictionary with seeding results
    """
    logger.info(f"👤 Seeding {count} test users...")
    
    user_service = UserService()
    results = {
        "users_created": 0,
        "users_failed": 0,
        "user_ids": [],
        "errors": []
    }
    
    for i in range(count):
        try:
            test_data = generate_test_user_data(i)
            
            # Create schema objects
            user = AppUser_API(**test_data["user"])
            person = Person_API(**test_data["person"]) if test_data.get("person") else None
            location = Location_API(**test_data["location"]) if test_data.get("location") else None
            
            # Create user using service - pass None as provider (no provider data for random users)
            result = await user_service.create_user(user, person, location, None)
            
            if result and hasattr(result, 'id_app_user'):
                results["users_created"] += 1
                results["user_ids"].append(result.id_app_user)
                logger.info(f"   ✅ Created user {i+1}: {user.app_user_name} (ID: {result.id_app_user})")
            else:
                results["users_failed"] += 1
                error_msg = f"Failed to create user {i+1}: {user.app_user_name}"
                results["errors"].append(error_msg)
                logger.warning(f"   ⚠️ {error_msg}")
                
        except APIException as e:
            results["users_failed"] += 1
            error_msg = f"API error for user {i+1}: {e.message}"
            results["errors"].append(error_msg)
            logger.error(f"   ❌ {error_msg}")
        except Exception as e:
            results["users_failed"] += 1
            error_msg = f"Unexpected error for user {i+1}: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(f"   ❌ {error_msg}")
    
    logger.info(f"✅ User seeding complete: {results['users_created']} created, {results['users_failed']} failed")
    return results


async def seed_specific_users() -> Dict[str, Any]:
    """
    Seed specific test users with known credentials for testing.
    """
    logger.info("👤 Seeding specific test users...")
    
    user_service = UserService()
    results = {
        "users_created": 0,
        "users_failed": 0,
        "user_ids": [],
        "errors": []
    }
    
    # Define specific test users
    test_users = [
        {
            "user": {
                "app_user_name": "test_admin",
                "app_user_password": "Admin123!@#",
                "app_user_email": "admin@test.com",
                "app_user_type": "provider",
                "app_user_preferences": {"theme": "dark", "notifications": True, "language": "en"}
            },
            "person": {
                "person_first_name": "Admin",
                "person_last_name": "User",
                "person_birth_date": "1985-01-01",
                "person_gender": "male",
                "person_country_code": "DZ",
                "blood_type": "O+"
            },
            "location": {
                "location_latitude": 36.7538,
                "location_longitude": 3.0588,
                "location_name": "Office",
                "address_street": "123 Admin St",
                "address_city": "Algiers",
                "address_postal_code": "16000",
                "address_country": "DZ"
            },
            "provider": {
                "provider_organisation_name": "Admin Org",
                "provider_organisation_desc": "Admin organisation for testing",
                "provider_organisation_icon_url": "https://example.com/orgs/admin.png"
            }
        },
        {
            "user": {
                "app_user_name": "test_customer",
                "app_user_password": "Customer123!@#",
                "app_user_email": "customer@test.com",
                "app_user_type": "customer",
                "app_user_preferences": {"theme": "light", "notifications": True, "language": "en"}
            },
            "person": {
                "person_first_name": "Test",
                "person_last_name": "Customer",
                "person_birth_date": "1990-06-15",
                "person_gender": "female",
                "person_country_code": "DZ",
                "blood_type": "A+"
            },
            "location": {
                "location_latitude": 36.7538,
                "location_longitude": 3.0588,
                "location_name": "Home",
                "address_street": "456 Customer Ave",
                "address_city": "Algiers",
                "address_postal_code": "16000",
                "address_country": "DZ"
            },
            "provider": None
        },
        {
            "user": {
                "app_user_name": "test_provider",
                "app_user_password": "Provider123!@#",
                "app_user_email": "provider@test.com",
                "app_user_type": "provider",
                "app_user_preferences": {"theme": "dark", "notifications": False, "language": "fr"}
            },
            "person": {
                "person_first_name": "Provider",
                "person_last_name": "User",
                "person_birth_date": "1980-03-20",
                "person_gender": "male",
                "person_country_code": "DZ",
                "blood_type": "B+"
            },
            "location": {
                "location_latitude": 36.7538,
                "location_longitude": 3.0588,
                "location_name": "Clinic",
                "address_street": "789 Provider Blvd",
                "address_city": "Oran",
                "address_postal_code": "31000",
                "address_country": "DZ"
            },
            "provider": {
                "provider_organisation_name": "Provider Clinic",
                "provider_organisation_desc": "Provider clinic for testing",
                "provider_organisation_icon_url": "https://example.com/orgs/provider.png"
            }
        }
    ]
    
    for i, test_data in enumerate(test_users):
        try:
            # Create schema objects
            user = AppUser_API(**test_data["user"])
            person = Person_API(**test_data["person"]) if test_data.get("person") else None
            location = Location_API(**test_data["location"]) if test_data.get("location") else None
            
            
            # Create user using service - pass proper provider object or None
            result = await user_service.create_user(user, person, location)
            
            if result and hasattr(result, 'id_app_user'):
                results["users_created"] += 1
                results["user_ids"].append(result.id_app_user)
                logger.info(f"   ✅ Created specific user: {user.app_user_name} (ID: {result.id_app_user})")
                logger.info(f"      📧 Email: {user.app_user_email}")
                logger.info(f"      🔑 Password: {user.app_user_password}")
            else:
                results["users_failed"] += 1
                error_msg = f"Failed to create specific user: {user.app_user_name}"
                results["errors"].append(error_msg)
                logger.warning(f"   ⚠️ {error_msg}")
                
        except Exception as e:
            results["users_failed"] += 1
            error_msg = f"Error creating specific user {i+1}: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(f"   ❌ {error_msg}")
    
    return results


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
        
        # Seed users
        if seed_users:
            logger.info("\n" + "="*50)
            logger.info("👤 Seeding users...")
            
            # Create specific test users first
            if seed_specific:
                specific_results = await seed_specific_users()
                results["specific_users_created"] = specific_results["users_created"]
                results["specific_user_ids"] = specific_results["user_ids"]
                logger.info(f"   ✅ Created {specific_results['users_created']} specific test users")
                if specific_results["errors"]:
                    logger.warning(f"   ⚠️ {len(specific_results['errors'])} errors during specific user creation")
            
            # Create random users
            if user_count > 0:
                random_results = await seed_users_now(user_count)
                results["users_created"] = random_results["users_created"]
                results["user_ids"] = random_results["user_ids"]
                if random_results["errors"]:
                    logger.warning(f"   ⚠️ {len(random_results['errors'])} errors during random user creation")
            
            logger.info("="*50)
        
        # Calculate total
        results["total"] = sum([
            results["product_categories"],
            results["recipe_categories"],
            results["product_provider_types"],
            results["service_categories"],
            results["staff_roles"],
            results["ingredients"],
            results["iproducts"],
            results["plans"],
            results["users_created"],
            results["specific_users_created"],
        ])
        
        logger.info(f"\n✅ Seeding complete! Total records inserted: {results['total']}")
        
        # Log user credentials if specific users were created
        if seed_specific and results["specific_users_created"] > 0:
            logger.info("\n📋 Specific Test Users Created:")
            logger.info("   🔑 test_admin / Admin123!@#")
            logger.info("   🔑 test_customer / Customer123!@#")
            logger.info("   🔑 test_provider / Provider123!@#")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        raise


async def seed_users_only(count: int = 5, seed_specific: bool = True) -> Dict[str, Any]:
    """
    Seed only users (useful for adding users to an already seeded database).
    
    Args:
        count: Number of random users to create
        seed_specific: Whether to create specific test users
        
    Returns:
        Dictionary with seeding results
    """
    logger.info("👤 Seeding users only...")
    
    results = {
        "users_created": 0,
        "user_ids": [],
        "specific_users_created": 0,
        "specific_user_ids": [],
        "errors": []
    }
    
    # Create specific test users
    if seed_specific:
        specific_results = await seed_specific_users()
        results["specific_users_created"] = specific_results["users_created"]
        results["specific_user_ids"] = specific_results["user_ids"]
        if specific_results["errors"]:
            results["errors"].extend(specific_results["errors"])
    
    # Create random users
    if count > 0:
        random_results = await seed_users_now(count)
        results["users_created"] = random_results["users_created"]
        results["user_ids"] = random_results["user_ids"]
        if random_results["errors"]:
            results["errors"].extend(random_results["errors"])
    
    logger.info(f"✅ User seeding complete: {results['users_created'] + results['specific_users_created']} users created")
    return results


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
        
        if args.users_only:
            # Seed only users
            results = asyncio.run(seed_users_only(
                count=args.user_count,
                seed_specific=not args.no_specific_users
            ))
            
            print(f"\n✅ User seeding complete!")
            print(f"   Random Users Created: {results['users_created']}")
            print(f"   Specific Users Created: {results['specific_users_created']}")
            if results.get("specific_user_ids"):
                print(f"   Specific User IDs: {results['specific_user_ids']}")
            if results.get("user_ids"):
                print(f"   Random User IDs: {results['user_ids'][:10]}{'...' if len(results['user_ids']) > 10 else ''}")
            
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