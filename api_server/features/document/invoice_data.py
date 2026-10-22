from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
import json
import base64
from io import BytesIO
from enum import Enum
from pathlib import Path
from decimal import Decimal

from features.document.utils.qr_generator import ProfessionalQRGenerator

class InvoiceStatus(Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class PaymentMethod(Enum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    CHECK = "check"

@dataclass
class PersonDetails:
    person_first_name: str
    person_last_name: str
    person_birth_date: str
    person_gender: str
    person_nationality: str
    id_person_details: int = 0
    
    def to_dict(self):
        return {
            "id_person_details": self.id_person_details,
            "person_first_name": self.person_first_name,
            "person_last_name": self.person_last_name,
            "person_birth_date": self.person_birth_date,
            "person_gender": self.person_gender,
            "person_nationality": self.person_nationality
        }

@dataclass
class Person:
    id_person: int
    person_details_id: int
    person_blood_type_id: Optional[int] = None
    person_location_id: Optional[int] = None
    person_details: Optional[PersonDetails] = None
    
    def to_dict(self):
        return {
            "id_person": self.id_person,
            "person_details_id": self.person_details_id,
            "person_blood_type_id": self.person_blood_type_id,
            "person_location_id": self.person_location_id,
            "person_details": self.person_details.to_dict() if self.person_details else None
        }

@dataclass
class AppUser:
    id_app_user: int
    app_user_name: str
    app_user_person_id: int
    app_user_type_id: int
    app_user_password: Optional[str] = None
    app_user_preferences: Optional[str] = None
    app_user_image_url: Optional[str] = None
    app_user_last_active: Optional[str] = None
    app_user_last_updated: Optional[str] = None
    app_user_creation: Optional[str] = None
    app_user_subscription_id: Optional[int] = None
    app_user_person: Optional[Person] = None
    
    def to_dict(self):
        return {
            "id_app_user": self.id_app_user,
            "app_user_name": self.app_user_name,
            "app_user_person_id": self.app_user_person_id,
            "app_user_type_id": self.app_user_type_id,
            "app_user_password": self.app_user_password,
            "app_user_preferences": self.app_user_preferences,
            "app_user_image_url": self.app_user_image_url,
            "app_user_last_active": self.app_user_last_active,
            "app_user_last_updated": self.app_user_last_updated,
            "app_user_creation": self.app_user_creation,
            "app_user_subscription_id": self.app_user_subscription_id,
            "app_user_person": self.app_user_person.to_dict() if self.app_user_person else None
        }

@dataclass
class ProviderDetails:
    provider_name: str
    provider_contact_info: str
    idprovider_details_id: int
    
    def to_dict(self):
        return {
            "idprovider_details_id": self.idprovider_details_id,
            "provider_name": self.provider_name,
            "provider_contact_info": self.provider_contact_info
        }

@dataclass
class ProductProvider:
    id_product_provider: int
    product_provider_details_id: int
    product_provider_type_id: int
    product_provider_details: ProviderDetails
    product_provider_owner: Optional[int] = None
    product_provider_location_id: Optional[int] = None
    product_provider_org_id: Optional[int] = None
    
    def to_dict(self):
        return {
            "id_product_provider": self.id_product_provider,
            "product_provider_details_id": self.product_provider_details_id,
            "product_provider_type_id": self.product_provider_type_id,
            "product_provider_details": self.product_provider_details.to_dict(),
            "product_provider_owner": self.product_provider_owner,
            "product_provider_location_id": self.product_provider_location_id,
            "product_provider_org_id": self.product_provider_org_id
        }

@dataclass
class OrderedProduct:
    id_product: int
    product_name: str
    product_price: float
    product_description: Optional[str] = None
    product_provider_id: Optional[int] = None
    product_brand: Optional[str] = None
    product_category_id: Optional[int] = None
    product_barcode: Optional[str] = None
    product_quantity: Optional[int] = None
    
    def to_dict(self):
        return {
            "id_product": self.id_product,
            "product_name": self.product_name,
            "product_price": self.unit_price,
            "product_description": self.product_description,
            "product_provider_id": self.product_provider_id,
            "product_brand": self.product_brand,
            "product_category_id": self.product_category_id,
            "product_barcode": self.product_barcode,
            "product_quantity": self.product_quantity
        }

@dataclass
class OrderedItem:
    id_ordered_item: int
    product_id: int
    ordered_quantity: int
    unit_price: float
    vat_rate: float
    product_discount: float
    order_ref: Optional[int] = None
    ordered_product: Optional[OrderedProduct] = None
    
    @property
    def total(self) -> float:
        discount_factor = (100 - self.product_discount) / 100
        vat_factor = (100 + self.vat_rate) / 100
        return self.ordered_quantity * self.unit_price * discount_factor * vat_factor
    
    def to_dict(self):
        return {
            "id_ordered_item": self.id_ordered_item,
            "product_id": self.product_id,
            "ordered_quantity": self.ordered_quantity,
            "unit_price": self.unit_price,
            "vat_rate": self.vat_rate,
            "product_discount": self.product_discount,
            "order_ref": self.order_ref,
            "ordered_product": self.ordered_product.to_dict() if self.ordered_product else None,
            "total": round(self.total, 2)
        }

@dataclass
class ProvidedService:
    """Service details from ordered_service_service"""
    provided_service_id: int
    provided_service_name: str
    provided_service_final_price: float
    provided_service_description: str
    provided_service_base_price: float
    provided_service_product_provider_id: int
    category_id: int
    provided_service_actual_duration: int
    provided_service_is_active: int
    provided_service_created_at: str
    provided_service_updated_at: str
    provided_service_deleted_at: Optional[str] = None
    provided_service_pricing_config: Optional[Dict] = None
    
    def to_dict(self):
        return {
            "provided_service_id": self.provided_service_id,
            "provided_service_name": self.provided_service_name,
            "provided_service_final_price": self.provided_service_final_price,
            "provided_service_description": self.provided_service_description,
            "provided_service_base_price": self.provided_service_base_price,
            "provided_service_product_provider_id": self.provided_service_product_provider_id,
            "category_id": self.category_id,
            "provided_service_actual_duration": self.provided_service_actual_duration,
            "provided_service_is_active": self.provided_service_is_active,
            "provided_service_created_at": self.provided_service_created_at,
            "provided_service_updated_at": self.provided_service_updated_at,
            "provided_service_deleted_at": self.provided_service_deleted_at,
            "provided_service_pricing_config": self.provided_service_pricing_config
        }

@dataclass
class OrderedService:
    ordered_service_id: int
    ordered_service_service_id: int
    ordered_service_quantity: int
    ordered_service_unit_price: float
    ordered_service_total_price: float
    ordered_service_notes: str
    ordered_service_cart_id: int
    ordered_service_scheduled_at: Optional[str] = None
    ordered_service_created_at: Optional[str] = None
    ordered_service_updated_at: Optional[str] = None
    ordered_service_service: Optional[ProvidedService] = None
    
    @property
    def total(self) -> float:
        return self.ordered_service_total_price
    
    def to_dict(self):
        return {
            "ordered_service_id": self.ordered_service_id,
            "ordered_service_service_id": self.ordered_service_service_id,
            "ordered_service_quantity": self.ordered_service_quantity,
            "ordered_service_unit_price": self.ordered_service_unit_price,
            "ordered_service_total_price": self.ordered_service_total_price,
            "ordered_service_notes": self.ordered_service_notes,
            "ordered_service_cart_id": self.ordered_service_cart_id,
            "ordered_service_scheduled_at": self.ordered_service_scheduled_at,
            "ordered_service_created_at": self.ordered_service_created_at,
            "ordered_service_updated_at": self.ordered_service_updated_at,
            "ordered_service_service": self.ordered_service_service.to_dict() if self.ordered_service_service else None,
            "total": round(self.total, 2)
        }

@dataclass
class InvoiceData:
    invoice_id: int
    invoice_reference: str
    grand_total: float
    invoice_status: str
    invoice_issue_date: str
    invoice_due_date: Optional[str]
    invoice_notes: Optional[str]
    invoice_cart_id: int
    created_at: str
    updated_at: str
    payment: List[Dict] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "invoice_id": self.invoice_id,
            "invoice_reference": self.invoice_reference,
            "grand_total": self.grand_total,
            "invoice_status": self.invoice_status,
            "invoice_issue_date": self.invoice_issue_date,
            "invoice_due_date": self.invoice_due_date,
            "invoice_notes": self.invoice_notes,
            "invoice_cart_id": self.invoice_cart_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "payment": self.payment
        }

@dataclass
class ReceiptData:
    receipt_id: int
    receipt_number: str
    receipt_amount: float
    receipt_notes: Optional[str]
    receipt_cart_ref: Optional[int]
    receipt_payment_id: Optional[int]
    receipt_created_at: str
    receipt_payment: Optional[Dict] = None
    deposit: List[Dict] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "receipt_id": self.receipt_id,
            "receipt_number": self.receipt_number,
            "receipt_amount": self.receipt_amount,
            "receipt_notes": self.receipt_notes,
            "receipt_cart_ref": self.receipt_cart_ref,
            "receipt_payment_id": self.receipt_payment_id,
            "receipt_created_at": self.receipt_created_at,
            "receipt_payment": self.receipt_payment,
            "deposit": self.deposit
        }

@dataclass
class Cart:
    cart_id: int
    cart_product_provider_id: int
    cart_selling_user: int
    cart_person_ref: int
    cart_client_user: Optional[int]
    cart_status: str
    cart_total_amount: float
    cart_notes: str
    cart_created_at: str
    cart_updated_at: str
    person: Optional[Person] = None
    app_user_: Optional[AppUser] = None
    cart_product_provider: Optional[ProductProvider] = None
    invoice: List[InvoiceData] = field(default_factory=list)
    receipt: List[ReceiptData] = field(default_factory=list)
    deposit: List[Dict] = field(default_factory=list)
    ordered_item: List[OrderedItem] = field(default_factory=list)
    ordered_service: List[OrderedService] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "cart_id": self.cart_id,
            "cart_product_provider_id": self.cart_product_provider_id,
            "cart_selling_user": self.cart_selling_user,
            "cart_person_ref": self.cart_person_ref,
            "cart_client_user": self.cart_client_user,
            "cart_status": self.cart_status,
            "cart_total_amount": self.cart_total_amount,
            "cart_notes": self.cart_notes,
            "cart_created_at": self.cart_created_at,
            "cart_updated_at": self.cart_updated_at,
            "person": self.person.to_dict() if self.person else None,
            "app_user_": self.app_user_.to_dict() if self.app_user_ else None,
            "cart_product_provider": self.cart_product_provider.to_dict() if self.cart_product_provider else None,
            "invoice": [inv.to_dict() for inv in self.invoice],
            "receipt": [rec.to_dict() for rec in self.receipt],
            "deposit": self.deposit,
            "ordered_item": [item.to_dict() for item in self.ordered_item],
            "ordered_service": [service.to_dict() for service in self.ordered_service]
        }

@dataclass
class Company:
    name: str
    address: str
    city_state_zip: str
    email: str
    phone: str
    website: str
    tax_id: str
    tax_id_label: str = "Tax ID"
    logo_path: Optional[str] = None
    tagline: Optional[str] = None
    
    @classmethod
    def from_product_provider(cls, product_provider: ProductProvider) -> 'Company':
        """Create Company from ProductProvider"""
        details = product_provider.product_provider_details
        
        # Parse contact info for phone/email
        contact_info = details.provider_contact_info or ""
        phone = "Not provided"
        email = "Not provided"
        website = "Not provided"
        
        # Extract email from contact info
        import re
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_info)
        if email_match:
            email = email_match.group(0)
        
        # Extract phone number (simplified)
        phone_match = re.search(r'(\+\d{1,3}[-.]?)?\d{3}[-.]?\d{3}[-.]?\d{4}', contact_info)
        if phone_match:
            phone = phone_match.group(0)
        
        # Extract website
        url_match = re.search(r'(https?://\S+)', contact_info)
        if url_match:
            website = url_match.group(0)
        
        return cls(
            name=details.provider_name,
            address="Address not specified",
            city_state_zip="Location not specified",
            email=email,
            phone=phone,
            website=website,
            tax_id="N/A",
            tax_id_label="Business ID",
            tagline="Quality products and services"
        )
    
    @classmethod
    def create_default_company(cls, cart_data: Dict) -> 'Company':
        """Create a default company when product provider is missing"""
        return cls(
            name=f"Business #{cart_data.get('cart_product_provider_id', 'Unknown')}",
            address="Address not specified",
            city_state_zip="Location not specified",
            email="contact@business.com",
            phone="Not provided",
            website="www.business.com",
            tax_id="N/A",
            tax_id_label="Business ID",
            tagline="Quality products and services"
        )
    
    def to_dict(self):
        return {
            "name": self.name,
            "address": self.address,
            "city_state_zip": self.city_state_zip,
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
            "tax_id": self.tax_id,
            "tax_id_label": self.tax_id_label,
            "tagline": self.tagline,
            "logo_path": str(self.logo_path) if self.logo_path else None
        }

@dataclass
class Client:
    name: str
    email: str
    address: str
    phone: str
    company: Optional[str] = None
    tax_id: Optional[str] = None
    person_id: Optional[int] = None
    
    @classmethod
    def from_person(cls, person: Person) -> 'Client':
        """Create Client from Person"""
        details = person.person_details
        
        # Build address (simplified)
        address_lines = []
        if details.person_nationality:
            address_lines.append(f"Nationality: {details.person_nationality}")
        
        return cls(
            name=f"{details.person_first_name} {details.person_last_name}",
            email="Not provided",
            address=", ".join(address_lines) if address_lines else "Address not specified",
            phone="Not provided",
            company=None,
            tax_id=None,
            person_id=person.id_person
        )
    
    @classmethod
    def from_app_user(cls, app_user: AppUser) -> 'Client':
        """Create Client from AppUser"""
        person = app_user.app_user_person
        if not person:
            raise ValueError("AppUser has no associated person")
        
        details = person.person_details
        if not details:
            raise ValueError("Person has no details")
        
        # Build address
        address_lines = []
        if details.person_nationality:
            address_lines.append(f"Nationality: {details.person_nationality}")
        
        return cls(
            name=f"{details.person_first_name} {details.person_last_name}",
            email=app_user.app_user_name,
            address=", ".join(address_lines) if address_lines else "Address not specified",
            phone="Not provided",
            company=None,
            tax_id=None,
            person_id=person.id_person
        )
    
    @classmethod
    def create_default_client(cls) -> 'Client':
        """Create a default client when no person/app_user is available"""
        return cls(
            name="Customer",
            email="customer@example.com",
            address="Address not specified",
            phone="Not provided",
            company=None,
            tax_id=None
        )
    
    def to_dict(self):
        return {
            "name": self.name,
            "email": self.email,
            "address": self.address,
            "phone": self.phone,
            "company": self.company,
            "tax_id": self.tax_id,
            "person_id": self.person_id
        }

@dataclass
class InvoiceItem:
    description: str
    quantity: float
    unit_price: float
    tax_rate: float = 0.0
    unit: str = "unit"
    details: Optional[str] = None
    item_type: str = "product"
    
    @property
    def total(self) -> float:
        return self.quantity * self.unit_price * (1 + self.tax_rate / 100)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "tax_rate": self.tax_rate,
            "unit": self.unit,
            "details": self.details,
            "total": self.total,
            "item_type": self.item_type
        }

@dataclass
class Invoice:
    company: Company
    client: Client
    items: List[InvoiceItem]
    invoice_reference: str
    issue_date: str
    due_date: str
    cart_id: int
    status: str = "draft"
    currency_symbol: str = "DZD"
    currency_code: str = "DZD"
    po_number: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    terms: Optional[str] = None
    discount_percent: float = 0.0
    shipping: float = 0.0
    amount_paid: float = 0.0
    payment_instructions: str = "Please make payment within 30 days of invoice date."
    payment_details: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        # Initialize QR generator
        self.qr_generator = ProfessionalQRGenerator(enable_caching=True)
    
    @classmethod
    def from_cart_and_invoice_data(cls, cart: Cart, invoice_data: InvoiceData) -> 'Invoice':
        """Create Invoice from Cart and InvoiceData"""
        # Get company from product provider or create default
        if cart.cart_product_provider:
            company = Company.from_product_provider(cart.cart_product_provider)
        else:
            # Create a mock cart_data dict with the cart_id
            mock_cart_data = {"cart_product_provider_id": cart.cart_product_provider_id}
            company = Company.create_default_company(mock_cart_data)
        
        # Get client from person or app_user
        if cart.app_user_:
            try:
                client = Client.from_app_user(cart.app_user_)
            except (ValueError, AttributeError):
                if cart.person:
                    client = Client.from_person(cart.person)
                else:
                    client = Client.create_default_client()
        elif cart.person:
            client = Client.from_person(cart.person)
        else:
            client = Client.create_default_client()
        
        # Convert ordered items to InvoiceItems
        items = []
        
        # Add ordered items (products)
        for ordered_item in cart.ordered_item:
            product = ordered_item.ordered_product
            description = product.product_name if product else f"Product #{ordered_item.product_id}"
            details = product.product_description if product else None
            
            items.append(InvoiceItem(
                description=description,
                quantity=ordered_item.ordered_quantity,
                unit_price=ordered_item.unit_price,
                tax_rate=ordered_item.vat_rate,
                unit="unit",
                details=details,
                item_type="product"
            ))
        
        # Add ordered services
        for ordered_service in cart.ordered_service:
            service = ordered_service.ordered_service_service
            if service:
                description = service.provided_service_name
                details = f"{service.provided_service_description} (Duration: {service.provided_service_actual_duration} mins)"
            else:
                description = f"Service #{ordered_service.ordered_service_service_id}"
                details = ordered_service.ordered_service_notes
            
            items.append(InvoiceItem(
                description=description,
                quantity=ordered_service.ordered_service_quantity,
                unit_price=ordered_service.ordered_service_unit_price,
                tax_rate=0.0,
                unit="service",
                details=details,
                item_type="service"
            ))
        
        return cls(
            company=company,
            client=client,
            items=items,
            invoice_reference=invoice_data.invoice_reference,
            issue_date=invoice_data.invoice_issue_date,
            due_date=invoice_data.invoice_due_date or "Upon receipt",
            cart_id=cart.cart_id,
            status=invoice_data.invoice_status.lower(),
            currency_symbol="DZD",
            currency_code="DZD",
            notes=invoice_data.invoice_notes,
            amount_paid=0.0,
            payment_instructions=f"Invoice for Cart #{cart.cart_id}"
        )
    
    def calculate_totals(self) -> Dict[str, Any]:
        subtotal = sum(item.quantity * item.unit_price for item in self.items)
        discount = subtotal * (self.discount_percent / 100)
        
        tax_groups = {}
        for item in self.items:
            rate = item.tax_rate
            if rate > 0:
                tax_amount = item.quantity * item.unit_price * (rate / 100)
                if rate not in tax_groups:
                    tax_groups[rate] = 0
                tax_groups[rate] += tax_amount
        
        taxes = [{"rate": rate, "amount": amount} for rate, amount in tax_groups.items()]
        total_tax = sum(tax["amount"] for tax in taxes)
        
        total = subtotal + total_tax - discount + self.shipping
        balance_due = total - self.amount_paid
        
        return {
            "subtotal": round(subtotal, 2),
            "discount": round(discount, 2),
            "taxes": taxes,
            "total_tax": round(total_tax, 2),
            "shipping": round(self.shipping, 2),
            "total": round(total, 2),
            "amount_paid": round(self.amount_paid, 2),
            "balance_due": round(balance_due, 2),
            "discount_percent": self.discount_percent
        }
    
    def get_qr_code_data(self, size: int = 150, style: str = "professional") -> str:
        """Generate QR code for invoice"""
        invoice_data = {
            "invoice_reference": self.invoice_reference,
            "cart_id": self.cart_id,
            "company_name": self.company.name,
            "company_tax_id": self.company.tax_id,
            "client_name": self.client.name,
            "issue_date": self.issue_date,
            "due_date": self.due_date,
            "grand_total": self.calculate_totals()["total"],
            "currency": self.currency_code,
            "status": self.status,
            "items_count": len(self.items)
        }
        
        # Generate QR data structure
        qr_data = self.qr_generator.generate_qr_data(
            document_type="invoice",
            document_id=self.invoice_reference,
            data=invoice_data
        )
        
        # Generate QR code as data URI
        return self.qr_generator.get_qr_as_data_uri(
            qr_data, 
            size=size, 
            style=style,
            include_logo=bool(self.company.logo_path)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        totals = self.calculate_totals()
        
        invoice_dict = {
            "company": self.company.to_dict(),
            "client": self.client.to_dict(),
            "items": [item.to_dict() for item in self.items],
            "invoice_reference": self.invoice_reference,
            "issue_date": self.issue_date,
            "due_date": self.due_date,
            "cart_id": self.cart_id,
            "status": self.status,
            "currency_symbol": self.currency_symbol,
            "currency_code": self.currency_code,
            "po_number": self.po_number,
            "reference": self.reference,
            "notes": self.notes,
            "terms": self.terms,
            "payment_instructions": self.payment_instructions,
            "payment_details": self.payment_details,
            "qr_code_data": self.get_qr_code_data(),
            "generated_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **totals
        }
        
        return invoice_dict

@dataclass
class Receipt:
    invoice: Invoice
    receipt_number: str
    payment_date: str
    payment_time: str
    payment_method: str
    transaction_id: str
    fee: float = 0.0
    last_four: Optional[str] = None
    auth_code: Optional[str] = None
    
    def __post_init__(self):
        # Initialize QR generator
        self.qr_generator = ProfessionalQRGenerator(enable_caching=True)
    
    @classmethod
    def from_receipt_data(cls, invoice: Invoice, receipt_data: ReceiptData) -> 'Receipt':
        """Create Receipt from Invoice and ReceiptData"""
        # Parse payment date from receipt_created_at
        try:
            created_at = receipt_data.receipt_created_at
            payment_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime("%B %d, %Y")
            payment_time = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime("%I:%M %p")
        except (ValueError, AttributeError):
            payment_date = datetime.now().strftime("%B %d, %Y")
            payment_time = datetime.now().strftime("%I:%M %p")
        
        # Get payment method from receipt_payment if available
        payment_method = "Cash"
        if receipt_data.receipt_payment and 'payment_method' in receipt_data.receipt_payment:
            payment_method = receipt_data.receipt_payment['payment_method']
        
        return cls(
            invoice=invoice,
            receipt_number=receipt_data.receipt_number,
            payment_date=payment_date,
            payment_time=payment_time,
            payment_method=payment_method,
            transaction_id=f"TXN-{receipt_data.receipt_id}",
            fee=0.0,
            last_four=None,
            auth_code=None
        )
    
    def get_qr_code_data(self, size: int = 150, style: str = "professional") -> str:
        """Generate QR code for receipt"""
        receipt_data = {
            "receipt_number": self.receipt_number,
            "invoice_reference": self.invoice.invoice_reference,
            "cart_id": self.invoice.cart_id,
            "company_name": self.invoice.company.name,
            "company_tax_id": self.invoice.company.tax_id,
            "client_name": self.invoice.client.name,
            "payment_date": self.payment_date,
            "payment_time": self.payment_time,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "amount_paid": self.invoice.calculate_totals()["total"] + self.fee,
            "currency": self.invoice.currency_code,
            "auth_code": self.auth_code,
            "last_four": self.last_four
        }
        
        # Generate QR data structure
        qr_data = self.qr_generator.generate_qr_data(
            document_type="receipt",
            document_id=self.receipt_number,
            data=receipt_data
        )
        
        # Generate QR code as data URI
        return self.qr_generator.get_qr_as_data_uri(
            qr_data, 
            size=size, 
            style=style,
            include_logo=bool(self.invoice.company.logo_path)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        totals = self.invoice.calculate_totals()
        
        return {
            "company": self.invoice.company.to_dict(),
            "client": self.invoice.client.to_dict(),
            "items": [item.to_dict() for item in self.invoice.items],
            "receipt_number": self.receipt_number,
            "invoice_reference": self.invoice.invoice_reference,
            "cart_id": self.invoice.cart_id,
            "payment_date": self.payment_date,
            "payment_time": self.payment_time,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "last_four": self.last_four,
            "auth_code": self.auth_code,
            "currency_symbol": self.invoice.currency_symbol,
            "currency_code": self.invoice.currency_code,
            "amount_paid": totals["total"],
            "tax_amount": totals["total_tax"],
            "fee": self.fee,
            "total_paid": round(totals["total"] + self.fee, 2),
            "tax_percent": self._calculate_tax_percent(totals["total_tax"], totals["total"]),
            "qr_code_data": self.get_qr_code_data(),
            "receipt_id": f"RCPT-{self.receipt_number}",
            "generated_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _calculate_tax_percent(self, tax_amount: float, total: float) -> float:
        """Calculate tax percentage"""
        if total == 0:
            return 0.0
        return round((tax_amount / (total - tax_amount)) * 100, 2)

class InvoiceGenerator:
    @staticmethod
    def cart_to_json(cart) -> str:
        """
        Convert SQLAlchemy Cart object to JSON format for invoice generation
        """
        cart_dict = {
            "cart_status": cart.cart_status,
            "cart_total_amount": float(cart.cart_total_amount) if cart.cart_total_amount else 0.0,
            "cart_client_user": cart.cart_client_user,
            "cart_notes": cart.cart_notes or "",
            "cart_created_at": cart.cart_created_at.isoformat() if cart.cart_created_at else datetime.now().isoformat(),
            "cart_updated_at": cart.cart_updated_at.isoformat() if cart.cart_updated_at else datetime.now().isoformat(),
            "cart_product_provider_id": cart.cart_product_provider_id,
            "cart_person_ref": cart.cart_person_ref,
            "cart_selling_user": cart.cart_selling_user,
            "cart_id": cart.cart_id
        }
        
        # Add related app_user data
        if cart.app_user:
            app_user_dict = {
                "app_user_person_id": cart.app_user.app_user_person_id,
                "id_app_user": cart.app_user.id_app_user,
                "app_user_type_id": cart.app_user.app_user_type_id,
                "app_user_password": cart.app_user.app_user_password,
                "app_user_preferences": cart.app_user.app_user_preferences,
                "app_user_image_url": cart.app_user.app_user_image_url,
                "app_user_last_active": cart.app_user.app_user_last_active.isoformat() if cart.app_user.app_user_last_active else None,
                "app_user_name": cart.app_user.app_user_name,
                "app_user_last_updated": cart.app_user.app_user_last_updated.isoformat() if cart.app_user.app_user_last_updated else None,
                "app_user_creation": cart.app_user.app_user_creation.isoformat() if cart.app_user.app_user_creation else None,
                "app_user_subscription_id": cart.app_user.app_user_subscription_id,
                "app_user_person": None
            }
            
            # Add person details if available
            if cart.app_user.app_user_person:
                person = cart.app_user.app_user_person
                app_user_dict["app_user_person"] = {
                    "id_person": person.id_person,
                    "person_details_id": person.person_details_id,
                    "person_blood_type_id": person.person_blood_type_id,
                    "person_location_id": person.person_location_id,
                    "person_details": {
                        "person_last_name": person.person_details.person_last_name if person.person_details else "",
                        "id_person_details": person.person_details.id_person_details if person.person_details else None,
                        "person_first_name": person.person_details.person_first_name if person.person_details else "",
                        "person_birth_date": person.person_details.person_birth_date.isoformat() if person.person_details and person.person_details.person_birth_date else None,
                        "person_gender": person.person_details.person_gender if person.person_details else "",
                        "person_nationality": person.person_details.person_nationality if person.person_details else ""
                    } if person.person_details else None
                }
            
            cart_dict["app_user"] = app_user_dict
        
        # Add person data
        if cart.person:
            cart_dict["person"] = {
                "id_person": cart.person.id_person,
                "person_details_id": cart.person.person_details_id,
                "person_blood_type_id": cart.person.person_blood_type_id,
                "person_location_id": cart.person.person_location_id,
                "person_details": {
                    "person_last_name": cart.person.person_details.person_last_name if cart.person.person_details else "",
                    "id_person_details": cart.person.person_details.id_person_details if cart.person.person_details else None,
                    "person_first_name": cart.person.person_details.person_first_name if cart.person.person_details else "",
                    "person_birth_date": cart.person.person_details.person_birth_date.isoformat() if cart.person.person_details and cart.person.person_details.person_birth_date else None,
                    "person_gender": cart.person.person_details.person_gender if cart.person.person_details else "",
                    "person_nationality": cart.person.person_details.person_nationality if cart.person.person_details else ""
                } if cart.person.person_details else None
            }
        
        # Add selling user data
        if cart.app_user_:
            cart_dict["app_user_"] = {
                "app_user_person_id": cart.app_user_.app_user_person_id,
                "id_app_user": cart.app_user_.id_app_user,
                "app_user_type_id": cart.app_user_.app_user_type_id,
                "app_user_password": cart.app_user_.app_user_password,
                "app_user_preferences": cart.app_user_.app_user_preferences,
                "app_user_image_url": cart.app_user_.app_user_image_url,
                "app_user_last_active": cart.app_user_.app_user_last_active.isoformat() if cart.app_user_.app_user_last_active else None,
                "app_user_name": cart.app_user_.app_user_name,
                "app_user_last_updated": cart.app_user_.app_user_last_updated.isoformat() if cart.app_user_.app_user_last_updated else None,
                "app_user_creation": cart.app_user_.app_user_creation.isoformat() if cart.app_user_.app_user_creation else None,
                "app_user_subscription_id": cart.app_user_.app_user_subscription_id,
                "app_user_person": None
            }
        
        # Add invoice list (empty as per your example)
        cart_dict["invoice"] = []
        
        # Add ordered services
        cart_dict["ordered_service"] = []
        if cart.ordered_service:
            for service in cart.ordered_service:
                service_dict = {
                    "ordered_service_service_id": service.ordered_service_service_id,
                    "ordered_service_cart_id": service.ordered_service_cart_id,
                    "ordered_service_quantity": service.ordered_service_quantity,
                    "ordered_service_total_price": float(service.ordered_service_total_price) if service.ordered_service_total_price else 0.0,
                    "ordered_service_scheduled_at": service.ordered_service_scheduled_at.isoformat() if service.ordered_service_scheduled_at else None,
                    "ordered_service_updated_at": service.ordered_service_updated_at.isoformat() if service.ordered_service_updated_at else None,
                    "ordered_service_id": service.ordered_service_id,
                    "ordered_service_unit_price": float(service.ordered_service_unit_price) if service.ordered_service_unit_price else 0.0,
                    "ordered_service_notes": service.ordered_service_notes or "",
                    "ordered_service_created_at": service.ordered_service_created_at.isoformat() if service.ordered_service_created_at else None
                }
                cart_dict["ordered_service"].append(service_dict)
        
        # Add receipts
        cart_dict["receipt"] = []
        if cart.receipt:
            for receipt in cart.receipt:
                receipt_dict = {
                    "receipt_id": receipt.receipt_id,
                    "receipt_number": receipt.receipt_number,
                    "receipt_notes": receipt.receipt_notes or "",
                    "receipt_cart_ref": receipt.receipt_cart_ref,
                    "receipt_amount": float(receipt.receipt_amount) if receipt.receipt_amount else 0.0,
                    "receipt_payment_id": receipt.receipt_payment_id,
                    "receipt_created_at": receipt.receipt_created_at.isoformat() if receipt.receipt_created_at else None,
                    "receipt_payment": {
                        "payment_amount": float(receipt.receipt_payment.payment_amount) if receipt.receipt_payment and receipt.receipt_payment.payment_amount else 0.0,
                        "payment_reference": receipt.receipt_payment.payment_reference if receipt.receipt_payment else "",
                        "payment_created_at": receipt.receipt_payment.payment_created_at.isoformat() if receipt.receipt_payment and receipt.receipt_payment.payment_created_at else None,
                        "payment_invoice_id": receipt.receipt_payment.payment_invoice_id if receipt.receipt_payment else None,
                        "payment_id": receipt.receipt_payment.payment_id if receipt.receipt_payment else None,
                        "payment_method": receipt.receipt_payment.payment_method if receipt.receipt_payment else "",
                        "payment_status": receipt.receipt_payment.payment_status if receipt.receipt_payment else "",
                        "payment_notes": receipt.receipt_payment.payment_notes if receipt.receipt_payment else None,
                        "payment_updated_at": receipt.receipt_payment.payment_updated_at.isoformat() if receipt.receipt_payment and receipt.receipt_payment.payment_updated_at else None
                    } if receipt.receipt_payment else None,
                    "deposit": []
                }
                cart_dict["receipt"].append(receipt_dict)
        
        # Add deposits
        cart_dict["deposit"] = []
        
        # Add ordered items
        cart_dict["ordered_item"] = []
        if cart.ordered_item:
            for item in cart.ordered_item:
                item_dict = {
                    "id_ordered_item": item.id_ordered_item,
                    "ordered_quantity": item.ordered_quantity,
                    "vat_rate": float(item.vat_rate) if item.vat_rate else 0.0,
                    "product_id": item.product_id,
                    "order_ref": item.order_ref,
                    "unit_price": float(item.unit_price) if item.unit_price else 0.0,
                    "product_discount": float(item.product_discount) if item.product_discount else None,
                    "ordered_product": {
                        "product_provider_id": item.ordered_product.provider_id if item.ordered_product else None,
                        "product_quantifier": item.ordered_product.product_quantifier if item.ordered_product else None,
                        "product_owner": item.ordered_product.product_owner if item.ordered_product else None,
                        "product_brand": item.ordered_product.product_brand if item.ordered_product else "",
                        "product_category_id": item.ordered_product.product_category_id if item.ordered_product else None,
                        "product_barcode": item.ordered_product.product_barcode if item.ordered_product else "",
                        "id_product": item.ordered_product.id_product if item.ordered_product else None,
                        "last_updated": item.ordered_product.last_updated.isoformat() if item.ordered_product and item.ordered_product.last_updated else None,
                        "created": item.ordered_product.created.isoformat() if item.ordered_product and item.ordered_product.created else None,
                        "product_description": item.ordered_product.product_description if item.ordered_product else "",
                        "product_origin_id": item.ordered_product.product_origin_id if item.ordered_product else None,
                        "product_name": item.ordered_product.product_name if item.ordered_product else "",
                        "product_price": float(item.ordered_product.unit_price) if item.ordered_product and item.ordered_product.unit_price else 0.0,
                        "product_quantity": item.ordered_product.product_quantity if item.ordered_product else 0
                    } if item.ordered_product else None
                }
                cart_dict["ordered_item"].append(item_dict)
        
        return cart_dict
    
    @staticmethod
    def generate_invoice_reference(prefix="INV", year=None, sequence=1):
        if year is None:
            year = datetime.now().year
        return f"{prefix}-{year}-{sequence:04d}"
    
    @staticmethod
    def from_json(json_data: Dict[str, Any]) -> Invoice:
        """Create Invoice from JSON data"""
        cart_data = json_data
        
        # Handle missing person data gracefully
        person = None
        person_details = None
        if cart_data.get('person'):
            if cart_data['person'].get('person_details'):
                pd = cart_data['person']['person_details']
                person_details = PersonDetails(
                    id_person_details=pd.get('id_person_details', 0),
                    person_first_name=pd.get('person_first_name', ''),
                    person_last_name=pd.get('person_last_name', ''),
                    person_birth_date=pd.get('person_birth_date', ''),
                    person_gender=pd.get('person_gender', ''),
                    person_nationality=pd.get('person_nationality', '')
                )
            
            person = Person(
                id_person=cart_data['person'].get('id_person', 0),
                person_details_id=cart_data['person'].get('person_details_id', 0),
                person_blood_type_id=cart_data['person'].get('person_blood_type_id'),
                person_location_id=cart_data['person'].get('person_location_id'),
                person_details=person_details
            )
        
        # Handle missing app_user_ data gracefully
        app_user = None
        if cart_data.get('app_user_'):
            au_data = cart_data['app_user_']
            app_user_person = None
            
            if au_data.get('app_user_person'):
                au_person_data = au_data['app_user_person']
                au_person_details = None
                
                if au_person_data.get('person_details'):
                    pd = au_person_data['person_details']
                    au_person_details = PersonDetails(
                        id_person_details=pd.get('id_person_details', 0),
                        person_first_name=pd.get('person_first_name', ''),
                        person_last_name=pd.get('person_last_name', ''),
                        person_birth_date=pd.get('person_birth_date', ''),
                        person_gender=pd.get('person_gender', ''),
                        person_nationality=pd.get('person_nationality', '')
                    )
                
                app_user_person = Person(
                    id_person=au_person_data.get('id_person', 0),
                    person_details_id=au_person_data.get('person_details_id', 0),
                    person_blood_type_id=au_person_data.get('person_blood_type_id'),
                    person_location_id=au_person_data.get('person_location_id'),
                    person_details=au_person_details
                )
            
            app_user = AppUser(
                id_app_user=au_data.get('id_app_user', 0),
                app_user_name=au_data.get('app_user_name', ''),
                app_user_person_id=au_data.get('app_user_person_id', 0),
                app_user_type_id=au_data.get('app_user_type_id', 0),
                app_user_password=au_data.get('app_user_password'),
                app_user_preferences=au_data.get('app_user_preferences'),
                app_user_image_url=au_data.get('app_user_image_url'),
                app_user_last_active=au_data.get('app_user_last_active'),
                app_user_last_updated=au_data.get('app_user_last_updated'),
                app_user_creation=au_data.get('app_user_creation'),
                app_user_subscription_id=au_data.get('app_user_subscription_id'),
                app_user_person=app_user_person
            )
        
        # Handle missing product_provider data gracefully
        product_provider = None
        if cart_data.get('cart_product_provider'):
            pp_data = cart_data['cart_product_provider']
            provider_details = None
            
            if pp_data.get('product_provider_details'):
                pd_data = pp_data['product_provider_details']
                provider_details = ProviderDetails(
                    provider_name=pd_data.get('provider_name', ''),
                    provider_contact_info=pd_data.get('provider_contact_info', ''),
                    idprovider_details_id=pd_data.get('idprovider_details_id', 0)
                )
            
            # Only create ProductProvider if we have the essential details
            if provider_details:
                product_provider = ProductProvider(
                    id_product_provider=pp_data.get('id_product_provider', 0),
                    product_provider_details_id=pp_data.get('product_provider_details_id', 0),
                    product_provider_type_id=pp_data.get('product_provider_type_id', 0),
                    product_provider_details=provider_details,
                    product_provider_owner=pp_data.get('product_provider_owner'),
                    product_provider_location_id=pp_data.get('product_provider_location_id'),
                    product_provider_org_id=pp_data.get('product_provider_org_id')
                )
        
        # Create OrderedItems
        ordered_items = []
        for item_data in cart_data.get('ordered_item', []):
            ordered_product = None
            if item_data.get('ordered_product'):
                op_data = item_data['ordered_product']
                ordered_product = OrderedProduct(
                    id_product=op_data.get('id_product', 0),
                    product_name=op_data.get('product_name', ''),
                    product_price=op_data.get('product_price', 0.0),
                    product_description=op_data.get('product_description'),
                    product_provider_id=op_data.get('product_provider_id'),
                    product_brand=op_data.get('product_brand'),
                    product_category_id=op_data.get('product_category_id'),
                    product_barcode=op_data.get('product_barcode'),
                    product_quantity=op_data.get('product_quantity')
                )
            
            ordered_item = OrderedItem(
                id_ordered_item=item_data.get('id_ordered_item', 0),
                product_id=item_data.get('product_id', 0),
                ordered_quantity=item_data.get('ordered_quantity', 0),
                unit_price=item_data.get('unit_price', 0.0),
                vat_rate=item_data.get('vat_rate', 0.0),
                product_discount=item_data.get('product_discount', 0.0),
                order_ref=item_data.get('order_ref'),
                ordered_product=ordered_product
            )
            ordered_items.append(ordered_item)
        
        # Create OrderedServices
        ordered_services = []
        for service_data in cart_data.get('ordered_service', []):
            provided_service = None
            if service_data.get('ordered_service_service'):
                ps_data = service_data['ordered_service_service']
                provided_service = ProvidedService(
                    provided_service_id=ps_data.get('provided_service_id', 0),
                    provided_service_name=ps_data.get('provided_service_name', ''),
                    provided_service_final_price=ps_data.get('provided_service_final_price', 0.0),
                    provided_service_description=ps_data.get('provided_service_description', ''),
                    provided_service_base_price=ps_data.get('provided_service_base_price', 0.0),
                    provided_service_product_provider_id=ps_data.get('provided_service_product_provider_id', 0),
                    category_id=ps_data.get('category_id', 0),
                    provided_service_actual_duration=ps_data.get('provided_service_actual_duration', 0),
                    provided_service_is_active=ps_data.get('provided_service_is_active', 0),
                    provided_service_created_at=ps_data.get('provided_service_created_at', ''),
                    provided_service_updated_at=ps_data.get('provided_service_updated_at', ''),
                    provided_service_deleted_at=ps_data.get('provided_service_deleted_at'),
                    provided_service_pricing_config=ps_data.get('provided_service_pricing_config')
                )
            
            ordered_service = OrderedService(
                ordered_service_id=service_data.get('ordered_service_id', 0),
                ordered_service_service_id=service_data.get('ordered_service_service_id', 0),
                ordered_service_quantity=service_data.get('ordered_service_quantity', 0),
                ordered_service_unit_price=service_data.get('ordered_service_unit_price', 0.0),
                ordered_service_total_price=service_data.get('ordered_service_total_price', 0.0),
                ordered_service_notes=service_data.get('ordered_service_notes', ''),
                ordered_service_cart_id=service_data.get('ordered_service_cart_id', 0),
                ordered_service_scheduled_at=service_data.get('ordered_service_scheduled_at'),
                ordered_service_created_at=service_data.get('ordered_service_created_at'),
                ordered_service_updated_at=service_data.get('ordered_service_updated_at'),
                ordered_service_service=provided_service
            )
            ordered_services.append(ordered_service)
        
        # Handle missing invoice data gracefully
        invoice_data = None
        if cart_data.get('invoice') and len(cart_data['invoice']) > 0:
            inv_data = cart_data['invoice'][0]
            invoice_data = InvoiceData(
                invoice_id=inv_data.get('invoice_id', 0),
                invoice_reference=inv_data.get('invoice_reference', f"INV-{cart_data.get('cart_id', 0)}"),
                grand_total=inv_data.get('grand_total', 0.0),
                invoice_status=inv_data.get('invoice_status', 'pending'),
                invoice_issue_date=inv_data.get('invoice_issue_date', cart_data.get('cart_created_at', '')[:10]),
                invoice_due_date=inv_data.get('invoice_due_date'),
                invoice_notes=inv_data.get('invoice_notes'),
                invoice_cart_id=inv_data.get('invoice_cart_id', cart_data.get('cart_id', 0)),
                created_at=inv_data.get('created_at', cart_data.get('cart_created_at', '')),
                updated_at=inv_data.get('updated_at', cart_data.get('cart_updated_at', '')),
                payment=inv_data.get('payment', [])
            )
        else:
            # Create default invoice data if none exists
            invoice_data = InvoiceData(
                invoice_id=cart_data.get('cart_id', 0),
                invoice_reference=f"INV-{cart_data.get('cart_id', 0)}",
                grand_total=cart_data.get('cart_total_amount', 0.0),
                invoice_status='pending',
                invoice_issue_date=cart_data.get('cart_created_at', '')[:10],
                invoice_due_date=None,
                invoice_notes=cart_data.get('cart_notes', ''),
                invoice_cart_id=cart_data.get('cart_id', 0),
                created_at=cart_data.get('cart_created_at', ''),
                updated_at=cart_data.get('cart_updated_at', ''),
                payment=[]
            )
        
        # Create Cart with all data (including possibly None values)
        cart = Cart(
            cart_id=cart_data.get('cart_id', 0),
            cart_product_provider_id=cart_data.get('cart_product_provider_id', 0),
            cart_selling_user=cart_data.get('cart_selling_user', 0),
            cart_person_ref=cart_data.get('cart_person_ref', 0),
            cart_client_user=cart_data.get('cart_client_user'),
            cart_status=cart_data.get('cart_status', ''),
            cart_total_amount=cart_data.get('cart_total_amount', 0.0),
            cart_notes=cart_data.get('cart_notes', ''),
            cart_created_at=cart_data.get('cart_created_at', ''),
            cart_updated_at=cart_data.get('cart_updated_at', ''),
            person=person,
            app_user_=app_user,
            cart_product_provider=product_provider,
            ordered_item=ordered_items,
            ordered_service=ordered_services,
            invoice=[invoice_data] if invoice_data else []
        )
        
        # Create Invoice from Cart and InvoiceData
        if invoice_data:
            return Invoice.from_cart_and_invoice_data(cart, invoice_data)
        else:
            # Fallback: create basic invoice from cart
            if product_provider:
                company = Company.from_product_provider(product_provider)
            else:
                company = Company.create_default_company(cart_data)
            
            if app_user:
                try:
                    client = Client.from_app_user(app_user)
                except (ValueError, AttributeError):
                    if person:
                        client = Client.from_person(person)
                    else:
                        client = Client.create_default_client()
            elif person:
                client = Client.from_person(person)
            else:
                client = Client.create_default_client()
            
            # Convert ordered items to InvoiceItems
            items = []
            for ordered_item in ordered_items:
                product = ordered_item.ordered_product
                description = product.product_name if product else f"Product #{ordered_item.product_id}"
                items.append(InvoiceItem(
                    description=description,
                    quantity=ordered_item.ordered_quantity,
                    unit_price=ordered_item.unit_price,
                    tax_rate=ordered_item.vat_rate,
                    unit="unit",
                    details=product.product_description if product else None,
                    item_type="product"
                ))
            
            for ordered_service in ordered_services:
                service = ordered_service.ordered_service_service
                if service:
                    description = service.provided_service_name
                    details = f"{service.provided_service_description} (Duration: {service.provided_service_actual_duration} mins)"
                else:
                    description = f"Service #{ordered_service.ordered_service_service_id}"
                    details = ordered_service.ordered_service_notes
                
                items.append(InvoiceItem(
                    description=description,
                    quantity=ordered_service.ordered_service_quantity,
                    unit_price=ordered_service.ordered_service_unit_price,
                    tax_rate=0.0,
                    unit="service",
                    details=details,
                    item_type="service"
                ))
            
            return Invoice(
                company=company,
                client=client,
                items=items,
                invoice_reference=f"INV-{cart.cart_id}",
                issue_date=cart.cart_created_at[:10] if cart.cart_created_at else datetime.now().strftime('%Y-%m-%d'),
                due_date="Upon receipt",
                cart_id=cart.cart_id,
                status=cart.cart_status,
                currency_symbol="DZD",
                currency_code="DZD",
                notes=cart.cart_notes
            )
    
    @staticmethod
    def generate_sample_invoice():
        """Generate a sample invoice"""
        sample_json = {
            "cart_id": 37,
            "cart_product_provider_id": 6,
            "cart_selling_user": 1,
            "cart_person_ref": 1,
            "cart_client_user": None,
            "cart_status": "open",
            "cart_total_amount": 250,
            "cart_notes": "Genetic counseling and testing consideration",
            "cart_created_at": "2025-12-23T10:59:45",
            "cart_updated_at": "2025-12-23T10:59:45"
        }
        
        return InvoiceGenerator.from_json(sample_json)

def generate_invoice_qr(invoice: Invoice, size: int = 150) -> str:
    """Quick function to get invoice QR code"""
    return invoice.get_qr_code_data(size=size)

def generate_receipt_qr(receipt: Receipt, size: int = 150) -> str:
    """Quick function to get receipt QR code"""
    return receipt.get_qr_code_data(size=size)