# ============================================================================
# components/config_helpers.py - Reuse configuration helpers
# ============================================================================

"""
Configuration helpers reused from existing system
"""

from modules.stp.stp_helpers import get_account_type, validate_account_number, get_account_folder_mapping
from modules.bbva.bbva_config import BBVA_ACCOUNTS, get_account_by_clabe

class ConfigHelper:
    """Configuration helper for unified system"""
    
    @staticmethod
    def get_stp_account_type(account_number):
        """Get STP account type"""
        return get_account_type(account_number)
    
    @staticmethod
    def validate_stp_account(account_number):
        """Validate STP account number"""
        return validate_account_number(account_number)
    
    @staticmethod
    def get_stp_folder_mapping():
        """Get STP folder mapping"""
        return get_account_folder_mapping()
    
    @staticmethod
    def get_bbva_accounts():
        """Get BBVA accounts configuration"""
        return BBVA_ACCOUNTS
    
    @staticmethod
    def get_bbva_account_info(clabe):
        """Get BBVA account info by CLABE"""
        return get_account_by_clabe(clabe)
