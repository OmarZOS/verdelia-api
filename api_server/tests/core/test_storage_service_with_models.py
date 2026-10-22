# tests/test_storage_service_with_models.py
import pytest
from unittest.mock import patch, MagicMock, Mock
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy import desc, and_, or_
import sqlalchemy as sa
from core.models.models import *
from core.exceptions.handler import APIException

# Import your models

from core.models.models import (
    Product, AppUser, Cart, Invoice, Person, 
    ProductProvider, Recipe, ProductReaction, OrderedItem,
    
)

from core.models.persistent_models import (
    BusinessOperation, FinancialDocument
)

# class TestStorageServiceWithActualModels:
#     """Test StorageService with actual project models."""
    
#     # Test get_engine with actual configuration
#     def test_get_engine_with_db_uri(self, db_module):
#         """Test engine creation with database URI."""
#         test_uri = "sqlite:///:memory:"
#         engine = db_module.get_engine(test_uri)
        
#         assert engine is not None
#         assert hasattr(engine, 'connect')
#         assert hasattr(engine, 'execute')
    
#     # Test session_scope
#     def test_session_scope_with_actual_engine(self, db_module, db_engine_with_data):
#         """Test session_scope context manager."""
#         with db_module.session_scope(db_engine_with_data) as session:
#             assert session is not None
            
#             # Test we can query using the session
#             users = session.query(AppUser).all()
#             assert isinstance(users, list)
    
#     # Test add_record with actual model
#     def test_add_record_product(self, db_module, db_engine_with_data, populated_db):
#         """Test adding a Product record."""
#         # Get existing product provider
#         product_provider = populated_db['product_provider']
#         app_user = populated_db['app_user']
        
#         # Create new product
#         new_product = Product(
#             product_name="Test Product",
#             product_brand="Test Brand",
#             product_provider=product_provider,
#             product_category_id=populated_db['categories'][0].id_product_category,
#             product_description="Test description",
#             product_price=10.99,
#             product_quantity=100,
#             product_quantifier="piece",
#             product_owner=app_user.id_app_user
#         )
        
#         # Add the record
#         result = db_module.add_record(db_engine_with_data, new_product)
        
#         assert result is new_product
#         assert result.id_product is not None
#         assert result.product_name == "Test Product"
        
#         # Verify it's in the database
#         retrieved = db_module.get_record_by_id(
#             db_engine_with_data, 
#             Product, 
#             result.id_product
#         )
#         assert retrieved is not None
#         assert retrieved.product_name == "Test Product"
    
#     def test_add_record_app_user(self, db_module, db_engine_with_data, populated_db):
#         """Test adding an AppUser record."""
#         person = populated_db['person']
#         user_type = populated_db['user_types'][1]  # User type
#         wallet = MagicMock(spec=Wallet)
#         wallet.id_wallet = 999
        
#         new_user = AppUser(
#             app_user_name="newuser",
#             app_user_password="hashedpass",
#             app_user_person=person,
#             app_user_type=user_type,
#             app_user_email="newuser@example.com"
#         )
        
#         result = db_module.add_record(db_engine_with_data, new_user)
        
#         assert result is new_user
#         assert result.id_app_user is not None
#         assert result.app_user_name == "newuser"
    
#     # Test get_all_records
#     def test_get_all_records_products(self, db_module, db_engine_with_data, populated_db):
#         """Test retrieving all products."""
#         products = db_module.get_all_records(db_engine_with_data, Product)
        
#         assert isinstance(products, list)
#         assert len(products) >= 1
#         assert all(isinstance(p, Product) for p in products)
    
#     def test_get_all_records_users(self, db_module, db_engine_with_data, populated_db):
#         """Test retrieving all users."""
#         users = db_module.get_all_records(db_engine_with_data, AppUser)
        
#         assert isinstance(users, list)
#         assert len(users) >= 1
#         assert all(isinstance(u, AppUser) for u in users)
    
#     # Test get_record_by_id
#     def test_get_record_by_id_product(self, db_module, db_engine_with_data, populated_db):
#         """Test retrieving product by ID."""
#         product = populated_db['product']
        
#         retrieved = db_module.get_record_by_id(
#             db_engine_with_data,
#             Product,
#             product.id_product
#         )
        
#         assert retrieved is not None
#         assert retrieved.id_product == product.id_product
#         assert retrieved.product_name == product.product_name
    
#     def test_get_record_by_id_user(self, db_module, db_engine_with_data, populated_db):
#         """Test retrieving user by ID."""
#         user = populated_db['app_user']
        
#         retrieved = db_module.get_record_by_id(
#             db_engine_with_data,
#             AppUser,
#             user.id_app_user
#         )
        
#         assert retrieved is not None
#         assert retrieved.id_app_user == user.id_app_user
#         assert retrieved.app_user_name == user.app_user_name
    
#     # Test get_records with conditions
#     def test_get_records_with_simple_conditions(self, db_module, db_engine_with_data, populated_db):
#         """Test get_records with simple conditions."""
#         # Note: Adjust based on your actual conditions implementation
#         # The current implementation expects conditions dict with specific format
        
#         # Add a product with specific price for testing
#         product_provider = populated_db['product_provider']
#         app_user = populated_db['app_user']
        
#         high_price_product = Product(
#             product_name="Expensive Product",
#             product_brand="Luxury",
#             product_provider=product_provider,
#             product_category_id=populated_db['categories'][0].id_product_category,
#             product_price=999.99,
#             product_quantity=10,
#             product_owner=app_user.id_app_user
#         )
#         db_module.add_record(db_engine_with_data, high_price_product)
        
#         # The exact way to apply conditions depends on your implementation
#         # You might need to adjust this based on how conditions are processed
#         pass
    
#     # Test get_records with eager loading
#     def test_get_records_with_eager_loading(self, db_module, db_engine_with_data, populated_db):
#         """Test get_records with eager loading relationships."""
#         products = db_module.get_records(
#             db_engine_with_data,
#             Product,
#             eager_load_depth=["product_provider", "app_user"]
#         )
        
#         assert len(products) > 0
        
#         # With eager loading, relationships should be accessible
#         for product in products:
#             assert hasattr(product, 'product_provider')
#             # Note: In SQLAlchemy, we can't easily test if it's eager-loaded
#             # without making actual queries, but the structure should be there
    
#     def test_get_records_with_complex_eager_loading(self, db_module, db_engine_with_data):
#         """Test get_records with complex eager loading configuration."""
#         # Test nested eager loading
#         eager_config = [
#             "product_provider",
#             {"product_provider": ["product_provider_details", "product_provider_type"]},
#             "app_user"
#         ]
        
#         products = db_module.get_records(
#             db_engine_with_data,
#             Product,
#             eager_load_depth=eager_config
#         )
        
#         assert isinstance(products, list)
    
#     # Test update_record
#     def test_update_record_product(self, db_module, db_engine_with_data, populated_db):
#         """Test updating a product record."""
#         product = populated_db['product']
#         original_price = product.unit_price
        
#         # Update the product
#         product.unit_price = original_price + 10.00
#         product.product_quantity = product.product_quantity - 5
        
#         updated = db_module.update_record(db_engine_with_data, product)
        
#         assert updated.unit_price == original_price + 10.00
        
#         # Verify update persisted
#         retrieved = db_module.get_record_by_id(
#             db_engine_with_data,
#             Product,
#             product.id_product
#         )
#         assert retrieved.unit_price == original_price + 10.00
    
#     # Test delete_record
#     def test_delete_record_product(self, db_module, db_engine_with_data):
#         """Test deleting a product record."""
#         # Create a product to delete
#         product_provider = MagicMock(spec=ProductProvider)
#         product_provider.id_product_provider = 1
        
#         product = Product(
#             product_name="Product to Delete",
#             product_brand="Test",
#             product_provider=product_provider,
#             product_price=10.00,
#             product_quantity=50,
#             product_owner=1
#         )
        
#         added = db_module.add_record(db_engine_with_data, product)
#         product_id = added.id_product
        
#         # Delete the product
#         result = db_module.delete_record(db_engine_with_data, added)
        
#         # Verify deletion
#         deleted = db_module.get_record_by_id(db_engine_with_data, Product, product_id)
#         assert deleted is None
    
#     # Test count_records
#     def test_count_records_products(self, db_module, db_engine_with_data, populated_db):
#         """Test counting product records."""
#         count = db_module.count_records(db_engine_with_data, Product)
        
#         assert isinstance(count, int)
#         assert count >= 1
    
#     def test_count_records_with_conditions(self, db_module, db_engine_with_data):
#         """Test count_records with conditions."""
#         # This depends on how conditions are implemented
#         # You might need InstrumentedAttribute for conditions
#         pass
    
#     # Test search_records
#     def test_search_records_by_product_name(self, db_module, db_engine_with_data, populated_db):
#         """Test searching products by name."""
#         # Add more test products
#         product_provider = populated_db['product_provider']
#         app_user = populated_db['app_user']
        
#         products = [
#             Product(
#                 product_name="Special Gluten Free Bread",
#                 product_provider=product_provider,
#                 product_price=6.99,
#                 product_quantity=30,
#                 product_owner=app_user.id_app_user
#             ),
#             Product(
#                 product_name="Regular Wheat Bread",
#                 product_provider=product_provider,
#                 product_price=3.99,
#                 product_quantity=40,
#                 product_owner=app_user.id_app_user
#             ),
#         ]
        
#         for product in products:
#             db_module.add_record(db_engine_with_data, product)
        
#         # Search for gluten free products
#         results = db_module.search_records(
#             db_engine_with_data,
#             Product,
#             join_tables=None,
#             eager_load_depth=None,
#             search_query="Gluten Free",
#             search_fields=["product_name"]
#         )
        
#         assert len(results) >= 1
#         assert any("Gluten Free" in p.product_name for p in results)
    
#     def test_search_records_multiple_fields(self, db_module, db_engine_with_data, populated_db):
#         """Test search across multiple fields."""
#         product_provider = populated_db['product_provider']
#         app_user = populated_db['app_user']
        
#         # Create product with specific description
#         product = Product(
#             product_name="Test Search Product",
#             product_description="This is a premium gluten-free organic product",
#             product_provider=product_provider,
#             product_price=15.99,
#             product_quantity=20,
#             product_owner=app_user.id_app_user
#         )
        
#         db_module.add_record(db_engine_with_data, product)
        
#         # Search in both name and description
#         results = db_module.search_records(
#             db_engine_with_data,
#             Product,
#             join_tables=None,
#             eager_load_depth=None,
#             search_query="premium organic",
#             search_fields=["product_name", "product_description"]
#         )
        
#         assert len(results) >= 1
    
#     # Test build_eager_options with actual models
#     def test_build_eager_options_product_relationships(self, db_module):
#         """Test building eager options for product relationships."""
#         options = db_module.build_eager_options(
#             Product,
#             [
#                 "product_provider",
#                 "app_user",
#                 {"product_provider": ["product_provider_details"]}
#             ]
#         )
        
#         assert isinstance(options, list)
#         assert len(options) == 3
    
#     def test_build_eager_options_user_relationships(self, db_module):
#         """Test building eager options for user relationships."""
#         options = db_module.build_eager_options(
#             AppUser,
#             [
#                 "app_user_person",
#                 "app_user_type",
#                 {"app_user_person": ["person_details", "person_blood_type"]}
#             ]
#         )
        
#         assert isinstance(options, list)
#         assert len(options) == 3
    
#     # Test get_records_by_filter
#     def test_get_records_by_filter_simple(self, db_module, db_engine_with_data, populated_db):
#         """Test simple filtered query."""
#         results = db_module.get_records_by_filter(
#             db_engine_with_data,
#             Product,
#             offset=0,
#             limit=10
#         )
        
#         assert isinstance(results, list)
#         assert len(results) > 0
    
#     def test_get_records_by_filter_with_ordering(self, db_module, db_engine_with_data):
#         """Test filtered query with ordering."""
#         # Add products with different prices
#         product_provider = MagicMock(spec=ProductProvider)
#         product_provider.id_product_provider = 1
        
#         products = [
#             Product(product_name="Cheap", product_price=5.00, product_provider=product_provider, product_owner=1),
#             Product(product_name="Medium", product_price=15.00, product_provider=product_provider, product_owner=1),
#             Product(product_name="Expensive", product_price=25.00, product_provider=product_provider, product_owner=1),
#         ]
        
#         for product in products:
#             db_module.add_record(db_engine_with_data, product)
        
#         # Order by price descending
#         from sqlalchemy import desc
#         ordering_attr = [desc(Product.unit_price)]
        
#         results = db_module.get_records_by_filter(
#             db_engine_with_data,
#             Product,
#             ordering_attr=ordering_attr,
#             offset=0,
#             limit=10
#         )
        
#         # Results should be ordered by price descending
#         # Note: This depends on your implementation
#         pass
    
#     # Test with view models (BusinessOperation, FinancialDocument)
#     def test_get_records_view_models(self, db_module, db_engine_with_data):
#         """Test getting records from view models."""
#         # Note: BusinessOperation and FinancialDocument are views
#         # They might not work with SQLite in tests, but we can test the structure
        
#         # This would test if we can query view models
#         # In practice with SQLite, these might not exist
#         pass
    
#     # Test error handling
#     def test_add_record_with_invalid_data(self, db_module, db_engine_with_data):
#         """Test adding record with invalid data."""
#         # Try to add a product without required fields
#         product = Product()  # Missing required fields
        
#         with pytest.raises(Exception):
#             db_module.add_record(db_engine_with_data, product)
    
#     def test_get_record_by_id_nonexistent(self, db_module, db_engine_with_data):
#         """Test getting non-existent record."""
#         result = db_module.get_record_by_id(db_engine_with_data, Product, 999999)
        
#         assert result is None
    
#     # Test edge cases
#     def test_get_records_empty_table(self, db_module, db_engine_with_data):
#         """Test getting records from empty table."""
#         # Use a model that should be empty (or create a test-only model)
#         # For example, if you have a model that's not populated in tests
#         pass
    
#     def test_get_records_with_large_limit(self, db_module, db_engine_with_data):
#         """Test getting records with large limit."""
#         results = db_module.get_records(
#             db_engine_with_data,
#             Product,
#             offset=0,
#             limit=1000  # Large limit
#         )
        
#         assert isinstance(results, list)
#         # Should not crash with large limit

# class TestComplexQueries:
#     """Test complex query scenarios."""
    
#     def test_nested_eager_loading(self, db_module, db_engine_with_data, populated_db):
#         """Test deeply nested eager loading."""
#         eager_config = [
#             "product_provider",
#             {
#                 "product_provider": [
#                     "product_provider_details",
#                     "product_provider_type",
#                     "product_provider_org",
#                     {"product_provider_org": ["provider_organisation_wallet"]}
#                 ]
#             },
#             "app_user",
#             {"app_user": ["app_user_person", "app_user_type"]}
#         ]
        
#         products = db_module.get_records(
#             db_engine_with_data,
#             Product,
#             eager_load_depth=eager_config,
#             limit=5
#         )
        
#         assert isinstance(products, list)
    
#     def test_search_with_relationships(self, db_module, db_engine_with_data, populated_db):
#         """Test search across relationship fields."""
#         # This tests searching through related tables
#         # e.g., product -> product_provider -> provider_details
        
#         results = db_module.search_records(
#             db_engine_with_data,
#             Product,
#             join_tables=None,
#             eager_load_depth=None,
#             search_query="Test",  # Search term
#             search_fields=[
#                 "product_name",
#                 "product_description",
#                 "product_provider.product_provider_details.provider_name"
#             ]
#         )
        
#         # The exact results depend on your test data
#         assert isinstance(results, list)
    
#     def test_count_with_group_by(self, db_module, db_engine_with_data):
#         """Test count with group by clause."""
#         # Add products with different categories
#         product_provider = MagicMock(spec=ProductProvider)
#         product_provider.id_product_provider = 1
        
#         # This would require InstrumentedAttribute for group_by
#         # group_by_attr = Product.product_category_id
        
#         # count_by_category = db_module.count_records(
#         #     db_engine_with_data,
#         #     Product,
#         #     group_by=group_by_attr
#         # )
        
#         # assert isinstance(count_by_category, list)
#         # assert all(isinstance(item, tuple) and len(item) == 2 for item in count_by_category)
#         pass

# class TestTransactionHandling:
#     """Test transaction handling scenarios."""
    
#     def test_transaction_rollback_on_error(self, db_module, db_engine_with_data):
#         """Test that transactions roll back on error."""
#         # Start a transaction
#         with db_module.session_scope(db_engine_with_data) as session:
#             # Create a product
#             product_provider = MagicMock(spec=ProductProvider)
#             product_provider.id_product_provider = 1
            
#             product1 = Product(
#                 product_name="Product 1",
#                 product_provider=product_provider,
#                 product_price=10.00,
#                 product_owner=1
#             )
#             session.add(product1)
#             session.flush()  # Assign ID but don't commit yet
            
#             product1_id = product1.id_product
            
#             # Intentionally cause an error
#             raise ValueError("Test rollback")
        
#         # The transaction should have rolled back
#         # Product1 should not exist
#         retrieved = db_module.get_record_by_id(db_engine_with_data, Product, product1_id)
#         assert retrieved is None
    
#     def test_concurrent_sessions(self, db_module, db_engine_with_data):
#         """Test handling of concurrent sessions."""
#         # Create two products in separate sessions
#         product_provider = MagicMock(spec=ProductProvider)
#         product_provider.id_product_provider = 1
        
#         product1 = Product(
#             product_name="Concurrent Product 1",
#             product_provider=product_provider,
#             product_price=10.00,
#             product_owner=1
#         )
        
#         product2 = Product(
#             product_name="Concurrent Product 2", 
#             product_provider=product_provider,
#             product_price=20.00,
#             product_owner=1
#         )
        
#         # Add in separate operations
#         result1 = db_module.add_record(db_engine_with_data, product1)
#         result2 = db_module.add_record(db_engine_with_data, product2)
        
#         assert result1.id_product != result2.id_product
        
#         # Both should be retrievable
#         retrieved1 = db_module.get_record_by_id(db_engine_with_data, Product, result1.id_product)
#         retrieved2 = db_module.get_record_by_id(db_engine_with_data, Product, result2.id_product)
        
#         assert retrieved1 is not None
#         assert retrieved2 is not None

# # class TestModelSpecificTests:
# #     """Tests specific to certain models."""
    
# #     def test_location_model_geometry(self, db_module, db_engine_with_data):
# #         """Test Location model with geometry field."""
# #         address = MagicMock(spec=Address)
# #         address.id_address = 1
        
# #         location = Location(
# #             location_name="Test Location",
# #             location_address=address,
# #             location_postal_code=12345
# #             # Note: location_position (Geometry field) might be tricky in SQLite
# #         )
        
# #         result = db_module.add_record(db_engine_with_data, location)
        
# #         assert result is location
# #         assert result.id_location is not None
    
# #     def test_cart_with_relationships(self, db_module, db_engine_with_data, populated_db):
# #         """Test Cart model with all relationships."""
# #         cart = populated_db['cart']
        
# #         # Test eager loading all relationships
# #         eager_config = [
# #             "cart_product_provider",
# #             "app_user",  # cart_selling_user relationship
# #             "app_user_",  # cart_client_user relationship  
# #             "person",
# #             "delivery",
# #             "invoice",
# #             "receipt",
# #             "ordered_item",
# #             "ordered_service"
# #         ]
        
# #         carts = db_module.get_records(
# #             db_engine_with_data,
# #             Cart,
# #             eager_load_depth=eager_config,
# #             limit=1
# #         )
        
# #         if carts:
# #             cart = carts[0]
# #             assert hasattr(cart, 'cart_product_provider')
# #             assert hasattr(cart, 'app_user')
# #             assert hasattr(cart, 'app_user_')
    
# #     def test_invoice_payment_flow(self, db_module, db_engine_with_data, populated_db):
# #         """Test the invoice-payment-receipt flow."""
# #         invoice = populated_db['invoice']
# #         payment = populated_db['payment']
# #         receipt = populated_db['receipt']
        
# #         # Test retrieving invoice with payments and receipts
# #         invoices = db_module.get_records(
# #             db_engine_with_data,
# #             Invoice,
# #             eager_load_depth=["payment", "invoice_cart", "placed_order"],
# #             limit=1
# #         )
        
# #         if invoices:
# #             inv = invoices[0]
# #             assert hasattr(inv, 'payment')
# #             assert hasattr(inv, 'invoice_cart')
# #             assert hasattr(inv, 'placed_order')
    
#     # def test_recipe_with_ingredients(self, db_module, db_engine_with_data, populated_db):
#     #     """Test Recipe model with ingredients."""
#     #     recipe = populated_db['recipe']
        
#     #     # Test eager loading recipe with ingredients
#     #     recipes = db_module.get_records(
#     #         db_engine_with_data,
#     #         Recipe,
#     #         eager_load_depth=[
#     #             "recipe_owner",
#     #             "recipe_category",
#     #             {"recipe_contains_ingredient": ["contained_ingredient"]}
#     #         ],
#     #         limit=1
#     #     )
        
#     #     if recipes:
#     #         recipe = recipes[0]
#     #         assert hasattr(recipe, 'recipe_owner')
#     #         assert hasattr(recipe, 'recipe_category')
#     #         assert hasattr(recipe, 'recipe_contains_ingredient')

# # Run with: pytest tests/test_storage_service_with_models.py -v