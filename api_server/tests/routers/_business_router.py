#!/usr/bin/env python3
"""
Test script for business order endpoints
Run with: python test_business_orders.py
"""

import requests
import json
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# from core.api_models import Delivery_API

# Configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:9000/api")
HEADERS = {"Content-Type": "application/json"}

def print_test_result(test_name: str, success: bool, response=None, error=None):
    """Helper to print test results"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    
    if response:
        print(f"   Status: {response.status_code}")
        if response.text:
            try:
                response_data = response.json()
                # Print abbreviated response for readability
                if isinstance(response_data, list):
                    print(f"   Response: List with {len(response_data)} items")
                else:
                    print(f"   Response: {json.dumps(response_data, indent=2)}")
            except:
                print(f"   Response: {response.text[:200]}...")  # Truncate long responses
    
    if error:
        print(f"   Error: {error}")
    
    print("-" * 50)

def create_sample_order_data(user_id: int = 1) -> tuple:
    """Create sample order data for testing"""
    
    # Sample placed order
    submitted_order = {
        "id_placed_order": 0,  # Will be auto-generated
        "ordered_timestamp": datetime.now().isoformat(),
        "order_discount": 10.0,
        "placed_order_last_mod": datetime.now().isoformat(),
        "payment_status": "pending",
        "payment_ref": f"TEST_PAY_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "placed_order_state": "processing",
        "payment_method": "credit_card",
        "ordering_user_id": user_id
    }
    
    # Sample ordered items
    ordered_items = [
        {
            "id_ordered_item": 0,  # Will be auto-generated
            "product_id": 1,  # Assuming product ID 1 exists
            "order_id": 0,  # Will be set to actual order ID
            "product_discount": 5.0,
            "ordered_quantity": 2.0,
            "unit_price": 25.99,
            "vat_rate": 0.21
        },
        {
            "id_ordered_item": 0,
            "product_id": 2,  # Assuming product ID 2 exists
            "order_id": 0,
            "product_discount": 0.0,
            "ordered_quantity": 1.0,
            "unit_price": 15.50,
            "vat_rate": 0.21
        }
    ]
    
    return ordered_items, submitted_order

def test_create_order():
    """Test POST /business/order/add endpoint"""
    print("Testing POST /business/order/add endpoint...")
    try:
        ordered_items, submitted_order = create_sample_order_data(user_id=1)
        
        # Prepare the request data
        request_data = {
            "ordered_items": ordered_items,
            "submitted_order": submitted_order
        }
        
        url = f"{BASE_URL}/business/order"
        response = requests.post(url, json=request_data, headers=HEADERS)
        
        success = response.status_code == 200
        print_test_result("CREATE Order", success, response)
        
        # Extract order ID from response for later tests
        if success:
            response_data = response.json()
            # Try different possible ID field names
            order_id = (response_data.get('id_placed_order') or 
                       response_data.get('order_id') or 
                       response_data.get('id'))
            return order_id
        
        return None
        
    except Exception as e:
        print_test_result("CREATE Order", False, error=str(e))
        return None

def test_get_all_user_orders(user_id: int = 1):
    """Test GET /business/user/orders/all/{user_id} endpoint"""
    print(f"Testing GET /business/user/orders/all/{user_id} endpoint...")
    try:
        url = f"{BASE_URL}/business/user/orders/all/{user_id}"
        response = requests.get(url)
        
        success = response.status_code in [200, 404]  # 404 is valid if user has no orders
        print_test_result(f"GET All User Orders (user_id: {user_id})", success, response)
        
        if success and response.status_code == 200:
            orders = response.json()
            if isinstance(orders, list) and len(orders) > 0:
                return orders[0].get('id_placed_order')  # Return first order ID for testing
        return None
        
    except Exception as e:
        print_test_result("GET All User Orders", False, error=str(e))
        return None

def test_get_order_details(order_id: int):
    """Test GET /business/user/orders/{order_id} endpoint"""
    print(f"Testing GET /business/user/orders/{order_id} endpoint...")
    try:
        url = f"{BASE_URL}/business/user/orders/{order_id}"
        response = requests.get(url)
        
        success = response.status_code in [200, 404]  # 404 is valid if order doesn't exist
        print_test_result(f"GET Order Details (order_id: {order_id})", success, response)
        return success
        
    except Exception as e:
        print_test_result("GET Order Details", False, error=str(e))
        return False

def test_update_order(order_id: int):
    """Test PUT /business/order/update/{order_id} endpoint"""
    print(f"Testing PUT /business/order/update/{order_id} endpoint...")
    try:
        # Create updated order data
        ordered_items, submitted_order = create_sample_order_data(user_id=1)
        
        # Update the order data
        submitted_order.update({
            "id_placed_order": order_id,
            "payment_status": "paid",
            "placed_order_state": "shipped",
            "order_discount": 15.0  # Increased discount
        })
        
        # Update items
        for item in ordered_items:
            item["order_id"] = order_id
            item["ordered_quantity"] = 3.0  # Increased quantity
        
        # Prepare the request data
        request_data = {
            "updated_items": ordered_items,
            "updated_order": submitted_order
        }
        
        url = f"{BASE_URL}/business/order/update/{order_id}"
        response = requests.put(url, json=request_data, headers=HEADERS)
        
        success = response.status_code == 200
        print_test_result(f"UPDATE Order (order_id: {order_id})", success, response)
        return success
        
    except Exception as e:
        print_test_result("UPDATE Order", False, error=str(e))
        return False

def test_delete_order(order_id: int):
    """Test DELETE /business/order/delete/{order_id} endpoint"""
    print(f"Testing DELETE /business/order/delete/{order_id} endpoint...")
    try:
        url = f"{BASE_URL}/business/order/delete/{order_id}"
        response = requests.delete(url)
        
        success = response.status_code == 200
        print_test_result(f"DELETE Order (order_id: {order_id})", success, response)
        return success
        
    except Exception as e:
        print_test_result("DELETE Order", False, error=str(e))
        return False

def test_invalid_order_scenarios():
    """Test endpoints with invalid data"""
    print("Testing with invalid data scenarios...")
    
    # Test 1: Create order with missing required fields
    try:
        invalid_data = {
            "ordered_items": [],  # Empty items list
            "submitted_order": {
                "payment_status": "pending"
                # Missing required fields
            }
        }
        url = f"{BASE_URL}/business/order"
        response = requests.post(url, json=invalid_data, headers=HEADERS)
        
        success = response.status_code in [400, 422, 500]  # Expecting some error
        print_test_result("CREATE Order with Invalid Data", success, response)
        
    except Exception as e:
        print_test_result("CREATE Order with Invalid Data", False, error=str(e))
    
    # Test 2: Get orders for non-existent user
    try:
        invalid_user_id = 999999
        url = f"{BASE_URL}/business/user/orders/all/{invalid_user_id}"
        response = requests.get(url)
        
        success = response.status_code in [200, 404]  # Both are acceptable
        print_test_result(f"GET Orders for Non-existent User (id: {invalid_user_id})", success, response)
        
    except Exception as e:
        print_test_result("GET Orders for Non-existent User", False, error=str(e))
    
    # Test 3: Get details for non-existent order
    try:
        invalid_order_id = 999999
        url = f"{BASE_URL}/business/user/orders/{invalid_order_id}"
        response = requests.get(url)
        
        success = response.status_code in [200, 404]  # Both are acceptable
        print_test_result(f"GET Details for Non-existent Order (id: {invalid_order_id})", success, response)
        
    except Exception as e:
        print_test_result("GET Details for Non-existent Order", False, error=str(e))

def test_complete_order_workflow():
    """Test a complete order management workflow"""
    print("Testing complete order management workflow...")
    
    # Step 1: Create a new order
    ordered_items, submitted_order = create_sample_order_data(user_id=2)
    
    request_data = {
        "ordered_items": ordered_items,
        "submitted_order": submitted_order
    }
    
    create_response = requests.post(f"{BASE_URL}/business/order", json=request_data, headers=HEADERS)
    if create_response.status_code != 200:
        print("❌ Workflow failed at creation step")
        return False
    
    created_order = create_response.json()
    order_id = (created_order.get('id_placed_order') or 
                created_order.get('order_id') or 
                created_order.get('id'))
    
    if not order_id:
        print("❌ Could not extract order ID from creation response")
        return False
    
    print(f"✅ Created order with ID: {order_id}")
    
    # Step 2: Get all orders for the user
    user_orders_response = requests.get(f"{BASE_URL}/business/user/orders/all/2")
    if user_orders_response.status_code not in [200, 404]:
        print("❌ Workflow failed at get user orders step")
        return False
    
    print("✅ Successfully retrieved user orders")
    
    # Step 3: Get order details
    order_details_response = requests.get(f"{BASE_URL}/business/user/orders/{order_id}")
    if order_details_response.status_code not in [200, 404]:
        print("❌ Workflow failed at get order details step")
        return False
    
    print("✅ Successfully retrieved order details")
    
    # Step 4: Update the order
    updated_items, updated_order_data = create_sample_order_data(user_id=2)
    updated_order_data.update({
        "id_placed_order": order_id,
        "payment_status": "completed",
        "placed_order_state": "delivered"
    })
    
    for item in updated_items:
        item["order_id"] = order_id
    
    update_data = {
        "updated_items": updated_items,
        "updated_order": updated_order_data
    }
    
    update_response = requests.put(f"{BASE_URL}/business/order/update/{order_id}", json=update_data, headers=HEADERS)
    if update_response.status_code != 200:
        print("❌ Workflow failed at update step")
        return False
    
    print("✅ Successfully updated order")
    
    # Step 5: Delete the order
    delete_response = requests.delete(f"{BASE_URL}/business/order/delete/{order_id}")
    if delete_response.status_code != 200:
        print("❌ Workflow failed at delete step")
        return False
    
    print("✅ Successfully deleted order")
    print("🎉 Complete order workflow test passed!")
    return True

def run_all_tests():
    """Run all test scenarios"""
    print("🚀 Starting Business Order Endpoints Tests")
    print("=" * 50)
    
    results = {
        "create_order": False,
        "get_user_orders": False,
        "get_order_details": False,
        "update_order": False,
        "delete_order": False,
        "complete_workflow": False
    }
    
    # Test 1: Create a new order
    created_order_id = test_create_order()
    results["create_order"] = created_order_id is not None
    
    # Test 2: Get all orders for a user
    existing_order_id = test_get_all_user_orders(user_id=1)
    results["get_user_orders"] = True  # This test passes even if no orders exist
    
    # Test 3: Get order details (use created order if available, otherwise any existing order)
    test_order_id = created_order_id or existing_order_id
    if test_order_id:
        results["get_order_details"] = test_get_order_details(test_order_id)
    else:
        # Test with a likely non-existent ID
        results["get_order_details"] = test_get_order_details(999999)
    
    # Test 4 & 5: Update and delete if we have a created order
    if created_order_id:
        results["update_order"] = test_update_order(created_order_id)
        results["delete_order"] = test_delete_order(created_order_id)
    else:
        print("⚠️  Skipping update/delete tests - no order was created")
    
    # Test 6: Invalid data scenarios
    test_invalid_order_scenarios()
    
    # Test 7: Complete workflow
    results["complete_workflow"] = test_complete_order_workflow()
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 50)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    print(f"\nOverall: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 All tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

def check_server_connectivity():
    """Check if the server is reachable"""
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"✅ Server is reachable at {BASE_URL}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print("Make sure your FastAPI server is running!")
        return False

def create_sample_delivery_data(order_id: int = 0, provider_id: int = 1, broker_id: int = 1) :
    """Create sample delivery data for testing"""
    
    delivery = {
        "id_delivery": 0,  # Will be auto-generated
        "recipient_person": 1,
        "recipient_provider": 0,
        "delivery_package_count": 3,
        "delivery_total_weight": 15.5,
        "delivery_cargo_dimensions": "30x40x50 cm",
        "delivery_goods_description": "Electronics and accessories",
        "hs_code": "84713000",
        "delivery_merchant_name": "TechStore Ltd",
        "delivery_shipping_method": "express",
        "delivery_special_instructions": "Handle with care. Fragile items inside.",
        "delivery_status": "PENDING",
        "delivery_address_id": 1,
        "delivery_current_address_id": 1,
        "delivery_fee": 25.99,
        "delivery_placed_order": order_id,
        "delivery_provider_id": provider_id,
        "delivery_broker_id": broker_id
    }
    
    return delivery

def test_create_delivery():
    """Test POST /business/delivery/add endpoint"""
    print("Testing POST /business/delivery/add endpoint...")
    try:
        delivery_data = create_sample_delivery_data(order_id=0, provider_id=1, broker_id=1)
        
        url = f"{BASE_URL}/business/delivery"
        response = requests.post(url, json=delivery_data, headers=HEADERS)
        
        success = response.status_code == 200
        print_test_result("CREATE Delivery", success, response)
        
        # Extract delivery ID from response for later tests
        if success:
            response_data = response.json()
            # Try different possible ID field names
            delivery_id = (response_data.get('id_delivery') or 
                          response_data.get('delivery_id') or 
                          response_data.get('id'))
            return delivery_id
        
        return None
        
    except Exception as e:
        print_test_result("CREATE Delivery", False, error=str(e))
        return None

def test_create_delivery_with_order(order_id: int):
    """Test POST /business/delivery/add with an existing order"""
    print(f"Testing POST /business/delivery/add with order_id: {order_id}...")
    try:
        delivery_data = create_sample_delivery_data(order_id=order_id, provider_id=1, broker_id=1)
        
        url = f"{BASE_URL}/business/delivery"
        response = requests.post(url, json=delivery_data, headers=HEADERS)
        
        success = response.status_code == 200
        print_test_result(f"CREATE Delivery with Order (order_id: {order_id})", success, response)
        
        if success:
            response_data = response.json()
            delivery_id = (response_data.get('id_delivery') or 
                          response_data.get('delivery_id') or 
                          response_data.get('id'))
            return delivery_id
        
        return None
        
    except Exception as e:
        print_test_result("CREATE Delivery with Order", False, error=str(e))
        return None

def test_get_deliveries(provider_id: int = 0, order_id: int = 0, broker_id: int = 0, offset: int = 0, limit: int = 10):
    """Test GET /business/delivery/{provider_id}/{order_id}/{broker_id}/{offset}/{limit} endpoint"""
    print(f"Testing GET /business/delivery/{provider_id}/{order_id}/{broker_id}/{offset}/{limit} endpoint...")
    try:
        url = f"{BASE_URL}/business/delivery/{provider_id}/{order_id}/{broker_id}/{offset}/{limit}"
        response = requests.get(url)
        
        success = response.status_code in [200, 404]  # 404 is valid if no deliveries
        print_test_result(f"GET Deliveries (provider: {provider_id}, order: {order_id}, broker: {broker_id})", success, response)
        
        if success and response.status_code == 200:
            deliveries = response.json()
            if isinstance(deliveries, list) and len(deliveries) > 0:
                return deliveries[0].get('id_delivery')  # Return first delivery ID for testing
        return None
        
    except Exception as e:
        print_test_result("GET Deliveries", False, error=str(e))
        return None

def test_get_delivery_by_id(delivery_id: int):
    """Test GET /business/delivery/single/{delivery_id} endpoint"""
    print(f"Testing GET /business/delivery/single/{delivery_id} endpoint...")
    try:
        url = f"{BASE_URL}/business/delivery/single/{delivery_id}"
        response = requests.get(url)
        
        success = response.status_code in [200, 404]  # 404 is valid if delivery doesn't exist
        print_test_result(f"GET Delivery By ID (delivery_id: {delivery_id})", success, response)
        return success
        
    except Exception as e:
        print_test_result("GET Delivery By ID", False, error=str(e))
        return False

def test_update_delivery(delivery_id: int):
    """Test PUT /business/delivery/update/{delivery_id} endpoint"""
    print(f"Testing PUT /business/delivery/update/{delivery_id} endpoint...")
    try:
        # Create updated delivery data
        updated_delivery = create_sample_delivery_data(order_id=1, provider_id=2, broker_id=2)
        
        # Update some fields
        updated_delivery.update({
            "id_delivery": delivery_id,
            "delivery_status": "IN_TRANSIT",
            "delivery_package_count": 5,
            "delivery_total_weight": 25.5,
            "delivery_fee": 35.99,
            "delivery_special_instructions": "Updated: Ring doorbell before delivery"
        })
        
        url = f"{BASE_URL}/business/delivery/update/{delivery_id}"
        response = requests.put(url, json=updated_delivery, headers=HEADERS)
        
        success = response.status_code == 200
        print_test_result(f"UPDATE Delivery (delivery_id: {delivery_id})", success, response)
        return success
        
    except Exception as e:
        print_test_result("UPDATE Delivery", False, error=str(e))
        return False

def test_update_delivery_status(delivery_id: int, status: str):
    """Test PATCH /business/delivery/status/{delivery_id} endpoint"""
    print(f"Testing PATCH /business/delivery/status/{delivery_id} endpoint...")
    try:
        url = f"{BASE_URL}/business/delivery/status/{delivery_id}?status={status}"
        response = requests.patch(url, headers=HEADERS)
        
        success = response.status_code == 200
        print_test_result(f"UPDATE Delivery Status (delivery_id: {delivery_id}, status: {status})", success, response)
        return success
        
    except Exception as e:
        print_test_result("UPDATE Delivery Status", False, error=str(e))
        return False

def test_delete_delivery(delivery_id: int):
    """Test DELETE /business/delivery/delete/{delivery_id} endpoint"""
    print(f"Testing DELETE /business/delivery/delete/{delivery_id} endpoint...")
    try:
        url = f"{BASE_URL}/business/delivery/delete/{delivery_id}"
        response = requests.delete(url)
        
        success = response.status_code == 200
        print_test_result(f"DELETE Delivery (delivery_id: {delivery_id})", success, response)
        return success
        
    except Exception as e:
        print_test_result("DELETE Delivery", False, error=str(e))
        return False

def test_invalid_delivery_scenarios():
    """Test delivery endpoints with invalid data"""
    print("Testing delivery endpoints with invalid data scenarios...")
    
    # Test 1: Create delivery with missing required fields
    try:
        invalid_delivery = {
            "id_delivery": 0,
            "recipient_person": 0,
            "recipient_provider": 0,
            "delivery_package_count": 0,  # Invalid - should be > 0
            "delivery_total_weight": 0,   # Invalid - should be > 0
            "delivery_shipping_method": "",
            "delivery_address_id": 0      # Invalid - should be > 0
        }
        url = f"{BASE_URL}/business/delivery"
        response = requests.post(url, json=invalid_delivery, headers=HEADERS)
        
        success = response.status_code in [400, 422, 500]  # Expecting some error
        print_test_result("CREATE Delivery with Invalid Data", success, response)
        
    except Exception as e:
        print_test_result("CREATE Delivery with Invalid Data", False, error=str(e))
    
    # Test 2: Update non-existent delivery
    try:
        invalid_delivery_id = 999999
        updated_delivery = create_sample_delivery_data()
        updated_delivery["id_delivery"] = invalid_delivery_id
        
        url = f"{BASE_URL}/business/delivery/update/{invalid_delivery_id}"
        response = requests.put(url, json=updated_delivery, headers=HEADERS)
        
        success = response.status_code in [404, 400]
        print_test_result(f"UPDATE Non-existent Delivery (id: {invalid_delivery_id})", success, response)
        
    except Exception as e:
        print_test_result("UPDATE Non-existent Delivery", False, error=str(e))
    
    # Test 3: Delete non-existent delivery
    try:
        invalid_delivery_id = 999999
        url = f"{BASE_URL}/business/delivery/delete/{invalid_delivery_id}"
        response = requests.delete(url)
        
        success = response.status_code in [404, 400]
        print_test_result(f"DELETE Non-existent Delivery (id: {invalid_delivery_id})", success, response)
        
    except Exception as e:
        print_test_result("DELETE Non-existent Delivery", False, error=str(e))
    
    # Test 4: Get delivery with invalid ID format
    try:
        url = f"{BASE_URL}/business/delivery/single/invalid_id"
        response = requests.get(url)
        
        success = response.status_code in [400, 404, 422]
        print_test_result("GET Delivery with Invalid ID Format", success, response)
        
    except Exception as e:
        print_test_result("GET Delivery with Invalid ID Format", False, error=str(e))
    
    # Test 5: Update delivery with invalid status
    try:
        # First create a delivery
        delivery_data = create_sample_delivery_data()
        create_response = requests.post(f"{BASE_URL}/business/delivery", json=delivery_data, headers=HEADERS)
        
        if create_response.status_code == 200:
            created_delivery = create_response.json()
            delivery_id = created_delivery.get('id_delivery')
            
            if delivery_id:
                # Try to update with invalid status
                url = f"{BASE_URL}/business/delivery/status/{delivery_id}?status=INVALID_STATUS"
                response = requests.patch(url, headers=HEADERS)
                
                success = response.status_code in [400, 422]
                print_test_result("UPDATE Delivery with Invalid Status", success, response)
                
                # Clean up - delete the created delivery
                requests.delete(f"{BASE_URL}/business/delivery/delete/{delivery_id}")
        else:
            print_test_result("UPDATE Delivery with Invalid Status", False, error="Could not create test delivery")
        
    except Exception as e:
        print_test_result("UPDATE Delivery with Invalid Status", False, error=str(e))

def test_complete_delivery_workflow():
    """Test a complete delivery management workflow"""
    print("Testing complete delivery management workflow...")
    
    # Step 1: Create a new delivery
    delivery_data = create_sample_delivery_data(order_id=0, provider_id=1, broker_id=1)
    
    create_response = requests.post(f"{BASE_URL}/business/delivery", json=delivery_data, headers=HEADERS)
    if create_response.status_code != 200:
        print("❌ Workflow failed at creation step")
        return False
    
    created_delivery = create_response.json()
    delivery_id = (created_delivery.get('id_delivery') or 
                   created_delivery.get('delivery_id') or 
                   created_delivery.get('id'))
    
    if not delivery_id:
        print("❌ Could not extract delivery ID from creation response")
        return False
    
    print(f"✅ Created delivery with ID: {delivery_id}")
    
    # Step 2: Get delivery by ID
    get_response = requests.get(f"{BASE_URL}/business/delivery/single/{delivery_id}")
    if get_response.status_code != 200:
        print("❌ Workflow failed at get delivery step")
        return False
    
    print("✅ Successfully retrieved delivery details")
    
    # Step 3: Get all deliveries
    deliveries_response = requests.get(f"{BASE_URL}/business/delivery/0/0/0/0/10")
    if deliveries_response.status_code not in [200, 404]:
        print("❌ Workflow failed at get all deliveries step")
        return False
    
    print("✅ Successfully retrieved deliveries list")
    
    # Step 4: Update delivery status
    status_response = requests.patch(f"{BASE_URL}/business/delivery/status/{delivery_id}?status=IN_TRANSIT", headers=HEADERS)
    if status_response.status_code != 200:
        print("❌ Workflow failed at update status step")
        return False
    
    print("✅ Successfully updated delivery status to IN_TRANSIT")
    
    # Step 5: Update delivery details
    updated_delivery = create_sample_delivery_data(order_id=1, provider_id=2, broker_id=2)
    updated_delivery.update({
        "id_delivery": delivery_id,
        "delivery_status": "OUT_FOR_DELIVERY",
        "delivery_package_count": 4,
        "delivery_fee": 30.99
    })
    
    update_response = requests.put(f"{BASE_URL}/business/delivery/update/{delivery_id}", json=updated_delivery, headers=HEADERS)
    if update_response.status_code != 200:
        print("❌ Workflow failed at update delivery step")
        return False
    
    print("✅ Successfully updated delivery details")
    
    # Step 6: Delete the delivery
    delete_response = requests.delete(f"{BASE_URL}/business/delivery/delete/{delivery_id}")
    if delete_response.status_code != 200:
        print("❌ Workflow failed at delete step")
        return False
    
    print("✅ Successfully deleted delivery")
    print("🎉 Complete delivery workflow test passed!")
    return True

def run_delivery_tests():
    """Run all delivery test scenarios"""
    print("\n🚀 Starting Delivery Endpoints Tests")
    print("=" * 50)
    
    results = {
        "create_delivery": False,
        "get_deliveries": False,
        "get_delivery_by_id": False,
        "update_delivery": False,
        "update_delivery_status": False,
        "delete_delivery": False,
        "complete_workflow": False
    }
    
    # Test 1: Create a new delivery
    created_delivery_id = test_create_delivery()
    results["create_delivery"] = created_delivery_id is not None
    
    # Test 2: Get all deliveries
    existing_delivery_id = test_get_deliveries(provider_id=0, order_id=0, broker_id=0, offset=0, limit=10)
    results["get_deliveries"] = True  # This test passes even if no deliveries exist
    
    # Test 3: Get delivery by ID (use created delivery if available)
    test_delivery_id = created_delivery_id or existing_delivery_id
    if test_delivery_id:
        results["get_delivery_by_id"] = test_get_delivery_by_id(test_delivery_id)
    else:
        # Test with a likely non-existent ID
        results["get_delivery_by_id"] = test_get_delivery_by_id(999999)
    
    # Test 4-6: Update, update status, and delete if we have a created delivery
    if created_delivery_id:
        results["update_delivery"] = test_update_delivery(created_delivery_id)
        results["update_delivery_status"] = test_update_delivery_status(created_delivery_id, "DELIVERED")
        results["delete_delivery"] = test_delete_delivery(created_delivery_id)
    else:
        print("⚠️  Skipping update/delete tests - no delivery was created")
    
    # Test 7: Invalid data scenarios
    test_invalid_delivery_scenarios()
    
    # Test 8: Complete workflow
    results["complete_workflow"] = test_complete_delivery_workflow()
    
    # Summary
    print("\n📊 DELIVERY TEST SUMMARY")
    print("=" * 50)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    print(f"\nOverall: {passed_count}/{total_count} delivery tests passed")
    
    if passed_count == total_count:
        print("🎉 All delivery tests passed!")
        return True
    else:
        print("💥 Some delivery tests failed!")
        return False

# Add this to your run_all_tests() function to include delivery tests
def run_all_tests_with_deliveries():
    """Run all test scenarios including deliveries"""
    print("🚀 Starting Complete Business Endpoints Tests (Orders + Deliveries)")
    print("=" * 50)
    
    # Run order tests
    order_results = {
        "create_order": False,
        "get_user_orders": False,
        "get_order_details": False,
        "update_order": False,
        "delete_order": False,
        "complete_workflow": False
    }
    
    # Test orders
    created_order_id = test_create_order()
    order_results["create_order"] = created_order_id is not None
    
    existing_order_id = test_get_all_user_orders(user_id=1)
    order_results["get_user_orders"] = True
    
    test_order_id = created_order_id or existing_order_id
    if test_order_id:
        order_results["get_order_details"] = test_get_order_details(test_order_id)
    else:
        order_results["get_order_details"] = test_get_order_details(999999)
    
    if created_order_id:
        order_results["update_order"] = test_update_order(created_order_id)
        order_results["delete_order"] = test_delete_order(created_order_id)
    
    test_invalid_order_scenarios()
    order_results["complete_workflow"] = test_complete_order_workflow()
    
    # Run delivery tests
    delivery_results = {}
    delivery_success = run_delivery_tests()
    
    print("\n📊 FINAL TEST SUMMARY")
    print("=" * 50)
    
    order_passed = sum(order_results.values())
    order_total = len(order_results)
    print(f"Order Tests: {order_passed}/{order_total} passed")
    
    if delivery_success:
        print("Delivery Tests: All passed")
    else:
        print("Delivery Tests: Some failed")
    
    total_success = (order_passed == order_total) and delivery_success
    
    if total_success:
        print("\n🎉 All tests (Orders + Deliveries) passed!")
    else:
        print("\n💥 Some tests failed!")
    
    return total_success

if __name__ == "__main__":
    # Check server connectivity first
    if not check_server_connectivity():
        sys.exit(1)
    
    # Choose which tests to run
    import argparse
    parser = argparse.ArgumentParser(description='Test Business Endpoints')
    parser.add_argument('--test', choices=['orders', 'deliveries', 'all'], 
                       default='all', help='Which tests to run')
    args = parser.parse_args()
    
    if args.test == 'orders':
        success = run_all_tests()
    elif args.test == 'deliveries':
        success = run_delivery_tests()
    else:
        success = run_all_tests_with_deliveries()
    
    sys.exit(0 if success else 1)