# modules/statements/data_loader.py - Phase 1.3: Inventory Integration
"""
Phase 1.3: Data Loader that uses existing inventory system for fast loading
Reads from statements_inventory.json instead of making SharePoint calls
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

from .config import UNIFIED_ACCOUNTS, get_stp_accounts, get_bbva_accounts
from .inventory_manager import InventoryManager

logger = logging.getLogger(__name__)

class UnifiedDataLoader:
    """Data loader that uses inventory system for fast access"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.UnifiedDataLoader')
        self.inventory_manager = InventoryManager()
    
    def get_accounts_summary(self) -> Dict[str, Any]:
        """
        Get basic account information without loading files
        FAST - No SharePoint API calls
        """
        return {
            'total_accounts': len(UNIFIED_ACCOUNTS),
            'stp_accounts': len(get_stp_accounts()),
            'bbva_accounts': len(get_bbva_accounts()),
            'accounts': {
                account_id: {
                    'type': config['type'],
                    'name': config['name'],
                    'identifier': config['identifier'],
                    'currency': config['currency'],
                    'description': config['description'],
                    'status': 'ready'
                }
                for account_id, config in UNIFIED_ACCOUNTS.items()
            },
            'generated_at': datetime.now().isoformat()
        }
    
    def load_year_data_for_server(self, access_token: str, year: int) -> Dict[str, Any]:
        """
        Load complete data for a specific year using INVENTORY SYSTEM
        This is FAST - reads from existing inventory file
        """
        self.logger.info(f"Loading year data from INVENTORY for {year}")
        
        try:
            # Read inventory file (fast - cached)
            inventory = self.inventory_manager.read_inventory(access_token)
            
            if not inventory or 'accounts' not in inventory:
                self.logger.warning("No inventory data found - possible auth issue or missing file")
                # Check if this might be an auth issue
                if self._check_auth_status(access_token):
                    self.logger.error("Authentication appears to be valid but inventory is empty")
                    return self._create_fallback_year_data(year, "Inventory file missing or empty")
                else:
                    self.logger.error("Authentication token appears to be invalid")
                    raise Exception("Authentication token expired or invalid")
            
            year_data = {}
            accounts_data = inventory['accounts']
            
            for account_id, account_config in UNIFIED_ACCOUNTS.items():
                try:
                    # Get account inventory data
                    account_inventory = accounts_data.get(account_id, {})
                    
                    # Convert inventory format to display format for this year
                    account_data = self._convert_inventory_to_display_format(
                        account_id, account_config, account_inventory, year
                    )
                    
                    year_data[account_id] = account_data
                    
                except Exception as e:
                    self.logger.error(f"Error processing inventory for account {account_id}: {e}")
                    year_data[account_id] = self._create_error_account_data(account_config, str(e))
            
            self.logger.info(f"Loaded inventory data for {len(year_data)} accounts for year {year}")
            return year_data
            
        except Exception as e:
            self.logger.error(f"Error loading inventory data: {e}")
            # Check if it's an auth error and re-raise
            if "auth" in str(e).lower() or "token" in str(e).lower() or "401" in str(e) or "403" in str(e):
                raise Exception("Authentication token expired - please log in again")
            # Otherwise, fallback to basic account data
            return self._create_fallback_year_data(year, str(e))
    
    def _check_auth_status(self, access_token: str) -> bool:
        """Quick check if auth token is still valid"""
        try:
            import requests
            headers = {'Authorization': f'Bearer {access_token}'}
            # Simple Graph API call to check token validity
            response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Auth check failed: {e}")
            return False

    def _convert_inventory_to_display_format(self, account_id: str, account_config: Dict[str, Any], 
                                            account_inventory: Dict[str, Any], year: int) -> Dict[str, Any]:
        """
        Convert inventory data to display format with STP duplication fix
        
        Args:
            account_id: Account identifier
            account_config: Account configuration 
            account_inventory: Raw inventory data for the account
            year: Year to filter data for
            
        Returns:
            Dict in display format
        """
        
        # Initialize counters
        total_files = 0
        total_transactions = 0
        parsed_months = 0
        months_data = {}
        
        print(f"DEBUG DATA LOADER: Converting inventory for {account_id} (type: {account_config['type']})")
        
        # Filter inventory data to only include the requested year
        year_inventory = {}
        for month_key, month_data in account_inventory.items():
            if isinstance(month_data, dict) and month_key.startswith(str(year)):
                year_inventory[month_key] = month_data
        
        # Process each month for the specified year
        for month_key, month_data in year_inventory.items():
            if not isinstance(month_data, dict):
                continue
                
            # Extract file data
            pdf_data = month_data.get('pdf', {})
            xlsx_data = month_data.get('xlsx', {})
            
            print(f"DEBUG DATA LOADER {account_id} {month_key}:")
            print(f"  PDF data: {pdf_data}")
            print(f"  XLSX data: {xlsx_data}")
            
            # FIXED: Update totals without duplicating STP transaction counts
            if pdf_data.get('exists'):
                total_files += 1
                # For STP accounts, don't count PDF transactions (they inherit from XLSX)
                if account_config['type'] != 'stp':
                    pdf_transactions = pdf_data.get('transaction_count', 0)
                    total_transactions += pdf_transactions
                    print(f"  Adding PDF transactions (non-STP): {pdf_transactions}")
                else:
                    print(f"  Skipping PDF transactions for STP account")

            if xlsx_data.get('exists'):
                total_files += 1
                # Always count XLSX transactions (primary source for STP, only source for others)
                xlsx_transactions = xlsx_data.get('transaction_count', 0)
                total_transactions += xlsx_transactions
                print(f"  Adding XLSX transactions: {xlsx_transactions}")
            
            # Check what's being added to totals for this month
            month_pdf_count = pdf_data.get('transaction_count', 0) if pdf_data.get('exists') else 0
            month_xlsx_count = xlsx_data.get('transaction_count', 0) if xlsx_data.get('exists') else 0
            
            if account_config['type'] == 'stp':
                month_total_added = month_xlsx_count  # Only XLSX for STP
            else:
                month_total_added = month_pdf_count + month_xlsx_count  # Both for non-STP
                
            print(f"  Month total transactions added: {month_total_added}")
            
            # Determine month status
            month_status = 'missing'
            if pdf_data.get('exists') or xlsx_data.get('exists'):
                # Check if any files are parsed
                pdf_parsed = pdf_data.get('parse_status') == 'parsed'
                xlsx_parsed = xlsx_data.get('parse_status') == 'parsed'
                
                if pdf_parsed or xlsx_parsed:
                    month_status = 'complete'
                    parsed_months += 1
                else:
                    month_status = 'partial'
            
            # Convert month key to month number for frontend
            try:
                month_num = int(month_key.split('-')[1])
                months_data[month_key] = {
                    'month': month_num,
                    'status': month_status,
                    'pdf': pdf_data if pdf_data.get('exists') else None,
                    'xlsx': xlsx_data if xlsx_data.get('exists') else None,
                    'file_count': (1 if pdf_data.get('exists') else 0) + (1 if xlsx_data.get('exists') else 0)
                }
            except (ValueError, IndexError):
                continue
        
        # Determine if account has transactions
        has_transactions = total_transactions > 0
        
        # Determine last updated
        last_updated = 'Never'
        if months_data:
            # Find most recent file modification time
            latest_times = []
            for month_data in months_data.values():
                for file_type in ['pdf', 'xlsx']:
                    file_data = month_data.get(file_type)
                    if file_data and file_data.get('last_modified'):
                        latest_times.append(file_data['last_modified'])
            
            if latest_times:
                last_updated = max(latest_times)
        
        print(f"DEBUG DATA LOADER {account_id} FINAL TOTALS:")
        print(f"  Total files: {total_files}")
        print(f"  Total transactions: {total_transactions}")
        print(f"  Parsed months: {parsed_months}")
        print(f"  Has transactions: {has_transactions}")
        
        return {
            'type': account_config['type'],
            'name': account_config['name'],
            'identifier': account_config['identifier'],
            'currency': account_config['currency'],
            'description': account_config['description'],
            'total_files': total_files,
            'total_transactions': total_transactions,
            'parsed_months': parsed_months,
            'months': months_data,
            'last_updated': last_updated,
            'has_transactions': has_transactions,
            'status': 'loaded',
            'files_loaded': True
        }

    def _convert_file_info(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert inventory file format to display format"""
        if not file_data or not file_data.get('exists'):
            return None
        
        return {
            'exists': True,
            'last_modified': file_data.get('last_modified'),
            'last_modified_formatted': file_data.get('last_modified'),
            'parse_status': file_data.get('parse_status', 'not_parsed'),
            'transaction_count': file_data.get('transaction_count', 0),
            'size': file_data.get('file_size'),
            'filename': f"File ({file_data.get('file_size', 0)} bytes)"  # Placeholder filename
        }
    
    def _determine_month_status(self, pdf_data: Dict[str, Any], xlsx_data: Dict[str, Any], 
                              account_type: str) -> str:
        """Determine month status based on file availability and account type"""
        pdf_exists = pdf_data.get('exists', False)
        xlsx_exists = xlsx_data.get('exists', False)
        
        if account_type == 'stp':
            # STP requires both PDF and XLSX for complete status
            if pdf_exists and xlsx_exists:
                return 'complete'
            elif pdf_exists or xlsx_exists:
                return 'partial'
            else:
                return 'missing'
        else:
            # BBVA only requires PDF
            if pdf_exists:
                return 'complete'
            else:
                return 'missing'
    
    def _get_month_name(self, month_num: int) -> str:
        """Get month name from number"""
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        return month_names[month_num - 1]
    
    def _create_fallback_year_data(self, year: int, error_message: str = "Inventory not available") -> Dict[str, Any]:
        """Create basic account data when inventory is not available"""
        self.logger.warning(f"Creating fallback data for {year} - {error_message}")
        
        fallback_data = {}
        for account_id, account_config in UNIFIED_ACCOUNTS.items():
            fallback_data[account_id] = {
                'type': account_config['type'],
                'name': account_config['name'],
                'identifier': account_config['identifier'],
                'currency': account_config['currency'],
                'description': account_config['description'],
                'total_files': 0,
                'total_transactions': 0,
                'parsed_months': 0,
                'months': {},
                'last_updated': error_message,
                'has_transactions': False,
                'status': 'no_inventory',
                'files_loaded': False,
                'data_source': 'fallback',
                'error': error_message
            }
        
        return fallback_data
    
    # Keep existing methods for compatibility
    def load_account_files_data(self, account_id: str, access_token: str, year: int) -> Dict[str, Any]:
        """
        Load file data for a SINGLE account FROM INVENTORY
        This method now reads from inventory instead of SharePoint
        """
        if account_id not in UNIFIED_ACCOUNTS:
            raise ValueError(f"Invalid account ID: {account_id}")
        
        account_config = UNIFIED_ACCOUNTS[account_id]
        self.logger.info(f"Loading account {account_id} from INVENTORY")
        
        try:
            # Read inventory
            inventory = self.inventory_manager.read_inventory(access_token)
            
            if not inventory or 'accounts' not in inventory:
                return self._create_error_account_data(account_config, "Inventory not available")
            
            account_inventory = inventory['accounts'].get(account_id, {})
            
            # Convert to display format for all years (not just specific year)
            all_months = {}
            total_files = 0
            total_transactions = 0
            
            for month_key, month_data in account_inventory.items():
                if isinstance(month_data, dict):
                    pdf_data = month_data.get('pdf', {})
                    xlsx_data = month_data.get('xlsx', {})
                    
                    display_month_data = {
                        'month_name': self._get_month_name(int(month_key.split('-')[1])),
                        'pdf': self._convert_file_info(pdf_data) if pdf_data.get('exists') else None,
                        'xlsx': self._convert_file_info(xlsx_data) if xlsx_data.get('exists') else None,
                        'status': self._determine_month_status(pdf_data, xlsx_data, account_config['type']),
                        'file_count': sum(1 for f in [pdf_data, xlsx_data] if f.get('exists')),
                        'has_files': any(f.get('exists') for f in [pdf_data, xlsx_data])
                    }
                    
                    all_months[month_key] = display_month_data
                    
                    # Update totals - FIXED for STP duplication
                    if pdf_data.get('exists'):
                        total_files += 1
                        # For STP accounts, don't count PDF transactions (they inherit from XLSX)
                        if account_config['type'] != 'stp':
                            total_transactions += pdf_data.get('transaction_count', 0)
                            
                    if xlsx_data.get('exists'):
                        total_files += 1
                        # Always count XLSX transactions (primary source for STP, only source for others)
                        total_transactions += xlsx_data.get('transaction_count', 0)            
            return {
                'type': account_config['type'],
                'name': account_config['name'],
                'identifier': account_config['identifier'],
                'currency': account_config['currency'],
                'description': account_config['description'],
                'total_files': total_files,
                'total_transactions': total_transactions,
                'parsed_months': sum(1 for m in all_months.values() if m['status'] == 'complete'),
                'months': all_months,
                'last_updated': inventory.get('last_updated', 'From inventory'),
                'has_transactions': total_transactions > 0,
                'status': 'loaded',
                'files_loaded': True,
                'data_source': 'inventory'
            }
                
        except Exception as e:
            self.logger.error(f"Error loading account {account_id} from inventory: {e}")
            return self._create_error_account_data(account_config, str(e))
    
    def load_unified_statements_data(self, access_token: str, year: int, 
                                   load_files: bool = True) -> Dict[str, Any]:
        """
        Load unified statements data using INVENTORY SYSTEM
        Always fast now - reads from inventory file
        """
        self.logger.info(f"Loading unified data for {year} from INVENTORY")
        
        if load_files:
            # Use inventory system for fast loading
            return self.load_year_data_for_server(access_token, year)
        else:
            # Still return basic info
            summary = self.get_accounts_summary()
            unified_data = {}
            
            for account_id, account_info in summary['accounts'].items():
                unified_data[account_id] = {
                    **account_info,
                    'total_files': 0,
                    'total_transactions': 0,
                    'parsed_months': 0,
                    'months': {},
                    'last_updated': 'Not loaded',
                    'has_transactions': False,
                    'files_loaded': False
                }
            
            return unified_data
    
    def refresh_inventory(self, access_token: str, account_id: Optional[str] = None, 
                         progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Refresh inventory data by re-scanning SharePoint
        This is the only method that should trigger SharePoint scans
        
        Args:
            access_token: OAuth access token
            account_id: Optional account ID to refresh (None = refresh all)
            progress_callback: Callback to update progress
            
        Returns:
            Dict with refresh results
        """
        from .inventory_scanner import InventoryScanner
        
        scanner = InventoryScanner()
        
        if account_id:
            self.logger.info(f"Refreshing inventory for account: {account_id}")
            # Pass progress callback directly to scanner
            result = scanner.scan_single_account(account_id, access_token, progress_callback)
            
            # Convert single account result to match bulk scan format
            bulk_result = {
                'success': result.get('success', False),
                'accounts_scanned': 1 if result.get('success') else 0,
                'accounts_failed': 0 if result.get('success') else 1,
                'total_files_found': result.get('files_found', 0),
                'total_parsed_files': 0,  # Not tracked at this level
                'errors': [result.get('error')] if result.get('error') else []
            }
            
        else:
            self.logger.info("Refreshing inventory for all accounts")
            # Pass progress callback directly to scanner
            bulk_result = scanner.scan_all_accounts(access_token, progress_callback)
        
        # Clear cache to force reload
        self.inventory_manager.clear_cache()
        
        return bulk_result
    
    # Utility methods
    def _format_count(self, count: int) -> str:
        """Format count for display"""
        if count == 0:
            return '0'
        elif count < 1000:
            return str(count)
        elif count < 1000000:
            return f"{count/1000:.1f}k"
        else:
            return f"{count/1000000:.1f}M"
    
    def _create_error_account_data(self, account_config: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Create error data structure for failed account loads"""
        return {
            'type': account_config.get('type', 'unknown'),
            'name': account_config.get('name', 'Unknown Account'),
            'identifier': account_config.get('identifier', 'unknown'),
            'currency': account_config.get('currency', 'unknown'),
            'description': account_config.get('description', 'Unknown account'),
            'total_files': 0,
            'total_transactions': 0,
            'parsed_months': 0,
            'months': {},
            'last_updated': 'Error',
            'has_transactions': False,
            'status': 'error',
            'error': error,
            'files_loaded': False,
            'data_source': 'error'
        }