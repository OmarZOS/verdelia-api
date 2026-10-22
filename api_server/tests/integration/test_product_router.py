# # tests/integration/test_product_router.py
# """
# Integration tests for Product endpoints.
# Tests cover CRUD operations, barcode search, image recognition, and SSE.
# """

# import pytest
# from fastapi.testclient import TestClient
# from typing import Dict, Any
# import os
# import time
# import io
# from unittest.mock import patch, AsyncMock, Mock

# from server import app

# # Create test client
# client = TestClient(app)


# # ==================== Skip if no database ====================

# # Only run integration tests if explicitly requested
# pytestmark = pytest.mark.skipif(
#     not os.environ.get('RUN_INTEGRATION_TESTS', 'true').lower() == 'true',
#     reason="Integration tests require database. Set RUN_INTEGRATION_TESTS=true to run."
# )


# # ==================== Test Data Fixtures ====================

# @pytest.fixture
# def sample_product_data() -> Dict[str, Any]:
#     """Sample product data for testing"""
#     return {
#         "product": {
#             "id_product": 0,
#             "product_name": "Test Product",
#             "product_brand": "Test Brand",
#             "product_provider_id": 1,
#             "product_category_id": 1,
#             "product_barcode": "1234567890123",
#             "product_price": 99.99,
#             "product_quantity": 100,
#             "product_quantifier": "pcs",
#             "product_description": "This is a test product",
#             "product_owner": 1
#         },
#         "image": {
#             "id_product_image": 0,
#             "product_image_url": "https://example.com/product.jpg",
#             "product_ref_id": 0
#         },
#         "iproduct": {
#             "id_iproduct": 0,
#             "generic_name": "Test IProduct",
#             "barcode": "1234567890123",
#             "brand": "Test Brand",
#             "estimated_price": 99.99,
#             "price_currency": "USD",
#             "iproduct_gluten_status": "unknown",
#             "info_source": "openai",
#             "info_confidence": 0.95,
#             "model_name": "gpt-4",
#             "image_url": ""
#         }
#     }


# @pytest.fixture
# def sample_update_product_data() -> Dict[str, Any]:
#     """Sample product update data"""
#     return {
#         "product": {
#             "id_product": 0,
#             "product_name": "Updated Product Name",
#             "product_brand": "Updated Brand",
#             "product_provider_id": 1,
#             "product_category_id": 1,
#             "product_barcode": "9876543210987",
#             "product_price": 149.99,
#             "product_quantity": 50,
#             "product_quantifier": "pcs",
#             "product_description": "This is an updated test product",
#             "product_owner": 1
#         },
#         "image": {
#             "id_product_image": 0,
#             "product_image_url": "https://example.com/updated_product.jpg",
#             "product_ref_id": 0
#         }
#     }


# @pytest.fixture
# def cleanup_product():
#     """Clean up created products after tests"""
#     created_ids = []
    
#     def add_id(product_id):
#         created_ids.append(product_id)
    
#     yield add_id
    
#     # Clean up after test
#     for product_id in created_ids:
#         try:
#             client.delete(f"/api/v1/products/delete/{product_id}?force_delete=true")
#         except:
#             pass


# # ==================== SSE Endpoint Tests ====================

# class TestProductSSE:
#     """Test suite for SSE product updates"""
    
#     def test_product_updates_sse_connection(self):
#         """Test SSE connection for product updates"""
#         # This tests the endpoint exists and validates product
#         response = client.get("/api/v1/products/observer/1")
        
#         # Should return 200 or 404 depending on if product exists
#         assert response.status_code in [200, 404]
    
#     def test_product_updates_product_not_found(self):
#         """Test SSE connection for non-existent product"""
#         response = client.get("/api/v1/products/observer/999999")
        
#         assert response.status_code == 404
#         data = response.json()
#         assert data["success"] is False


# # ==================== Product Listing Endpoint Tests ====================

# class TestProductListingEndpoints:
#     """Test suite for product listing endpoints"""
    
#     def test_get_all_products_success(self):
#         """Test successful retrieval of all products"""
#         response = client.get("/api/v1/products/0/0/0/0/10")
        
#         assert response.status_code == 200
#         data = response.json()
#         assert data["success"] is True
#         assert "data" in data
#         assert isinstance(data["data"], list)
    
#     def test_get_all_products_with_filters(self):
#         """Test retrieval of products with filters"""
#         response = client.get("/api/v1/products/1/1/1/0/10")
        
#         assert response.status_code == 200
#         data = response.json()
#         assert data["success"] is True
    
#     def test_get_all_products_pagination(self):
#         """Test products retrieval with custom pagination"""
#         response = client.get("/api/v1/products/0/0/0/10/25")
        
#         assert response.status_code == 200
#         data = response.json()
#         assert data["success"] is True
    
#     def test_get_categories_success(self):
#         """Test successful retrieval of product categories"""
#         response = client.get("/api/v1/products/category/all")
        
#         assert response.status_code == 200
#         data = response.json()
#         assert data["success"] is True
#         assert "data" in data
#         assert isinstance(data["data"], list)
    
#     def test_get_products_by_category_success(self):
#         """Test retrieval of products by category"""
#         response = client.get("/api/v1/products/category/1/0/10")
        
#         assert response.status_code == 200
#         data = response.json()
#         assert data["success"] is True
    
#     def test_get_products_by_category_not_found(self):
#         """Test retrieval of products by non-existent category"""
#         response = client.get("/api/v1/products/category/999999/0/10")
        
#         assert response.status_code == 404
    
#     def test_get_product_by_id_success(self):
#         """Test successful retrieval of product by ID"""
#         response = client.get("/api/v1/products/1")
        
#         if response.status_code == 404:
#             pytest.skip("Product with ID 1 not found in database")
        
#         assert response.status_code == 200
#         data = response.json()
#         assert data["success"] is True
    
#     def test_get_product_by_id_not_found(self):
#         """Test product retrieval when product doesn't exist"""
#         response = client.get("/api/v1/products/999999")
        
#         assert response.status_code == 404
#         data = response.json()
#         assert data["success"] is False


# # ==================== Barcode Search Endpoint Tests ====================

# class TestBarcodeSearchEndpoints:
#     """Test suite for barcode search endpoints"""
    
#     def test_search_product_by_barcode_success_db(self):
#         """Test successful barcode search (DB hit)"""
#         response = client.get("/api/v1/products/barcode/1234567890123")
        
#         # May be 200 if exists, 404 if not
#         assert response.status_code in [200, 404]
    
#     def test_search_product_by_barcode_not_found(self):
#         """Test barcode search with non-existent barcode"""
#         response = client.get("/api/v1/products/barcode/NONEXISTENT123")
        
#         assert response.status_code == 404
    
#     @patch('services.product_service.ProductService.get_iproduct_by_barcode')
#     @patch('services.helpers.ai_service.AIService.generate_product_info_by_barcode')
#     def test_search_product_by_barcode_ai_fallback(self, mock_ai_generate, mock_db_search):
#         """Test barcode search with AI fallback"""
#         # Mock DB returns None (not found)
#         mock_db_search.return_value = None
        
#         # Mock AI returns a result
#         mock_ai_generate.return_value = (
#             {"product_name": "AI Generated Product", "price": 29.99},
#             "gpt-4"
#         )
        
#         response = client.get("/api/v1/products/barcode/AI_TEST_123")
        
#         # Should return 200 with AI-generated data
#         assert response.status_code == 200
#         data = response.json()
#         assert data["details"]["source"] == "ai"
    
#     def test_search_product_barcode_db_only_success(self):
#         """Test DB-only barcode search"""
#         response = client.get("/api/v1/products/db/barcode/1234567890123")
        
#         # May be 200 if exists, 404 if not
#         assert response.status_code in [200, 404]
    
#     def test_search_product_barcode_db_only_not_found(self):
#         """Test DB-only barcode search with non-existent barcode"""
#         response = client.get("/api/v1/products/db/barcode/NONEXISTENT123")
        
#         assert response.status_code == 404


# # ==================== Image Recognition Endpoint Tests ====================

# class TestImageRecognitionEndpoints:
#     """Test suite for image recognition endpoints"""
    
#     def test_search_product_by_image_no_file(self):
#         """Test image search with no file"""
#         response = client.post("/api/v1/products/search/image")
        
#         assert response.status_code == 422
    
#     def test_search_product_by_image_invalid_file_type(self):
#         """Test image search with invalid file type"""
#         # Create a text file instead of image
#         file_content = b"This is not an image"
#         files = {"file": ("test.txt", file_content, "text/plain")}
        
#         response = client.post("/api/v1/products/search/image", files=files)
        
#         assert response.status_code in [400, 422]
    
#     @patch('services.product_service.ProductService.recognize_product_from_image')
#     def test_search_product_by_image_success(self, mock_recognize):
#         """Test successful image search"""
#         # Mock the recognition result
#         mock_iproduct = Mock()
#         mock_iproduct.generic_name = "Recognized Product"
#         mock_recognize.return_value = mock_iproduct
        
#         # Create a dummy image file
#         image_content = b"fake_image_data"
#         files = {"file": ("test.jpg", image_content, "image/jpeg")}
        
#         response = client.post("/api/v1/products/search/image", files=files)
        
#         assert response.status_code == 200
#         data = response.json()
#         assert data["success"] is True
#         assert "Product recognized from image" in data["message"]


# # ==================== Product Image Endpoint Tests ====================

# class TestProductImageEndpoints:
#     """Test suite for product image endpoints"""
    
#     def test_get_product_image_success(self):
#         """Test successful retrieval of product image"""
#         response = client.get("/api/v1/products/image/1")
        
#         if response.status_code == 404:
#             pytest.skip("Product image with ID 1 not found in database")
        
#         assert response.status_code == 200
#         data = response.json()
#         assert data["success"] is True
    
#     def test_get_product_image_not_found(self):
#         """Test product image retrieval when doesn't exist"""
#         response = client.get("/api/v1/products/image/999999")
        
#         assert response.status_code == 404
#         data = response.json()
#         assert data["success"] is False


# # ==================== Product CRUD Operation Tests ====================

# class TestProductCrudEndpoints:
#     """Test suite for product CRUD operations"""
    
#     def test_create_product_success(self, sample_product_data, cleanup_product):
#         """Test successful product creation"""
#         response = client.post("/api/v1/products", json=sample_product_data)
        
#         # Skip if provider or category doesn't exist
#         if response.status_code == 404:
#             pytest.skip("Required provider or category not found in database")
        
#         assert response.status_code == 201, f"Expected 201, got {response.status_code}. Response: {response.text}"
#         data = response.json()
#         assert data["success"] is True
#         assert "Product created successfully" in data["message"]
        
#         if "product_id" in data.get("details", {}):
#             cleanup_product(data["details"]["product_id"])
    
#     def test_create_product_missing_required_fields(self):
#         """Test product creation with missing required fields"""
#         response = client.post("/api/v1/products", json={"product": {}})
        
#         assert response.status_code == 422
    
#     def test_create_product_duplicate(self, sample_product_data):
#         """Test creating duplicate product"""
#         # First creation
#         response1 = client.post("/api/v1/products", json=sample_product_data)
#         if response1.status_code == 404:
#             pytest.skip("Required dependencies not found")
        
#         # Second creation might be 409 if barcode duplicates
#         response2 = client.post("/api/v1/products", json=sample_product_data)
        
#         assert response2.status_code in [409, 201]  # 409 if duplicate detected
    
#     def test_update_product_success(self, sample_update_product_data):
#         """Test successful product update"""
#         # First create a product to update
#         create_response = client.post("/api/v1/products", json=sample_update_product_data)
#         if create_response.status_code == 404:
#             pytest.skip("Required dependencies not found")
        
#         if create_response.status_code == 201:
#             product_id = create_response.json().get("details", {}).get("product_id")
            
#             if product_id:
#                 # Update the product
#                 sample_update_product_data["product"]["id_product"] = product_id
#                 sample_update_product_data["image"]["product_ref_id"] = product_id
                
#                 response = client.put(f"/api/v1/products/{product_id}", json=sample_update_product_data)
                
#                 assert response.status_code == 200
#                 data = response.json()
#                 assert data["success"] is True
                
#                 # Cleanup
#                 client.delete(f"/api/v1/products/delete/{product_id}?force_delete=true")
    
#     def test_update_product_not_found(self, sample_update_product_data):
#         """Test product update when product doesn't exist"""
#         response = client.put("/api/v1/products/999999", json=sample_update_product_data)
        
#         assert response.status_code == 404
    
#     def test_delete_product_success(self, sample_product_data):
#         """Test successful product deletion"""
#         # Create a product first
#         create_response = client.post("/api/v1/products", json=sample_product_data)
#         if create_response.status_code == 404:
#             pytest.skip("Required dependencies not found")
        
#         if create_response.status_code == 201:
#             product_id = create_response.json().get("details", {}).get("product_id")
            
#             if product_id:
#                 # Delete it
#                 response = client.delete(f"/api/v1/products/delete/{product_id}")
                
#                 assert response.status_code == 200
#                 data = response.json()
#                 assert data["success"] is True
#                 assert "deleted successfully" in data["message"]
    
#     def test_delete_product_force_delete(self, sample_product_data):
#         """Test force deleting a product"""
#         create_response = client.post("/api/v1/products", json=sample_product_data)
#         if create_response.status_code == 404:
#             pytest.skip("Required dependencies not found")
        
#         if create_response.status_code == 201:
#             product_id = create_response.json().get("details", {}).get("product_id")
            
#             if product_id:
#                 response = client.delete(f"/api/v1/products/delete/{product_id}?force_delete=true")
                
#                 assert response.status_code == 200
#                 data = response.json()
#                 assert data["success"] is True
    
#     def test_delete_product_not_found(self):
#         """Test product deletion when product doesn't exist"""
#         response = client.delete("/api/v1/products/delete/999999")
        
#         assert response.status_code == 404


# # ==================== Edge Cases & Validation Tests ====================

# class TestProductEdgeCases:
#     """Test suite for edge cases and validation"""
    
#     def test_get_products_invalid_pagination(self):
#         """Test products with invalid pagination parameters"""
#         # Negative offset
#         response = client.get("/api/v1/products/0/0/0/-1/10")
#         assert response.status_code == 422
    
#     def test_get_products_by_category_invalid_pagination(self):
#         """Test products by category with invalid pagination"""
#         response = client.get("/api/v1/products/category/1/-1/10")
#         assert response.status_code == 422
    
#     def test_search_product_by_barcode_empty(self):
#         """Test barcode search with empty string"""
#         response = client.get("/api/v1/products/barcode/")
        
#         assert response.status_code == 404
    
#     def test_create_product_with_negative_price(self, sample_product_data):
#         """Test creating product with negative price"""
#         sample_product_data["product"]["product_price"] = -10.00
        
#         response = client.post("/api/v1/products", json=sample_product_data)
        
#         assert response.status_code == 422
    
#     def test_create_product_with_negative_quantity(self, sample_product_data):
#         """Test creating product with negative quantity"""
#         sample_product_data["product"]["product_quantity"] = -5
        
#         response = client.post("/api/v1/products", json=sample_product_data)
        
#         assert response.status_code == 422


# # ==================== Response Format Tests ====================

# class TestProductResponseFormat:
#     """Test suite for response format validation"""
    
#     def test_success_response_format(self):
#         """Test that success responses follow the expected format"""
#         response = client.get("/api/v1/products/category/all")
#         data = response.json()
        
#         assert "success" in data
#         assert "data" in data
#         assert "message" in data
#         assert "timestamp" in data
#         assert data["success"] is True
    
#     def test_error_response_format(self):
#         """Test that error responses follow the expected format"""
#         response = client.get("/api/v1/products/999999")
#         data = response.json()
        
#         assert "success" in data
#         assert "status_code" in data
#         assert "code" in data
#         assert "message" in data
#         assert "timestamp" in data
#         assert data["success"] is False
#         assert data["status_code"] == 404


# # ==================== Database Setup Helpers ====================

# @pytest.fixture(scope="session", autouse=True)
# def setup_test_database():
#     """Setup required test data in database before running tests"""
#     if os.environ.get('RUN_INTEGRATION_TESTS', 'false').lower() == 'true':
#         try:
#             from storage.storage_service.StorageService import get_engine, session_scope
#             from core.models import ProductCategory, ProductProvider, AppUser
#             from config import DB_URI
            
#             engine = get_engine(DB_URI)
            
#             with session_scope(engine) as session:
#                 # Check if product category exists
#                 category = session.query(ProductCategory).filter(
#                     ProductCategory.id_product_category == 1
#                 ).first()
                
#                 if not category:
#                     # Create test category
#                     test_category = ProductCategory(
#                         id_product_category=1,
#                         product_category_desc="Test Category",
#                         product_category_icon="https://example.com/category.jpg"
#                     )
#                     session.add(test_category)
#                     session.commit()
#                     print("\n✅ Created test product category")
                
#                 # Check if provider exists
#                 provider = session.query(ProductProvider).filter(
#                     ProductProvider.id_product_provider == 1
#                 ).first()
                
#                 if not provider:
#                     print("\n⚠️ Provider with ID 1 not found. Product creation tests may fail.")
                
#                 # Check if user exists
#                 user = session.query(AppUser).filter(
#                     AppUser.id_app_user == 1
#                 ).first()
                
#                 if not user:
#                     print("\n⚠️ AppUser with ID 1 not found. Product creation tests may fail.")
                    
#         except Exception as e:
#             print(f"\n⚠️ Could not setup test database: {e}")
    
#     yield


# # ==================== Run Tests ====================

# if __name__ == "__main__":
#     pytest.main([__file__, "-v", "--tb=short"])