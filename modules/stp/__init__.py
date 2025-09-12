"""
STP (Sistema de Transferencias y Pagos) Module Package

This package contains all STP-related functionality including:
- Database operations (stp_database)
- File parsing (stp_parser) 
- File management (stp_files)
- Analytics and reporting (stp_analytics)
- Helper utilities (stp_helpers)
"""

# Import key functions for easier access
try:
    from .stp_database import get_json_database, update_json_database
    from .stp_parser import parse_excel_file
    from .stp_files import get_stp_files, create_stp_calendar_data
    from .stp_analytics import get_monthly_record_counts
    from .stp_helpers import get_account_type, validate_account_number
except ImportError:
    # Graceful handling if some modules aren't available yet
    pass

__all__ = [
    'get_json_database', 'update_json_database',
    'parse_excel_file',
    'get_stp_files', 'create_stp_calendar_data', 
    'get_monthly_record_counts',
    'get_account_type', 'validate_account_number'
]
