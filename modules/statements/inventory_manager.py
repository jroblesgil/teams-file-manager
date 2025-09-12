# modules/statements/inventory_manager.py
"""
Inventory Management System for Unified Statements
Handles reading, writing, and updating the central inventory file
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class FileInfo:
    """Data structure for individual file information"""
    exists: bool
    last_modified: Optional[str] = None
    parse_status: str = "not_parsed"  # not_parsed, parsed, error
    transaction_count: int = 0
    file_size: Optional[int] = None

@dataclass
class MonthInfo:
    """Data structure for month information"""
    pdf: Optional[FileInfo] = None
    xlsx: Optional[FileInfo] = None

class InventoryManager:
    """Manages the central statements inventory file"""
    
    def __init__(self, inventory_file_path: str = "statements_inventory.json"):
        self.inventory_file_path = inventory_file_path
        self.logger = logging.getLogger(__name__ + '.InventoryManager')
        self._cached_inventory = None
        self._cache_timestamp = None
    
    def read_inventory(self, access_token: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Read the inventory file from SharePoint
        
        Args:
            access_token: OAuth access token
            force_refresh: If True, bypass cache and read from SharePoint
            
        Returns:
            Dict containing the full inventory structure
        """
        try:
            # Check cache first (unless force refresh)
            if not force_refresh and self._cached_inventory is not None:
                self.logger.debug("Returning cached inventory")
                return self._cached_inventory
            
            # Read from SharePoint using existing STP file functions
            from modules.stp.stp_files import get_file_content_by_ids
            
            self.logger.info(f"Reading inventory file: {self.inventory_file_path}")
            
            # Use hardcoded SharePoint structure like other modules
            drive_id = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
            
            # First, find the inventory file in the Inventario folder
            file_id = self._find_inventory_file_id(access_token)
            
            if not file_id:
                self.logger.warning("Inventory file not found, returning empty structure")
                return self._create_empty_inventory()
            
            # Download file content
            content_bytes = get_file_content_by_ids(drive_id, file_id, access_token)
            
            if content_bytes:
                content = content_bytes.decode('utf-8')
                inventory = json.loads(content)
                self._cached_inventory = inventory
                self._cache_timestamp = datetime.now()
                self.logger.info(f"Successfully loaded inventory with {len(inventory.get('accounts', {}))} accounts")
                return inventory
            else:
                self.logger.warning("Could not download inventory file content")
                return self._create_empty_inventory()
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in inventory file: {e}")
            return self._create_empty_inventory()
        except Exception as e:
            self.logger.error(f"Error reading inventory file: {e}")
            return self._create_empty_inventory()
    
    def write_inventory(self, inventory: Dict[str, Any], access_token: str) -> bool:
        """
        Write the inventory file to SharePoint
        
        Args:
            inventory: Complete inventory structure to write
            access_token: OAuth access token
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Import existing STP upload functionality (reuse for inventory)
            from modules.stp.stp_files import upload_to_sharepoint
            
            # Update last_updated timestamp
            inventory['last_updated'] = datetime.now().isoformat()
            inventory['version'] = inventory.get('version', '1.0')
            
            # Convert to JSON bytes
            content = json.dumps(inventory, indent=2, ensure_ascii=False)
            content_bytes = content.encode('utf-8')
            
            self.logger.info(f"Writing inventory file with {len(inventory.get('accounts', {}))} accounts")
            
            # Create Inventario folder path if it doesn't exist and upload
            success = self._upload_to_inventario_folder(content_bytes, access_token)
            
            if success:
                # Update cache
                self._cached_inventory = inventory
                self._cache_timestamp = datetime.now()
                self.logger.info("Successfully wrote inventory file")
                return True
            else:
                self.logger.error("Failed to write inventory file to SharePoint")
                return False
                
        except Exception as e:
            self.logger.error(f"Error writing inventory file: {e}")
            return False
    
    def update_account_month(self, account_id: str, year: int, month: int, 
                           file_type: str, file_info: FileInfo, access_token: str) -> bool:
        """
        Update a specific account-month-file entry in the inventory
        
        Args:
            account_id: Account identifier (e.g., 'stp_sa')
            year: Year (e.g., 2024)
            month: Month (1-12)
            file_type: 'pdf' or 'xlsx'
            file_info: FileInfo object with file details
            access_token: OAuth access token
            
        Returns:
            bool: True if successful
        """
        try:
            inventory = self.read_inventory(access_token, force_refresh=True)
            
            # Ensure account exists
            if account_id not in inventory['accounts']:
                inventory['accounts'][account_id] = {}
            
            # Create month key
            month_key = f"{year}-{month:02d}"
            
            # Ensure month exists
            if month_key not in inventory['accounts'][account_id]:
                inventory['accounts'][account_id][month_key] = {}
            
            # Update file info
            inventory['accounts'][account_id][month_key][file_type] = asdict(file_info)
            
            self.logger.info(f"Updated inventory: {account_id} {month_key} {file_type}")
            
            return self.write_inventory(inventory, access_token)
            
        except Exception as e:
            self.logger.error(f"Error updating account month: {e}")
            return False
    
    def update_account_inventory(self, account_id: str, account_data: Dict[str, Any], 
                               access_token: str) -> bool:
        """
        Update entire account inventory with new data
        
        Args:
            account_id: Account identifier
            account_data: Complete account data structure
            access_token: OAuth access token
            
        Returns:
            bool: True if successful
        """
        try:
            inventory = self.read_inventory(access_token, force_refresh=True)
            
            # Update account section
            inventory['accounts'][account_id] = account_data
            
            self.logger.info(f"Updated complete inventory for account: {account_id}")
            
            return self.write_inventory(inventory, access_token)
            
        except Exception as e:
            self.logger.error(f"Error updating account inventory: {e}")
            return False
    
    def get_account_months(self, account_id: str, year: int, access_token: str) -> Dict[str, MonthInfo]:
        """
        Get month information for a specific account and year
        
        Args:
            account_id: Account identifier
            year: Year to retrieve
            access_token: OAuth access token
            
        Returns:
            Dict of month_key -> MonthInfo objects
        """
        try:
            inventory = self.read_inventory(access_token)
            account_data = inventory.get('accounts', {}).get(account_id, {})
            
            months = {}
            for month in range(1, 13):
                month_key = f"{year}-{month:02d}"
                month_data = account_data.get(month_key, {})
                
                # Convert dict data back to FileInfo objects
                pdf_data = month_data.get('pdf')
                xlsx_data = month_data.get('xlsx')
                
                pdf_info = FileInfo(**pdf_data) if pdf_data else None
                xlsx_info = FileInfo(**xlsx_data) if xlsx_data else None
                
                months[month_key] = MonthInfo(pdf=pdf_info, xlsx=xlsx_info)
            
            return months
            
        except Exception as e:
            self.logger.error(f"Error getting account months: {e}")
            return {}
    
    def clear_cache(self):
        """Clear the cached inventory"""
        self._cached_inventory = None
        self._cache_timestamp = None
        self.logger.debug("Inventory cache cleared")
    
    def _create_empty_inventory(self) -> Dict[str, Any]:
        """Create an empty inventory structure"""
        return {
            "last_updated": datetime.now().isoformat(),
            "version": "1.0",
            "accounts": {}
        }
    
    def validate_inventory_structure(self, inventory: Dict[str, Any]) -> List[str]:
        """
        Validate inventory structure and return list of issues
        
        Args:
            inventory: Inventory dictionary to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []
        
        # Check required top-level keys
        required_keys = ['last_updated', 'version', 'accounts']
        for key in required_keys:
            if key not in inventory:
                issues.append(f"Missing required key: {key}")
        
        # Validate accounts structure
        accounts = inventory.get('accounts', {})
        if not isinstance(accounts, dict):
            issues.append("'accounts' must be a dictionary")
            return issues
        
        # Validate each account
        for account_id, account_data in accounts.items():
            if not isinstance(account_data, dict):
                issues.append(f"Account {account_id} data must be a dictionary")
                continue
            
            # Validate month entries
            for month_key, month_data in account_data.items():
                if not isinstance(month_data, dict):
                    issues.append(f"Month data {account_id}:{month_key} must be a dictionary")
                    continue
                
                # Validate file entries
                for file_type, file_data in month_data.items():
                    if file_type not in ['pdf', 'xlsx']:
                        issues.append(f"Invalid file type {file_type} in {account_id}:{month_key}")
                        continue
                    
                    if not isinstance(file_data, dict):
                        issues.append(f"File data must be dictionary: {account_id}:{month_key}:{file_type}")
                        continue
                    
                    # Validate required file fields
                    required_file_fields = ['exists', 'parse_status', 'transaction_count']
                    for field in required_file_fields:
                        if field not in file_data:
                            issues.append(f"Missing field {field} in {account_id}:{month_key}:{file_type}")
        
        return issues
    
    def _find_inventory_file_id(self, access_token: str) -> Optional[str]:
        """Find the inventory file ID in SharePoint Inventario folder"""
        try:
            import requests
            headers = {'Authorization': f'Bearer {access_token}'}
            drive_id = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
            bancos_folder_id = "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"
            
            # Navigate: 04 Bancos → Estados de Cuenta → Inventario
            # Get Estados de Cuenta folder
            bancos_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{bancos_folder_id}/children"
            bancos_response = requests.get(bancos_url, headers=headers)
            
            if bancos_response.status_code != 200:
                return None
            
            bancos_items = bancos_response.json().get('value', [])
            estados_folder = next((item for item in bancos_items if item.get('folder') and 'estado' in item.get('name', '').lower()), None)
            
            if not estados_folder:
                return None
            
            # Look for Inventario folder in Estados de Cuenta
            estados_id = estados_folder.get('id')
            estados_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{estados_id}/children"
            estados_response = requests.get(estados_url, headers=headers)
            
            if estados_response.status_code != 200:
                return None
            
            estados_items = estados_response.json().get('value', [])
            inventario_folder = next((item for item in estados_items if item.get('folder') and 'inventario' in item.get('name', '').lower()), None)
            
            if not inventario_folder:
                self.logger.warning("Inventario folder not found")
                return None
            
            # Look for inventory file in Inventario folder
            inventario_id = inventario_folder.get('id')
            inventario_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{inventario_id}/children"
            inventario_response = requests.get(inventario_url, headers=headers)
            
            if inventario_response.status_code != 200:
                return None
            
            inventario_items = inventario_response.json().get('value', [])
            inventory_file = next((item for item in inventario_items if not item.get('folder') and item.get('name') == self.inventory_file_path), None)
            
            if inventory_file:
                return inventory_file.get('id')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding inventory file: {e}")
            return None
    
    def _upload_to_inventario_folder(self, file_content: bytes, access_token: str) -> bool:
        """Upload inventory file to SharePoint Inventario folder"""
        try:
            import requests
            headers = {'Authorization': f'Bearer {access_token}'}
            drive_id = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
            bancos_folder_id = "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"
            
            # Navigate: 04 Bancos → Estados de Cuenta → Inventario (create if needed)
            inventario_folder_id = self._ensure_inventario_folder_exists(access_token)
            
            if not inventario_folder_id:
                self.logger.error("Could not find or create Inventario folder")
                return False
            
            # Upload file to Inventario folder
            upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{inventario_folder_id}:/{self.inventory_file_path}:/content"
            
            upload_headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            upload_response = requests.put(upload_url, headers=upload_headers, data=file_content)
            
            if upload_response.status_code in [200, 201]:
                self.logger.info(f"Inventory file uploaded successfully")
                return True
            else:
                self.logger.error(f"Upload failed: {upload_response.status_code} - {upload_response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error uploading inventory file: {e}")
            return False
    
    def _ensure_inventario_folder_exists(self, access_token: str) -> Optional[str]:
        """Ensure Inventario folder exists in Estados de Cuenta, create if needed"""
        try:
            import requests
            headers = {'Authorization': f'Bearer {access_token}'}
            drive_id = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
            bancos_folder_id = "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"
            
            # Get Estados de Cuenta folder
            bancos_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{bancos_folder_id}/children"
            bancos_response = requests.get(bancos_url, headers=headers)
            
            if bancos_response.status_code != 200:
                return None
            
            bancos_items = bancos_response.json().get('value', [])
            estados_folder = next((item for item in bancos_items if item.get('folder') and 'estado' in item.get('name', '').lower()), None)
            
            if not estados_folder:
                return None
            
            estados_id = estados_folder.get('id')
            
            # Check if Inventario folder already exists
            estados_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{estados_id}/children"
            estados_response = requests.get(estados_url, headers=headers)
            
            if estados_response.status_code == 200:
                estados_items = estados_response.json().get('value', [])
                inventario_folder = next((item for item in estados_items if item.get('folder') and 'inventario' in item.get('name', '').lower()), None)
                
                if inventario_folder:
                    return inventario_folder.get('id')
            
            # Create Inventario folder if it doesn't exist
            create_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{estados_id}/children"
            
            folder_data = {
                "name": "Inventario",
                "folder": {},
                "@microsoft.graph.conflictBehavior": "replace"
            }
            
            create_response = requests.post(create_url, headers=headers, json=folder_data)
            
            if create_response.status_code in [200, 201]:
                new_folder = create_response.json()
                self.logger.info("Created Inventario folder")
                return new_folder.get('id')
            else:
                self.logger.error(f"Failed to create Inventario folder: {create_response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error ensuring Inventario folder exists: {e}")
            return None