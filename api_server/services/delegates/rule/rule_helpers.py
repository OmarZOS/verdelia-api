"""
Helper functions for management rule service.
"""

import logging
from datetime import datetime
from typing import Optional

from core.logging_config import get_logger

logger = get_logger(__name__)



class RuleHelpers:
    """Helper functions for management rule operations"""
    
    @staticmethod
    def parse_expiry(value: str | None) -> datetime | None:
        """
        Parse expiry date from string to datetime.
        
        Args:
            value: Expiry date string in various formats
            
        Returns:
            datetime object or None if invalid
        """
        if not value or str(value).lower() == "null":
            return None
        
        # More comprehensive list of formats
        formats = [
            # ISO formats with microseconds
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%d %H:%M:%S.%f%z",
            
            # ISO formats without microseconds
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S%z",
            
            # Date only
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d/%m/%Y",
            
            # Other common formats
            "%Y/%m/%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
        ]
        
        # Try parsing with each format
        for fmt in formats:
            try:
                return datetime.strptime(str(value), fmt)
            except ValueError:
                continue
        
        # If all else fails, try to handle the string manually
        try:
            # Remove timezone info if present
            clean_value = str(value).replace('Z', '')
            if '+' in clean_value:
                clean_value = clean_value.split('+')[0]
            if '-' in clean_value and clean_value.count('-') > 2:
                # Handle negative timezone offset
                parts = clean_value.split('-')
                if len(parts) > 3:
                    clean_value = '-'.join(parts[:-1])
            
            # Try parsing with datetime.fromisoformat (Python 3.7+)
            try:
                return datetime.fromisoformat(clean_value)
            except ValueError:
                pass
            
            # Try parsing with dateutil if available
            try:
                from dateutil import parser
                return parser.parse(str(value))
            except ImportError:
                pass
                
        except Exception as e:
            logger.debug(f"Additional parsing attempts failed: {e}")
        
        logger.warning(f"Could not parse expiry date: {value}")
        return None
    
    @staticmethod
    def format_expiry(dt: Optional[datetime]) -> str | None:
        """
        Format datetime to ISO string for database storage.
        
        Args:
            dt: datetime object to format
            
        Returns:
            ISO formatted string or None
        """
        if dt is None:
            return None
        return dt.isoformat()
    
    @staticmethod
    def get_default_expiry(days: int = 30) -> datetime:
        """
        Get default expiry date (now + days).
        
        Args:
            days: Number of days to add (default: 30)
            
        Returns:
            datetime object
        """
        from datetime import timedelta
        return datetime.now() + timedelta(days=days)