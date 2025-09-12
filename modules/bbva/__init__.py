# modules/bbva/__init__.py
"""
BBVA (Banco Bilbao Vizcaya Argentaria) Module Package

This package contains all BBVA-related functionality including:
- Database operations (bbva_database)
- PDF parsing (bbva_parser) 
- File management (bbva_files)
- Configuration (bbva_config)
- Helper utilities (bbva_helpers)
"""

# Import key functions for easier access
try:
    from .bbva_database import (
        get_bbva_database, update_bbva_database,
        get_bbva_parse_tracking_data, update_bbva_parse_tracking_data,
        remove_file_transactions, synchronize_database_with_files,
        cleanup_tracking_data, create_empty_bbva_database
    )
    from .bbva_batch import (
        process_bbva_account, check_bbva_file_parsing_status,
        get_bbva_parse_summary
    )
    from .bbva_parser import BBVAParser
    from .bbva_files import get_bbva_files
    from .bbva_config import BBVA_ACCOUNTS, get_account_by_clabe, validate_clabe
    from .bbva_helpers import BBVAHelpers
except ImportError:
    # Graceful handling if some modules aren't available yet
    pass

__all__ = [
    # Database operations
    'get_bbva_database', 'update_bbva_database',
    'get_bbva_parse_tracking_data', 'update_bbva_parse_tracking_data',
    'remove_file_transactions', 'synchronize_database_with_files',
    'cleanup_tracking_data', 'create_empty_bbva_database',
    
    # Batch processing
    'process_bbva_account', 'check_bbva_file_parsing_status',
    'get_bbva_parse_summary',
    
    # Core functionality
    'BBVAParser', 'get_bbva_files', 'BBVAHelpers',
    
    # Configuration
    'BBVA_ACCOUNTS', 'get_account_by_clabe', 'validate_clabe'
]