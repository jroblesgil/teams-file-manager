# modules/bbva/bbva_database.py
"""
BBVA Database Management Module

Handles JSON database operations for BBVA transaction data.
Mirrors the STP system architecture for consistency.
"""

import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

from .bbva_config import BBVA_ACCOUNTS, get_database_mapping

logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DRIVE_ID = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
BANCOS_FOLDER_ID = "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"

# ============================================================================
# CORE DATABASE FUNCTIONS
# ============================================================================

def navigate_to_bbva_db_folder(access_token: str) -> Dict[str, str]:
    """
    Navigate to BBVA DB folder: Estados de Cuenta/BBVA/BBVA DB/
    Returns drive_id and folder_id for database operations
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Step 1: Navigate to Bancos folder
        bancos_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{BANCOS_FOLDER_ID}/children"
        bancos_response = requests.get(bancos_url, headers=headers)
        
        if bancos_response.status_code != 200:
            raise Exception(f"Failed to access Bancos folder: {bancos_response.status_code}")
        
        bancos_items = bancos_response.json().get('value', [])
        
        # Step 2: Find Estados de Cuenta folder
        estados_folder = next(
            (item for item in bancos_items 
             if item.get('folder') and 'estado' in item.get('name', '').lower()), 
            None
        )
        
        if not estados_folder:
            raise Exception("Estados de Cuenta folder not found")
        
        # Step 3: Navigate to BBVA folder
        estados_id = estados_folder.get('id')
        estados_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{estados_id}/children"
        estados_response = requests.get(estados_url, headers=headers)
        
        if estados_response.status_code != 200:
            raise Exception(f"Failed to access Estados folder: {estados_response.status_code}")
        
        estados_items = estados_response.json().get('value', [])
        bbva_folder = next(
            (item for item in estados_items 
             if item.get('folder') and 'bbva' in item.get('name', '').lower()), 
            None
        )
        
        if not bbva_folder:
            raise Exception("BBVA folder not found")
        
        # Step 4: Get BBVA DB folder (create if doesn't exist)
        bbva_id = bbva_folder.get('id')
        bbva_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{bbva_id}/children"
        bbva_response = requests.get(bbva_url, headers=headers)
        
        if bbva_response.status_code != 200:
            raise Exception(f"Failed to access BBVA folder: {bbva_response.status_code}")
        
        bbva_items = bbva_response.json().get('value', [])
        bbva_db_folder = next(
            (item for item in bbva_items 
             if item.get('folder') and 'bbva db' in item.get('name', '').lower()), 
            None
        )
        
        # Create BBVA DB folder if it doesn't exist
        if not bbva_db_folder:
            logger.info("Creating BBVA DB folder...")
            create_folder_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{bbva_id}/children"
            create_folder_data = {
                "name": "BBVA DB",
                "folder": {},
                "@microsoft.graph.conflictBehavior": "fail"
            }
            
            create_response = requests.post(
                create_folder_url, 
                headers={**headers, 'Content-Type': 'application/json'}, 
                json=create_folder_data
            )
            
            if create_response.status_code in [200, 201]:
                bbva_db_folder = create_response.json()
                logger.info("✅ BBVA DB folder created successfully")
            else:
                raise Exception(f"Failed to create BBVA DB folder: {create_response.status_code}")
        
        return {
            'drive_id': DRIVE_ID,
            'folder_id': bbva_db_folder.get('id'),
            'folder_name': bbva_db_folder.get('name')
        }
        
    except Exception as e:
        logger.error(f"Error navigating to BBVA DB folder: {e}")
        raise


def get_bbva_database(account_clabe: str, access_token: str) -> Dict[str, Any]:
    """
    Load JSON database for BBVA account
    
    Args:
        account_clabe: BBVA account CLABE number
        access_token: Microsoft Graph API access token
        
    Returns:
        Database dictionary with metadata and transactions
    """
    try:
        bbva_db_info = navigate_to_bbva_db_folder(access_token)
        drive_id = bbva_db_info['drive_id']
        folder_id = bbva_db_info['folder_id']
        
        # Determine database filename
        db_filename = get_database_filename(account_clabe)
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Try to get database file
        db_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}:/{db_filename}:/content"
        response = requests.get(db_url, headers=headers)
        
        if response.status_code == 200:
            try:
                database = json.loads(response.text)
                logger.info(f"✅ Loaded BBVA database: {db_filename}")
                return database
            except json.JSONDecodeError:
                logger.warning(f"Database file {db_filename} corrupted, recreating")
                return create_empty_bbva_database(account_clabe)
        elif response.status_code == 404:
            logger.info(f"Database file {db_filename} not found, creating new one")
            return create_empty_bbva_database(account_clabe)
        else:
            logger.error(f"Error accessing database file: {response.status_code}")
            return create_empty_bbva_database(account_clabe)
            
    except Exception as e:
        logger.error(f"Error getting BBVA JSON database: {e}")
        return create_empty_bbva_database(account_clabe)


def update_bbva_database(account_clabe: str, data: Dict[str, Any], access_token: str) -> bool:
    """
    Save JSON database for BBVA account
    
    Args:
        account_clabe: BBVA account CLABE number
        data: Database dictionary to save
        access_token: Microsoft Graph API access token
        
    Returns:
        True if successful, False otherwise
    """
    try:
        bbva_db_info = navigate_to_bbva_db_folder(access_token)
        drive_id = bbva_db_info['drive_id']
        folder_id = bbva_db_info['folder_id']
        
        # Update metadata
        data['metadata']['last_updated'] = datetime.now().isoformat()
        data['metadata']['total_transactions'] = len(data.get('transactions', []))
        
        # Determine database filename
        db_filename = get_database_filename(account_clabe)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Upload database file
        db_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}:/{db_filename}:/content"
        db_json = json.dumps(data, indent=2, ensure_ascii=False)
        
        response = requests.put(db_url, headers=headers, data=db_json.encode('utf-8'))
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to save database: {response.status_code}")
        
        logger.info(f"✅ BBVA database updated: {db_filename}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating BBVA database: {e}")
        return False


def get_bbva_parse_tracking_data(access_token: str) -> Dict[str, Any]:
    """
    Load BBVA parsing tracking metadata
    
    Returns:
        Dictionary with parsing tracking data for all BBVA accounts
    """
    try:
        bbva_db_info = navigate_to_bbva_db_folder(access_token)
        drive_id = bbva_db_info['drive_id']
        folder_id = bbva_db_info['folder_id']
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Try to get tracking file
        tracking_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}:/BBVA_Parse_Tracking.json:/content"
        response = requests.get(tracking_url, headers=headers)
        
        if response.status_code == 200:
            try:
                tracking_data = json.loads(response.text)
                logger.info("✅ Loaded BBVA tracking data")
                return tracking_data
            except json.JSONDecodeError:
                logger.warning("BBVA tracking file corrupted, recreating")
                return {}
        elif response.status_code == 404:
            logger.info("BBVA tracking file not found, will create new one")
            return {}
        else:
            logger.error(f"Error accessing BBVA tracking file: {response.status_code}")
            return {}
            
    except Exception as e:
        logger.error(f"Error getting BBVA tracking data: {e}")
        return {}


def update_bbva_parse_tracking_data(tracking_data: Dict[str, Any], access_token: str) -> bool:
    """
    Save BBVA parsing tracking metadata
    
    Args:
        tracking_data: Tracking dictionary to save
        access_token: Microsoft Graph API access token
        
    Returns:
        True if successful, False otherwise
    """
    try:
        bbva_db_info = navigate_to_bbva_db_folder(access_token)
        drive_id = bbva_db_info['drive_id']
        folder_id = bbva_db_info['folder_id']
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Upload tracking file
        tracking_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}:/BBVA_Parse_Tracking.json:/content"
        tracking_json = json.dumps(tracking_data, indent=2, ensure_ascii=False)
        
        response = requests.put(tracking_url, headers=headers, data=tracking_json.encode('utf-8'))
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to save BBVA tracking data: {response.status_code}")
        
        logger.info("✅ BBVA tracking data updated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error updating BBVA tracking data: {e}")
        return False


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_empty_bbva_database(account_clabe: str) -> Dict[str, Any]:
    """
    Create empty BBVA database structure
    
    Args:
        account_clabe: BBVA account CLABE number
        
    Returns:
        Empty database dictionary
    """
    from .bbva_config import get_account_by_clabe
    
    account_info = get_account_by_clabe(account_clabe)
    account_name = account_info['name'] if account_info else f'BBVA_{account_clabe}'
    
    return {
        'metadata': {
            'account_clabe': account_clabe,
            'account_type': account_name,
            'last_updated': datetime.now().isoformat(),
            'total_transactions': 0,
            'files_parsed': 0
        },
        'transactions': []
    }


def get_database_filename(account_clabe: str) -> str:
    """
    Get database filename for BBVA account
    
    Args:
        account_clabe: BBVA account CLABE number
        
    Returns:
        Database filename (e.g., 'BBVA_MX_MXN_DB.json')
    """
    database_mapping = get_database_mapping()
    
    # Find the account key that matches this CLABE
    for account_key, account_data in BBVA_ACCOUNTS.items():
        if account_data['clabe'] == account_clabe:
            return database_mapping.get(account_key, f'BBVA_{account_clabe}_DB.json')
    
    # Fallback if not found
    return f'BBVA_{account_clabe}_DB.json'


def remove_file_transactions(database: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """
    Remove all transactions from a specific file
    
    Args:
        database: Database dictionary
        filename: Name of file to remove transactions from
        
    Returns:
        Updated database dictionary
    """
    original_count = len(database.get('transactions', []))
    
    # Filter out transactions from this file
    database['transactions'] = [
        tx for tx in database.get('transactions', [])
        if tx.get('file_source') != filename
    ]
    
    removed_count = original_count - len(database['transactions'])
    
    if removed_count > 0:
        logger.info(f"Removed {removed_count} transactions from file: {filename}")
    
    return database


def synchronize_database_with_files(database: Dict[str, Any], current_files: List[Dict], 
                                  account_clabe: str) -> Dict[str, Any]:
    """
    Remove transactions from files that no longer exist in SharePoint
    
    Args:
        database: Database dictionary
        current_files: List of current files from SharePoint
        account_clabe: BBVA account CLABE number
        
    Returns:
        Synchronized database dictionary
    """
    if not database.get('transactions'):
        return database
    
    # Get list of current filenames
    current_filenames = {file_info.get('filename', '') for file_info in current_files}
    
    # Find transactions from deleted files
    original_count = len(database['transactions'])
    
    database['transactions'] = [
        tx for tx in database['transactions']
        if tx.get('file_source', '') in current_filenames
    ]
    
    removed_count = original_count - len(database['transactions'])
    
    if removed_count > 0:
        logger.info(f"Synchronized database for {account_clabe}: removed {removed_count} orphaned transactions")
    
    return database


def cleanup_tracking_data(tracking_data: Dict[str, Any], current_files: List[Dict], 
                         account_clabe: str) -> Dict[str, Any]:
    """
    Remove tracking entries for files that no longer exist
    
    Args:
        tracking_data: Tracking data dictionary
        current_files: List of current files from SharePoint
        account_clabe: BBVA account CLABE number
        
    Returns:
        Cleaned tracking data dictionary
    """
    if account_clabe not in tracking_data:
        return tracking_data
    
    # Get list of current filenames
    current_filenames = {file_info.get('filename', '') for file_info in current_files}
    
    # Clean up tracking data
    original_files = len(tracking_data[account_clabe])
    
    tracking_data[account_clabe] = {
        filename: file_data
        for filename, file_data in tracking_data[account_clabe].items()
        if filename in current_filenames
    }
    
    removed_files = original_files - len(tracking_data[account_clabe])
    
    if removed_files > 0:
        logger.info(f"Cleaned tracking data for {account_clabe}: removed {removed_files} deleted file entries")
    
    return tracking_data