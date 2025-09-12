import logging
import re
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import math

from .bbva_config import BBVA_ACCOUNTS, get_folder_path_mapping, validate_clabe

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

DRIVE_ID = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
BANCOS_FOLDER_ID = "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"

# BBVA PDF file pattern: YYMM [pattern].pdf (e.g., "2501 FMX BBVA MXN.pdf")
BBVA_FILE_PATTERN = r'^(\d{4})\s+.*\.pdf$'

# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def get_bbva_files(
    account_clabe: str, 
    access_token: str, 
    year: Optional[int] = None, 
    month: Optional[int] = None, 
    account_info: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """
    Get BBVA PDF files using Graph API navigation
    
    Args:
        account_clabe: BBVA account CLABE number
        access_token: Microsoft Graph API access token
        year: Optional year filter
        month: Optional month filter  
        account_info: Account configuration dict (prevents circular imports)
        
    Returns:
        List of BBVA file dictionaries with metadata
    """
    try:
        logger.info(f"Getting BBVA files for account {account_clabe}, year={year}, month={month}")
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Navigate through SharePoint folder hierarchy
        # 04 Bancos → Estados de Cuenta → BBVA → [Account Folder]
        account_folder_id = _navigate_to_account_folder(account_clabe, headers)
        
        if not account_folder_id:
            logger.warning(f"Could not find folder for BBVA account {account_clabe}")
            return []
        
        # Get files from the account folder
        files = _get_files_from_folder(account_folder_id, headers)
        
        # Filter and process BBVA files
        bbva_files = _process_bbva_files(
            files, account_clabe, year, month, account_info
        )
        
        logger.info(f"Found {len(bbva_files)} BBVA files for account {account_clabe}")
        return bbva_files
        
    except Exception as e:
        logger.error(f"Error getting BBVA files for account {account_clabe}: {e}")
        return []


def _navigate_to_account_folder(account_clabe: str, headers: Dict[str, str]) -> Optional[str]:
    """
    Navigate through SharePoint folder hierarchy to find the account folder
    
    Returns:
        Folder ID of the account-specific folder, or None if not found
    """
    try:
        # Step 1: Get Estados de Cuenta folder from Bancos
        estados_folder_id = _get_estados_folder(headers)
        if not estados_folder_id:
            return None
        
        # Step 2: Get BBVA folder from Estados de Cuenta
        bbva_folder_id = _get_bbva_folder(estados_folder_id, headers)
        if not bbva_folder_id:
            return None
        
        # Step 3: Navigate to account-specific folder
        account_folder_id = _get_account_folder(bbva_folder_id, account_clabe, headers)
        return account_folder_id
        
    except Exception as e:
        logger.error(f"Error navigating to account folder: {e}")
        return None


def _get_estados_folder(headers: Dict[str, str]) -> Optional[str]:
    """Get Estados de Cuenta folder ID from Bancos folder"""
    try:
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{BANCOS_FOLDER_ID}/children"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to access Bancos folder: {response.status_code}")
            return None
        
        items = response.json().get('value', [])
        estados_folder = next(
            (item for item in items 
             if item.get('folder') and 'estado' in item.get('name', '').lower()), 
            None
        )
        
        if estados_folder:
            logger.debug(f"Found Estados de Cuenta folder: {estados_folder.get('name')}")
            return estados_folder.get('id')
        
        logger.error("Estados de Cuenta folder not found")
        return None
        
    except Exception as e:
        logger.error(f"Error getting Estados folder: {e}")
        return None


def _get_bbva_folder(estados_folder_id: str, headers: Dict[str, str]) -> Optional[str]:
    """Get BBVA folder ID from Estados de Cuenta folder"""
    try:
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{estados_folder_id}/children"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to access Estados folder: {response.status_code}")
            return None
        
        items = response.json().get('value', [])
        bbva_folder = next(
            (item for item in items 
             if item.get('folder') and 'bbva' in item.get('name', '').lower()), 
            None
        )
        
        if bbva_folder:
            logger.debug(f"Found BBVA folder: {bbva_folder.get('name')}")
            return bbva_folder.get('id')
        
        logger.error("BBVA folder not found in Estados de Cuenta")
        return None
        
    except Exception as e:
        logger.error(f"Error getting BBVA folder: {e}")
        return None

def _get_account_folder(bbva_folder_id: str, account_clabe: str, headers: Dict[str, str]) -> Optional[str]:
    """Navigate to account-specific folder within BBVA hierarchy"""
    try:
        # UPDATED: Use centralized config
        folder_mapping = get_folder_path_mapping()
        target_folder_path = folder_mapping.get(account_clabe)
        
        if not target_folder_path:
            logger.error(f"Unknown BBVA account CLABE: {account_clabe}")
            return None
        
        # Extract the relative path (remove "Estados de Cuenta/BBVA/" prefix)
        if target_folder_path.startswith("Estados de Cuenta/BBVA/"):
            relative_path = target_folder_path[len("Estados de Cuenta/BBVA/"):]
        else:
            relative_path = target_folder_path
        
        # Navigate through nested folder structure
        current_folder_id = bbva_folder_id
        path_parts = relative_path.split('/')
        
        logger.debug(f"Navigating BBVA path: {path_parts}")
        
        for path_part in path_parts:
            current_folder_id = _find_subfolder(current_folder_id, path_part, headers)
            if not current_folder_id:
                logger.error(f"Folder '{path_part}' not found in BBVA hierarchy")
                return None
            logger.debug(f"Found folder: {path_part} (ID: {current_folder_id})")
        
        return current_folder_id
        
    except Exception as e:
        logger.error(f"Error getting account folder: {e}")
        return None

def _find_subfolder(parent_folder_id: str, folder_name: str, headers: Dict[str, str]) -> Optional[str]:
    """Find a specific subfolder within a parent folder"""
    try:
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{parent_folder_id}/children"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to access folder {folder_name}: {response.status_code}")
            return None
        
        items = response.json().get('value', [])
        target_folder = next(
            (item for item in items 
             if item.get('folder') and item.get('name') == folder_name), 
            None
        )
        
        return target_folder.get('id') if target_folder else None
        
    except Exception as e:
        logger.error(f"Error finding subfolder {folder_name}: {e}")
        return None


def _get_files_from_folder(folder_id: str, headers: Dict[str, str]) -> List[Dict]:
    """Get all files from a SharePoint folder"""
    try:
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{folder_id}/children"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to get files from folder: {response.status_code}")
            return []
        
        files = response.json().get('value', [])
        # Filter out folders, keep only files
        files = [f for f in files if not f.get('folder')]
        
        logger.debug(f"Found {len(files)} files in folder")
        return files
        
    except Exception as e:
        logger.error(f"Error getting files from folder: {e}")
        return []

# Enhanced _process_bbva_files function with debug logging
# Replace this function in bbva_files.py

def _process_bbva_files(
    files: List[Dict], 
    account_clabe: str, 
    year: Optional[int], 
    month: Optional[int], 
    account_info: Optional[Dict]
) -> List[Dict[str, Any]]:
    """
    Process and filter BBVA files, extracting metadata - WITH DEBUG LOGGING
    """
    bbva_files = []
    
    # DEBUG: Log input parameters
    print(f"🔍 DEBUG: Processing {len(files)} raw files")
    print(f"🔍 DEBUG: Filters - Year: {year}, Month: {month}")
    print(f"🔍 DEBUG: Account CLABE: {account_clabe}")
    
    # DEBUG: Log all files found in SharePoint
    print(f"📁 DEBUG: All files in SharePoint folder:")
    for i, file in enumerate(files):
        filename = file.get('name', 'Unknown')
        print(f"  {i+1}. {filename}")
    
    for file in files:
        filename = file.get('name', '')
        
        # DEBUG: Log each file being processed
        print(f"\n🔍 Processing: {filename}")
        
        # Skip non-PDF files
        if not filename.lower().endswith('.pdf'):
            print(f"  ❌ Skipped: Not a PDF")
            continue
        
        # Check if file matches BBVA pattern
        match = re.match(BBVA_FILE_PATTERN, filename)
        if not match:
            print(f"  ❌ Skipped: Doesn't match pattern {BBVA_FILE_PATTERN}")
            continue
        
        print(f"  ✅ Pattern matched: {match.group(1)}")
        
        try:
            # Extract date from filename (YYMM format)
            date_match = match.group(1)  # YYMM
            file_year = "20" + date_match[:2]  # 25 -> 2025
            file_month = date_match[2:4]       # 01 -> 01
            
            print(f"  📅 Extracted: Year={file_year}, Month={file_month}")
            
            # Validate month
            if not (1 <= int(file_month) <= 12):
                print(f"  ❌ Invalid month: {file_month}")
                continue
            
            # Apply filters - DEBUG EACH FILTER
            if year and int(file_year) != year:
                print(f"  ❌ Filtered by year: {file_year} != {year}")
                continue
            else:
                print(f"  ✅ Year filter passed: {file_year}")
                
            if month and int(file_month) != month:
                print(f"  ❌ Filtered by month: {file_month} != {month}")
                continue
            else:
                print(f"  ✅ Month filter passed: {file_month}")
            
            # Get account name (use passed account_info to avoid circular imports)
            account_name = account_info['name'] if account_info else f'BBVA Account {account_clabe}'
            
            # Create file metadata
            file_data = {
                'filename': filename,
                'account': account_clabe,
                'account_type': account_name,
                'month': file_month,
                'year': file_year,
                'date_string': f"{file_year}-{file_month}",
                'extension': 'pdf',
                'file_type': 'PDF Document',
                'drive_id': DRIVE_ID,
                'file_id': file.get('id'),
                'download_url': f"/download/{DRIVE_ID}/{file.get('id')}",
                'web_url': file.get('webUrl'),
                'size': file.get('size', 0),
                'size_formatted': format_file_size(file.get('size', 0)),
                'last_modified_formatted': format_datetime(file.get('lastModifiedDateTime'))
            }
            
            bbva_files.append(file_data)
            print(f"  ✅ ADDED to results: {filename}")
            
        except Exception as e:
            print(f"  ❌ Error processing: {e}")
            continue
    
    # DEBUG: Final results
    print(f"\n📊 DEBUG: Final results:")
    print(f"  📁 Raw files found: {len(files)}")
    print(f"  ✅ Files after filtering: {len(bbva_files)}")
    
    if bbva_files:
        print(f"  📄 Processed files:")
        for i, bbva_file in enumerate(bbva_files):
            print(f"    {i+1}. {bbva_file['filename']} ({bbva_file['year']}-{bbva_file['month']})")
    else:
        print(f"  ⚠️  NO FILES PASSED FILTERS!")
    
    # Sort by year-month descending (newest first)
    bbva_files.sort(key=lambda x: f"{x['year']}{x['month']}", reverse=True)
    
    return bbva_files

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"


def format_datetime(iso_datetime: str) -> str:
    """
    Format ISO datetime to readable format
    
    Args:
        iso_datetime: ISO format datetime string
        
    Returns:
        Formatted datetime string (YYYY-MM-DD HH:MM)
    """
    if not iso_datetime:
        return ""
    
    try:
        dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except Exception as e:
        logger.warning(f"Error formatting datetime {iso_datetime}: {e}")
        return iso_datetime

def validate_bbva_account(account_clabe: str) -> bool:
    """
    Validate if account CLABE is supported by BBVA module
    
    Args:
        account_clabe: BBVA account CLABE number
        
    Returns:
        True if account is supported, False otherwise
    """
    return validate_clabe(account_clabe) and account_clabe in get_folder_path_mapping()

def get_supported_accounts() -> List[str]:
    """
    Get list of supported BBVA account CLABEs
    
    Returns:
        List of supported account CLABE numbers
    """
    return list(get_folder_path_mapping().keys())

# ============================================================================
# FILE CONTENT OPERATIONS
# ============================================================================

def get_bbva_file_content(file_id: str, access_token: str) -> Optional[bytes]:
    """
    Download BBVA file content using Microsoft Graph API
    
    Args:
        file_id: SharePoint file ID
        access_token: Microsoft Graph API access token
        
    Returns:
        File content as bytes, or None if failed
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{file_id}/content"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            logger.info(f"Successfully downloaded file {file_id}")
            return response.content
        else:
            logger.error(f"Failed to download file {file_id}: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {e}")
        return None

# ============================================================================
# STATISTICS AND REPORTING
# ============================================================================

def get_bbva_account_statistics(account_clabe: str, access_token: str) -> Dict[str, Any]:
    """
    Get statistics for a BBVA account
    
    Args:
        account_clabe: BBVA account CLABE number
        access_token: Microsoft Graph API access token
        
    Returns:
        Dictionary with account statistics
    """
    try:
        files = get_bbva_files(account_clabe, access_token)
        
        if not files:
            return {
                'account_clabe': account_clabe,
                'total_files': 0,
                'years_covered': [],
                'months_covered': [],
                'latest_file': None,
                'oldest_file': None
            }
        
        # Calculate statistics
        years = sorted(list(set(f['year'] for f in files)))
        months = sorted(list(set(f'{f["year"]}-{f["month"]}' for f in files)))
        
        return {
            'account_clabe': account_clabe,
            'total_files': len(files),
            'years_covered': years,
            'months_covered': months,
            'latest_file': files[0] if files else None,  # Already sorted newest first
            'oldest_file': files[-1] if files else None,
            'file_size_total': sum(f.get('size', 0) for f in files),
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics for account {account_clabe}: {e}")
        return {
            'account_clabe': account_clabe,
            'error': str(e),
            'generated_at': datetime.now().isoformat()
        }