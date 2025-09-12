# modules/statements/__init__.py
"""
Clean Unified Statements Module - Phase 1a & 1b Complete
No backward compatibility, clean architecture
"""

from .config import (
    UNIFIED_ACCOUNTS,
    get_account_by_id,
    get_accounts_by_type,
    get_stp_accounts,
    get_bbva_accounts,
    get_account_by_identifier,
    validate_unified_config,
    get_configuration_summary
)

from .data_loader import UnifiedDataLoader
from .parse_coordinator import UnifiedParseCoordinator  
from .upload_handler import UnifiedUploadHandler

from .inventory_manager import InventoryManager, FileInfo, MonthInfo
from .inventory_scanner import InventoryScanner


__version__ = "1.0.0"

__all__ = [
    # Configuration
    'UNIFIED_ACCOUNTS',
    'get_account_by_id',
    'get_accounts_by_type', 
    'get_stp_accounts',
    'get_bbva_accounts',
    'get_account_by_identifier',
    'validate_unified_config',
    'get_configuration_summary',
    
    # Core components
    'UnifiedDataLoader',
    'UnifiedParseCoordinator',
    'UnifiedUploadHandler',
 
    # Inventory components (ADD THESE)
    'InventoryManager',
    'InventoryScanner', 
    'FileInfo',
    'MonthInfo',
     
    # Flask integration
    'register_statements_routes'
]

def register_statements_routes(app):
    """Register all statements routes with Flask app"""
    from .api_endpoints import register_routes
    register_routes(app)
