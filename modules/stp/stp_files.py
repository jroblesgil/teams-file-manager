"""
STP Files Management Module

Handles file operations, SharePoint navigation, and file content retrieval.
"""

import logging
import re
import requests
from typing import List, Dict, Any, Optional
from modules.stp.stp_helpers import get_account_type, get_file_type, format_file_size, format_datetime, get_month_name

logger = logging.getLogger(__name__)


def get_stp_files(account_number: str, access_token: str, year: Optional[int] = None, month: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get STP files using Graph API navigation"""
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        drive_id = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
        bancos_folder_id = "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"
        
        # Navigate through folder hierarchy
        # 04 Bancos → Estados de Cuenta → STP → [Account Folder]
        
        # Get Estados de Cuenta folder
        bancos_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{bancos_folder_id}/children"
        bancos_response = requests.get(bancos_url, headers=headers)
        
        if bancos_response.status_code != 200:
            return []
        
        bancos_items = bancos_response.json().get('value', [])
        estados_folder = next((item for item in bancos_items if item.get('folder') and 'estado' in item.get('name', '').lower()), None)
        
        if not estados_folder:
            return []
        
        # Get STP folder
        estados_id = estados_folder.get('id')
        estados_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{estados_id}/children"
        estados_response = requests.get(estados_url, headers=headers)
        
        if estados_response.status_code != 200:
            return []
        
        estados_items = estados_response.json().get('value', [])
        stp_folder = next((item for item in estados_items if item.get('folder') and 'stp' in item.get('name', '').lower()), None)
        
        if not stp_folder:
            return []
        
        # Get account-specific folder
        account_folder_map = {
            '646180559700000009': 'STP SA New',
            '646180403000000004': 'STP IP',
            '646990403000000003': 'STP IP'
        }
        
        target_folder_name = account_folder_map.get(account_number)
        if not target_folder_name:
            return []
        
        stp_id = stp_folder.get('id')
        stp_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{stp_id}/children"
        stp_response = requests.get(stp_url, headers=headers)
        
        if stp_response.status_code != 200:
            return []
        
        stp_items = stp_response.json().get('value', [])
        account_folder = next((item for item in stp_items if item.get('folder') and item.get('name') == target_folder_name), None)
        
        if not account_folder:
            return []
        
        # Get files from account folder
        account_id = account_folder.get('id')
        files_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{account_id}/children"
        files_response = requests.get(files_url, headers=headers)
        
        if files_response.status_code != 200:
            return []
        
        files = files_response.json().get('value', [])
        
        # Filter and process STP files
        stp_files = []
        pattern = rf"ec-{account_number}-(\d{{4}})(\d{{2}})\.(.+)$"
        
        for file in files:
            if file.get('folder'):
                continue
                
            filename = file.get('name', '')
            match = re.match(pattern, filename)
            
            if match:
                file_year = match.group(1)
                file_month = match.group(2)
                extension = match.group(3).lower()
                
                # Apply filters
                if year and file_year != str(year):
                    continue
                if month and file_month != f"{month:02d}":
                    continue
                if extension not in ['pdf', 'xlsx']:
                    continue
                
                file_data = {
                    'filename': filename,
                    'account': account_number,
                    'account_type': get_account_type(account_number),
                    'month': file_month,
                    'year': file_year,
                    'date_string': f"{file_year}-{file_month}",
                    'extension': extension,
                    'file_type': get_file_type(extension),
                    'drive_id': drive_id,
                    'file_id': file.get('id'),
                    'download_url': f"/download/{drive_id}/{file.get('id')}",
                    'web_url': file.get('webUrl'),
                    'size': file.get('size', 0),
                    'size_formatted': format_file_size(file.get('size', 0)),
                    'last_modified_formatted': format_datetime(file.get('lastModifiedDateTime'))
                }
                stp_files.append(file_data)
        
        # Sort by year-month descending (newest first)
        stp_files.sort(key=lambda x: f"{x['year']}{x['month']}", reverse=True)
        return stp_files
        
    except Exception as e:
        logger.error(f"Error getting STP files for account {account_number}: {e}")
        return []


def create_stp_calendar_data(access_token: str, year: int = 2025) -> Dict[str, Any]:
    """Create comprehensive STP calendar data"""

    # FIXED: Use OrderedDict or maintain specific order
    from collections import OrderedDict
     
    accounts = OrderedDict([
        ('646180559700000009', 'STP SA'),           # First tab
        ('646180403000000004', 'STP IP - PD'),      # Second tab  
        ('646990403000000003', 'STP IP - PI')       # Third tab
    ])
     
    calendar_data = OrderedDict()  # Use OrderedDict to preserve order
    
    for account_number, account_type in accounts.items():
        files = get_stp_files(account_number, access_token, year=year)
        
        # Organize by month
        months_data = {}
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            months_data[month_key] = {
                'pdf': None,
                'xlsx': None,
                'status': 'missing',
                'month_name': get_month_name(month),
                'month_num': month
            }
        
        # Add found files to months
        for file in files:
            month_key = f"{file['year']}-{file['month']}"
            if month_key in months_data:
                months_data[month_key][file['extension']] = file
        
        # Update status for each month
        for month_key, month_data in months_data.items():
            if month_data['pdf'] and month_data['xlsx']:
                month_data['status'] = 'complete'
            elif month_data['pdf'] or month_data['xlsx']:
                month_data['status'] = 'partial'
            else:
                month_data['status'] = 'missing'
        
        calendar_data[account_number] = {
            'account_type': account_type,
            'months': months_data,
            'total_files': len(files)
        }
    
    return calendar_data


def get_file_content_by_ids(drive_id: str, file_id: str, access_token: str) -> Optional[bytes]:
    """Download file content using drive_id and file_id"""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get download URL
        file_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}"
        response = requests.get(file_url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to get file info: {response.status_code}")
            return None
        
        file_info = response.json()
        download_url = file_info.get('@microsoft.graph.downloadUrl')
        
        if not download_url:
            logger.error("No download URL found")
            return None
        
        # Download file content
        download_response = requests.get(download_url, timeout=60)
        download_response.raise_for_status()
        
        return download_response.content
        
    except Exception as e:
        logger.error(f"Error downloading file content: {e}")
        return None


def upload_to_sharepoint(filename: str, file_content: bytes, target_folder: str, access_token: str) -> bool:
    """Upload file to specific SharePoint folder"""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Your SharePoint structure
        drive_id = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
        bancos_folder_id = "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"
        
        # Navigate to target folder (same logic as get_stp_files)
        # 04 Bancos → Estados de Cuenta → STP → [target_folder]
        
        # Get Estados de Cuenta folder
        bancos_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{bancos_folder_id}/children"
        bancos_response = requests.get(bancos_url, headers=headers)
        
        if bancos_response.status_code != 200:
            logger.error(f"Failed to access Bancos folder: {bancos_response.status_code}")
            return False
        
        bancos_items = bancos_response.json().get('value', [])
        estados_folder = next((item for item in bancos_items if item.get('folder') and 'estado' in item.get('name', '').lower()), None)
        
        if not estados_folder:
            logger.error("Estados de Cuenta folder not found")
            return False
        
        # Get STP folder
        estados_id = estados_folder.get('id')
        estados_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{estados_id}/children"
        estados_response = requests.get(estados_url, headers=headers)
        
        if estados_response.status_code != 200:
            logger.error(f"Failed to access Estados folder: {estados_response.status_code}")
            return False
        
        estados_items = estados_response.json().get('value', [])
        stp_folder = next((item for item in estados_items if item.get('folder') and 'stp' in item.get('name', '').lower()), None)
        
        if not stp_folder:
            logger.error("STP folder not found")
            return False
        
        # Get target account folder
        stp_id = stp_folder.get('id')
        stp_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{stp_id}/children"
        stp_response = requests.get(stp_url, headers=headers)
        
        if stp_response.status_code != 200:
            logger.error(f"Failed to access STP folder: {stp_response.status_code}")
            return False
        
        stp_items = stp_response.json().get('value', [])
        target_account_folder = next((item for item in stp_items if item.get('folder') and item.get('name') == target_folder), None)
        
        if not target_account_folder:
            logger.error(f"Target folder '{target_folder}' not found")
            return False
        
        # Upload file to target folder
        target_folder_id = target_account_folder.get('id')
        upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{target_folder_id}:/{filename}:/content"
        
        upload_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/octet-stream'
        }
        
        upload_response = requests.put(upload_url, headers=upload_headers, data=file_content)
        
        if upload_response.status_code in [200, 201]:
            logger.info(f"File {filename} uploaded successfully to {target_folder}")
            return True
        else:
            logger.error(f"Upload failed: {upload_response.status_code} - {upload_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"SharePoint upload error: {str(e)}")
        return False