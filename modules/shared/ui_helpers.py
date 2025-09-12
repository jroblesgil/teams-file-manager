"""
Common UI utilities for both STP and BBVA systems
"""

import json
from decimal import Decimal
from datetime import datetime

class UIHelpers:
    """Common UI helper functions"""
    
    @staticmethod
    def format_currency(amount: float, currency: str = "MXN") -> str:
        """Format currency amounts for display"""
        if currency == "USD":
            return f"${amount:,.2f} USD"
        else:
            return f"${amount:,.2f} MXN"
    
    @staticmethod
    def format_date(date_str: str, input_format: str = "%m/%d/%Y") -> str:
        """Format dates for display"""
        try:
            date_obj = datetime.strptime(date_str, input_format)
            return date_obj.strftime("%d/%m/%Y")
        except:
            return date_str
    
    @staticmethod
    def get_status_icon(status: str, file_type: str = "pdf") -> str:
        """Get appropriate icon class for status"""
        status_icons = {
            'parsed': 'fas fa-file-pdf text-primary',
            'unparsed': 'fas fa-file-pdf text-danger', 
            'different': 'fas fa-file-pdf text-warning',
            'missing': 'fas fa-file-pdf text-muted',
            'complete': 'fas fa-check-circle text-success',
            'partial': 'fas fa-exclamation-triangle text-warning',
            'error': 'fas fa-times-circle text-danger'
        }
        return status_icons.get(status, 'fas fa-file text-muted')
    
    @staticmethod
    def get_status_class(status: str) -> str:
        """Get CSS class for status"""
        status_classes = {
            'parsed': 'status-parsed',
            'unparsed': 'status-unparsed',
            'different': 'status-different', 
            'missing': 'status-missing',
            'complete': 'status-complete',
            'partial': 'status-partial',
            'error': 'status-error'
        }
        return status_classes.get(status, 'status-unknown')
    
    @staticmethod
    def safe_json_decode(json_str: str, default=None):
        """Safely decode JSON string"""
        try:
            return json.loads(json_str)
        except:
            return default or {}
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 50) -> str:
        """Truncate text for display"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
