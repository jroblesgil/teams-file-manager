"""
BBVA-specific helper functions
"""

import re
from datetime import datetime
from typing import Dict, Optional, Tuple, List

class BBVAHelpers:
    """Helper functions specific to BBVA processing"""
    
    # BBVA Account Configuration
    BBVA_ACCOUNTS = {
        'BBVA_MX_mxn': {
            'clabe': '012180001198203451',
            'file_pattern': r'^\d{4}\s+FMX\s+BBVA\s+MXN',
            'database': 'BBVA_MX_mxn_DB.json',
            'folder': 'BBVA MX/BBVA MX MXN',
            'currency': 'MXN',
            'display_name': 'BBVA MX MXN'
        },
        'BBVA_MX_usd': {
            'clabe': '012180001201205883', 
            'file_pattern': r'^\d{4}\s+FMX\s+BBVA\s+USD',
            'database': 'BBVA_MX_usd_DB.json',
            'folder': 'BBVA MX/BBVA MX USD',
            'currency': 'USD',
            'display_name': 'BBVA MX USD'
        },
        'BBVA_SA_mxn': {
            'clabe': '012180001182790637',  # CORRECTED CLABE
            'file_pattern': r'^\d{4}\s+FSA\s+BBVA\s+MXN', 
            'database': 'BBVA_SA_mxn_DB.json',
            'folder': 'BBVA SA/BBVA SA MXN',
            'currency': 'MXN',
            'display_name': 'BBVA SA MXN'
        },
        'BBVA_SA_usd': {
            'clabe': '012222001182793149',
            'file_pattern': r'^\d{4}\s+FSA\s+BBVA\s+USD',
            'database': 'BBVA_SA_usd_DB.json', 
            'folder': 'BBVA SA/BBVA SA USD',
            'currency': 'USD',
            'display_name': 'BBVA SA USD'
        },
        'BBVA_IP_clientes': {
            'clabe': '012180001232011635',
            'file_pattern': r'^\d{4}\s+BBVA\s+IP\s+MXN\s+Clientes',
            'database': 'BBVA_IP_clientes_DB.json',
            'folder': 'BBVA IP/BBVA IP MXN Clientes', 
            'currency': 'MXN',
            'display_name': 'BBVA IP Clientes'
        },
        'BBVA_IP_corp': {
            'clabe': '012180001232011554',
            'file_pattern': r'^\d{4}\s+BBVA\s+IP\s+MXN\s+Corp',
            'database': 'BBVA_IP_corp_DB.json',
            'folder': 'BBVA IP/BBVA IP MXN Corp',
            'currency': 'MXN', 
            'display_name': 'BBVA IP Corp'
        }
    }
    
    # Spanish month mapping
    SPANISH_MONTHS = {
        'ENE': '01', 'FEB': '02', 'MAR': '03', 'ABR': '04',
        'MAY': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08', 
        'SEP': '09', 'OCT': '10', 'NOV': '11', 'DIC': '12'
    }
    
    @classmethod
    def identify_account_by_clabe(cls, clabe: str) -> Optional[str]:
        """Identify BBVA account type by CLABE number"""
        for account_type, config in cls.BBVA_ACCOUNTS.items():
            if config['clabe'] == clabe:
                return account_type
        return None
    
    @classmethod
    def identify_account_by_filename(cls, filename: str) -> Optional[str]:
        """Identify BBVA account type by filename pattern"""
        for account_type, config in cls.BBVA_ACCOUNTS.items():
            if re.match(config['file_pattern'], filename):
                return account_type
        return None
    
    @classmethod
    def validate_clabe(cls, clabe: str) -> bool:
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
    
    @classmethod
    def convert_spanish_date(cls, date_str: str, year: int) -> str:
        """Convert Spanish date format (DD/MMM) to MM/DD/YYYY"""
        try:
            if '/' not in date_str:
                return date_str
                
            day, month_abbr = date_str.split('/')
            month_num = cls.SPANISH_MONTHS.get(month_abbr.upper())
            
            if not month_num:
                return date_str
                
            return f"{month_num}/{day.zfill(2)}/{year}"
        except:
            return date_str
    
    @classmethod
    def extract_period_year(cls, period_text: str) -> Optional[int]:
        """Extract year from period text (DEL DD/MM/YYYY AL DD/MM/YYYY)"""
        try:
            # Look for 4-digit year pattern
            year_match = re.search(r'\b(20\d{2})\b', period_text)
            if year_match:
                return int(year_match.group(1))
        except:
            pass
        return None
    
    @classmethod
    def get_account_config(cls, account_type: str) -> Dict:
        """Get configuration for specific account type"""
        return cls.BBVA_ACCOUNTS.get(account_type, {})
    
    @classmethod
    def get_all_account_types(cls) -> List[str]:
        """Get list of all BBVA account types"""
        return list(cls.BBVA_ACCOUNTS.keys())
    
    @classmethod
    def format_transaction_description(cls, descripcion: str, referencia: str = "") -> str:
        """Format transaction description combining descripcion and referencia"""
        if not descripcion:
            return referencia or ""
            
        if not referencia:
            return descripcion
            
        # Combine with newline if both exist
        return f"{descripcion}\n{referencia}".strip()