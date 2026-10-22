# document/compact_invoice_renderer.py
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
import os
from pathlib import Path
from features.document.invoice_data import InvoiceGenerator, Invoice, Receipt, Cart, ReceiptData
import base64
from datetime import datetime
import json
from typing import Optional
import threading

class CompactInvoiceRenderer:
    """
    Singleton class for rendering compact invoices and receipts.
    Use get_renderer() to get the singleton instance.
    """
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self, template_dir: str = "document/templates", static_dir: str = "static"):
        """Initialize renderer. Use get_renderer() instead of direct instantiation."""
        if CompactInvoiceRenderer._instance is not None:
            raise RuntimeError("Use get_renderer() to get the singleton instance")
        
        self.template_dir = template_dir
        self.static_dir = static_dir
        self.env = self._create_jinja_environment()
        
        # Create directories if they don't exist
        self._create_directories()
        
        # Create default CSS if it doesn't exist
        self._create_default_css()
    
    @classmethod
    def get_renderer(cls, template_dir: str = "document/templates", static_dir: str = "static") -> 'CompactInvoiceRenderer':
        """
        Get the singleton instance of CompactInvoiceRenderer.
        
        Args:
            template_dir: Directory containing Jinja2 templates
            static_dir: Directory for static files (CSS, images)
            
        Returns:
            CompactInvoiceRenderer: Singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-checked locking
                    cls._instance = cls.__new__(cls)
                    cls._instance.__init__(template_dir, static_dir)
        return cls._instance
    
    @classmethod
    def reset_renderer(cls):
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None
    
    def _create_jinja_environment(self) -> Environment:
        """Create and configure Jinja2 environment with custom filters."""
        env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        env.filters['format_currency'] = self._format_currency
        env.filters['format_date'] = self._format_date
        
        return env
    
    def _format_currency(self, value, symbol: str = "DZD") -> str:
        """Format currency value."""
        if value is None:
            return f"0.00 {symbol}"
        try:
            return f"{float(value):,.2f} {symbol}"
        except (ValueError, TypeError):
            return f"0.00 {symbol}"
    
    def _format_date(self, date_str: str) -> str:
        """Format date string."""
        if not date_str:
            return ""
        
        try:
            # Try different date formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%b %d, %Y")
                except ValueError:
                    continue
            return date_str
        except Exception:
            return date_str
    
    def _create_directories(self):
        """Create necessary directories."""
        Path(self.template_dir).mkdir(parents=True, exist_ok=True)
        Path(self.static_dir).mkdir(parents=True, exist_ok=True)
        
        # Create CSS directory
        css_dir = Path(self.static_dir) / "css"
        css_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_default_css(self):
        """Create default CSS for invoices if it doesn't exist."""
        css_dir = Path(self.static_dir) / "css"
        css_path = css_dir / "invoice.css"
        
        if not css_path.exists():
            css_content = self._get_default_css_content()
            with open(css_path, 'w') as f:
                f.write(css_content)
    
    def _get_default_css_content(self) -> str:
        """Get default CSS content."""
        return """
        /* Default invoice CSS */
        body {
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            font-size: 12px;
        }
        
        .invoice-container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        
        .company-info h1 {
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 24px;
        }
        
        .invoice-info {
            text-align: right;
        }
        
        .invoice-number {
            font-size: 20px;
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }
        
        .invoice-date {
            color: #7f8c8d;
            font-size: 14px;
        }
        
        .client-info, .company-details {
            margin-bottom: 20px;
        }
        
        .section-title {
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 16px;
        }
        
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 11px;
        }
        
        .items-table th {
            background-color: #f8f9fa;
            text-align: left;
            padding: 8px;
            border-bottom: 2px solid #dee2e6;
            font-weight: bold;
        }
        
        .items-table td {
            padding: 8px;
            border-bottom: 1px solid #dee2e6;
            vertical-align: top;
        }
        
        .items-table .text-right {
            text-align: right;
        }
        
        .items-table .text-center {
            text-align: center;
        }
        
        .totals {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
        }
        
        .total-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            padding: 5px 0;
        }
        
        .total-label {
            font-weight: bold;
        }
        
        .total-amount {
            text-align: right;
            min-width: 100px;
        }
        
        .grand-total {
            font-size: 16px;
            color: #27ae60;
            border-top: 2px solid #e0e0e0;
            padding-top: 10px;
            margin-top: 10px;
        }
        
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            font-size: 10px;
            color: #7f8c8d;
            text-align: center;
        }
        
        .qr-code {
            text-align: center;
            margin: 20px 0;
        }
        
        .qr-code img {
            max-width: 100px;
            height: auto;
        }
        
        .notes {
            margin-top: 20px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
            font-size: 11px;
        }
        
        .compact-mode .items-table {
            font-size: 10px;
        }
        
        .compact-mode .items-table th,
        .compact-mode .items-table td {
            padding: 4px 6px;
        }
        
        @media print {
            body {
                padding: 0;
            }
            
            .invoice-container {
                box-shadow: none;
                padding: 0;
            }
        }
        """
    
    # Public methods for rendering
    
    def render_compact_invoice(self, invoice: Invoice) -> str:
        """Render compact invoice as HTML string."""
        template = self.env.get_template("invoice.html")
        context = invoice.to_dict()
        # Add generated date
        context['generated_date'] = datetime.now().strftime("%B %d, %Y %H:%M")
        return template.render(**context)
    
    def render_compact_receipt(self, receipt: Receipt) -> str:
        """Render compact receipt as HTML string."""
        template = self.env.get_template("receipt.html")
        context = receipt.to_dict()
        context['generated_date'] = datetime.now().strftime("%B %d, %Y %H:%M")
        return template.render(**context)
    
    def generate_invoice_from_json(self, json_data: dict) -> Invoice:
        """Generate invoice from JSON data."""
        return InvoiceGenerator.from_json(json_data)
    
    def generate_compact_invoice_pdf(self, invoice: Invoice, output_path: Optional[str] = None) -> bytes:
        """Generate PDF from compact invoice."""
        html_content = self.render_compact_invoice(invoice)
        
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        html = HTML(string=html_content, base_url=os.path.abspath(self.static_dir))
        pdf_bytes = html.write_pdf()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    def generate_compact_receipt_pdf(self, receipt: Receipt, output_path: Optional[str] = None) -> bytes:
        """Generate PDF from compact receipt."""
        html_content = self.render_compact_receipt(receipt)
        
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        html = HTML(string=html_content, base_url=os.path.abspath(self.static_dir))
        pdf_bytes = html.write_pdf()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    def generate_compact_invoice_html(self, invoice: Invoice, output_path: Optional[str] = None) -> str:
        """Save compact invoice as HTML file."""
        html_content = self.render_compact_invoice(invoice)
        
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        return html_content
    
    def generate_compact_receipt_html(self, receipt: Receipt, output_path: Optional[str] = None) -> str:
        """Save compact receipt as HTML file."""
        html_content = self.render_compact_receipt(receipt)
        
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        return html_content
    
    def preview_compact_invoice(self, invoice: Invoice, output_dir: str = "output") -> dict:
        """Preview compact invoice - generates both HTML and PDF."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Clean filename
        safe_invoice_reference = invoice.invoice_reference.replace('/', '-').replace('\\', '-')
        html_path = Path(output_dir) / f"invoice-{safe_invoice_reference}.html"
        pdf_path = Path(output_dir) / f"invoice-{safe_invoice_reference}.pdf"
        
        print(f"Generating compact invoice HTML: {html_path}")
        html_content = self.generate_compact_invoice_html(invoice, str(html_path))
        
        print(f"Generating compact invoice PDF: {pdf_path}")
        pdf_bytes = self.generate_compact_invoice_pdf(invoice, str(pdf_path))
        
        return {
            "html": str(html_path),
            "pdf": str(pdf_path),
            "html_content": html_content,
            "pdf_bytes": pdf_bytes
        }
    
    def preview_compact_receipt(self, receipt: Receipt, output_dir: str = "output") -> dict:
        """Preview compact receipt - generates both HTML and PDF."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Clean filename
        safe_receipt_number = receipt.receipt_number.replace('/', '-').replace('\\', '-')
        html_path = Path(output_dir) / f"receipt-{safe_receipt_number}.html"
        pdf_path = Path(output_dir) / f"receipt-{safe_receipt_number}.pdf"
        
        print(f"Generating compact receipt HTML: {html_path}")
        html_content = self.generate_compact_receipt_html(receipt, str(html_path))
        
        print(f"Generating compact receipt PDF: {pdf_path}")
        pdf_bytes = self.generate_compact_receipt_pdf(receipt, str(pdf_path))
        
        return {
            "html": str(html_path),
            "pdf": str(pdf_path),
            "html_content": html_content,
            "pdf_bytes": pdf_bytes
        }
    
    def generate_invoice_pdf_base64(self, invoice: Invoice) -> str:
        """Generate PDF and return as base64 string."""
        pdf_bytes = self.generate_compact_invoice_pdf(invoice)
        return base64.b64encode(pdf_bytes).decode('utf-8')
    
    def generate_receipt_pdf_base64(self, receipt: Receipt) -> str:
        """Generate PDF and return as base64 string."""
        pdf_bytes = self.generate_compact_receipt_pdf(receipt)
        return base64.b64encode(pdf_bytes).decode('utf-8')


# Convenience functions for easy access
def get_renderer(template_dir: str = "document/templates", static_dir: str = "static") -> CompactInvoiceRenderer:
    """
    Convenience function to get the singleton renderer instance.
    
    Example:
        renderer = get_renderer()
        invoice = renderer.generate_invoice_from_json(json_data)
        pdf_bytes = renderer.generate_compact_invoice_pdf(invoice)
    """
    return CompactInvoiceRenderer.get_renderer(template_dir, static_dir)


def render_invoice_from_json(json_data: dict, output_pdf_path: Optional[str] = None) -> dict:
    """
    One-line function to render invoice from JSON data.
    
    Args:
        json_data: JSON data containing invoice information
        output_pdf_path: Optional path to save PDF file
        
    Returns:
        dict: Contains 'invoice', 'html', and 'pdf_bytes'
    """
    renderer = get_renderer()
    invoice = renderer.generate_invoice_from_json(json_data)
    html_content = renderer.render_compact_invoice(invoice)
    pdf_bytes = renderer.generate_compact_invoice_pdf(invoice, output_pdf_path)
    
    return {
        'invoice': invoice,
        'html': html_content,
        'pdf_bytes': pdf_bytes,
        'base64': base64.b64encode(pdf_bytes).decode('utf-8') if pdf_bytes else None
    }


def render_receipt_from_json(json_data: dict, output_pdf_path: Optional[str] = None) -> dict:
    """
    One-line function to render receipt from JSON data.
    
    Args:
        json_data: JSON data containing receipt information
        output_pdf_path: Optional path to save PDF file
        
    Returns:
        dict: Contains 'receipt', 'html', and 'pdf_bytes'
    """
    renderer = get_renderer()
    
    # Extract receipt data
    receipt_data = json_data.get('receipt', [{}])[0] if json_data.get('receipt') else {}
    invoice = renderer.generate_invoice_from_json(json_data)
    
    # Create ReceiptData
    receipt_data_obj = ReceiptData(
        receipt_id=receipt_data.get('receipt_id'),
        receipt_number=receipt_data.get('receipt_number'),
        receipt_amount=receipt_data.get('receipt_amount'),
        receipt_notes=receipt_data.get('receipt_notes'),
        receipt_cart_ref=receipt_data.get('receipt_cart_ref'),
        receipt_payment_id=receipt_data.get('receipt_payment_id'),
        receipt_created_at=receipt_data.get('receipt_created_at'),
        receipt_payment=receipt_data.get('receipt_payment'),
        deposit=receipt_data.get('deposit', [])
    )
    
    # Create Receipt
    receipt = Receipt.from_receipt_data(invoice, receipt_data_obj)
    html_content = renderer.render_compact_receipt(receipt)
    pdf_bytes = renderer.generate_compact_receipt_pdf(receipt, output_pdf_path)
    
    return {
        'receipt': receipt,
        'html': html_content,
        'pdf_bytes': pdf_bytes,
        'base64': base64.b64encode(pdf_bytes).decode('utf-8') if pdf_bytes else None
    }