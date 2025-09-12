# ============================================================================
# components/file_operations.py - Reuse file operations
# ============================================================================

"""
File operations reused from existing system
"""

from modules.stp.stp_files import get_file_content_by_ids
from modules.bbva.bbva_files import get_bbva_files
from modules.stp.stp_files import get_stp_files

class FileOperationsManager:
    """Centralized file operations for unified system"""
    
    @staticmethod
    def get_stp_account_files(account_number, access_token, year=None):
        """Get STP files for account"""
        return get_stp_files(account_number, access_token, year)
    
    @staticmethod
    def get_bbva_account_files(clabe, access_token, year=None, account_info=None):
        """Get BBVA files for account"""
        return get_bbva_files(clabe, access_token, year, account_info)
    
    @staticmethod
    def download_file_content(drive_id, file_id, access_token):
        """Download file content by IDs"""
        return get_file_content_by_ids(drive_id, file_id, access_token)
