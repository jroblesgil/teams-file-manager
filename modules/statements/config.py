# modules/statements/config.py
"""
Phase 1a: Clean Unified Statements Configuration
Defines all 9 accounts (3 STP + 6 BBVA) in a single, authoritative structure
"""

import logging
from collections import OrderedDict
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ============================================================================
# UNIFIED ACCOUNT CONFIGURATION - 9 ACCOUNTS TOTAL
# ============================================================================

UNIFIED_ACCOUNTS = OrderedDict([
    # STP ACCOUNTS (3)
    ('stp_sa', {
        'type': 'stp',
        'name': 'STP SA',
        'identifier': '646180559700000009',
        'currency': 'MXN',
        'folder_name': 'STP SA New',
        'file_pattern': r'^ec-646180559700000009-(\d{4})(\d{2})\.(pdf|xlsx)$',
        'database_file': 'STP_SA_DB.json',
        'description': 'STP Servicios Administrativos'
    }),
    
    ('stp_ip_pi', {
        'type': 'stp',
        'name': 'STP IP - PI',
        'identifier': '646990403000000003',
        'currency': 'MXN',
        'folder_name': 'STP IP',
        'file_pattern': r'^ec-646990403000000003-(\d{4})(\d{2})\.(pdf|xlsx)$',
        'database_file': 'STP_IP_PI_DB.json',
        'description': 'STP Institución de Pagos - Payment Institution'
    }),
    
    ('stp_ip_pd', {
        'type': 'stp',
        'name': 'STP IP - PD',
        'identifier': '646180403000000004',
        'currency': 'MXN',
        'folder_name': 'STP IP',
        'file_pattern': r'^ec-646180403000000004-(\d{4})(\d{2})\.(pdf|xlsx)$',
        'database_file': 'STP_IP_PD_DB.json',
        'description': 'STP Institución de Pagos - Payment Distribution'
    }),
    
    # BBVA ACCOUNTS (6)
    ('bbva_mx_mxn', {
        'type': 'bbva',
        'name': 'BBVA MX MXN',
        'identifier': '012180001198203451',
        'currency': 'MXN',
        'folder_path': 'Estados de Cuenta/BBVA/BBVA MX/BBVA MX MXN',
        'file_pattern': r'^(\d{4})\s+FMX\s+BBVA\s+MXN.*\.pdf$',
        'database_file': 'BBVA_MX_mxn_DB.json',
        'description': 'BBVA México - Pesos Mexicanos'
    }),
    
    ('bbva_mx_usd', {
        'type': 'bbva',
        'name': 'BBVA MX USD',
        'identifier': '012180001201205883',
        'currency': 'USD',
        'folder_path': 'Estados de Cuenta/BBVA/BBVA MX/BBVA MX USD',
        'file_pattern': r'^(\d{4})\s+FMX\s+BBVA\s+USD.*\.pdf$',
        'database_file': 'BBVA_MX_usd_DB.json',
        'description': 'BBVA México - Dólares Americanos'
    }),
    
    ('bbva_sa_mxn', {
        'type': 'bbva',
        'name': 'BBVA SA MXN',
        'identifier': '012180001182790637',
        'currency': 'MXN',
        'folder_path': 'Estados de Cuenta/BBVA/BBVA SA/BBVA SA MXN',
        'file_pattern': r'^(\d{4})\s+FSA\s+BBVA\s+MXN.*\.pdf$',
        'database_file': 'BBVA_SA_mxn_DB.json',
        'description': 'BBVA Servicios Administrativos - Pesos Mexicanos'
    }),
    
    ('bbva_sa_usd', {
        'type': 'bbva',
        'name': 'BBVA SA USD',
        'identifier': '012222001182793149',
        'currency': 'USD',
        'folder_path': 'Estados de Cuenta/BBVA/BBVA SA/BBVA SA USD',
        'file_pattern': r'^(\d{4})\s+FSA\s+BBVA\s+USD.*\.pdf$',
        'database_file': 'BBVA_SA_usd_DB.json',
        'description': 'BBVA Servicios Administrativos - Dólares Americanos'
    }),
    
    ('bbva_ip_corp', {
        'type': 'bbva',
        'name': 'BBVA IP Corp',
        'identifier': '012180001232011554',
        'currency': 'MXN',
        'folder_path': 'Estados de Cuenta/BBVA/BBVA IP/BBVA IP MXN Corp',
        'file_pattern': r'^(\d{4})\s+BBVA\s+IP\s+MXN\s+Corp.*\.pdf$',
        'database_file': 'BBVA_IP_corp_DB.json',
        'description': 'BBVA Institución de Pagos - Corporativo'
    }),
    
    ('bbva_ip_clientes', {
        'type': 'bbva',
        'name': 'BBVA IP Clientes',
        'identifier': '012180001232011635',
        'currency': 'MXN',
        'folder_path': 'Estados de Cuenta/BBVA/BBVA IP/BBVA IP MXN Clientes',
        'file_pattern': r'^(\d{4})\s+BBVA\s+IP\s+MXN\s+Clientes.*\.pdf$',
        'database_file': 'BBVA_IP_clientes_DB.json',
        'description': 'BBVA Institución de Pagos - Clientes'
    })
])

# ============================================================================
# INVENTORY CONFIGURATION
# ============================================================================

# Inventory file configuration
INVENTORY_CONFIG = {
    'file_path': 'statements_inventory.json',
    'folder_path': 'Estados de Cuenta/Inventario',
    'full_path': 'Estados de Cuenta/Inventario/statements_inventory.json'
}

# ============================================================================
# CONFIGURATION HELPERS
# ============================================================================

def get_account_by_id(account_id: str) -> Dict[str, Any]:
    """Get account configuration by account ID"""
    return UNIFIED_ACCOUNTS.get(account_id, {})

def get_accounts_by_type(account_type: str) -> Dict[str, Dict[str, Any]]:
    """Get all accounts of a specific type (stp or bbva)"""
    return {
        account_id: account_config
        for account_id, account_config in UNIFIED_ACCOUNTS.items()
        if account_config['type'] == account_type
    }

def get_stp_accounts() -> Dict[str, Dict[str, Any]]:
    """Get all STP accounts"""
    return get_accounts_by_type('stp')

def get_bbva_accounts() -> Dict[str, Dict[str, Any]]:
    """Get all BBVA accounts"""
    return get_accounts_by_type('bbva')

def get_account_by_identifier(identifier: str) -> tuple[str, Dict[str, Any]]:
    """Get account by its identifier (account number or CLABE)"""
    for account_id, account_config in UNIFIED_ACCOUNTS.items():
        if account_config['identifier'] == identifier:
            return account_id, account_config
    return None, {}

def validate_unified_config() -> Dict[str, bool]:
    """Validate the unified configuration"""
    validation_results = {
        'accounts_defined': len(UNIFIED_ACCOUNTS) > 0,
        'stp_accounts_count': len(get_stp_accounts()) == 3,
        'bbva_accounts_count': len(get_bbva_accounts()) == 6,
        'total_accounts_count': len(UNIFIED_ACCOUNTS) == 9,
        'all_required_fields': True,
        'unique_identifiers': True,
        'valid_patterns': True,
        'inventory_config': validate_inventory_config()
    }
    
    # Validate required fields
    required_fields = ['type', 'name', 'identifier', 'currency', 'database_file', 'description']
    stp_required = required_fields + ['folder_name']
    bbva_required = required_fields + ['folder_path']
    
    identifiers_seen = set()
    
    for account_id, config in UNIFIED_ACCOUNTS.items():
        # Check required fields based on type
        fields_to_check = stp_required if config['type'] == 'stp' else bbva_required
        
        for field in fields_to_check:
            if field not in config or not config[field]:
                validation_results['all_required_fields'] = False
                logger.warning(f"Missing or empty field '{field}' in account '{account_id}'")
        
        # Check identifier uniqueness
        identifier = config.get('identifier', '')
        if identifier in identifiers_seen:
            validation_results['unique_identifiers'] = False
            logger.warning(f"Duplicate identifier '{identifier}' found")
        else:
            identifiers_seen.add(identifier)
        
        # Validate file patterns
        pattern = config.get('file_pattern', '')
        if not pattern:
            validation_results['valid_patterns'] = False
            logger.warning(f"Missing file pattern in account '{account_id}'")
    
    return validation_results

def get_configuration_summary() -> Dict[str, Any]:
    """Get a summary of the configuration"""
    return {
        'total_accounts': len(UNIFIED_ACCOUNTS),
        'stp_accounts': len(get_stp_accounts()),
        'bbva_accounts': len(get_bbva_accounts()),
        'currencies': list(set(config['currency'] for config in UNIFIED_ACCOUNTS.values())),
        'account_types': list(set(config['type'] for config in UNIFIED_ACCOUNTS.values())),
        'validation': validate_unified_config()
    }

def get_inventory_config() -> Dict[str, str]:
    """Get inventory file configuration"""
    return INVENTORY_CONFIG.copy()

def validate_inventory_config() -> bool:
    """Validate inventory configuration"""
    required_keys = ['file_path', 'folder_path', 'full_path']
    return all(key in INVENTORY_CONFIG for key in required_keys)

# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_unified_config():
    """Initialize and validate unified configuration"""
    logger.info("Initializing unified statements configuration...")
    
    validation = validate_unified_config()
    
    if all(validation.values()):
        logger.info(f"✅ Configuration validated successfully - {len(UNIFIED_ACCOUNTS)} accounts loaded")
        logger.info(f"  - STP accounts: {len(get_stp_accounts())}")
        logger.info(f"  - BBVA accounts: {len(get_bbva_accounts())}")
    else:
        logger.error("❌ Configuration validation failed:")
        for check, result in validation.items():
            if not result:
                logger.error(f"  - {check}: FAILED")
        raise ValueError("Configuration validation failed")
    
    return True

# Auto-initialize when module is imported
try:
    initialize_unified_config()
except Exception as e:
    logger.error(f"Failed to initialize unified configuration: {e}")
    raise