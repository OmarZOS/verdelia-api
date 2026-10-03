"""
Advanced QR Code Generator with versioning, security, and caching
"""

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, SquareModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask, RadialGradiantColorMask
import segno
from PIL import Image, ImageDraw, ImageFont
import hashlib
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, Union
import io
import os
from pathlib import Path
import logging

from features.document import constants
from features.document import settings

from core.logging_config import get_logger

logger = get_logger(__name__)



class ProfessionalQRGenerator:
    """Professional QR code generator with advanced features"""
    
    def __init__(self, enable_caching: bool = True):
        self.enable_caching = enable_caching
        self.cache_dir = settings.QR_CACHE_DIR
        
        # Create cache directory
        self.cache_dir.mkdir(exist_ok=True)
        
        # Load company logo for embedding
        self.logo_path = settings.COMPANY_LOGO_PATH if settings.COMPANY_LOGO_PATH.exists() else None
        
    def generate_qr_data(self, 
                        document_type: str,
                        document_id: str,
                        data: Dict[str, Any],
                        include_metadata: bool = False) -> Dict[str, Any]:
        """
        Generate MINIMAL structured QR data
        
        Args:
            document_type: 'invoice' or 'receipt'
            document_id: Unique document identifier
            data: Document data
            include_metadata: Include app version, timestamp, etc. (disabled by default)
            
        Returns:
            Dict with MINIMAL QR data
        """
        # Extract only essential information
        company_name = data.get("company_name", constants.COMPANY_INFO["name"])
        company_tax_id = data.get("company_tax_id", constants.COMPANY_INFO["tax_id"])
        client_name = data.get("client_name", "")
        amount = data.get("grand_total", 0)
        date = data.get("issue_date", datetime.now().isoformat())
        
        return f"{constants.BASE_URL}/document/cart/{document_type}/0/0/{data.get('cart_id')}/0/0"

        # Create MINIMAL QR data structure
        qr_data = {
            "t": document_type.upper()[0],  # "I" for invoice, "R" for receipt
            "id": document_id,
            "a": round(float(amount), 2),
            "d": date[:10] if len(date) > 10 else date,  # Use only date part
            "c": data.get("currency", constants.CURRENCY)[:3],
        }
        
        # Add only company name (shortened) if space allows
        if company_name:
            qr_data["co"] = company_name[:20]  # Limit to 20 chars
        
        # Add verification hash (shortened)
        verification_string = f"{document_id}:{amount}:{date}"
        qr_data["h"] = hashlib.md5(verification_string.encode()).hexdigest()[:8]
        
        # Only add metadata if explicitly requested
        if include_metadata:
            qr_data["ver"] = constants.APP_VERSION[:5]
            qr_data["ts"] = datetime.now().isoformat()
        
        return qr_data
    
    def _calculate_document_hash(self, data: Dict[str, Any]) -> str:
        """Calculate MINIMAL hash for document verification"""
        document_id = data.get("invoice_number") or data.get("receipt_number", "")
        amount = data.get("grand_total", 0)
        date = data.get("issue_date", "")
        
        hash_string = f"{document_id}:{amount}:{date}"
        return hashlib.md5(hash_string.encode()).hexdigest()[:8]  # Only 8 chars
    
    def generate_qr_code(
        self,
        data: Dict[str, Any],
        size: int = 120,  # Reduced from 200 for compactness
        style: str = "minimal",  # Changed default to minimal
        include_logo: bool = True  # Disabled by default for compactness
    ) -> Image.Image:

        cache_key = self._generate_cache_key(data, size, style, include_logo)
        cached_path = self.cache_dir / f"{cache_key}.png"

        if self.enable_caching and cached_path.exists():
            return Image.open(cached_path)

        # Use compact JSON encoding
        qr_content = json.dumps(data, separators=(',', ':'))

        # Use higher error correction for smaller data
        qr = segno.make_qr(qr_content, error="M")  # Medium error correction

        scale = max(1, size // qr.symbol_size()[0])

        # Simplified color schemes for better readability
        if style == "corporate":
            dark = "#000000"  # Pure black for max contrast
            light = "#FFFFFF"
        elif style == "colorful":
            dark = "#2C3E50"  # Dark blue
            light = "#FFFFFF"
        else:  # minimal (default)
            dark = "#000000"  # Black
            light = "#FFFFFF"  # White

        buffer = io.BytesIO()
        qr.save(
            buffer,
            kind="png",
            scale=scale,
            border=2,  # Reduced from constants.QR_BORDER
            dark=dark,
            light=light
        )
        buffer.seek(0)

        img = Image.open(buffer).convert("RGB")
        img = img.resize((size, size), Image.Resampling.LANCZOS)

    

        # Only include logo if explicitly requested
        if include_logo and self.logo_path:
            img = self._add_logo_to_qr(img)

        # Only add border if explicitly requested
        if style in ["corporate", "colorful"]:
            img = self._add_border(img, style)

        # Only add version text if explicitly enabled
        if settings.QR_INCLUDE_VERSION and style != "minimal":
            img = self._add_version_text(img)

        if self.enable_caching:
            img.save(cached_path, "PNG", optimize=True, compress_level=9)

        return img

    
    def _add_logo_to_qr(self, qr_img: Image.Image) -> Image.Image:
        """Embed company logo with transparent background in QR code center"""
        try:
            logo = Image.open(self.logo_path)

            # Ensure logo is in RGBA mode to handle transparency
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')[citation:9]

            # Calculate logo size (20% of QR size)
            qr_size = qr_img.size[0]
            logo_size = int(qr_size * 0.2)

            # Resize logo while preserving aspect ratio and transparency
            logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)

            # Calculate position to paste logo in the center of the QR code
            position = (
                (qr_size - logo.width) // 2,
                (qr_size - logo.height) // 2
            )

            # Paste the logo using itself as the mask to preserve transparency
            qr_img.paste(logo, position, mask=logo)

        except Exception as e:
            logger.warning(f"Failed to add logo to QR: {e}")

        return qr_img
    
    def _add_border(self, img: Image.Image, style: str) -> Image.Image:
        """Add SIMPLE border to QR code"""
        border_size = 2  # Reduced from 10
        new_size = img.size[0] + (border_size * 2)
        
        # Create new image with border
        bordered = Image.new('RGB', (new_size, new_size), color='black')
        bordered.paste(img, (border_size, border_size))
        
        return bordered
    
    def _add_version_text(self, img: Image.Image) -> Image.Image:
        """Add version text at bottom of QR - simplified"""
        try:
            draw = ImageDraw.Draw(img)
            
            # Use default font
            font = ImageFont.load_default()
            
            version_text = f"v{constants.APP_VERSION[:3]}"  # Short version
            text_bbox = draw.textbbox((0, 0), version_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            
            # Position at bottom center
            position = (
                (img.size[0] - text_width) // 2,
                img.size[1] - 12
            )
            
            # Simple text without background
            draw.text(position, version_text, fill="#666666", font=font)
            
        except Exception as e:
            logger.warning(f"Failed to add version text: {e}")
        
        return img
    
    def _generate_cache_key(self, data: Dict, size: int, style: str, include_logo: bool) -> str:
        """Generate cache key from parameters"""
        import hashlib
        
        # Simplified key data
        key_data = {
            "data": json.dumps(data, sort_keys=True)[:100],  # Limit length
            "size": size,
            "style": style,
            "include_logo": include_logo,
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def get_qr_as_base64(self, data: Dict[str, Any], **kwargs) -> str:
        """Get QR code as base64 string"""
        qr_img = self.generate_qr_code(data, **kwargs)
        
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG", optimize=True, compress_level=9)
        
        return base64.b64encode(buffered.getvalue()).decode()
    
    def get_qr_as_data_uri(self, data: Dict[str, Any], **kwargs) -> str:
        """Get QR code as data URI for embedding in HTML"""
        base64_data = self.get_qr_as_base64(data, **kwargs)
        return f"data:image/png;base64,{base64_data}"


class BatchQRGenerator:
    """Generate QR codes for batch processing"""
    
    def __init__(self):
        self.qr_gen = ProfessionalQRGenerator()
    
    def generate_for_documents(self, documents: list, output_dir: Path) -> Dict[str, str]:
        """Generate QR codes for multiple documents"""
        results = {}
        
        for doc in documents:
            doc_id = doc.get("invoice_number") or doc.get("receipt_number") or f"doc_{hash(str(doc))}"
            qr_data = self.qr_gen.generate_qr_data(
                document_type=doc.get("type", "invoice"),
                document_id=doc_id,
                data=doc,
                include_metadata=False  # No metadata for batch
            )
            
            # Generate QR image with minimal settings
            qr_img = self.qr_gen.generate_qr_code(qr_data, style="minimal", size=100)
            
            # Save to file
            output_path = output_dir / f"qr_{doc_id}.png"
            qr_img.save(output_path, "PNG", optimize=True, compress_level=9)
            
            results[doc_id] = str(output_path)
        
        return results


# Quick utility function
def generate_qr_for_document(document_data: Dict[str, Any], 
                           document_type: str = "invoice",
                           size: int = 100) -> str:  # Reduced from 150
    """
    Quick utility to generate QR code data URI
    """
    generator = ProfessionalQRGenerator()
    
    # Extract minimal data
    doc_id = document_data.get("invoice_number") or document_data.get("receipt_number", "temp_id")
    
    qr_data = generator.generate_qr_data(
        document_type, 
        doc_id, 
        document_data,
        include_metadata=False
    )
    
    return generator.get_qr_as_data_uri(qr_data, size=size, style="minimal")