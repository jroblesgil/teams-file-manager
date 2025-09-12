# ============================================================================
# components/upload.py - Reuse upload logic
# ============================================================================

"""
Upload components reused from existing system
"""

from modules.stp.stp_files import upload_to_sharepoint

class UnifiedUploadManager:
    """Centralized upload management for unified system"""
    
    @staticmethod
    def upload_stp_file(filename, file_content, target_folder, access_token):
        """Upload STP file to SharePoint"""
        return upload_to_sharepoint(filename, file_content, target_folder, access_token)
    
    @staticmethod
    def upload_bbva_file(filename, file_content, clabe, access_token):
        """Upload BBVA file to SharePoint"""
        # This would need to be implemented or imported from BBVA upload logic
        # from modules.bbva.bbva_upload import upload_bbva_to_sharepoint
        # return upload_bbva_to_sharepoint(filename, file_content, clabe, access_token)
        pass
