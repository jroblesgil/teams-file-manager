# modules/statements/file_access.py
"""
Unified File Access Module for Statements
Provides clean access to SharePoint files for both STP and BBVA accounts
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

def get_statement_file_content(drive_id: str, file_id: str, access_token: str) -> Optional[bytes]:
    """
    Get file content from SharePoint using drive_id and file_id
    Unified function for both STP and BBVA file access
    
    Args:
        drive_id: SharePoint drive ID
        file_id: SharePoint file ID  
        access_token: OAuth access token
        
    Returns:
        File content as bytes, or None if failed
    """
    try:
        # Import the actual SharePoint file access function
        # This isolates the dependency to one place
        from modules.stp.stp_files import get_file_content_by_ids
        
        logger.info(f"Downloading file: drive_id={drive_id[:8]}..., file_id={file_id[:8]}...")
        
        file_content = get_file_content_by_ids(drive_id, file_id, access_token)
        
        if file_content:
            logger.info(f"Successfully downloaded file ({len(file_content)} bytes)")
            return file_content
        else:
            logger.warning("File content is empty or None")
            return None
            
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return None

def get_sharepoint_file_by_path(file_path: str, access_token: str) -> Optional[bytes]:
    """
    Get file content from SharePoint using file path
    Alternative method for files accessed by path rather than ID
    
    Args:
        file_path: SharePoint file path
        access_token: OAuth access token
        
    Returns:
        File content as bytes, or None if failed
    """
    try:
        # This would use a different SharePoint access method if needed
        # For now, most files should use drive_id/file_id method above
        logger.warning(f"Path-based file access not yet implemented for: {file_path}")
        return None
        
    except Exception as e:
        logger.error(f"Error downloading file by path: {e}")
        return None

def validate_file_identifiers(drive_id: str, file_id: str) -> bool:
    """
    Validate that file identifiers are present and valid format
    
    Args:
        drive_id: SharePoint drive ID
        file_id: SharePoint file ID
        
    Returns:
        True if identifiers are valid, False otherwise
    """
    if not drive_id or not file_id:
        return False
        
    # Basic format validation - SharePoint IDs are typically long alphanumeric strings
    if len(drive_id) < 10 or len(file_id) < 10:
        return False
        
    return True