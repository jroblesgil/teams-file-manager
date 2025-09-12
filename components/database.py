# ============================================================================
# components/database.py - Reuse database operations
# ============================================================================

"""
Database operations reused from existing system
"""

from modules.stp.stp_database import (
    get_json_database, update_json_database,
    get_parse_tracking_data, update_parse_tracking_data
)
from modules.bbva.bbva_database import (
    get_bbva_database, update_bbva_database,
    get_bbva_parse_tracking_data, update_bbva_parse_tracking_data
)

class UnifiedDatabaseManager:
    """Centralized database operations for unified system"""
    
    @staticmethod
    def get_stp_database(account_number, access_token):
        """Get STP account database"""
        return get_json_database(account_number, access_token)
    
    @staticmethod
    def update_stp_database(account_number, database, access_token):
        """Update STP account database"""
        return update_json_database(account_number, database, access_token)
    
    @staticmethod
    def get_bbva_database(clabe, access_token):
        """Get BBVA account database"""
        return get_bbva_database(clabe, access_token)
    
    @staticmethod
    def update_bbva_database(clabe, database, access_token):
        """Update BBVA account database"""
        return update_bbva_database(clabe, database, access_token)
    
    @staticmethod
    def get_stp_tracking_data(access_token):
        """Get STP parse tracking data"""
        return get_parse_tracking_data(access_token)
    
    @staticmethod
    def update_stp_tracking_data(tracking_data, access_token):
        """Update STP parse tracking data"""
        return update_parse_tracking_data(tracking_data, access_token)
    
    @staticmethod
    def get_bbva_tracking_data(access_token):
        """Get BBVA parse tracking data"""
        return get_bbva_parse_tracking_data(access_token)
    
    @staticmethod
    def update_bbva_tracking_data(tracking_data, access_token):
        """Update BBVA parse tracking data"""
        return update_bbva_parse_tracking_data(tracking_data, access_token)
