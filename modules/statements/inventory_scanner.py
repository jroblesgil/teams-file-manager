# modules/statements/inventory_scanner.py
"""
Inventory Scanner for Unified Statements
Scans SharePoint folders to build complete file inventory
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional, Tuple

from .config import UNIFIED_ACCOUNTS
from .inventory_manager import InventoryManager, FileInfo

logger = logging.getLogger(__name__)

class InventoryScanner:
    """Scans SharePoint folders and builds inventory data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.InventoryScanner')
        self.inventory_manager = InventoryManager()
    
    def scan_all_accounts(self, access_token: str, 
                         progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Scan all accounts and build complete inventory
        
        Args:
            access_token: OAuth access token
            progress_callback: Function to call with progress updates
            
        Returns:
            Dict with scan results and statistics
        """
        self.logger.info("Starting full inventory scan for all accounts")
        
        if progress_callback:
            progress_callback({
                'status': 'initializing',
                'progress_percentage': 0,
                'details': 'Initializing inventory scan...',
                'total_accounts': len(UNIFIED_ACCOUNTS)
            })
        
        # Create empty inventory structure
        inventory = {
            'last_updated': datetime.now().isoformat(),
            'version': '1.0',
            'accounts': {}
        }
        
        results = {
            'success': True,
            'accounts_scanned': 0,
            'accounts_failed': 0,
            'total_files_found': 0,
            'total_parsed_files': 0,
            'errors': []
        }
        
        total_accounts = len(UNIFIED_ACCOUNTS)
        
        for idx, (account_id, account_config) in enumerate(UNIFIED_ACCOUNTS.items()):
            try:
                if progress_callback:
                    progress_callback({
                        'status': 'scanning_account',
                        'progress_percentage': int((idx / total_accounts) * 90),
                        'details': f'Scanning {account_config["name"]} ({idx + 1}/{total_accounts})',
                        'current_account': account_config["name"],
                        'accounts_processed': idx
                    })
                
                # Scan individual account
                account_inventory = self._scan_single_account(account_id, account_config, access_token)
                
                if account_inventory:
                    inventory['accounts'][account_id] = account_inventory
                    results['accounts_scanned'] += 1
                    
                    # Count files for statistics
                    for month_data in account_inventory.values():
                        for file_type, file_info in month_data.items():
                            if file_info and file_info.get('exists'):
                                results['total_files_found'] += 1
                                if file_info.get('parse_status') == 'parsed':
                                    results['total_parsed_files'] += 1
                else:
                    results['accounts_failed'] += 1
                    results['errors'].append(f"Failed to scan account: {account_id}")
                    
            except Exception as e:
                self.logger.error(f"Error scanning account {account_id}: {e}")
                results['accounts_failed'] += 1
                results['errors'].append(f"Error scanning {account_id}: {str(e)}")
        
        # Save inventory to SharePoint
        if progress_callback:
            progress_callback({
                'status': 'saving_inventory',
                'progress_percentage': 95,
                'details': 'Saving inventory file to SharePoint...'
            })
        
        try:
            save_success = self.inventory_manager.write_inventory(inventory, access_token)
            if not save_success:
                results['success'] = False
                results['errors'].append("Failed to save inventory file to SharePoint")
        except Exception as e:
            self.logger.error(f"Error saving inventory: {e}")
            results['success'] = False
            results['errors'].append(f"Failed to save inventory: {str(e)}")
        
        if progress_callback:
            progress_callback({
                'status': 'completed' if results['success'] else 'error',
                'progress_percentage': 100,
                'details': f'Scan complete: {results["accounts_scanned"]} accounts, {results["total_files_found"]} files found',
                'accounts_processed': total_accounts
            })
        
        self.logger.info(f"Inventory scan complete - Success: {results['success']}, "
                        f"Accounts: {results['accounts_scanned']}/{total_accounts}, "
                        f"Files: {results['total_files_found']}")
        
        return results
    
    def scan_single_account(self, account_id: str, access_token: str,
                          progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Scan a single account and update its inventory
        
        Args:
            account_id: Account identifier
            access_token: OAuth access token
            progress_callback: Function to call with progress updates
            
        Returns:
            Dict with scan results
        """
        if account_id not in UNIFIED_ACCOUNTS:
            raise ValueError(f"Invalid account ID: {account_id}")
        
        account_config = UNIFIED_ACCOUNTS[account_id]
        
        if progress_callback:
            progress_callback({
                'status': 'scanning_account',
                'progress_percentage': 10,
                'details': f'Scanning {account_config["name"]}...'
            })
        
        try:
            # Scan the account
            account_inventory = self._scan_single_account(account_id, account_config, access_token)
            
            if account_inventory:
                # Update inventory with new data
                success = self.inventory_manager.update_account_inventory(
                    account_id, account_inventory, access_token
                )
                
                if progress_callback:
                    progress_callback({
                        'status': 'completed' if success else 'error',
                        'progress_percentage': 100,
                        'details': f'Scan complete for {account_config["name"]}'
                    })
                
                # Calculate statistics
                file_count = sum(
                    1 for month_data in account_inventory.values()
                    for file_info in month_data.values()
                    if file_info and file_info.get('exists')
                )
                
                return {
                    'success': success,
                    'account_id': account_id,
                    'files_found': file_count,
                    'error': None if success else 'Failed to update inventory'
                }
            else:
                return {
                    'success': False,
                    'account_id': account_id,
                    'files_found': 0,
                    'error': 'Failed to scan account files'
                }
                
        except Exception as e:
            self.logger.error(f"Error scanning account {account_id}: {e}")
            return {
                'success': False,
                'account_id': account_id,
                'files_found': 0,
                'error': str(e)
            }
    
    def _scan_single_account(self, account_id: str, account_config: Dict[str, Any],
                           access_token: str) -> Optional[Dict[str, Any]]:
        """
        Internal method to scan a single account's files
        
        Args:
            account_id: Account identifier
            account_config: Account configuration from UNIFIED_ACCOUNTS
            access_token: OAuth access token
            
        Returns:
            Dict with account inventory data or None if failed
        """
        try:
            account_type = account_config['type']
            
            if account_type == 'stp':
                return self._scan_stp_account(account_id, account_config, access_token)
            elif account_type == 'bbva':
                return self._scan_bbva_account(account_id, account_config, access_token)
            else:
                self.logger.error(f"Unknown account type: {account_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in _scan_single_account for {account_id}: {e}")
            return None
    
    def _scan_stp_account(self, account_id: str, account_config: Dict[str, Any],
                         access_token: str) -> Optional[Dict[str, Any]]:
        """Scan STP account using existing modules"""
        try:
            # Import existing STP modules
            from modules.stp.stp_files import get_stp_files
            from modules.stp.stp_database import get_parse_tracking_data
            
            # Try to get database too for additional tracking info
            try:
                from modules.stp.stp_database import get_json_database
                has_database = True
            except ImportError:
                has_database = False
            
            account_number = account_config['identifier']
            self.logger.info(f"Scanning STP account: {account_id} ({account_number})")
            
            # Get all files
            all_files = get_stp_files(account_number, access_token)
            
            # Get parse tracking data
            try:
                tracking_data = get_parse_tracking_data(access_token)
                account_tracking = tracking_data.get(account_number, {})
            except Exception as e:
                self.logger.warning(f"Could not load parse tracking for {account_id}: {e}")
                account_tracking = {}
            
            # Build inventory structure
            inventory = {}
            
            # Process all years present in files
            years_found = set()
            for file_info in all_files:
                date_string = file_info.get('date_string', '')
                if date_string:
                    try:
                        year = int(date_string.split('-')[0])
                        years_found.add(year)
                    except (ValueError, IndexError):
                        continue
            
            # For each year found, process all 12 months
            for year in years_found:
                for month in range(1, 13):
                    month_key = f"{year}-{month:02d}"
                    
                    # Find files for this month
                    pdf_file = next((f for f in all_files 
                                   if f.get('date_string') == month_key and f.get('extension') == 'pdf'), None)
                    xlsx_file = next((f for f in all_files 
                                    if f.get('date_string') == month_key and f.get('extension') == 'xlsx'), None)
                    
                    month_data = {}
                    
                    # Process PDF file
                    if pdf_file:
                        month_data['pdf'] = self._create_file_info(
                            pdf_file, account_tracking, 'pdf'
                        )
                    
                    # Process XLSX file
                    if xlsx_file:
                        month_data['xlsx'] = self._create_file_info(
                            xlsx_file, account_tracking, 'xlsx'
                        )
                    
                    # Only add month if it has files
                    if month_data:
                        inventory[month_key] = month_data
            
            self.logger.info(f"STP scan complete for {account_id}: {len(inventory)} months with files")
            return inventory
            
        except Exception as e:
            self.logger.error(f"Error scanning STP account {account_id}: {e}")
            return None
    
    def _scan_bbva_account(self, account_id: str, account_config: Dict[str, Any],
                          access_token: str) -> Optional[Dict[str, Any]]:
        """Scan BBVA account using existing modules"""
        try:
            # Import existing BBVA modules  
            from modules.bbva.bbva_files import get_bbva_files
            
            # Try to get parse tracking data
            try:
                from modules.bbva.bbva_database import get_bbva_parse_tracking_data
                has_tracking = True
            except ImportError:
                has_tracking = False
            
            clabe = account_config['identifier']
            self.logger.info(f"Scanning BBVA account: {account_id} ({clabe})")
            
            # Create account_info for get_bbva_files
            account_info = {
                'name': account_config['name'],
                'clabe': clabe,
                'directory': account_config['folder_path']
            }
            
            # Get all files
            all_files = get_bbva_files(clabe, access_token, account_info=account_info)
            
            # Get parse tracking data
            try:
                if has_tracking:
                    tracking_data = get_bbva_parse_tracking_data(access_token)
                    account_tracking = tracking_data.get(clabe, {})
                else:
                    account_tracking = {}
            except Exception as e:
                self.logger.warning(f"Could not load BBVA parse tracking for {account_id}: {e}")
                account_tracking = {}
            
            # Build inventory structure
            inventory = {}
            
            # Process all years present in files
            years_found = set()
            for file_info in all_files:
                date_string = file_info.get('date_string', '')
                if date_string:
                    try:
                        year = int(date_string.split('-')[0])
                        years_found.add(year)
                    except (ValueError, IndexError):
                        continue
            
            # For each year found, process all 12 months
            for year in years_found:
                for month in range(1, 13):
                    month_key = f"{year}-{month:02d}"
                    
                    # Find PDF file for this month (BBVA only uses PDFs)
                    pdf_file = next((f for f in all_files 
                                   if f.get('date_string') == month_key), None)
                    
                    if pdf_file:
                        inventory[month_key] = {
                            'pdf': self._create_file_info(pdf_file, account_tracking, 'pdf')
                        }
            
            self.logger.info(f"BBVA scan complete for {account_id}: {len(inventory)} months with files")
            return inventory
            
        except Exception as e:
            self.logger.error(f"Error scanning BBVA account {account_id}: {e}")
            return None
    
    def _create_file_info(self, file_data: Dict[str, Any], tracking_data: Dict[str, Any],
                         file_type: str) -> Dict[str, Any]:
        """
        Create file info structure from file data and tracking data
        
        Args:
            file_data: File information from SharePoint
            tracking_data: Parse tracking data for this account
            file_type: 'pdf' or 'xlsx'
            
        Returns:
            Dict containing file information
        """
        filename = file_data.get('filename', '')
        
        # Get tracking info for this file
        file_tracking = tracking_data.get(filename, {})
        
        # Determine parse status and transaction count
        parse_status = 'not_parsed'
        transaction_count = 0
        
        if file_tracking:
            if file_tracking.get('parse_status') == 'success':
                parse_status = 'parsed'
                transaction_count = file_tracking.get('transaction_count', 0)
            elif file_tracking.get('parse_status') == 'error':
                parse_status = 'error'
        
        return {
            'exists': True,
            'last_modified': file_data.get('last_modified_formatted'),
            'parse_status': parse_status,
            'transaction_count': transaction_count,
            'file_size': file_data.get('size')
        }