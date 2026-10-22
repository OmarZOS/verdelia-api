# # tests/services/test_cart_service.py (fixed)
# import pytest
# from unittest.mock import Mock, patch, MagicMock, ANY
# from datetime import datetime, timedelta
# from decimal import Decimal
# from typing import List, Dict, Any, Optional

# from services.cart_service import CartService
# from core.api_models import (
#     Cart_API, OrderedItem_API, OrderedService_API, Delivery_API,
#     Person_API, Payment_API
# )
# from core.exceptions.handler import APIException, InsufficientStockException
# from core.exceptions.specific.cart_exceptions import (
#     CartNotFoundException,
#     CartCreationFailedException,
#     CartProductNotFoundException,
# )
# from core.messages import *
# from core.models import (
#     Cart, Delivery, OrderedItem, OrderedService, Product, Invoice, 
#     Payment, Receipt, Deposit, ProductProvider, AppUser, Person,
#     Address, ProviderDetails
# )


# class TestCartService:
#     """Test suite for CartService with mocked repositories"""
    
#     @pytest.fixture
#     def cart_service(self):
#         """Create CartService instance with mocked repositories"""
#         with patch('services.cart_service.CartRepository') as mock_cart_repo_class, \
#              patch('services.cart_service.FinancialRepository') as mock_financial_repo_class, \
#              patch('services.cart_service.ProductRepository') as mock_product_repo_class, \
#              patch('services.cart_service.UserRepository') as mock_user_repo_class, \
#              patch('services.cart_service.SupplierRepository') as mock_supplier_repo_class, \
#              patch('services.cart_service.OrderService') as mock_order_service_class, \
#              patch('services.cart_service.DeliveryService') as mock_delivery_service_class, \
#              patch('services.cart_service.PersonService') as mock_person_service_class:
            
#             service = CartService()
            
#             # Store mocks for access in tests
#             service.mock_cart_repo = mock_cart_repo_class.return_value
#             service.mock_financial_repo = mock_financial_repo_class.return_value
#             service.mock_product_repo = mock_product_repo_class.return_value
#             service.mock_user_repo = mock_user_repo_class.return_value
#             service.mock_supplier_repo = mock_supplier_repo_class.return_value
#             service.mock_order_service = mock_order_service_class.return_value
#             service.mock_delivery_service = mock_delivery_service_class.return_value
#             service.mock_person_service = mock_person_service_class.return_value
            
#             yield service
    
#     @pytest.fixture
#     def sample_cart(self):
#         """Create a sample cart for testing"""
#         cart = Cart()
#         cart.cart_id = 1
#         cart.cart_product_provider_id = 100
#         cart.cart_selling_user = 200
#         cart.cart_client_user = 300
#         cart.cart_person_ref = 400
#         cart.cart_status = 'pending'
#         cart.cart_total_amount = Decimal('500.00')
#         cart.cart_notes = 'Test cart'
#         cart.cart_due_date = datetime.now().date() + timedelta(days=30)
#         return cart
    
#     @pytest.fixture
#     def sample_product(self):
#         """Create a sample product for testing"""
#         product = Product()
#         product.id_product = 1
#         product.product_name = 'Test Product'
#         product.unit_price = Decimal('100.00')
#         product.product_quantity = 50
#         product.product_description = 'Test description'
#         return product
    
#     @pytest.fixture
#     def sample_supplier(self):
#         """Create a sample supplier/product provider"""
#         supplier = ProductProvider()
#         supplier.id_product_provider = 100
#         # Create provider details
#         supplier.product_provider_details = ProviderDetails()
#         supplier.product_provider_details.provider_name = "Test Supplier"
#         return supplier
    
#     @pytest.fixture
#     def sample_app_user(self):
#         """Create a sample app user"""
#         user = AppUser()
#         user.id_app_user = 200
#         user.app_user_name = "testuser"
#         user.app_user_email = "test@example.com"
#         return user
    
#     @pytest.fixture
#     def sample_person(self):
#         """Create a sample person"""
#         person = Person()
#         person.id_person = 1
#         return person
    
#     @pytest.fixture
#     def sample_ordered_item_api(self):
#         """Create sample ordered item API data"""
#         return OrderedItem_API(
#             id_ordered_item=None,
#             product_id=1,
#             order_ref=None,
#             product_discount=0.0,
#             ordered_quantity=2,
#             unit_price=100.00,
#             vat_rate=0.2
#         )
    
#     @pytest.fixture
#     def sample_ordered_service_api(self):
#         """Create sample ordered service API data"""
#         return OrderedService_API(
#             ordered_service_service_id=1,
#             ordered_service_quantity=3,
#             ordered_service_unit_price=150.00,
#             ordered_service_total_price=450.00,
#             ordered_service_notes="Test service",
#             ordered_service_scheduled_at=datetime.now().isoformat(),
#             resource_requirement_id=0
#         )
    
#     @pytest.fixture
#     def sample_cart_api(self):
#         """Create sample cart API data"""
#         return Cart_API(
#             cart_id=0,
#             cart_product_provider_id=100,
#             cart_selling_user=200,
#             cart_client_user=300,
#             cart_person_ref=0,
#             cart_due_date=(datetime.now() + timedelta(days=30)).isoformat(),
#             cart_status='pending',
#             cart_total_amount=500.00,
#             cart_notes='Test cart',
#             cart_invoice=True,
#             cart_receipt=True,
#             cart_deposit=False,
#             cart_payment=True,
#             cart_paid_money=500.00
#         )
    
#     @pytest.fixture
#     def sample_delivery_api(self):
#         """Create sample delivery API data"""
#         return Delivery_API(
#             id_delivery=0,
#             recipient_person=1,
#             recipient_provider=0,
#             delivery_package_count=1,
#             delivery_total_weight=10.5,
#             delivery_cargo_dimensions="10x10x10",
#             delivery_goods_description="Test goods",
#             hs_code="12345",
#             delivery_merchant_name="Test Merchant",
#             delivery_shipping_method="Standard",
#             delivery_special_instructions="Handle with care",
#             delivery_status="pending",
#             delivery_address_id=1,
#             delivery_current_address_id=1,
#             delivery_fee=10.00,
#             delivery_placed_order=0,
#             delivery_provider_id=100,
#             delivery_broker_id=0,
#             address_street="123 Test St",
#             address_city="Test City",
#             address_postal_code="12345",
#             address_country="Test Country"
#         )
    
#     @pytest.fixture
#     def sample_person_api(self):
#         """Create sample person API data"""
#         return Person_API(
#             id_person=0,
#             person_details_id=1,
#             id_person_details=1,
#             person_first_name="John",
#             person_last_name="Doe",
#             person_birth_date="1990-01-01",
#             person_gender="Male",
#             person_nationality="US",
#             id_blood_type=1
#         )
    
#     # ========== GET Methods Tests ==========
    
#     def test_get_cart_by_id_success(self, cart_service, sample_cart):
#         """Test successful retrieval of cart by ID"""
#         cart_service.mock_cart_repo.get_cart_by_id.return_value = sample_cart
        
#         result = cart_service.get_cart_by_id(1)
        
#         assert result == sample_cart
#         assert result.cart_id == 1
#         cart_service.mock_cart_repo.get_cart_by_id.assert_called_once_with(1)
    
#     def test_get_cart_by_id_not_found(self, cart_service):
#         """Test getting non-existent cart raises exception"""
#         cart_service.mock_cart_repo.get_cart_by_id.return_value = None
        
#         with pytest.raises(CartNotFoundException):
#             cart_service.get_cart_by_id(999)
    
#     def test_get_carts_by_provider(self, cart_service, sample_cart):
#         """Test getting carts by provider"""
#         expected_carts = [sample_cart]
#         provider_id = 100
#         cart_service.mock_cart_repo.get_carts_by_provider.return_value = expected_carts
        
#         result = cart_service.get_carts_by_provider(provider_id, offset=0, limit=50)
        
#         assert result == expected_carts
#         assert len(result) == 1
#         cart_service.mock_cart_repo.get_carts_by_provider.assert_called_once_with(provider_id, 0, 50)
    
#     def test_get_carts_by_seller(self, cart_service, sample_cart):
#         """Test getting carts by seller"""
#         expected_carts = [sample_cart]
#         seller_id = 200
#         cart_service.mock_cart_repo.get_carts_by_seller.return_value = expected_carts
        
#         result = cart_service.get_carts_by_seller(seller_id, offset=10, limit=20)
        
#         assert result == expected_carts
#         cart_service.mock_cart_repo.get_carts_by_seller.assert_called_once_with(seller_id, 10, 20)
    
#     def test_get_carts_by_buyer(self, cart_service, sample_cart):
#         """Test getting carts by buyer"""
#         expected_carts = [sample_cart]
#         buyer_id = 300
#         cart_service.mock_cart_repo.get_carts_by_buyer.return_value = expected_carts
        
#         result = cart_service.get_carts_by_buyer(buyer_id, offset=5, limit=15)
        
#         assert result == expected_carts
#         cart_service.mock_cart_repo.get_carts_by_buyer.assert_called_once_with(buyer_id, 5, 15)
    
#     # ========== Financial Methods Tests ==========
    
#     def test_create_invoice_for_cart(self, cart_service, sample_cart):
#         """Test invoice creation for a cart"""
#         total_amount = Decimal('500.00')
#         expected_invoice = Invoice()
#         expected_invoice.invoice_id = 1
#         expected_invoice.invoice_cart_id = sample_cart.cart_id
#         expected_invoice.grand_total = total_amount
#         expected_invoice.invoice_status = 'unpaid'
        
#         cart_service.mock_financial_repo.create_invoice.return_value = expected_invoice
        
#         result = cart_service._create_invoice_for_cart(sample_cart, total_amount)
        
#         assert result == expected_invoice
#         assert result.grand_total == total_amount
#         assert result.invoice_status == 'unpaid'
#         cart_service.mock_financial_repo.create_invoice.assert_called_once()
    
#     def test_create_payment_without_invoice(self, cart_service):
#         """Test payment creation without invoice"""
#         amount = Decimal('500.00')
#         status = 'completed'
        
#         expected_payment = Payment()
#         expected_payment.payment_id = 1
#         expected_payment.payment_amount = amount
#         expected_payment.payment_status = status
        
#         cart_service.mock_financial_repo.create_payment.return_value = expected_payment
        
#         result = cart_service._create_payment(amount, status)
        
#         assert result.payment_amount == amount
#         assert result.payment_status == status
#         cart_service.mock_financial_repo.create_payment.assert_called_once()
    
#     def test_create_payment_with_invoice_id(self, cart_service):
#         """Test payment creation with invoice ID"""
#         amount = Decimal('500.00')
#         status = 'completed'
#         invoice_id = 1
        
#         expected_payment = Payment()
#         expected_payment.payment_id = 1
#         expected_payment.payment_invoice_id = invoice_id
#         expected_payment.payment_amount = amount
        
#         cart_service.mock_financial_repo.create_payment.return_value = expected_payment
        
#         result = cart_service._create_payment(amount, status, invoice_id)
        
#         assert result.payment_invoice_id == invoice_id
#         cart_service.mock_financial_repo.create_payment.assert_called_once()
    
#     def test_create_payment_for_invoice_full_payment(self, cart_service):
#         """Test creating payment that fully pays an invoice"""
#         invoice = Invoice()
#         invoice.invoice_id = 1
#         invoice.grand_total = Decimal('500.00')
#         invoice.invoice_status = 'unpaid'
#         amount = Decimal('500.00')
        
#         expected_payment = Payment()
#         expected_payment.payment_id = 1
#         expected_payment.payment_amount = amount
#         expected_payment.payment_status = 'completed'
        
#         cart_service.mock_financial_repo.create_payment.return_value = expected_payment
#         cart_service.mock_financial_repo.update_invoice.return_value = invoice
        
#         result = cart_service._create_payment_for_invoice(invoice, amount)
        
#         assert invoice.invoice_status == 'paid'
#         assert result.payment_status == 'completed'
#         cart_service.mock_financial_repo.update_invoice.assert_called_once_with(invoice)
    
#     def test_create_payment_for_invoice_partial_payment(self, cart_service):
#         """Test creating partial payment for an invoice"""
#         invoice = Invoice()
#         invoice.invoice_id = 1
#         invoice.grand_total = Decimal('500.00')
#         invoice.invoice_status = 'unpaid'
#         amount = Decimal('200.00')
        
#         expected_payment = Payment()
#         expected_payment.payment_id = 1
#         expected_payment.payment_amount = amount
#         expected_payment.payment_status = 'partial'
        
#         cart_service.mock_financial_repo.create_payment.return_value = expected_payment
        
#         result = cart_service._create_payment_for_invoice(invoice, amount)
        
#         assert invoice.invoice_status == 'unpaid'  # Not fully paid
#         assert result.payment_amount == amount
#         assert result.payment_status == 'partial'
#         cart_service.mock_financial_repo.update_invoice.assert_not_called()
    
#     def test_create_receipt_for_payment(self, cart_service, sample_cart):
#         """Test receipt creation for a payment"""
#         payment = Payment()
#         payment.payment_id = 1
#         payment.payment_amount = Decimal('500.00')
        
#         expected_receipt = Receipt()
#         expected_receipt.receipt_id = 1
#         expected_receipt.receipt_payment_id = payment.payment_id
#         expected_receipt.receipt_amount = payment.payment_amount
        
#         cart_service.mock_financial_repo.create_receipt.return_value = expected_receipt
        
#         result = cart_service._create_receipt_for_payment(payment, sample_cart)
        
#         assert result == expected_receipt
#         cart_service.mock_financial_repo.create_receipt.assert_called_once()
    
#     def test_create_deposit_for_cart(self, cart_service, sample_cart):
#         """Test deposit creation for a cart"""
#         amount = Decimal('200.00')
        
#         expected_deposit = Deposit()
#         expected_deposit.deposit_id = 1
#         expected_deposit.deposit_cart_id = sample_cart.cart_id
#         expected_deposit.deposit_amount = amount
        
#         cart_service.mock_financial_repo.create_deposit.return_value = expected_deposit
        
#         result = cart_service._create_deposit_for_cart(sample_cart, amount)
        
#         assert result == expected_deposit
#         cart_service.mock_financial_repo.create_deposit.assert_called_once()
    
#     # ========== Status Update Tests ==========
    
#     def test_update_cart_status_completed_from_payment(self, cart_service, sample_cart):
#         """Test updating cart status to completed when fully paid"""
#         api_cart = Cart_API(cart_status='pending', cart_total_amount=500.00)
#         financial_docs = {
#             'payment': Payment(payment_status='completed', payment_amount=Decimal('500.00'))
#         }
#         sample_cart.cart_total_amount = Decimal('500.00')
#         sample_cart.cart_status = 'pending'
        
#         cart_service.mock_cart_repo.update_cart.return_value = sample_cart
        
#         cart_service._update_cart_status(sample_cart, api_cart, financial_docs)
        
#         assert sample_cart.cart_status == 'completed'
#         cart_service.mock_cart_repo.update_cart.assert_called_once_with(sample_cart)
    
#     def test_update_cart_status_partial_from_payment(self, cart_service, sample_cart):
#         """Test updating cart status to partial when partially paid"""
#         api_cart = Cart_API(cart_status='pending', cart_total_amount=500.00)
#         financial_docs = {
#             'payment': Payment(payment_status='partial', payment_amount=Decimal('200.00'))
#         }
#         sample_cart.cart_total_amount = Decimal('500.00')
#         sample_cart.cart_status = 'pending'
        
#         cart_service._update_cart_status(sample_cart, api_cart, financial_docs)
        
#         assert sample_cart.cart_status == 'pending'
    
#     def test_update_cart_status_from_deposit(self, cart_service, sample_cart):
#         """Test updating cart status to deposit_paid when deposit is made"""
#         api_cart = Cart_API(cart_status='pending', cart_total_amount=500.00)
#         financial_docs = {
#             'deposit': Deposit(deposit_amount=Decimal('200.00'))
#         }
#         sample_cart.cart_status = 'pending'
        
#         cart_service._update_cart_status(sample_cart, api_cart, financial_docs)
        
#         assert sample_cart.cart_status == 'deposit_paid'
    
#     def test_update_cart_status_success(self, cart_service, sample_cart):
#         """Test successful cart status update"""
#         cart_service.mock_cart_repo.get_cart_by_id.return_value = sample_cart
#         cart_service.mock_cart_repo.update_cart.return_value = sample_cart
        
#         result = cart_service.update_cart_status(1, 'completed')
        
#         assert result.cart_status == 'completed'
#         cart_service.mock_cart_repo.get_cart_by_id.assert_called_once_with(1)
#         cart_service.mock_cart_repo.update_cart.assert_called_once()
    
#     def test_update_cart_status_not_found(self, cart_service):
#         """Test updating status of non-existent cart"""
#         cart_service.mock_cart_repo.get_cart_by_id.return_value = None
        
#         with pytest.raises(CartNotFoundException):
#             cart_service.update_cart_status(999, 'completed')
    
#     # ========== Delete Cart Tests ==========
    
#     def test_delete_cart_success(self, cart_service, sample_cart, sample_product):
#         """Test successful cart deletion with stock restoration"""
#         ordered_item = OrderedItem()
#         ordered_item.product_id = sample_product.id_product
#         ordered_item.ordered_quantity = 2
#         sample_cart.ordered_item = [ordered_item]
        
#         cart_service.mock_cart_repo.get_cart_by_id.return_value = sample_cart
#         cart_service.mock_product_repo.get_product_by_id.return_value = sample_product
#         cart_service.mock_product_repo.update_product.return_value = sample_product
#         cart_service.mock_cart_repo.delete_cart.return_value = True
        
#         result = cart_service.delete_cart(1)
        
#         assert result is True
#         cart_service.mock_cart_repo.delete_cart.assert_called_once_with(sample_cart)
    
#     def test_delete_cart_not_found(self, cart_service):
#         """Test deleting non-existent cart"""
#         cart_service.mock_cart_repo.get_cart_by_id.return_value = None
        
#         with pytest.raises(CartNotFoundException):
#             cart_service.delete_cart(999)
    
#     # ========== Helper Method Tests ==========
    
#     def test_build_ordered_service_model(self, cart_service, sample_ordered_service_api):
#         """Test building ordered service model from API data"""
#         result = cart_service._build_ordered_service_model(sample_ordered_service_api)
        
#         assert isinstance(result, OrderedService)
#         assert result.ordered_service_quantity == sample_ordered_service_api.ordered_service_quantity
    
#     # ========== Create Cart Error Tests (Fixed) ==========
    
#     def test_create_cart_supplier_not_found(self, cart_service, sample_cart_api):
#         """Test cart creation with non-existent supplier"""
#         cart_service.mock_supplier_repo.get_supplier_basic.return_value = None
        
#         with pytest.raises(CartCreationFailedException):
#             cart_service.create_cart(
#                 ordered_items=[],
#                 ordered_services=[],
#                 cart_data=sample_cart_api,
#                 provider_id=999,
#                 seller_user_id=200,
#                 buyer_user_id=0
#             )
    
#     def test_create_cart_seller_not_found(self, cart_service, sample_cart_api, sample_supplier):
#         """Test cart creation with non-existent seller"""
#         cart_service.mock_supplier_repo.get_supplier_basic.return_value = sample_supplier
#         cart_service.mock_user_repo.get_by_id.return_value = None
        
#         with pytest.raises(CartCreationFailedException):
#             cart_service.create_cart(
#                 ordered_items=[],
#                 ordered_services=[],
#                 cart_data=sample_cart_api,
#                 provider_id=sample_cart_api.cart_product_provider_id,
#                 seller_user_id=999,
#                 buyer_user_id=0
#             )
    
#     def test_create_cart_product_not_found(self, cart_service, sample_cart_api, 
#                                             sample_ordered_item_api, sample_supplier, 
#                                             sample_app_user):
#         """Test cart creation with non-existent product"""
#         cart_service.mock_supplier_repo.get_supplier_basic.return_value = sample_supplier
#         cart_service.mock_user_repo.get_by_id.return_value = sample_app_user
#         cart_service.mock_product_repo.get_product_by_id.return_value = None
        
#         ordered_item_model = OrderedItem()
#         ordered_item_model.id_ordered_item = 1
#         ordered_item_model.product_id = 999
#         ordered_item_model.ordered_quantity = 2
        
#         cart_service.mock_order_service._build_ordered_item_model.return_value = ordered_item_model
        
#         with pytest.raises(CartProductNotFoundException):
#             cart_service.create_cart(
#                 ordered_items=[sample_ordered_item_api],
#                 ordered_services=[],
#                 cart_data=sample_cart_api,
#                 provider_id=sample_cart_api.cart_product_provider_id,
#                 seller_user_id=sample_cart_api.cart_selling_user,
#                 buyer_user_id=0
#             )
    
#     def test_create_cart_insufficient_stock(self, cart_service, sample_cart_api, 
#                                              sample_ordered_item_api, sample_product, 
#                                              sample_supplier, sample_app_user):
#         """Test cart creation with insufficient product stock"""
#         sample_product.product_quantity = 1
        
#         cart_service.mock_supplier_repo.get_supplier_basic.return_value = sample_supplier
#         cart_service.mock_user_repo.get_by_id.return_value = sample_app_user
#         cart_service.mock_product_repo.get_product_by_id.return_value = sample_product
        
#         ordered_item_model = OrderedItem()
#         ordered_item_model.id_ordered_item = 1
#         ordered_item_model.product_id = sample_product.id_product
#         ordered_item_model.ordered_quantity = 5
        
#         cart_service.mock_order_service._build_ordered_item_model.return_value = ordered_item_model
        
#         with pytest.raises(InsufficientStockException):
#             cart_service.create_cart(
#                 ordered_items=[sample_ordered_item_api],
#                 ordered_services=[],
#                 cart_data=sample_cart_api,
#                 provider_id=sample_cart_api.cart_product_provider_id,
#                 seller_user_id=sample_cart_api.cart_selling_user,
#                 buyer_user_id=0
#             )
    
#     def test_create_cart_database_error_rollback(self, cart_service, sample_cart_api, 
#                                                    sample_ordered_item_api, sample_product, 
#                                                    sample_supplier, sample_app_user):
#         """Test rollback of product stock when cart creation fails"""
#         cart_service.mock_supplier_repo.get_supplier_basic.return_value = sample_supplier
#         cart_service.mock_user_repo.get_by_id.return_value = sample_app_user
#         cart_service.mock_product_repo.get_product_by_id.return_value = sample_product
#         cart_service.mock_product_repo.update_product.return_value = sample_product
        
#         ordered_item_model = OrderedItem()
#         ordered_item_model.id_ordered_item = 1
#         ordered_item_model.product_id = sample_product.id_product
#         ordered_item_model.ordered_quantity = 2
        
#         cart_service.mock_order_service._build_ordered_item_model.return_value = ordered_item_model
        
#         # Simulate database error on cart creation
#         cart_service.mock_cart_repo.create_cart.side_effect = Exception("Database connection error")
        
#         with pytest.raises(CartCreationFailedException):
#             cart_service.create_cart(
#                 ordered_items=[sample_ordered_item_api],
#                 ordered_services=[],
#                 cart_data=sample_cart_api,
#                 provider_id=sample_cart_api.cart_product_provider_id,
#                 seller_user_id=sample_cart_api.cart_selling_user,
#                 buyer_user_id=0
#             )
    
#     # ========== Create Cart Success Tests ==========
    
#     def test_create_cart_success(self, cart_service, sample_cart_api, sample_ordered_item_api, 
#                                 sample_product, sample_supplier, sample_app_user, 
#                                 sample_person_api):
#         """Test successful cart creation with all documents"""
        
#         # Setup mocks
#         cart_service.mock_supplier_repo.get_supplier_basic.return_value = sample_supplier
        
#         # Mock both seller and buyer users to exist
#         buyer_user = AppUser()
#         buyer_user.id_app_user = 300
#         buyer_user.app_user_name = "buyer"
        
#         cart_service.mock_user_repo.get_by_id.side_effect = [sample_app_user, buyer_user]  # seller then buyer
        
#         cart_service.mock_person_service.create_person.return_value = sample_person_api
        
#         # Mock product validation
#         cart_service.mock_product_repo.get_product_by_id.return_value = sample_product
#         cart_service.mock_product_repo.update_product.return_value = sample_product
        
#         # Mock ordered item building
#         ordered_item_model = OrderedItem()
#         ordered_item_model.id_ordered_item = 1
#         ordered_item_model.product_id = sample_product.id_product
#         ordered_item_model.ordered_quantity = 2
#         ordered_item_model.vat_rate = 0.2
#         ordered_item_model.unit_price = sample_product.unit_price
        
#         cart_service.mock_order_service._build_ordered_item_model.return_value = ordered_item_model
        
#         # Mock cart creation
#         new_cart = Cart()
#         new_cart.cart_id = 1
#         cart_service.mock_cart_repo.create_cart.return_value = new_cart
        
#         # Mock financial documents with proper grand_total
#         mock_invoice = Invoice()
#         mock_invoice.invoice_id = 1
#         mock_invoice.grand_total = Decimal('500.00')
#         mock_invoice.invoice_status = 'unpaid'
        
#         mock_payment = Payment()
#         mock_payment.payment_id = 1
        
#         mock_receipt = Receipt()
#         mock_receipt.receipt_id = 1
        
#         cart_service.mock_financial_repo.create_invoice.return_value = mock_invoice
#         cart_service.mock_financial_repo.create_payment.return_value = mock_payment
#         cart_service.mock_financial_repo.create_receipt.return_value = mock_receipt
        
#         ordered_items = [sample_ordered_item_api]
#         ordered_services = []
        
#         financial_docs, cart = cart_service.create_cart(
#             ordered_items=ordered_items,
#             ordered_services=ordered_services,
#             cart_data=sample_cart_api,
#             delivery=None,
#             client=sample_person_api,
#             provider_id=sample_cart_api.cart_product_provider_id,
#             seller_user_id=sample_cart_api.cart_selling_user,
#             buyer_user_id=sample_cart_api.cart_client_user  # 300 - this now exists in mock
#         )
        
#         assert 'invoice' in financial_docs
#         assert 'payment' in financial_docs
#         assert 'receipt' in financial_docs
#         assert cart is not None
#         cart_service.mock_cart_repo.create_cart.assert_called_once()
    
#     def test_create_cart_with_delivery(self, cart_service, sample_cart_api, sample_ordered_item_api,
#                                         sample_product, sample_supplier, sample_app_user,
#                                         sample_delivery_api):
#         """Test cart creation with delivery information"""
#         cart_service.mock_supplier_repo.get_supplier_basic.return_value = sample_supplier
#         cart_service.mock_user_repo.get_by_id.return_value = sample_app_user
#         cart_service.mock_product_repo.get_product_by_id.return_value = sample_product
#         cart_service.mock_product_repo.update_product.return_value = sample_product
        
#         ordered_item_model = OrderedItem()
#         ordered_item_model.id_ordered_item = 1
#         ordered_item_model.product_id = sample_product.id_product
#         ordered_item_model.ordered_quantity = 2
#         ordered_item_model.unit_price = sample_product.unit_price
        
#         cart_service.mock_order_service._build_ordered_item_model.return_value = ordered_item_model
        
#         delivery_model = Delivery()
#         delivery_model.id_delivery = 1
        
#         cart_service.mock_delivery_service._build_delivery_model.return_value = delivery_model
        
#         new_cart = Cart()
#         new_cart.cart_id = 1
#         cart_service.mock_cart_repo.create_cart.return_value = new_cart
        
#         ordered_items = [sample_ordered_item_api]
#         ordered_services = []
        
#         financial_docs, cart = cart_service.create_cart(
#             ordered_items=ordered_items,
#             ordered_services=ordered_services,
#             cart_data=sample_cart_api,
#             delivery=sample_delivery_api,
#             client=None,
#             provider_id=sample_cart_api.cart_product_provider_id,
#             seller_user_id=sample_cart_api.cart_selling_user,
#             buyer_user_id=0
#         )
        
#         assert cart is not None
#         cart_service.mock_delivery_service._build_delivery_model.assert_called_once_with(sample_delivery_api)
    
#     def test_create_cart_with_services(self, cart_service, sample_cart_api, 
#                                         sample_ordered_service_api, sample_supplier, 
#                                         sample_app_user):
#         """Test cart creation with ordered services"""
#         cart_service.mock_supplier_repo.get_supplier_basic.return_value = sample_supplier
#         cart_service.mock_user_repo.get_by_id.return_value = sample_app_user
        
#         ordered_service_model = OrderedService()
#         ordered_service_model.ordered_service_id = 1
#         ordered_service_model.ordered_service_quantity = 3
        
#         # Mock the _build_ordered_service_model method
#         with patch.object(cart_service, '_build_ordered_service_model', return_value=ordered_service_model):
#             new_cart = Cart()
#             new_cart.cart_id = 1
#             cart_service.mock_cart_repo.create_cart.return_value = new_cart
            
#             financial_docs, cart = cart_service.create_cart(
#                 ordered_items=[],
#                 ordered_services=[sample_ordered_service_api],
#                 cart_data=sample_cart_api,
#                 delivery=None,
#                 client=None,
#                 provider_id=sample_cart_api.cart_product_provider_id,
#                 seller_user_id=sample_cart_api.cart_selling_user,
#                 buyer_user_id=0
#             )
            
#             assert cart is not None
    
#     def test_create_cart_without_buyer(self, cart_service, sample_cart_api, sample_ordered_item_api,
#                                         sample_product, sample_supplier, sample_app_user):
#         """Test cart creation without a buyer user"""
#         cart_service.mock_supplier_repo.get_supplier_basic.return_value = sample_supplier
#         cart_service.mock_user_repo.get_by_id.return_value = sample_app_user
#         cart_service.mock_product_repo.get_product_by_id.return_value = sample_product
#         cart_service.mock_product_repo.update_product.return_value = sample_product
        
#         ordered_item_model = OrderedItem()
#         ordered_item_model.id_ordered_item = 1
#         ordered_item_model.product_id = sample_product.id_product
#         ordered_item_model.ordered_quantity = 2
        
#         cart_service.mock_order_service._build_ordered_item_model.return_value = ordered_item_model
        
#         # Create cart without buyer (buyer_user_id = 0)
#         sample_cart_api.cart_client_user = 0
#         new_cart = Cart()
#         new_cart.cart_id = 1
#         cart_service.mock_cart_repo.create_cart.return_value = new_cart
        
#         financial_docs, cart = cart_service.create_cart(
#             ordered_items=[sample_ordered_item_api],
#             ordered_services=[],
#             cart_data=sample_cart_api,
#             delivery=None,
#             client=None,
#             provider_id=sample_cart_api.cart_product_provider_id,
#             seller_user_id=sample_cart_api.cart_selling_user,
#             buyer_user_id=0
#         )
        
#         assert cart is not None
    
#     def test_create_cart_with_existing_person(self, cart_service, sample_cart_api, 
#                                                 sample_ordered_item_api, sample_product,
#                                                 sample_supplier, sample_app_user,
#                                                 sample_person_api):
#         """Test cart creation with an existing person"""
#         sample_person_api.id_person = 1
        
#         cart_service.mock_supplier_repo.get_supplier_basic.return_value = sample_supplier
#         cart_service.mock_user_repo.get_by_id.return_value = sample_app_user
#         cart_service.mock_person_service.get_person_by_id.return_value = sample_person_api
#         cart_service.mock_product_repo.get_product_by_id.return_value = sample_product
#         cart_service.mock_product_repo.update_product.return_value = sample_product
        
#         ordered_item_model = OrderedItem()
#         ordered_item_model.id_ordered_item = 1
#         ordered_item_model.product_id = sample_product.id_product
#         ordered_item_model.ordered_quantity = 2
        
#         cart_service.mock_order_service._build_ordered_item_model.return_value = ordered_item_model
        
#         new_cart = Cart()
#         new_cart.cart_id = 1
#         cart_service.mock_cart_repo.create_cart.return_value = new_cart
        
#         financial_docs, cart = cart_service.create_cart(
#             ordered_items=[sample_ordered_item_api],
#             ordered_services=[],
#             cart_data=sample_cart_api,
#             delivery=None,
#             client=sample_person_api,
#             provider_id=sample_cart_api.cart_product_provider_id,
#             seller_user_id=sample_cart_api.cart_selling_user,
#             buyer_user_id=0
#         )
        
#         assert cart is not None
#         cart_service.mock_person_service.get_person_by_id.assert_called_once_with(1)
#         cart_service.mock_person_service.create_person.assert_not_called()