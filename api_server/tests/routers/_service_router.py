# #!/usr/bin/env python3
# """
# Test script for /business/cart/add endpoint
# Run with: python test_cart_endpoint.py
# """

# import requests
# import json
# import sys
# from datetime import datetime, timedelta
# import uuid

# # Configuration
# BASE_URL = "http://localhost:9000/api"  # Change to your server URL
# HEADERS = {"Content-Type": "application/json"}

# def print_test_result(test_name, success, response=None, error=None):
#     """Helper to print test results"""
#     status = "✅ PASS" if success else "❌ FAIL"
#     print(f"{status} {test_name}")
    
#     if response:
#         print(f"   Status: {response.status_code}")
#         if response.text:
#             try:
#                 data = response.json()
#                 # Pretty print the response
#                 print(f"   Response: {json.dumps(data, indent=2, default=str)}")
#             except:
#                 print(f"   Response: {response.text[:200]}...")  # Truncate long responses
    
#     if error:
#         print(f"   Error: {error}")
    
#     print("-" * 50)
#     return success

# def generate_cart_data():
#     """Generate test cart data based on actual database IDs"""
#     timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
#     order_id = 0
    
#     cart_data = {
#         "seller_user_id": 2,          # ProviderAdmin user
#         "buyer_user_id": 1,           # SomeOne user
#         "provider_id": 2,             # Uno supermarket provider
#         "api_ordered_items": [
#             {
#                 "id_ordered_item": 0,
#                 "product_id": 1,  # Grano'Sac Raisin Cacahuetes
#                 "order_id": order_id,
#                 "product_discount": 10.0,
#                 "ordered_quantity": 2,
#                 "unit_price": 5.99,
#                 "vat_rate": 18.0
#             },
#             {
#                 "id_ordered_item": 0,
#                 "product_id": 2,  # Butter Biscuits LEGER
#                 "order_id": order_id,
#                 "product_discount": 5.0,
#                 "ordered_quantity": 3,
#                 "unit_price": 4.49,
#                 "vat_rate": 18.0
#             },
#             {
#                 "id_ordered_item": 0,
#                 "product_id": 3,  # Cookies from Home Bakery
#                 "order_id": order_id,
#                 "product_discount": 15.0,
#                 "ordered_quantity": 1,
#                 "unit_price": 3.99,
#                 "vat_rate": 18.0
#             }
#         ],
#         "api_provided_services": [
#             {
#                 "ordered_service_service_id": 1,  # CBC Test
#                 "ordered_service_quantity": 1,
#                 "ordered_service_unit_price": 20.00,
#                 "ordered_service_total_price": 20.00,
#                 "ordered_service_notes": "Routine blood work",
#                 "resource_requirement_id": 0
#             },
#             {
#                 "ordered_service_service_id": 2,  # Lipid Profile
#                 "ordered_service_quantity": 1,
#                 "ordered_service_unit_price": 28.00,
#                 "ordered_service_total_price": 28.00,
#                 "ordered_service_notes": "Annual checkup",
#                 "resource_requirement_id": 0
#             }
#         ],
#         "api_cart": {
#             "cart_id": 0,
#             "cart_product_provider_id": 2,  # Uno provider
#             "cart_selling_user": 2,         # ProviderAdmin
#             "cart_person_ref": 1,           # Person ID
#             "cart_client_user": 1,          # SomeOne user
#             "cart_status": "PENDING",
#             "cart_total_amount": 0.0,       # Will be calculated
#             "cart_notes": f"Test cart created via API on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
#             "cart_invoice": False,
#             "cart_receipt": False,
#             "cart_deposit": False,
#             "cart_payment": False,
#             "cart_paid_money": 0.0
#         },
#         "client": {
#             "id_person": 1,
#             "person_details_id": 1,
#             "id_person_details": 1,
#             "person_first_name": "John",
#             "person_last_name": "Doe",
#             "person_birth_date": "1990-01-01",
#             "person_gender": "Male",
#             "person_nationality": "US",
#             "id_blood_type": 1
#         }
#     }
    
#     # Calculate total amount
#     items_total = 0
#     for item in cart_data["api_ordered_items"]:
#         item_total = item["ordered_quantity"] * item["unit_price"]
#         discount_amount = item_total * (item["product_discount"] / 100)
#         items_total += item_total - discount_amount
    
#     services_total = sum(
#         service["ordered_service_total_price"] 
#         for service in cart_data["api_provided_services"]
#     )
    
#     cart_data["api_cart"]["cart_total_amount"] = round(items_total + services_total, 2)
    
#     return cart_data

# def test_create_cart():
#     """Test POST /business/cart/add endpoint"""
#     print("Testing POST /business/cart/add endpoint...")
#     try:
#         cart_data = generate_cart_data()
        
#         url = f"{BASE_URL}/business/cart"
#         print(f"URL: {url}")
#         print(f"Payload preview: {json.dumps(cart_data, indent=2)}")
        
#         response = requests.post(url, json=cart_data, headers=HEADERS, timeout=30)
        
#         success = response.status_code in [200, 201]
#         if success:
#             response_data = response.json()
#             print_test_result("Create Cart", True, response)
            
#             # Extract cart ID from response
#             cart_id = None
#             if isinstance(response_data, dict):
#                 cart_id = (response_data.get('cart_id') or 
#                           response_data.get('id') or 
#                           response_data.get('api_cart', {}).get('cart_id'))
#             elif isinstance(response_data, list) and len(response_data) > 0:
#                 # Try to get ID from first item if response is list
#                 cart_id = response_data[0].get('cart_id')
            
#             return cart_id
#         else:
#             print_test_result("Create Cart", False, response)
#             return None
        
#     except requests.exceptions.Timeout:
#         print_test_result("Create Cart", False, error="Request timeout")
#         return None
#     except Exception as e:
#         print_test_result("Create Cart", False, error=str(e))
#         return None

# def test_create_cart_products_only():
#     """Test cart creation with products only (no services)"""
#     print("Testing cart creation with products only...")
#     try:
#         cart_data = generate_cart_data()
        
#         # Remove services
#         cart_data["api_provided_services"] = []
        
#         # Update cart notes
#         cart_data["api_cart"]["cart_notes"] = "Products-only test cart"
        
#         # Recalculate total
#         items_total = 0
#         for item in cart_data["api_ordered_items"]:
#             item_total = item["ordered_quantity"] * item["unit_price"]
#             discount_amount = item_total * (item["product_discount"] / 100)
#             items_total += item_total - discount_amount
        
#         cart_data["api_cart"]["cart_total_amount"] = round(items_total, 2)
        
#         url = f"{BASE_URL}/business/cart"
#         response = requests.post(url, json=cart_data, headers=HEADERS)
        
#         success = response.status_code in [200, 201]
#         return print_test_result("Create Cart (Products Only)", success, response)
        
#     except Exception as e:
#         return print_test_result("Create Cart (Products Only)", False, error=str(e))

# def test_create_cart_services_only():
#     """Test cart creation with services only (no products)"""
#     print("Testing cart creation with services only...")
#     try:
#         cart_data = generate_cart_data()
        
#         # Remove products
#         cart_data["api_ordered_items"] = []
        
#         # Update cart notes
#         cart_data["api_cart"]["cart_notes"] = "Services-only test cart"
        
#         # Recalculate total
#         services_total = sum(
#             service["ordered_service_total_price"] 
#             for service in cart_data["api_provided_services"]
#         )
        
#         cart_data["api_cart"]["cart_total_amount"] = round(services_total, 2)
        
#         url = f"{BASE_URL}/business/cart"
#         response = requests.post(url, json=cart_data, headers=HEADERS)
        
#         success = response.status_code in [200, 201]
#         return print_test_result("Create Cart (Services Only)", success, response)
        
#     except Exception as e:
#         return print_test_result("Create Cart (Services Only)", False, error=str(e))

# def test_create_cart_existing_client():
#     """Test cart creation using existing client (no client data in payload)"""
#     print("Testing cart creation with existing client...")
#     try:
#         cart_data = generate_cart_data()
        
#         # Remove client data - should use cart_person_ref instead
#         del cart_data["client"]
        
#         # Ensure cart has person reference
#         cart_data["api_cart"]["cart_person_ref"] = 1  # Existing person ID
        
#         url = f"{BASE_URL}/business/cart"
#         response = requests.post(url, json=cart_data, headers=HEADERS)
        
#         success = response.status_code in [200, 201]
#         return print_test_result("Create Cart (Existing Client)", success, response)
        
#     except Exception as e:
#         return print_test_result("Create Cart (Existing Client)", False, error=str(e))

# def test_create_cart_new_client():
#     """Test cart creation with new client data"""
#     print("Testing cart creation with new client...")
#     try:
#         cart_data = generate_cart_data()
        
#         # Modify client data to represent a new client
#         timestamp = datetime.now().strftime("%Y%m%d%H%M")
#         cart_data["client"]["person_first_name"] = "Jane"
#         cart_data["client"]["person_last_name"] = f"Smith-{timestamp}"
#         cart_data["client"]["person_birth_date"] = "1995-05-15"
#         cart_data["client"]["person_gender"] = "Female"
#         cart_data["client"]["person_nationality"] = "UK"
        
#         # Reset IDs since it's a new client
#         cart_data["client"]["id_person"] = 0
#         cart_data["client"]["person_details_id"] = 0
#         cart_data["client"]["id_person_details"] = 0
        
#         # Update cart to reference new client (or should be 0?)
#         cart_data["api_cart"]["cart_person_ref"] = 0  # Will be created
        
#         url = f"{BASE_URL}/business/cart"
#         response = requests.post(url, json=cart_data, headers=HEADERS)
        
#         success = response.status_code in [200, 201]
#         return print_test_result("Create Cart (New Client)", success, response)
        
#     except Exception as e:
#         return print_test_result("Create Cart (New Client)", False, error=str(e))

# def test_invalid_cart_scenarios():
#     """Test various invalid cart creation scenarios"""
#     print("Testing invalid cart scenarios...")
    
#     test_cases = [
#         {
#             "name": "Missing required fields",
#             "data": {
#                 "seller_user_id": 2,
#                 # Missing buyer_user_id, provider_id, etc.
#             },
#             "expected_status": [400, 422]
#         },
#         {
#             "name": "Invalid user IDs",
#             "data": {
#                 "seller_user_id": 9999,  # Non-existent user
#                 "buyer_user_id": 9998,   # Non-existent user
#                 "provider_id": 2,
#                 "api_ordered_items": [],
#                 "api_provided_services": [],
#                 "api_cart": {
#                     "cart_product_provider_id": 2,
#                     "cart_selling_user": 9999,
#                     "cart_person_ref": 1,
#                     "cart_client_user": 9998,
#                     "cart_status": "PENDING",
#                     "cart_total_amount": 0.0,
#                     "cart_notes": "Invalid user test"
#                 }
#             },
#             "expected_status": [400, 422, 404]
#         },
#         {
#             "name": "Empty cart (no items or services)",
#             "data": generate_cart_data()
#         }
#     ]
    
#     # Modify the empty cart test case
#     test_cases[2]["data"]["api_ordered_items"] = []
#     test_cases[2]["data"]["api_provided_services"] = []
#     test_cases[2]["data"]["api_cart"]["cart_total_amount"] = 0.0
#     test_cases[2]["data"]["api_cart"]["cart_notes"] = "Empty cart test"
#     test_cases[2]["expected_status"] = [400, 422]  # Should reject empty carts
    
#     test_cases.append({
#         "name": "Invalid product ID",
#         "data": generate_cart_data()
#     })
    
#     # Modify invalid product ID test
#     test_cases[3]["data"]["api_ordered_items"][0]["product_id"] = 9999
#     test_cases[3]["expected_status"] = [400, 422, 404]
    
#     test_cases.append({
#         "name": "Invalid service ID",
#         "data": generate_cart_data()
#     })
    
#     # Modify invalid service ID test
#     test_cases[4]["data"]["api_provided_services"][0]["ordered_service_service_id"] = 9999
#     test_cases[4]["expected_status"] = [400, 422, 404]
    
#     for test_case in test_cases:
#         try:
#             url = f"{BASE_URL}/business/cart"
#             response = requests.post(url, json=test_case["data"], headers=HEADERS, timeout=10)
            
#             expected = test_case.get("expected_status", [200, 201])
#             success = response.status_code in expected
            
#             print_test_result(f"Invalid: {test_case['name']}", success, response)
                
#         except Exception as e:
#             print_test_result(f"Invalid: {test_case.get('name', 'Test')}", False, error=str(e))

# def test_different_providers():
#     """Test cart creation with different providers"""
#     print("Testing cart creation with different providers...")
    
#     providers = [
#         {"id": 1, "name": "Magasin habibou sans gluten", "type": "Bakery"},
#         {"id": 2, "name": "Uno", "type": "Supermarket"},
#         {"id": 3, "name": "Superette université", "type": "Supermarket"},
#         {"id": 4, "name": "Corridors Shopping", "type": "Restaurant"},
#         {"id": 5, "name": "Caramel sans gluten", "type": "Supermarket"},
#         {"id": 6, "name": "Magasin habibou sans gluten", "type": "Bakery"},
#         {"id": 7, "name": "Uno", "type": "Supermarket"}
#     ]
    
#     for provider in providers[:3]:  # Test first 3 providers
#         try:
#             cart_data = generate_cart_data()
            
#             # Update provider information
#             cart_data["provider_id"] = provider["id"]
#             cart_data["api_cart"]["cart_product_provider_id"] = provider["id"]
#             cart_data["api_cart"]["cart_notes"] = f"Test cart for {provider['name']} ({provider['type']})"
            
#             # Adjust products/services based on provider type
#             if provider["type"] == "Bakery":
#                 # Bakery might have different products
#                 cart_data["api_ordered_items"] = [
#                     {
#                         "id_ordered_item": 0,
#                         "product_id": 7,  # JUMPY Peanut Butter (from provider 6 - bakery)
#                         "order_id": f"BAKERY-{datetime.now().strftime('%H%M%S')}",
#                         "product_discount": 5.0,
#                         "ordered_quantity": 1,
#                         "unit_price": 5.79,
#                         "vat_rate": 18.0
#                     }
#                 ]
#                 cart_data["api_provided_services"] = []  # Bakeries might not have services
            
#             url = f"{BASE_URL}/business/cart"
#             response = requests.post(url, json=cart_data, headers=HEADERS)
            
#             success = response.status_code in [200, 201]
#             print_test_result(f"Create Cart for {provider['name']}", success, response)
            
#         except Exception as e:
#             print_test_result(f"Create Cart for {provider['name']}", False, error=str(e))

# def test_cart_status_updates():
#     """Test if we can update cart status after creation"""
#     print("Testing cart status updates...")
    
#     # First create a cart
#     cart_data = generate_cart_data()
#     url = f"{BASE_URL}/business/cart"
#     create_response = requests.post(url, json=cart_data, headers=HEADERS)
    
#     if create_response.status_code not in [200, 201]:
#         print("❌ Failed to create cart for status update test")
#         return False
    
#     created_data = create_response.json()
    
#     # Try to extract cart ID
#     cart_id = None
#     if isinstance(created_data, dict):
#         cart_id = created_data.get('cart_id')
#     elif isinstance(created_data, list) and len(created_data) > 0:
#         cart_id = created_data[0].get('cart_id')
    
#     if not cart_id:
#         print("⚠️  Could not extract cart ID from response")
#         print(f"Response: {created_data}")
#         return False
    
#     print(f"✅ Created cart with ID: {cart_id}")
    
#     # Try different status update endpoints
#     status_endpoints = [
#         f"/business/cart/0/0/{cart_id}/0/0/0/1",
#         f"/cart/0/0/{cart_id}/0/0/0/1",
#         f"/api/cart/0/0/{cart_id}/0/0/0/1"
#     ]
    
#     update_data = {
#         "status": "PROCESSING",
#         "notes": "Updated via test script"
#     }
    
#     for endpoint in status_endpoints:
#         try:
#             url = f"http://localhost:9000{endpoint}"
#             print(f"Trying status update endpoint: {url}")
            
#             response = requests.put(url, json=update_data, headers=HEADERS, timeout=5)
            
#             if response.status_code != 404:
#                 success = response.status_code in [200, 201]
#                 print_test_result(f"Update Cart Status via {endpoint}", success, response)
#                 if success:
#                     return True
                    
#         except requests.exceptions.RequestException:
#             continue
    
#     print("⚠️  Could not find valid status update endpoint")
#     return False

# def test_complete_workflow():
#     """Test complete cart creation workflow"""
#     print("Testing complete cart workflow...")
    
#     # Step 1: Create a comprehensive cart
#     cart_data = generate_cart_data()
    
#     # Add more items for a realistic workflow
#     cart_data["api_ordered_items"].extend([
#         {
#             "id_ordered_item": 0,
#             "product_id": 4,  # Gullon Cookies
#             "order_id": 0,
#             "product_discount": 12.0,
#             "ordered_quantity": 2,
#             "unit_price": 6.29,
#             "vat_rate": 18.0
#         },
#         {
#             "id_ordered_item": 0,
#             "product_id": 5,  # Date Butter
#             "order_id": 0,
#             "product_discount": 8.0,
#             "ordered_quantity": 1,
#             "unit_price": 7.99,
#             "vat_rate": 18.0
#         }
#     ])
    
#     # Add more services
#     cart_data["api_provided_services"].append({
#         "ordered_service_service_id": 3,  # Blood Glucose Test
#         "ordered_service_quantity": 1,
#         "ordered_service_unit_price": 12.00,
#         "ordered_service_total_price": 12.00,
#         "ordered_service_notes": "Added for workflow test",
#         "resource_requirement_id": 0
#     })
    
#     # Recalculate total
#     items_total = 0
#     for item in cart_data["api_ordered_items"]:
#         item_total = item["ordered_quantity"] * item["unit_price"]
#         discount_amount = item_total * (item["product_discount"] / 100)
#         items_total += item_total - discount_amount
    
#     services_total = sum(
#         service["ordered_service_total_price"] 
#         for service in cart_data["api_provided_services"]
#     )
    
#     cart_data["api_cart"]["cart_total_amount"] = round(items_total + services_total, 2)
#     cart_data["api_cart"]["cart_notes"] = "Complete workflow test cart"
    
#     # Create the cart
#     url = f"{BASE_URL}/business/cart"
#     create_response = requests.post(url, json=cart_data, headers=HEADERS)
    
#     if create_response.status_code not in [200, 201]:
#         print("❌ Workflow failed at creation step")
#         print(f"Status: {create_response.status_code}")
#         print(f"Response: {create_response.text[:200]}")
#         return False
    
#     created_cart = create_response.json()
#     print(f"✅ Cart created successfully")
#     print(f"Response: {json.dumps(created_cart, indent=2, default=str)}")
    
#     # Step 2: Try to retrieve the cart (if endpoint exists)
#     cart_id = None
#     if isinstance(created_cart, dict):
#         cart_id = created_cart.get('cart_id')
#     elif isinstance(created_cart, list) and len(created_cart) > 0:
#         cart_id = created_cart[0].get('cart_id')
    
#     if cart_id:
#         print(f"✅ Cart ID: {cart_id}")
        
#         # Try to get cart details
#         try:
#             get_url = f"http://localhost:9000/api/cart/0/0/{cart_id}/0/0/0/1"
#             get_response = requests.get(get_url, timeout=5)
            
#             if get_response.status_code in [200, 201]:
#                 print("✅ Successfully retrieved cart details")
#                 print(f"Cart details: {json.dumps(get_response.json(), indent=2, default=str)[:300]}...")
#             else:
#                 print(f"⚠️  Cart retrieval endpoint returned {get_response.status_code}")
#         except:
#             print("⚠️  Cart retrieval endpoint not available or failed")
    
#     print("🎉 Complete cart workflow test passed!")
#     return True

# def run_all_tests():
#     """Run all test scenarios"""
#     print("🚀 Starting /business/cart/add Endpoint Tests")
#     print("=" * 60)
    
#     # Check server connectivity
#     try:
#         response = requests.get("http://localhost:9000", timeout=5)
#         print(f"✅ Server is reachable at http://localhost:9000")
#     except requests.exceptions.ConnectionError:
#         print(f"❌ Cannot connect to server at http://localhost:9000")
#         print("Make sure your FastAPI server is running!")
#         sys.exit(1)
    
#     results = {
#         "create_full_cart": False,
#         "products_only": False,
#         "services_only": False,
#         "existing_client": False,
#         "new_client": False,
#         "complete_workflow": False
#     }
    
#     # Test 1: Create full cart
#     cart_id = test_create_cart()
#     results["create_full_cart"] = cart_id is not None
    
#     # Test 2: Products only
#     results["products_only"] = test_create_cart_products_only()
    
#     # Test 3: Services only
#     results["services_only"] = test_create_cart_services_only()
    
#     # Test 4: Existing client
#     results["existing_client"] = test_create_cart_existing_client()
    
#     # Test 5: New client
#     results["new_client"] = test_create_cart_new_client()
    
#     # Test 6: Invalid scenarios
#     test_invalid_cart_scenarios()
    
#     # Test 7: Different providers
#     test_different_providers()
    
#     # Test 8: Status updates (if cart was created)
#     if cart_id:
#         test_cart_status_updates()
    
#     # Test 9: Complete workflow
#     results["complete_workflow"] = test_complete_workflow()
    
#     # Summary
#     print("\n📊 TEST SUMMARY")
#     print("=" * 60)
#     for test_name, passed in results.items():
#         status = "✅ PASS" if passed else "❌ FAIL"
#         print(f"{status} {test_name.replace('_', ' ').title()}")
    
#     passed_count = sum(results.values())
#     total_count = len(results)
#     print(f"\nOverall: {passed_count}/{total_count} tests passed")
    
#     if passed_count == total_count:
#         print("🎉 All tests passed!")
#         return True
#     else:
#         print("💥 Some tests failed!")
#         print("\n💡 Tips:")
#         print("   1. Check that all IDs (users, providers, products, services) exist in your database")
#         print("   2. Verify the endpoint path is correct")
#         print("   3. Check server logs for detailed error messages")
#         return False

# if __name__ == "__main__":
#     success = run_all_tests()
#     sys.exit(0 if success else 1)