# services/document_service.py
import json
import base64
import qrcode
from io import BytesIO
from typing import Optional, Dict, Any, Union
from fastapi.responses import HTMLResponse
from features.document.generator import get_renderer
from features.document.invoice_data import InvoiceGenerator
from services.cart_service import CartService


class DocumentService:
    """Service for document generation (invoices, receipts) with QR code support"""
    
    def __init__(self):
        self.cart_service = CartService()
    
    def get_cart_for_document(
        self,
        provider_id: int = 0,
        seller_id: int = 0,
        cart_id: int = 0,
        client_id: int = 0,
        person_id: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Get cart data for document generation"""
        
        # Use cart service to fetch the cart
        if cart_id > 0:
            try:
                cart = self.cart_service.get_cart_by_id(cart_id)
                return InvoiceGenerator.cart_to_json(cart)
            except Exception:
                return None
        elif provider_id > 0:
            try:
                carts = self.cart_service.get_carts_by_provider(provider_id, offset=0, limit=1)
                if carts:
                    return InvoiceGenerator.cart_to_json(carts[0])
            except Exception:
                return None
        elif seller_id > 0:
            try:
                carts = self.cart_service.get_carts_by_seller(seller_id, offset=0, limit=1)
                if carts:
                    return InvoiceGenerator.cart_to_json(carts[0])
            except Exception:
                return None
        elif client_id > 0:
            try:
                carts = self.cart_service.get_carts_by_buyer(client_id, offset=0, limit=1)
                if carts:
                    return InvoiceGenerator.cart_to_json(carts[0])
            except Exception:
                return None
        
        return None
    
    def generate_invoice_html(
        self,
        provider_id: int = 0,
        seller_id: int = 0,
        cart_id: int = 0,
        client_id: int = 0,
        person_id: int = 0,
        include_qr: bool = False,
        qr_data: Optional[Dict[str, Any]] = None
    ) -> HTMLResponse:
        """Generate invoice HTML for a cart"""
        
        cart_data = self.get_cart_for_document(provider_id, seller_id, cart_id, client_id, person_id)
        
        if not cart_data:
            return HTMLResponse(
                content="<h1>Error: Cart not found</h1>",
                status_code=404
            )
        
        # Add QR code if requested
        if include_qr:
            if qr_data is None:
                qr_data = self._generate_qr_data_for_invoice(cart_data)
            cart_data["qr_code"] = qr_data
            cart_data["qr_code_image"] = self._generate_qr_code_image(qr_data)
        
        try:
            invoice = InvoiceGenerator.from_json(cart_data)
            html_content = get_renderer().render_compact_invoice(invoice)
            return HTMLResponse(content=html_content, status_code=200)
        except Exception as e:
            return HTMLResponse(
                content=f"<h1>Error generating invoice: {str(e)}</h1>",
                status_code=500
            )
    
    def generate_receipt_html(
        self,
        provider_id: int = 0,
        seller_id: int = 0,
        cart_id: int = 0,
        client_id: int = 0,
        person_id: int = 0,
        include_qr: bool = False,
        qr_data: Optional[Dict[str, Any]] = None
    ) -> HTMLResponse:
        """Generate receipt HTML for a cart"""
        
        cart_data = self.get_cart_for_document(provider_id, seller_id, cart_id, client_id, person_id)
        
        if not cart_data:
            return HTMLResponse(
                content="<h1>Error: Cart not found</h1>",
                status_code=404
            )
        
        # Add QR code if requested
        if include_qr:
            if qr_data is None:
                qr_data = self._generate_qr_data_for_receipt(cart_data)
            cart_data["qr_code"] = qr_data
            cart_data["qr_code_image"] = self._generate_qr_code_image(qr_data)
        
        try:
            invoice = InvoiceGenerator.from_json(cart_data)
            html_content = get_renderer().render_compact_receipt(invoice)
            return HTMLResponse(content=html_content, status_code=200)
        except Exception as e:
            return HTMLResponse(
                content=f"<h1>Error generating receipt: {str(e)}</h1>",
                status_code=500
            )
    
    def generate_invoice_pdf(
        self,
        provider_id: int = 0,
        seller_id: int = 0,
        cart_id: int = 0,
        client_id: int = 0,
        person_id: int = 0,
        include_qr: bool = False,
        qr_data: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate invoice PDF for a cart"""
        
        cart_data = self.get_cart_for_document(provider_id, seller_id, cart_id, client_id, person_id)
        
        if not cart_data:
            raise ValueError("Cart not found")
        
        # Add QR code if requested
        if include_qr:
            if qr_data is None:
                qr_data = self._generate_qr_data_for_invoice(cart_data)
            cart_data["qr_code"] = qr_data
            cart_data["qr_code_image"] = self._generate_qr_code_image(qr_data)
        
        invoice = InvoiceGenerator.from_json(cart_data)
        return get_renderer().render_pdf_invoice(invoice)
    
    def generate_receipt_pdf(
        self,
        provider_id: int = 0,
        seller_id: int = 0,
        cart_id: int = 0,
        client_id: int = 0,
        person_id: int = 0,
        include_qr: bool = False,
        qr_data: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate receipt PDF for a cart"""
        
        cart_data = self.get_cart_for_document(provider_id, seller_id, cart_id, client_id, person_id)
        
        if not cart_data:
            raise ValueError("Cart not found")
        
        # Add QR code if requested
        if include_qr:
            if qr_data is None:
                qr_data = self._generate_qr_data_for_receipt(cart_data)
            cart_data["qr_code"] = qr_data
            cart_data["qr_code_image"] = self._generate_qr_code_image(qr_data)
        
        invoice = InvoiceGenerator.from_json(cart_data)
        return get_renderer().render_pdf_receipt(invoice)
    
    # ==================== Direct Data Input Methods ====================
    
    def generate_invoice_from_data_html(
        self,
        invoice_data: Dict[str, Any],
        include_qr: bool = False,
        qr_data: Optional[Dict[str, Any]] = None
    ) -> HTMLResponse:
        """Generate invoice HTML from direct data input"""
        
        # Add QR code if requested
        if include_qr:
            if qr_data is None:
                qr_data = self._generate_qr_data_for_invoice(invoice_data)
            invoice_data["qr_code"] = qr_data
            invoice_data["qr_code_image"] = self._generate_qr_code_image(qr_data)
        
        try:
            invoice = InvoiceGenerator.from_json(invoice_data)
            html_content = get_renderer().render_compact_invoice(invoice)
            return HTMLResponse(content=html_content, status_code=200)
        except Exception as e:
            return HTMLResponse(
                content=f"<h1>Error generating invoice: {str(e)}</h1>",
                status_code=500
            )
    
    def generate_receipt_from_data_html(
        self,
        receipt_data: Dict[str, Any],
        include_qr: bool = False,
        qr_data: Optional[Dict[str, Any]] = None
    ) -> HTMLResponse:
        """Generate receipt HTML from direct data input"""
        
        # Add QR code if requested
        if include_qr:
            if qr_data is None:
                qr_data = self._generate_qr_data_for_receipt(receipt_data)
            receipt_data["qr_code"] = qr_data
            receipt_data["qr_code_image"] = self._generate_qr_code_image(qr_data)
        
        try:
            invoice = InvoiceGenerator.from_json(receipt_data)
            html_content = get_renderer().render_compact_receipt(invoice)
            return HTMLResponse(content=html_content, status_code=200)
        except Exception as e:
            return HTMLResponse(
                content=f"<h1>Error generating receipt: {str(e)}</h1>",
                status_code=500
            )
    
    def generate_invoice_from_data_pdf(
        self,
        invoice_data: Dict[str, Any],
        include_qr: bool = False,
        qr_data: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate invoice PDF from direct data input"""
        
        # Add QR code if requested
        if include_qr:
            if qr_data is None:
                qr_data = self._generate_qr_data_for_invoice(invoice_data)
            invoice_data["qr_code"] = qr_data
            invoice_data["qr_code_image"] = self._generate_qr_code_image(qr_data)
        
        invoice = InvoiceGenerator.from_json(invoice_data)
        return get_renderer().render_pdf_invoice(invoice)
    
    def generate_receipt_from_data_pdf(
        self,
        receipt_data: Dict[str, Any],
        include_qr: bool = False,
        qr_data: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate receipt PDF from direct data input"""
        
        # Add QR code if requested
        if include_qr:
            if qr_data is None:
                qr_data = self._generate_qr_data_for_receipt(receipt_data)
            receipt_data["qr_code"] = qr_data
            receipt_data["qr_code_image"] = self._generate_qr_code_image(qr_data)
        
        invoice = InvoiceGenerator.from_json(receipt_data)
        return get_renderer().render_pdf_receipt(invoice)
    
    # ==================== QR Code Methods ====================
    
    def _generate_qr_data_for_invoice(self, cart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate QR code data for invoice"""
        return {
            "type": "invoice",
            "invoice_reference": cart_data.get("invoice_reference", f"INV-{cart_data.get('cart_id', '000')}"),
            "amount": cart_data.get("total", cart_data.get("cart_total_amount", 0)),
            "currency": cart_data.get("currency", "USD"),
            "due_date": cart_data.get("due_date", ""),
            "payment_url": f"https://payment.example.com/pay/{cart_data.get('invoice_reference', 'unknown')}"
        }
    
    def _generate_qr_data_for_receipt(self, cart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate QR code data for receipt"""
        return {
            "type": "receipt",
            "receipt_number": cart_data.get("receipt_number", f"RCP-{cart_data.get('cart_id', '000')}"),
            "amount": cart_data.get("total", cart_data.get("cart_total_amount", 0)),
            "currency": cart_data.get("currency", "USD"),
            "transaction_id": cart_data.get("transaction_id", f"TXN-{cart_data.get('cart_id', '000')}"),
            "verification_url": f"https://verify.example.com/receipt/{cart_data.get('receipt_number', 'unknown')}"
        }
    
    def _generate_qr_code_image(self, qr_data: Dict[str, Any]) -> str:
        """Generate QR code image as base64 string"""
        try:
            # Convert QR data to JSON string
            qr_content = json.dumps(qr_data)
            
            # Create QR code instance
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_content)
            qr.make(fit=True)
            
            # Create image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffered = BytesIO()
            qr_image.save(buffered, format="PNG")
            qr_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/png;base64,{qr_base64}"
        except Exception as e:
            # Return empty string if QR generation fails
            return ""
    
    def validate_qr_data(self, qr_data: Dict[str, Any]) -> bool:
        """Validate QR code data structure"""
        required_fields = ["type", "amount", "currency", "recipient", "reference"]
        
        # Check required fields
        for field in required_fields:
            if field not in qr_data:
                return False
        
        # Validate amount is positive
        if qr_data.get("amount", 0) <= 0:
            return False
        
        # Validate currency
        valid_currencies = ["USD", "EUR", "DZD", "GBP"]
        if qr_data.get("currency") not in valid_currencies:
            return False
        
        return True
    
    def generate_qr_code_for_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate QR code data for invoice"""
        qr_data = self._generate_qr_data_for_invoice(invoice_data)
        qr_image = self._generate_qr_code_image(qr_data)
        
        return {
            "data": qr_data,
            "image": qr_image,
            "valid": self.validate_qr_data(qr_data)
        }
    
    def generate_qr_code_for_receipt(self, receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate QR code data for receipt"""
        qr_data = self._generate_qr_data_for_receipt(receipt_data)
        qr_image = self._generate_qr_code_image(qr_data)
        
        return {
            "data": qr_data,
            "image": qr_image,
            "valid": self.validate_qr_data(qr_data)
        }
    
    # ==================== Helper Methods ====================
    
    def cart_to_invoice_data(self, cart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert cart data to invoice format"""
        return {
            "invoice_reference": f"INV-{cart_data.get('cart_id', '000')}",
            "invoice_date": cart_data.get("created_at", ""),
            "due_date": cart_data.get("due_date", ""),
            "company": cart_data.get("company", {}),
            "customer": cart_data.get("customer", {}),
            "items": cart_data.get("items", []),
            "subtotal": cart_data.get("subtotal", 0),
            "tax": cart_data.get("tax", 0),
            "total": cart_data.get("total", cart_data.get("cart_total_amount", 0)),
            "currency": cart_data.get("currency", "USD"),
            "notes": cart_data.get("notes", ""),
            "payment_terms": cart_data.get("payment_terms", "Net 30")
        }
    
    def cart_to_receipt_data(self, cart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert cart data to receipt format"""
        return {
            "receipt_number": f"RCP-{cart_data.get('cart_id', '000')}",
            "receipt_date": cart_data.get("created_at", ""),
            "payment_method": cart_data.get("payment_method", "Credit Card"),
            "transaction_id": cart_data.get("transaction_id", f"TXN-{cart_data.get('cart_id', '000')}"),
            "company": cart_data.get("company", {}),
            "customer": cart_data.get("customer", {}),
            "items": cart_data.get("items", []),
            "subtotal": cart_data.get("subtotal", 0),
            "tax": cart_data.get("tax", 0),
            "total": cart_data.get("total", cart_data.get("cart_total_amount", 0)),
            "currency": cart_data.get("currency", "USD"),
            "amount_paid": cart_data.get("amount_paid", 0),
            "change_due": cart_data.get("change_due", 0)
        }