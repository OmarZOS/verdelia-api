# tests/test_storage_service.py
import pytest
from unittest.mock import patch, MagicMock, Mock
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import InstrumentedAttribute
import sqlalchemy as sa
from core.models.models import AppUser, Product
from core.models.persistent_models import Base
from core.exceptions.handler import APIException

# class TestDatabaseUtilities:
#     """Test suite for database utility functions."""
    
#     # Test get_engine
#     def test_get_engine_success(self, db_module):
#         """Test successful engine creation."""
#         with patch('storage.storage_service.StorageService.create_engine') as mock_create_engine:
#             mock_engine = MagicMock()
#             mock_create_engine.return_value = mock_engine
            
#             engine = db_module.get_engine('sqlite:///:memory:')
            
#             assert engine == mock_engine
#             mock_create_engine.assert_called_once_with('sqlite:///:memory:')
    
#     def test_get_engine_failure(self, db_module):
#         """Test engine creation failure."""
#         with patch('storage.storage_service.StorageService.create_engine') as mock_create_engine:
#             mock_create_engine.side_effect = OperationalError("test", "test", "test")
            
#             with pytest.raises(APIException) as exc_info:
#                 db_module.get_engine('invalid://uri')
            
#             assert exc_info.value.code == "DATABASE_ERROR"
#             assert exc_info.value.status == 511  # HTTP_511_NETWORK_AUTHENTICATION_REQUIRED
    
#     # Test session_scope context manager
#     def test_session_scope_success(self, db_module, test_engine):
#         """Test successful session scope."""
#         with db_module.session_scope(test_engine) as session:
#             assert session is not None
#             assert hasattr(session, 'commit')
#             assert hasattr(session, 'rollback')
#             assert hasattr(session, 'close')
    
#     def test_session_scope_exception_handling(self, db_module, test_engine):
#         """Test session scope rollback on exception."""
#         with patch('storage.storage_service.StorageService.get_session') as mock_get_session:
#             mock_session = MagicMock()
#             mock_get_session.return_value = mock_session
#             mock_session.commit.side_effect = Exception("Test error")
            
#             with pytest.raises(Exception, match="Test error"):
#                 with db_module.session_scope(test_engine):
#                     pass
            
#             mock_session.rollback.assert_called_once()
#             mock_session.close.assert_called_once()
    
#     # Test get_session
#     # def test_get_session_without_object(self, db_module, test_engine):
#     #     """Test get_session without existing object session."""
#     #     session = db_module.get_session(test_engine)
#     #     assert session is not None
    
#     def test_get_session_with_object_has_session(self, db_module, test_engine, db_session):
#         """Test get_session when object already has a session."""
#         # Create a test object in a session
#         obj = Product(product_name="Test", product_code="TEST", product_price=100)
#         db_session.add(obj)
#         db_session.flush()
        
#         # Mock object_session to return existing session
#         with patch('storage.storage_service.StorageService.object_session') as mock_object_session:
#             mock_object_session.return_value = db_session
            
#             session = db_module.get_session(test_engine, obj)
            
#             assert session == db_session
#             mock_object_session.assert_called_once_with(obj)
    
#     # Test add_record
#     def test_add_record_success(self, db_module, db_engine_with_data, populated_db):
#         """Test adding a single record."""
#         # Create new product
#         new_product = Product(
#             product_name="New Product",
#             product_code="NP001",
#             product_price=1500
#         )
        
#         # Add the record
#         result = db_module.add_record(db_engine_with_data, new_product)
        
#         # Verify the result
#         assert result is new_product
#         assert result.product_id is not None  # Should have been assigned by DB
#         assert result.product_name == "New Product"
    
#     def test_add_record_with_existing_session(self, db_module, db_engine_with_data, db_session):
#         """Test add_record when object already has a session."""
#         # Create object and add to session
#         obj = Product(product_name="Test", product_code="TEST", product_price=100)
#         db_session.add(obj)
#         db_session.flush()  # Assign ID but don't commit
        
#         # Mock get_session to return the existing session
#         with patch.object(db_module, 'get_session') as mock_get_session:
#             mock_get_session.return_value = db_session
            
#             result = db_module.add_record(db_engine_with_data, obj)
            
#             assert result == obj
#             db_session.commit.assert_called()  # Should have been called in session_scope
    
#     # Test add_records
#     def test_add_records_success(self, db_module, db_engine_with_data):
#         """Test adding multiple records."""
#         products = [
#             Product(product_name="Product 1", product_code="P1", product_price=100),
#             Product(product_name="Product 2", product_code="P2", product_price=200),
#             Product(product_name="Product 3", product_code="P3", product_price=300),
#         ]
        
#         results = db_module.add_records(db_engine_with_data, products)
        
#         assert len(results) == 3
#         for i, result in enumerate(results):
#             assert result.product_id is not None
#             assert result.product_name == f"Product {i+1}"
    
#     # Test get_all_records
#     def test_get_all_records(self, db_module, db_engine_with_data, populated_db):
#         """Test retrieving all records from a table."""
#         products = db_module.get_all_records(db_engine_with_data, Product)
        
#         assert len(products) == 3
#         assert all(isinstance(p, Product) for p in products)
        
#         # Check product names
#         product_names = {p.product_name for p in products}
#         assert "Product A" in product_names
#         assert "Product B" in product_names
#         assert "Product C" in product_names
    
#     # Test get_record_by_id
#     def test_get_record_by_id_exists(self, db_module, db_engine_with_data, populated_db):
#         """Test retrieving record by existing ID."""
#         # Get a product ID from populated data
#         product_id = populated_db['products'][0].product_id
        
#         # Retrieve the record
#         product = db_module.get_record_by_id(db_engine_with_data, Product, product_id)
        
#         assert product is not None
#         assert product.product_id == product_id
#         assert product.product_name == "Product A"
    
#     def test_get_record_by_id_not_exists(self, db_module, db_engine_with_data):
#         """Test retrieving non-existent record."""
#         product = db_module.get_record_by_id(db_engine_with_data, Product, 9999)
        
#         assert product is None
    
#     # Test _get_attr_key helper
#     def test_get_attr_key_string(self, db_module):
#         """Test _get_attr_key with string input."""
#         result = db_module._get_attr_key("field_name")
#         assert result == "field_name"
    
#     def test_get_attr_key_instrumented_attribute(self, db_module):
#         """Test _get_attr_key with InstrumentedAttribute."""
#         mock_attr = MagicMock()
#         mock_attr.key = "mock_key"
        
#         result = db_module._get_attr_key(mock_attr)
#         assert result == "mock_key"
    
#     def test_get_attr_key_with_dot_notation(self, db_module):
#         """Test _get_attr_key with dot notation string."""
#         mock_attr = MagicMock()
#         mock_attr.key = None
#         mock_attr.__str__ = Mock(return_value="Model.field_name")
        
#         result = db_module._get_attr_key(mock_attr)
#         assert result == "field_name"
    
#     # Test _resolve_attr helper
#     def test_resolve_attr_success(self, db_module):
#         """Test _resolve_attr with existing attribute."""
#         class MockModel:
#             field_name = "value"
        
#         result = db_module._resolve_attr(MockModel(), "field_name")
#         assert result == "value"
    
#     def test_resolve_attr_not_found(self, db_module):
#         """Test _resolve_attr with non-existent attribute."""
#         class MockModel:
#             pass
        
#         with pytest.raises(ValueError, match="has no attribute"):
#             db_module._resolve_attr(MockModel(), "non_existent")
    
#     # Test build_eager_options
#     def test_build_eager_options_simple_column(self, db_module):
#         """Test building eager options with simple column."""
#         options = db_module.build_eager_options(AppUser, ["user_name"])
        
#         assert len(options) == 1
#         # Should create a load_only option
    
#     def test_build_eager_options_relationship(self, db_module):
#         """Test building eager options with relationship."""
#         options = db_module.build_eager_options(AppUser, ["person"])
        
#         assert len(options) == 1
#         # Should create a joinedload option
    
#     def test_build_eager_options_nested_dict(self, db_module):
#         """Test building eager options with nested dictionary."""
#         options = db_module.build_eager_options(
#             AppUser,
#             [{"person": ["person_name", "person_email"]}]
#         )
        
#         assert len(options) == 1
#         # Should create a joinedload with nested options
    
#     def test_build_eager_options_mixed(self, db_module):
#         """Test building eager options with mixed fields."""
#         options = db_module.build_eager_options(
#             AppUser,
#             [
#                 "user_name",
#                 "person",
#                 {"person": ["person_name"]},
#                 {"user_type": ["user_type_name"]}
#             ]
#         )
        
#         assert len(options) == 4
    
#     def test_build_eager_options_invalid_relationship(self, db_module):
#         """Test building eager options with invalid relationship."""
#         with pytest.raises(ValueError, match="is not a relationship"):
#             db_module.build_eager_options(
#                 AppUser,
#                 [{"non_existent": ["field"]}]
#             )
    
#     def test_build_eager_options_invalid_field(self, db_module):
#         """Test building eager options with invalid field."""
#         with pytest.raises(ValueError, match="is not a recognized relationship/column"):
#             db_module.build_eager_options(AppUser, ["non_existent_field"])
    
#     # Test get_records
#     def test_get_records_basic(self, db_module, db_engine_with_data, populated_db):
#         """Test basic get_records without filters."""
#         users = db_module.get_records(db_engine_with_data, AppUser)
        
#         assert len(users) == 2  # Should respect default limit of 10
#         assert all(isinstance(u, AppUser) for u in users)
    
#     def test_get_records_with_conditions(self, db_module, db_engine_with_data, populated_db):
#         """Test get_records with conditions."""
#         # Get admin user type ID
#         admin_type = populated_db['user_types'][0]
        
#         # This depends on your conditions format - adjust based on your actual implementation
#         # The current implementation expects conditions as a dict with attribute names
#         # You might need to adjust this based on how conditions are processed
#         pass
    
#     def test_get_records_with_eager_loading(self, db_module, db_engine_with_data, populated_db):
#         """Test get_records with eager loading."""
#         users = db_module.get_records(
#             db_engine_with_data,
#             AppUser,
#             eager_load_depth=["person", "user_type"]
#         )
        
#         assert len(users) > 0
        
#         # Check that relationships are loaded (not lazy)
#         # In SQLAlchemy, we can check if the relationship is loaded
#         for user in users:
#             # The person and user_type should be accessible without additional queries
#             # when eager loaded
#             assert hasattr(user, 'person')
#             assert hasattr(user, 'user_type')
    
#     def test_get_records_with_offset_limit(self, db_module, db_engine_with_data):
#         """Test get_records with offset and limit."""
#         # Add more products for testing
#         more_products = [
#             Product(product_name=f"Product {i}", product_code=f"P{i}", product_price=i*100)
#             for i in range(4, 15)
#         ]
#         db_module.add_records(db_engine_with_data, more_products)
        
#         # Test with offset and limit
#         products = db_module.get_records(
#             db_engine_with_data,
#             Product,
#             offset=5,
#             limit=5
#         )
        
#         assert len(products) == 5
    
#     # Test count_records
#     def test_count_records_total(self, db_module, db_engine_with_data, populated_db):
#         """Test counting all records."""
#         count = db_module.count_records(db_engine_with_data, Product)
        
#         assert count == 3  # 3 products in populated data
    
#     def test_count_records_with_conditions(self, db_module, db_engine_with_data, populated_db):
#         """Test counting records with conditions."""
#         # This test depends on how conditions are implemented
#         # You might need to adjust based on your actual implementation
#         pass
    
#     def test_count_records_with_group_by(self, db_module, db_engine_with_data, populated_db):
#         """Test counting records with group by."""
#         # Add more products with different prices
#         products = [
#             Product(product_name="Cheap", product_code="C1", product_price=100),
#             Product(product_name="Cheap", product_code="C2", product_price=100),
#             Product(product_name="Expensive", product_code="E1", product_price=1000),
#         ]
#         db_module.add_records(db_engine_with_data, products)
        
#         # Count products by price (group by price)
#         # Note: This requires InstrumentedAttribute for group_by
#         # You'll need to adjust based on your actual implementation
#         pass
    
#     # Test update_record
#     def test_update_record(self, db_module, db_engine_with_data, populated_db):
#         """Test updating a record."""
#         # Get a product to update
#         product = populated_db['products'][0]
#         original_name = product.product_name
        
#         # Update the product
#         product.product_name = "Updated Product Name"
#         product.unit_price = 9999
        
#         updated = db_module.update_record(db_engine_with_data, product)
        
#         assert updated.product_name == "Updated Product Name"
#         assert updated.unit_price == 9999
#         assert updated.product_id == product.product_id
        
#         # Verify the update persisted
#         retrieved = db_module.get_record_by_id(
#             db_engine_with_data, 
#             Product, 
#             product.product_id
#         )
#         assert retrieved.product_name == "Updated Product Name"
    
#     # Test delete_record
#     def test_delete_record(self, db_module, db_engine_with_data, populated_db):
#         """Test deleting a record."""
#         # Get a product to delete
#         product = populated_db['products'][0]
#         product_id = product.product_id
        
#         # Delete the product
#         result = db_module.delete_record(db_engine_with_data, product)
        
#         # Verify it's deleted
#         deleted_product = db_module.get_record_by_id(
#             db_engine_with_data,
#             Product,
#             product_id
#         )
        
#         assert deleted_product is None
    
#     # Test search_records
#     def test_search_records_basic(self, db_module, db_engine_with_data, populated_db):
#         """Test basic search functionality."""
#         # Search for products containing "A"
#         results = db_module.search_records(
#             db_engine_with_data,
#             Product,
#             join_tables=None,
#             eager_load_depth=None,
#             search_query="A",
#             search_fields=["product_name"]
#         )
        
#         assert len(results) >= 1
#         assert any("A" in p.product_name for p in results)
    
#     def test_search_records_multiple_keywords(self, db_module, db_engine_with_data):
#         """Test search with multiple keywords."""
#         # Add test data
#         products = [
#             Product(product_name="Red Apple", product_code="RA", product_price=100),
#             Product(product_name="Green Apple", product_code="GA", product_price=100),
#             Product(product_name="Red Tomato", product_code="RT", product_price=100),
#         ]
#         db_module.add_records(db_engine_with_data, products)
        
#         # Search for "Red Apple"
#         results = db_module.search_records(
#             db_engine_with_data,
#             Product,
#             join_tables=None,
#             eager_load_depth=None,
#             search_query="Red Apple",
#             search_fields=["product_name"]
#         )
        
#         # Should find "Red Apple"
#         assert any(p.product_name == "Red Apple" for p in results)
    
#     def test_search_records_multiple_fields(self, db_module, db_engine_with_data):
#         """Test search across multiple fields."""
#         products = [
#             Product(product_name="Special Item", product_code="SPECIAL", product_price=100),
#             Product(product_name="Regular Item", product_code="ITEM", product_price=100),
#         ]
#         db_module.add_records(db_engine_with_data, products)
        
#         # Search for "SPECIAL" in both name and code
#         results = db_module.search_records(
#             db_engine_with_data,
#             Product,
#             join_tables=None,
#             eager_load_depth=None,
#             search_query="SPECIAL",
#             search_fields=["product_name", "product_code"]
#         )
        
#         assert len(results) >= 1
    
#     def test_search_records_no_results(self, db_module, db_engine_with_data):
#         """Test search with no matching results."""
#         results = db_module.search_records(
#             db_engine_with_data,
#             Product,
#             join_tables=None,
#             eager_load_depth=None,
#             search_query="XYZ123NOMATCH",
#             search_fields=["product_name"]
#         )
        
#         assert len(results) == 0
    
#     # Test resolve_attr_recursive
#     def test_resolve_attr_recursive_simple(self, db_module):
#         """Test resolving simple attribute path."""
#         attr, joins = db_module.resolve_attr_recursive(AppUser, "user_name")
        
#         assert isinstance(attr, InstrumentedAttribute)
#         assert len(joins) == 0
    
#     def test_resolve_attr_recursive_with_relationship(self, db_module):
#         """Test resolving attribute path with relationship."""
#         attr, joins = db_module.resolve_attr_recursive(AppUser, "person.person_name")
        
#         assert isinstance(attr, InstrumentedAttribute)
#         assert len(joins) == 1
#         assert joins[0] == AppUser.person
    
#     def test_resolve_attr_recursive_deep_nesting(self, db_module):
#         """Test resolving deeply nested attribute path."""
#         # This would test paths like "person.blood_type.blood_type_name"
#         # You might need to adjust based on your actual model relationships
#         pass
    
#     def test_resolve_attr_recursive_invalid_path(self, db_module):
#         """Test resolving invalid attribute path."""
#         with pytest.raises(ValueError):
#             db_module.resolve_attr_recursive(AppUser, "invalid.attribute.path")
    
#     # Test get_records_by_filter
#     def test_get_records_by_filter_basic(self, db_module, db_engine_with_data, populated_db):
#         """Test basic filtered query."""
#         results = db_module.get_records_by_filter(
#             db_engine_with_data,
#             Product,
#             offset=0,
#             limit=10
#         )
        
#         assert len(results) > 0
#         assert all(isinstance(r, Product) for r in results)
    
#     def test_get_records_by_filter_with_selected_fields(self, db_module, db_engine_with_data, populated_db):
#         """Test query with selected fields only."""
#         results = db_module.get_records_by_filter(
#             db_engine_with_data,
#             Product,
#             selected_fields=[Product.product_name, Product.unit_price],
#             offset=0,
#             limit=10
#         )
        
#         # Results should be tuples or dicts when not selecting full model
#         assert len(results) > 0
        
#         # Check structure (could be dicts or tuples depending on SQLAlchemy version)
#         first_result = results[0]
#         if hasattr(first_result, '_mapping'):
#             # SQLAlchemy Row object
#             assert 'product_name' in first_result._mapping
#             assert 'product_price' in first_result._mapping
#         elif isinstance(first_result, dict):
#             # Dictionary
#             assert 'product_name' in first_result
#             assert 'product_price' in first_result
    
#     def test_get_records_by_filter_with_labeled_attrs(self, db_module, db_engine_with_data):
#         """Test query with labeled attributes."""
#         # This would test the labeled_attrs parameter
#         # You'll need to implement based on your use case
#         pass
    
#     def test_get_records_by_filter_with_conditions(self, db_module, db_engine_with_data):
#         """Test query with SQL conditions."""
#         # Add a specific product for testing
#         special_product = Product(
#             product_name="Special Test Product",
#             product_code="STP001",
#             product_price=5000
#         )
#         db_module.add_record(db_engine_with_data, special_product)
        
#         # Create a condition
#         from sqlalchemy import and_
#         condition = Product.unit_price > 4000
        
#         results = db_module.get_records_by_filter(
#             db_engine_with_data,
#             Product,
#             conditions=[condition],
#             offset=0,
#             limit=10
#         )
        
#         # Should find the special product
#         assert len(results) >= 1
#         assert any(r.unit_price > 4000 for r in results if isinstance(r, Product))
    
#     def test_get_records_by_filter_with_ordering(self, db_module, db_engine_with_data):
#         """Test query with ordering."""
#         # Clear existing products and add new ones with different prices
#         # This is a complex test that might need session management
#         pass

# class TestErrorHandling:
#     """Test error handling scenarios."""
    
#     def test_session_scope_exception_propagation(self, db_module, test_engine):
#         """Test that exceptions in session_scope are properly propagated."""
#         with pytest.raises(ValueError, match="Test exception"):
#             with db_module.session_scope(test_engine):
#                 raise ValueError("Test exception")
    
#     def test_database_connection_error(self, db_module):
#         """Test handling of database connection errors."""
#         with patch('storage.storage_service.StorageService.create_engine') as mock_create_engine:
#             mock_create_engine.side_effect = Exception("Connection failed")
            
#             with pytest.raises(APIException) as exc_info:
#                 db_module.get_engine('invalid://uri')
            
#             assert exc_info.value.code == "DATABASE_ERROR"
    
#     # def test_invalid_model_class(self, db_module, db_engine_with_data):
#     #     """Test with invalid model class."""
#     #     class InvalidModel:
#     #         pass
        
#     #     with pytest.raises(Exception):
#     #         db_module.get_all_records(db_engine_with_data, InvalidModel)

# class TestPerformanceAndEdgeCases:
#     """Test performance considerations and edge cases."""
    
#     def test_large_number_of_records(self, db_module, db_engine_with_data):
#         """Test handling large number of records."""
#         # Add many records
#         products = [
#             Product(
#                 product_name=f"Product {i}",
#                 product_code=f"P{i:04d}",
#                 product_price=i * 10
#             )
#             for i in range(100)
#         ]
        
#         db_module.add_records(db_engine_with_data, products)
        
#         # Get records with limit
#         results = db_module.get_records(
#             db_engine_with_data,
#             Product,
#             offset=0,
#             limit=50
#         )
        
#         assert len(results) == 50
    
#     def test_empty_database(self, db_module, test_engine):
#         """Test queries on empty database."""
#         # Create fresh empty database
#         Base.metadata.create_all(bind=test_engine)
        
#         # Test get_all_records on empty table
#         results = db_module.get_all_records(test_engine, Product)
#         assert len(results) == 0
        
#         # Test get_record_by_id on empty table
#         result = db_module.get_record_by_id(test_engine, Product, 1)
#         assert result is None
        
#         # Test count_records on empty table
#         count = db_module.count_records(test_engine, Product)
#         assert count == 0
    
#     def test_unicode_and_special_characters(self, db_module, db_engine_with_data):
#         """Test handling of unicode and special characters."""
#         # Product with special characters
#         product = Product(
#             product_name="Product with spéciäl chàracters & symbols ©™",
#             product_code="SPECIAL©",
#             product_price=1000
#         )
        
#         added = db_module.add_record(db_engine_with_data, product)
        
#         # Search for it
#         results = db_module.search_records(
#             db_engine_with_data,
#             Product,
#             join_tables=None,
#             eager_load_depth=None,
#             search_query="spéciäl",
#             search_fields=["product_name"]
#         )
        
#         assert len(results) >= 1
    
#     def test_null_values(self, db_module, db_engine_with_data):
#         """Test handling of null values."""
#         # Product with null-able fields (if any)
#         # This depends on your model definitions
#         pass

# # Run with: pytest tests/test_storage_service.py -v