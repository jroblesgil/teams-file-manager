"""
STP Database Management Module

Handles all database operations for STP file tracking and JSON database management.
"""

import logging
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def navigate_to_stp_db_folder(access_token: str) -> Dict[str, str]:
    """Navigate to STP DB folder and return folder ID"""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        drive_id = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
        
        # Navigate: 04 Bancos → Estados de Cuenta → STP → STP DB
        bancos_folder_id = "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"
        
        # Get Estados de Cuenta folder
        bancos_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{bancos_folder_id}/children"
        bancos_response = requests.get(bancos_url, headers=headers)
        
        if bancos_response.status_code != 200:
            raise Exception(f"Failed to access Bancos folder: {bancos_response.status_code}")
        
        bancos_items = bancos_response.json().get('value', [])
        estados_folder = next((item for item in bancos_items if item.get('folder') and 'estado' in item.get('name', '').lower()), None)
        
        if not estados_folder:
            raise Exception("Estados de Cuenta folder not found")
        
        # Get STP folder
        estados_id = estados_folder.get('id')
        estados_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{estados_id}/children"
        estados_response = requests.get(estados_url, headers=headers)
        
        if estados_response.status_code != 200:
            raise Exception(f"Failed to access Estados folder: {estados_response.status_code}")
        
        estados_items = estados_response.json().get('value', [])
        stp_folder = next((item for item in estados_items if item.get('folder') and 'stp' in item.get('name', '').lower()), None)
        
        if not stp_folder:
            raise Exception("STP folder not found")
        
        # Get STP DB folder
        stp_id = stp_folder.get('id')
        stp_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{stp_id}/children"
        stp_response = requests.get(stp_url, headers=headers)
        
        if stp_response.status_code != 200:
            raise Exception(f"Failed to access STP folder: {stp_response.status_code}")
        
        stp_items = stp_response.json().get('value', [])
        stp_db_folder = next((item for item in stp_items if item.get('folder') and 'stp db' in item.get('name', '').lower()), None)
        
        if not stp_db_folder:
            raise Exception("STP DB folder not found - please ensure it exists")
        
        return {
            'drive_id': drive_id,
            'folder_id': stp_db_folder.get('id'),
            'folder_name': stp_db_folder.get('name')
        }
        
    except Exception as e:
        logger.error(f"Error navigating to STP DB folder: {e}")
        raise


def get_parse_tracking_data(access_token: str) -> Dict[str, Any]:
    """Load parsing tracking metadata"""
    try:
        stp_db_info = navigate_to_stp_db_folder(access_token)
        drive_id = stp_db_info['drive_id']
        folder_id = stp_db_info['folder_id']
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Try to get tracking file
        tracking_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}:/STP_Parse_Tracking.json:/content"
        response = requests.get(tracking_url, headers=headers)
        
        if response.status_code == 200:
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                logger.warning("Tracking file corrupted, recreating")
                return {}
        elif response.status_code == 404:
            logger.info("Tracking file not found, will create new one")
            return {}
        else:
            logger.error(f"Error accessing tracking file: {response.status_code}")
            return {}
            
    except Exception as e:
        logger.error(f"Error getting tracking data: {e}")
        return {}


def update_parse_tracking_data(tracking_data: Dict[str, Any], access_token: str) -> bool:
    """Save parsing tracking metadata"""
    try:
        stp_db_info = navigate_to_stp_db_folder(access_token)
        drive_id = stp_db_info['drive_id']
        folder_id = stp_db_info['folder_id']
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Upload tracking file
        tracking_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}:/STP_Parse_Tracking.json:/content"
        tracking_json = json.dumps(tracking_data, indent=2)
        
        response = requests.put(tracking_url, headers=headers, data=tracking_json.encode('utf-8'))
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to save tracking data: {response.status_code}")
        
        logger.info("Tracking data updated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error updating tracking data: {e}")
        return False


def get_json_database(account_number: str, access_token: str) -> Dict[str, Any]:
    """Load JSON database for account"""
    try:
        stp_db_info = navigate_to_stp_db_folder(access_token)
        drive_id = stp_db_info['drive_id']
        folder_id = stp_db_info['folder_id']
        
        # Determine database filename
        db_filename = get_database_filename(account_number)
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Try to get database file
        db_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}:/{db_filename}:/content"
        response = requests.get(db_url, headers=headers)
        
        if response.status_code == 200:
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                logger.warning(f"Database file {db_filename} corrupted, recreating")
                return create_empty_database(account_number)
        elif response.status_code == 404:
            logger.info(f"Database file {db_filename} not found, creating new one")
            return create_empty_database(account_number)
        else:
            logger.error(f"Error accessing database file: {response.status_code}")
            return create_empty_database(account_number)
            
    except Exception as e:
        logger.error(f"Error getting JSON database: {e}")
        return create_empty_database(account_number)


def create_empty_database(account_number: str) -> Dict[str, Any]:
    """Create empty database structure"""
    account_types = {
        '646180559700000009': 'STP SA',
        '646990403000000003': 'STP IP - PI',
        '646180403000000004': 'STP IP - PD'
    }
    
    return {
        'metadata': {
            'account_number': account_number,
            'account_type': account_types.get(account_number, 'Unknown'),
            'last_updated': datetime.now().isoformat(),
            'total_transactions': 0,
            'files_parsed': 0
        },
        'transactions': []
    }


def get_database_filename(account_number: str) -> str:
    """Get database filename for account"""
    filename_mapping = {
        '646180559700000009': 'STP_SA_DB.json',
        '646990403000000003': 'STP_IP_PI_DB.json',
        '646180403000000004': 'STP_IP_PD_DB.json'
    }
    return filename_mapping.get(account_number, f'STP_{account_number}_DB.json')


def update_json_database(account_number: str, data: Dict[str, Any], access_token: str) -> bool:
    """Save JSON database for account"""
    try:
        stp_db_info = navigate_to_stp_db_folder(access_token)
        drive_id = stp_db_info['drive_id']
        folder_id = stp_db_info['folder_id']
        
        db_filename = get_database_filename(account_number)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Update metadata
        data['metadata']['last_updated'] = datetime.now().isoformat()
        data['metadata']['total_transactions'] = len(data['transactions'])
        
        # Upload database file
        db_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}:/{db_filename}:/content"
        db_json = json.dumps(data, indent=2, ensure_ascii=False)
        
        response = requests.put(db_url, headers=headers, data=db_json.encode('utf-8'))
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to save database: {response.status_code}")
        
        logger.info(f"Database {db_filename} updated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error updating JSON database: {e}")
        return False


def remove_file_transactions(data: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """Remove all transactions from a specific file"""
    original_count = len(data['transactions'])
    data['transactions'] = [t for t in data['transactions'] if t.get('file') != filename]
    removed_count = original_count - len(data['transactions'])
    
    logger.info(f"Removed {removed_count} transactions from file {filename}")
    return data


# ============================================================================
# NEW FUNCTIONS FOR DATABASE SYNCHRONIZATION
# ============================================================================

def cleanup_orphaned_transactions(database: Dict[str, Any], existing_filenames: List[str], account_number: str) -> Dict[str, Any]:
    """Remove transactions from files that no longer exist in SharePoint
    
    This is the key function that fixes the data synchronization issue.
    It ensures the database only contains transactions from files that actually exist.
    """
    try:
        original_count = len(database['transactions'])
        
        # Get list of files currently referenced in database
        db_files = set()
        for transaction in database['transactions']:
            filename = transaction.get('file')
            if filename:
                db_files.add(filename)
        
        # Find files that are in database but no longer exist in SharePoint
        existing_files_set = set(existing_filenames)
        orphaned_files = db_files - existing_files_set
        
        if orphaned_files:
            logger.info(f"Found {len(orphaned_files)} orphaned files in database for account {account_number}")
            logger.info(f"Orphaned files: {list(orphaned_files)}")
            
            # Remove transactions from orphaned files
            database['transactions'] = [
                t for t in database['transactions'] 
                if t.get('file') not in orphaned_files
            ]
            
            removed_count = original_count - len(database['transactions'])
            logger.info(f"Cleaned up {removed_count} orphaned transactions from {len(orphaned_files)} deleted files")
            
            # Update metadata
            database['metadata']['last_cleanup'] = datetime.now().isoformat()
            database['metadata']['orphaned_files_removed'] = list(orphaned_files)
            
        else:
            logger.info(f"No orphaned transactions found for account {account_number}")
        
        return database
        
    except Exception as e:
        logger.error(f"Error cleaning up orphaned transactions: {e}")
        return database


def synchronize_database_with_files(database: Dict[str, Any], current_files: List[Dict[str, Any]], account_number: str) -> Dict[str, Any]:
    """Synchronize database with current files in SharePoint directory
    
    This function ensures database integrity by:
    1. Removing transactions from deleted files
    2. Keeping only data from files that currently exist
    """
    try:
        # Extract filenames from current files (only Excel files)
        current_excel_filenames = [
            file_info.get('filename') 
            for file_info in current_files 
            if file_info.get('filename', '').endswith('.xlsx')
        ]
        
        logger.info(f"Synchronizing database with {len(current_excel_filenames)} current Excel files")
        logger.info(f"Current Excel files: {current_excel_filenames}")
        
        # Clean up orphaned transactions
        synchronized_database = cleanup_orphaned_transactions(
            database, 
            current_excel_filenames, 
            account_number
        )
        
        return synchronized_database
        
    except Exception as e:
        logger.error(f"Error synchronizing database with files: {e}")
        return database


def cleanup_tracking_data(tracking_data: Dict[str, Any], current_files: List[Dict[str, Any]], account_number: str) -> Dict[str, Any]:
    """Clean up tracking data to remove references to deleted files"""
    try:
        if account_number not in tracking_data:
            return tracking_data
        
        # Get current Excel filenames
        current_excel_filenames = set(
            file_info.get('filename') 
            for file_info in current_files 
            if file_info.get('filename', '').endswith('.xlsx')
        )
        
        # Get tracked filenames
        account_tracking = tracking_data[account_number]
        tracked_filenames = set(account_tracking.keys())
        
        # Find orphaned tracking entries
        orphaned_tracking = tracked_filenames - current_excel_filenames
        
        if orphaned_tracking:
            logger.info(f"Cleaning up {len(orphaned_tracking)} orphaned tracking entries")
            logger.info(f"Orphaned tracking entries: {list(orphaned_tracking)}")
            
            # Remove orphaned tracking entries
            for orphaned_file in orphaned_tracking:
                del account_tracking[orphaned_file]
        else:
            logger.info("No orphaned tracking entries found")
        
        return tracking_data
        
    except Exception as e:
        logger.error(f"Error cleaning up tracking data: {e}")