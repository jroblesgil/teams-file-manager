# modules/statements/upload_handler.py - FIXED VERSION WITH INVENTORY REFRESH
"""
Phase 1b: Clean Upload Handler for Unified Statements
Auto-detects file types, uploads to correct locations, and updates calendar
FIXED: Now includes immediate inventory refresh after upload
"""

import re
import logging
import tempfile
import os
import requests
from typing import Dict, Any, Optional
from werkzeug.datastructures import FileStorage

from .config import UNIFIED_ACCOUNTS, get_account_by_identifier

logger = logging.getLogger(__name__)

class UnifiedUploadHandler:
    """Clean upload handler with auto-detection and calendar updates"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.UnifiedUploadHandler')
    
    def process_upload(self, file: FileStorage, access_token: str) -> Dict[str, Any]:
        """Process file upload with auto-detection"""
        
        if not file or not file.filename:
            return {'success': False, 'error': 'No file provided', 'filename': 'unknown'}
        
        filename = file.filename
        self.logger.info(f"Processing upload: {filename}")
        
        # Step 1: Detect file type and validate
        detection_result = self._detect_file_type(filename)
        
        if not detection_result['success']:
            return {
                'success': False,
                'error': detection_result['error'],
                'filename': filename
            }
        
        file_info = detection_result['file_info']
        self.logger.info(f"Detected {file_info['type']} file for account {file_info.get('account_id', 'auto_detect')}")
        
        try:
            # Step 2: Route to appropriate upload handler
            if file_info['type'] == 'stp':
                return self._handle_stp_upload(file, file_info, access_token)
            elif file_info['type'] == 'bbva':
                return self._handle_bbva_upload(file, file_info, access_token)
            else:
                return {
                    'success': False,
                    'error': f"Unsupported file type: {file_info['type']}",
                    'filename': filename
                }
                
        except Exception as e:
            self.logger.error(f"Upload processing failed for {filename}: {e}")
            return {
                'success': False,
                'error': f'Upload processing failed: {str(e)}',
                'filename': filename
            }
    
    def _detect_file_type(self, filename: str) -> Dict[str, Any]:
        """Detect file type and extract metadata from filename"""
        
        if '.' not in filename:
            return {'success': False, 'error': 'File must have an extension'}
        
        extension = filename.split('.')[-1].lower()
        
        # STP files: ec-[account]-YYYYMM.ext
        stp_pattern = r'^ec-(\d{18})-(\d{4})(\d{2})\.(pdf|xlsx|xls)$'
        stp_match = re.match(stp_pattern, filename)
        
        if stp_match:
            account_number = stp_match.group(1)
            year = stp_match.group(2)
            month = stp_match.group(3)
            file_ext = stp_match.group(4)
            
            account_id, account_config = get_account_by_identifier(account_number)
            
            if not account_config or account_config['type'] != 'stp':
                return {'success': False, 'error': f'Unknown STP account number: {account_number}'}
            
            # Validate month
            month_num = int(month)
            if month_num < 1 or month_num > 12:
                return {'success': False, 'error': f'Invalid month: {month}. Must be 01-12'}
            
            return {
                'success': True,
                'file_info': {
                    'type': 'stp',
                    'account_id': account_id,
                    'account_number': account_number,
                    'account_name': account_config['name'],
                    'year': year,
                    'month': month,
                    'extension': file_ext,
                    'folder_name': account_config['folder_name'],
                    'expected_filename': filename
                }
            }
        
        # BBVA files: Any PDF for auto-detection
        if extension == 'pdf':
            return {
                'success': True,
                'file_info': {
                    'type': 'bbva',
                    'account_id': 'auto_detect',
                    'extension': 'pdf',
                    'auto_detected': True
                }
            }
        
        return {
            'success': False,
            'error': (
                'Unsupported file format. Expected:\n'
                '• STP: ec-[account]-YYYYMM.xlsx/pdf\n'
                '• BBVA: Any PDF file for auto-detection'
            )
        }
    
    def _handle_stp_upload(self, file: FileStorage, file_info: Dict[str, Any], 
                          access_token: str) -> Dict[str, Any]:
        """Handle STP file upload using existing modules"""
        
        try:
            from modules.stp.stp_files import upload_to_sharepoint
            
            file_content = file.read()
            file.seek(0)
            
            if not file_content:
                return {'success': False, 'error': 'File is empty', 'filename': file.filename}
            
            # Upload to SharePoint
            success = upload_to_sharepoint(
                filename=file_info['expected_filename'],
                file_content=file_content,
                target_folder=file_info['folder_name'],
                access_token=access_token
            )
            
            if success:
                # FIXED: Clear cache and update calendar with access_token
                self._clear_cache_and_update_calendar(file_info['account_id'], access_token)
                
                return {
                    'success': True,
                    'message': f'Successfully uploaded to {file_info["account_name"]}',
                    'filename': file.filename,
                    'account_name': file_info['account_name'],
                    'account_type': 'STP',
                    'target_folder': file_info['folder_name'],
                    'year': file_info['year'],
                    'month': file_info['month']
                }
            else:
                return {
                    'success': False,
                    'error': 'SharePoint upload failed',
                    'filename': file.filename
                }
                
        except Exception as e:
            self.logger.error(f"STP upload error: {e}")
            return {
                'success': False,
                'error': f'STP upload failed: {str(e)}',
                'filename': file.filename
            }
    
    def _handle_bbva_upload(self, file: FileStorage, file_info: Dict[str, Any], 
                           access_token: str) -> Dict[str, Any]:
        """Handle BBVA file upload with auto-detection"""
        
        filename = file.filename
        
        try:
            # Step 1: Auto-detect account from PDF content
            if file_info.get('auto_detected'):
                detection_result = self._detect_bbva_from_content(file)
                
                if not detection_result['success']:
                    return {
                        'success': False,
                        'error': detection_result['error'],
                        'filename': filename
                    }
                
                file_info.update(detection_result['detected_info'])
            
            # Step 2: Read file content
            file_content = file.read()
            file.seek(0)
            
            if not file_content:
                return {'success': False, 'error': 'File is empty', 'filename': filename}
            
            # Step 3: Upload to SharePoint using navigation method
            upload_result = self._upload_bbva_to_sharepoint(
                filename=filename,
                file_content=file_content,
                folder_path=file_info['folder_path'],
                access_token=access_token
            )
            
            if upload_result['success']:
                # FIXED: Clear cache and update calendar with access_token
                self._clear_cache_and_update_calendar(file_info['account_id'], access_token)
                
                return {
                    'success': True,
                    'message': f'Successfully uploaded to {file_info["account_name"]}',
                    'filename': filename,
                    'account_name': file_info['account_name'],
                    'account_type': 'BBVA',
                    'clabe': file_info['clabe'],
                    'folder_path': file_info['folder_path'],
                    'auto_detected': file_info.get('auto_detected', False)
                }
            else:
                return {
                    'success': False,
                    'error': f'SharePoint upload failed: {upload_result["error"]}',
                    'filename': filename
                }
                
        except Exception as e:
            self.logger.error(f"BBVA upload error: {e}")
            return {
                'success': False,
                'error': f'BBVA upload failed: {str(e)}',
                'filename': filename
            }
    
    def _detect_bbva_from_content(self, file: FileStorage) -> Dict[str, Any]:
        """Auto-detect BBVA account from PDF content using existing BBVAParser"""
        
        try:
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name
            
            file.seek(0)
            
            try:
                # Use existing BBVAParser
                from modules.bbva.bbva_parser import BBVAParser
                import pdfplumber
                
                parser = BBVAParser()
                
                # Extract PDF info
                with pdfplumber.open(temp_path) as pdf:
                    pdf_info = parser._extract_pdf_info(pdf)
                
                clabe = pdf_info.get('clabe')
                
                if not clabe:
                    return {
                        'success': False,
                        'error': 'Could not extract CLABE from PDF content'
                    }
                
                # Find account by CLABE
                account_id, account_config = get_account_by_identifier(clabe)
                
                if not account_config or account_config['type'] != 'bbva':
                    return {
                        'success': False,
                        'error': f'CLABE {clabe} not found in BBVA configuration'
                    }
                
                return {
                    'success': True,
                    'detected_info': {
                        'account_id': account_id,
                        'clabe': clabe,
                        'account_name': account_config['name'],
                        'folder_path': account_config['folder_path'],
                        'auto_detected': True
                    }
                }
                
            except ImportError:
                return {
                    'success': False,
                    'error': 'BBVAParser not available - ensure pdfplumber is installed'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'PDF analysis failed: {str(e)}'
            }
            
        finally:
            # Clean up temporary file
            try:
                if 'temp_path' in locals():
                    os.unlink(temp_path)
            except:
                pass
    
    def _upload_bbva_to_sharepoint(self, filename: str, file_content: bytes, 
                                  folder_path: str, access_token: str) -> Dict[str, Any]:
        """Upload BBVA file using navigation method (same as bbva_files.py)"""
        
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Same constants as bbva_files.py
            drive_id = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
            bancos_folder_id = "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"
            
            # Navigate to target folder using same method as read system
            estados_folder_id = self._get_estados_folder(bancos_folder_id, headers, drive_id)
            if not estados_folder_id:
                return {'success': False, 'error': 'Estados de Cuenta folder not found'}
            
            bbva_folder_id = self._get_bbva_folder(estados_folder_id, headers, drive_id)
            if not bbva_folder_id:
                return {'success': False, 'error': 'BBVA folder not found'}
            
            account_folder_id = self._get_account_folder(bbva_folder_id, folder_path, headers, drive_id)
            if not account_folder_id:
                return {'success': False, 'error': f'Account folder not found: {folder_path}'}
            
            # Upload file using folder ID
            upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{account_folder_id}:/{filename}:/content"
            
            upload_headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/pdf'
            }
            
            response = requests.put(upload_url, headers=upload_headers, data=file_content, timeout=30)
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                return {
                    'success': True,
                    'details': {
                        'file_id': response_data.get('id'),
                        'size': response_data.get('size'),
                        'web_url': response_data.get('webUrl')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text[:200]}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload exception: {str(e)}'
            }
    
    def _get_estados_folder(self, bancos_folder_id: str, headers: Dict, drive_id: str) -> Optional[str]:
        """Get Estados de Cuenta folder ID"""
        try:
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{bancos_folder_id}/children"
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                return None
            
            items = response.json().get('value', [])
            estados_folder = next(
                (item for item in items 
                 if item.get('folder') and 'estado' in item.get('name', '').lower()), 
                None
            )
            
            return estados_folder.get('id') if estados_folder else None
            
        except Exception:
            return None
    
    def _get_bbva_folder(self, estados_folder_id: str, headers: Dict, drive_id: str) -> Optional[str]:
        """Get BBVA folder ID"""
        try:
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{estados_folder_id}/children"
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                return None
            
            items = response.json().get('value', [])
            bbva_folder = next(
                (item for item in items 
                 if item.get('folder') and 'bbva' in item.get('name', '').lower()), 
                None
            )
            
            return bbva_folder.get('id') if bbva_folder else None
            
        except Exception:
            return None
    
    def _get_account_folder(self, bbva_folder_id: str, folder_path: str, headers: Dict, drive_id: str) -> Optional[str]:
        """Navigate to account-specific folder"""
        try:
            # Extract relative path
            if folder_path.startswith("Estados de Cuenta/BBVA/"):
                relative_path = folder_path[len("Estados de Cuenta/BBVA/"):]
            else:
                relative_path = folder_path
            
            # Navigate through folder structure
            current_folder_id = bbva_folder_id
            path_parts = relative_path.split('/')
            
            for path_part in path_parts:
                current_folder_id = self._find_subfolder(current_folder_id, path_part, headers, drive_id)
                if not current_folder_id:
                    return None
            
            return current_folder_id
            
        except Exception:
            return None
    
    def _find_subfolder(self, parent_folder_id: str, folder_name: str, headers: Dict, drive_id: str) -> Optional[str]:
        """Find specific subfolder"""
        try:
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_folder_id}/children"
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                return None
            
            items = response.json().get('value', [])
            target_folder = next(
                (item for item in items 
                 if item.get('folder') and item.get('name') == folder_name), 
                None
            )
            
            return target_folder.get('id') if target_folder else None
            
        except Exception:
            return None
    
    def _clear_cache_and_update_calendar(self, account_id: str, access_token: str):
        """FIXED: Clear cache and trigger inventory refresh after successful upload"""
        
        try:
            # Step 1: Clear inventory manager cache
            from .inventory_manager import InventoryManager
            inventory_manager = InventoryManager()
            inventory_manager.clear_cache()
            self.logger.info("Cleared inventory manager cache after upload")
            
            # Step 2: Trigger immediate inventory refresh for this account
            from .inventory_scanner import InventoryScanner
            scanner = InventoryScanner()
            
            self.logger.info(f"Triggering inventory refresh for {account_id} after upload")
            refresh_result = scanner.scan_single_account(account_id, access_token)
            
            if refresh_result.get('success'):
                self.logger.info(f"Successfully refreshed inventory for {account_id} - found {refresh_result.get('files_found', 0)} files")
            else:
                self.logger.warning(f"Failed to refresh inventory for {account_id}: {refresh_result.get('error')}")
                
        except Exception as e:
            self.logger.warning(f"Could not refresh inventory after upload: {e}")
        
        # Keep existing cache clearing code as fallback
        try:
            from modules.shared.performance_cache import unified_cache
            unified_cache.cache.clear()
            self.logger.info("Cleared performance cache after upload")
        except ImportError:
            pass
        
        try:
            # Clear inventory cache files for this account (legacy fallback)
            import glob
            
            cache_patterns = [
                f"*{account_id}*inventory*.json",
                f"*inventory*{account_id}*.json", 
                f"*inventory*.json",  # Clear all inventory files
            ]
            
            for pattern in cache_patterns:
                files = glob.glob(pattern)
                for file_path in files:
                    try:
                        os.remove(file_path)
                        self.logger.info(f"Removed inventory cache: {file_path}")
                    except:
                        pass
                        
        except Exception as e:
            self.logger.debug(f"Could not clear inventory files: {e}")
        
        self.logger.info(f"Cache cleared and inventory refreshed for account {account_id}")
    
    def validate_file_format(self, filename: str) -> Dict[str, Any]:
        """Validate file format without processing upload"""
        return self._detect_file_type(filename)
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """Get information about supported file formats"""
        return {
            'stp': {
                'pattern': 'ec-[account]-YYYYMM.xlsx/pdf',
                'example': 'ec-646180559700000009-202501.xlsx',
                'extensions': ['xlsx', 'pdf'],
                'description': 'STP Excel statements and PDF exports'
            },
            'bbva': {
                'pattern': 'Any PDF file for auto-detection',
                'example': '2508 FSA BBVA MXN.pdf',
                'extensions': ['pdf'],
                'description': 'BBVA PDF bank statements with auto-detection support'
            }
        }