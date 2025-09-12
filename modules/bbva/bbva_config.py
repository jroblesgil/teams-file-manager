# modules/bbva/bbva_config.py - Centralized BBVA Configuration

"""
Centralized BBVA Configuration

This module contains all BBVA account configurations in one place to avoid duplication
and inconsistencies across the application.
"""

from typing import Dict, Optional, List
from collections import OrderedDict


# ============================================================================
# MAIN BBVA ACCOUNT CONFIGURATION - ORDERED
# ============================================================================

BBVA_ACCOUNTS = OrderedDict([
    ('bbva_mx_mxn', {
        'name': 'BBVA MX MXN',
        'clabe': '012180001198203451',
        'directory': 'Estados de Cuenta/BBVA/BBVA MX/BBVA MX MXN',
        'file_pattern': r'^\d{4}\s+FMX\s+BBVA\s+MXN.*\.pdf$',
        'database': 'BBVA_MX_mxn_DB.json',
        'currency': 'MXN',
        'account_type': 'BBVA_MX_mxn',
        'display_name': 'BBVA MX MXN',
        'description': 'BBVA México - Pesos Mexicanos'
    }),
    ('bbva_mx_usd', {
        'name': 'BBVA MX USD',
        'clabe': '012180001201205883',
        'directory': 'Estados de Cuenta/BBVA/BBVA MX/BBVA MX USD',
        'file_pattern': r'^\d{4}\s+FMX\s+BBVA\s+USD.*\.pdf$',
        'database': 'BBVA_MX_usd_DB.json',
        'currency': 'USD',
        'account_type': 'BBVA_MX_usd',
        'display_name': 'BBVA MX USD',
        'description': 'BBVA México - Dólares Americanos'
    }),
    ('bbva_sa_mxn', {
        'name': 'BBVA SA MXN',
        'clabe': '012180001182790637',
        'directory': 'Estados de Cuenta/BBVA/BBVA SA/BBVA SA MXN',
        'file_pattern': r'^\d{4}\s+FSA\s+BBVA\s+MXN.*\.pdf$',
        'database': 'BBVA_SA_mxn_DB.json',
        'currency': 'MXN',
        'account_type': 'BBVA_SA_mxn',
        'display_name': 'BBVA SA MXN',
        'description': 'BBVA Servicios Administrativos - Pesos Mexicanos'
    }),
    ('bbva_sa_usd', {
        'name': 'BBVA SA USD',
        'clabe': '012222001182793149',
        'directory': 'Estados de Cuenta/BBVA/BBVA SA/BBVA SA USD',
        'file_pattern': r'^\d{4}\s+FSA\s+BBVA\s+USD.*\.pdf$',
        'database': 'BBVA_SA_usd_DB.json',
        'currency': 'USD',
        'account_type': 'BBVA_SA_usd',
        'display_name': 'BBVA SA USD',
        'description': 'BBVA Servicios Administrativos - Dólares Americanos'
    }),
    ('bbva_ip_corp', {
        'name': 'BBVA IP Corp',
        'clabe': '012180001232011554',
        'directory': 'Estados de Cuenta/BBVA/BBVA IP/BBVA IP MXN Corp',
        'file_pattern': r'^\d{4}\s+BBVA\s+IP\s+MXN\s+Corp.*\.pdf$',
        'database': 'BBVA_IP_corp_DB.json',
        'currency': 'MXN',
        'account_type': 'BBVA_IP_corp',
        'display_name': 'BBVA IP Corp',
        'description': 'BBVA Institución de Pagos - Corporativo'
    }),
    ('bbva_ip_clientes', {
        'name': 'BBVA IP Clientes',
        'clabe': '012180001232011635',
        'directory': 'Estados de Cuenta/BBVA/BBVA IP/BBVA IP MXN Clientes',
        'file_pattern': r'^\d{4}\s+BBVA\s+IP\s+MXN\s+Clientes.*\.pdf$',
        'database': 'BBVA_IP_clientes_DB.json',
        'currency': 'MXN',
        'account_type': 'BBVA_IP_clientes',
        'display_name': 'BBVA IP Clientes',
        'description': 'BBVA Institución de Pagos - Clientes'
    })
])

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_account_by_clabe(clabe: str) -> Optional[Dict]:
    """Get account configuration by CLABE number"""
    for account_key, account_data in BBVA_ACCOUNTS.items():
        if account_data['clabe'] == clabe:
            return {**account_data, 'account_key': account_key}
    return None

def get_account_by_key(account_key: str) -> Optional[Dict]:
    """Get account configuration by account key"""
    if account_key in BBVA_ACCOUNTS:
        return {**BBVA_ACCOUNTS[account_key], 'account_key': account_key}
    return None

def get_all_clabes() -> List[str]:
    """Get list of all BBVA account CLABEs"""
    return [account['clabe'] for account in BBVA_ACCOUNTS.values()]

def get_all_account_keys() -> List[str]:
    """Get list of all BBVA account keys"""
    return list(BBVA_ACCOUNTS.keys())

def validate_clabe(clabe: str) -> bool:
    """Validate CLABE number format and checksum"""
    if not clabe or len(clabe) != 18:
        return False
    
    if not clabe.isdigit():
        return False
        
    # CLABE checksum validation
    weights = [3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7]
    total = sum(int(digit) * weight for digit, weight in zip(clabe[:17], weights))
    check_digit = (10 - (total % 10)) % 10
    
    return int(clabe[17]) == check_digit

def get_folder_path_mapping() -> Dict[str, str]:
    """Get mapping of CLABE to SharePoint folder paths"""
    return {
        account['clabe']: account['directory'] 
        for account in BBVA_ACCOUNTS.values()
    }

def get_database_mapping() -> Dict[str, str]:
    """Get mapping of account keys to database filenames"""
    return {
        account_key: account_data['database']
        for account_key, account_data in BBVA_ACCOUNTS.items()
    }

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_configuration() -> Dict[str, bool]:
    """Validate the entire BBVA configuration for consistency"""
    results = {}
    
    # Check for duplicate CLABEs
    clabes = [acc['clabe'] for acc in BBVA_ACCOUNTS.values()]
    results['unique_clabes'] = len(clabes) == len(set(clabes))
    
    # Check CLABE format
    results['valid_clabe_format'] = all(validate_clabe(clabe) for clabe in clabes)
    
    # Check for duplicate database names
    databases = [acc['database'] for acc in BBVA_ACCOUNTS.values()]
    results['unique_databases'] = len(databases) == len(set(databases))
    
    # Check required fields
    required_fields = ['name', 'clabe', 'directory', 'file_pattern', 'database', 'currency']
    results['all_required_fields'] = all(
        all(field in account for field in required_fields)
        for account in BBVA_ACCOUNTS.values()
    )
    
    return results

# ============================================================================
# SPANISH MONTH MAPPING
# ============================================================================

SPANISH_MONTHS = {
    'ENE': '01', 'FEB': '02', 'MAR': '03', 'ABR': '04',
    'MAY': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08', 
    'SEP': '09', 'OCT': '10', 'NOV': '11', 'DIC': '12'
}

MONTH_NAMES_ES = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
    '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
    '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
}

MONTH_NAMES_EN = {
    '01': 'January', '02': 'February', '03': 'March', '04': 'April',
    '05': 'May', '06': 'June', '07': 'July', '08': 'August',
    '09': 'September', '10': 'October', '11': 'November', '12': 'December'
}

# ============================================================================
# EXPORT FOR EASY IMPORTING
# ============================================================================

__all__ = [
    'BBVA_ACCOUNTS',
    'get_account_by_clabe', 
    'get_account_by_key',
    'get_all_clabes',
    'get_all_account_keys', 
    'validate_clabe',
    'get_folder_path_mapping',
    'get_database_mapping',
    'validate_configuration',
    'SPANISH_MONTHS',
    'MONTH_NAMES_ES', 
    'MONTH_NAMES_EN'
]