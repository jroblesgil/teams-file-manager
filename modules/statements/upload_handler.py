# modules/statements/upload_handler.py
"""
Phase 1b: Clean Upload Handler for Unified Statements
Auto-detects file types and routes to appropriate existing upload systems
"""

import re
import logging
import tempfile
import os
from typing import Dict, Any, Union
from werkzeug.datastructures import FileStorage

from .config import UNIFIED_ACCOUNTS, get_account_by_identifier

logger = logging.getLogger(__name__)

class UnifiedUploadHandler:
    """Clean upload handler with auto-detection"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.UnifiedUploadHandler')
    
    def process_upload(self, file: FileStorage, access_token: str) -> Dict[str, Any]:
        """
        Process file upload with auto-detection
        
        Args:
            file: Uploaded file
            access_token: OAuth access token
            
        Returns:
            Dict with upload result
        """
        
        if not file or not file.filename:
            return {
                'success': False,
                'error': 'No file provided',
                'filename': 'unknown'
            }
        
        filename = file.filename
        self.logger.info(f"Processing upload: {filename}")
        
        # Step 1: Detect file type and validate
        detection_result = self._detect_file_type(filename)
        
        if not detection_result['success']:
            return {
                'success': False,
                'error': detection_result['error'],
                'filename': filename,
                'detection': detection_result
            }
        
        file_info = detection_result['file_info']
        self.logger.info(f"Detected {file_info['type']} file for account {file_info['account_id']}")
        
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
                'filename': filename,
                'details': str(e)
            }
    
    def _detect_file_type(self, filename: str) -> Dict[str, Any]:
        """
        Detect file type and extract metadata from filename
        
        Returns:
            Dict with success, file_info or error
        """
        
        # Get file extension
        if '.' not in filename:
            return {
                'success': False,
                'error': 'File must have an extension'
            }
        
        extension = filename.split('.')[-1].lower()
        
        # STP files: ec-[account]-YYYYMM.ext
        stp_pattern = r'^ec-(\d{18})-(\d{4})(\d{2})\.(pdf|xlsx|xls)$'
        stp_match = re.match(stp_pattern, filename)
        
        if stp_match:
            account_number = stp_match.group(1)
            year = stp_match.group(2)
            month = stp_match.group(3)
            file_ext = stp_match.group(4)
            
            # Find account configuration
            account_id, account_config = get_account_by_identifier(account_number)
            
            if not account_config or account_config['type'] != 'stp':
                return {
                    'success': False,
                    'error': f'Unknown STP account number: {account_number}'
                }
            
            # Validate month
            month_num = int(month)
            if month_num < 1 or month_num > 12:
                return {
                    'success': False,
                    'error': f'Invalid month: {month}. Must be 01-12'
                }
            
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
                    'expected_filename': filename  # STP uses exact filename format
                }
            }
        
        # BBVA files: YYMM [AccountName] BBVA [Currency].pdf
        # Also support auto-detection from PDF content
        bbva_pattern = r'^(\d{4})\s+(.+?)\.pdf$'
        bbva_match = re.match(bbva_pattern, filename)
        
        if bbva_match or extension == 'pdf':
            if bbva_match:
                yymm = bbva_match.group(1)
                account_part = bbva_match.group(2).strip()
                
                # Find matching BBVA account by name pattern
                matching_account = None
                for account_id, account_config in UNIFIED_ACCOUNTS.items():
                    if account_config['type'] == 'bbva':
                        account_name = account_config['name']
                        # Check if account name parts are in filename
                        if any(part.lower() in account_part.lower() for part in account_name.split()):
                            matching_account = (account_id, account_config)
                            break
                
                if matching_account:
                    account_id, account_config = matching_account
                    return {
                        'success': True,
                        'file_info': {
                            'type': 'bbva',
                            'account_id': account_id,
                            'clabe': account_config['identifier'],
                            'account_name': account_config['name'],
                            'year': '20' + yymm[:2],  # Convert YY to YYYY
                            'month': yymm[2:],
                            'extension': 'pdf',
                            'folder_path': account_config['folder_path'],
                            'auto_detected': False,
                            'filename_pattern': 'standard'
                        }
                    }
            
            # If pattern doesn't match but it's a PDF, try auto-detection
            if extension == 'pdf':
                return {
                    'success': True,
                    'file_info': {
                        'type': 'bbva',
                        'account_id': 'auto_detect',
                        'clabe': 'auto_detect',
                        'account_name': 'Auto-detect from PDF content',
                        'year': 'auto_detect',
                        'month': 'auto_detect',
                        'extension': 'pdf',
                        'folder_path': 'auto_detect',
                        'auto_detected': True,
                        'filename_pattern': 'auto_detect'
                    }
                }
        
        # No pattern matched
        return {
            'success': False,
            'error': (
                'Unsupported file format. Expected:\n'
                '• STP: ec-[account]-YYYYMM.xlsx/pdf\n'
                '• BBVA: YYMM [AccountName].pdf or any PDF for auto-detection'
            )
        }
    
    def _handle_stp_upload(self, file: FileStorage, file_info: Dict[str, Any], 
                          access_token: str) -> Dict[str, Any]:
        """Handle STP file upload using existing modules"""
        
        try:
            # Import existing STP upload functionality
            from modules.stp.stp_files import upload_to_sharepoint
            
            # Read file content
            file_content = file.read()
            file.seek(0)  # Reset for potential future reads
            
            if not file_content:
                return {
                    'success': False,
                    'error': 'File is empty',
                    'filename': file.filename
                }
            
            # Upload to SharePoint using existing function
            success = upload_to_sharepoint(
                filename=file_info['expected_filename'],
                file_content=file_content,
                target_folder=file_info['folder_name'],
                access_token=access_token
            )
            
            if success:
                # Clear cache to refresh data
                self._clear_cache_if_available()
                
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
                    'filename': file.filename,
                    'details': 'Check SharePoint permissions and network connectivity'
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
        """Handle BBVA file upload using existing modules"""
        
        try:
            filename = file.filename
            
            # If auto-detection is needed, analyze PDF content
            if file_info.get('auto_detected'):
                detection_result = self._detect_bbva_from_content(file)
                
                if not detection_result['success']:
                    return {
                        'success': False,
                        'error': detection_result['error'],
                        'filename': filename,
                        'details': 'Could not auto-detect BBVA account from PDF content'
                    }
                
                # Update file_info with detected information
                file_info.update(detection_result['detected_info'])
            
            # Try to use existing BBVA upload functionality if available
            try:
                from modules.bbva.bbva_upload import upload_bbva_to_sharepoint
                
                # Read file content
                file_content = file.read()
                file.seek(0)
                
                success = upload_bbva_to_sharepoint(
                    filename=filename,
                    file_content=file_content,
                    clabe=file_info['clabe'],
                    access_token=access_token
                )
                
                if success:
                    # Clear cache to refresh data
                    self._clear_cache_if_available()
                    
                    return {
                        'success': True,
                        'message': f'Successfully uploaded to {file_info["account_name"]}',
                        'filename': filename,
                        'account_name': file_info['account_name'],
                        'account_type': 'BBVA',
                        'clabe': file_info['clabe'],
                        'auto_detected': file_info.get('auto_detected', False)
                    }
                else:
                    return {
                        'success': False,
                        'error': 'BBVA SharePoint upload failed',
                        'filename': filename
                    }
                    
            except ImportError:
                # BBVA upload module not available yet - return validation success
                self.logger.warning("BBVA upload module not available, returning validation-only result")
                
                return {
                    'success': True,
                    'message': f'BBVA file validated successfully for {file_info["account_name"]}',
                    'filename': filename,
                    'account_name': file_info['account_name'],
                    'account_type': 'BBVA',
                    'clabe': file_info.get('clabe', 'auto_detect'),
                    'auto_detected': file_info.get('auto_detected', False),
                    'note': 'File validated but upload functionality not yet available'
                }
                
        except Exception as e:
            self.logger.error(f"BBVA upload error: {e}")
            return {
                'success': False,
                'error': f'BBVA upload failed: {str(e)}',
                'filename': file.filename
            }
    
    def _detect_bbva_from_content(self, file: FileStorage) -> Dict[str, Any]:
        """
        Detect BBVA account information from PDF content
        This would use the existing BBVA parser's PDF info extraction
        """
        
        try:
            # Save file temporarily for PDF analysis
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name
            
            file.seek(0)  # Reset file pointer
            
            try:
                # Use existing BBVA parser for PDF info extraction
                from modules.bbva.bbva_parser import BBVAParser
                
                parser = BBVAParser()
                
                # Use PDF analysis to extract account info
                with open(temp_path, 'rb') as f:
                    import pdfplumber
                    with pdfplumber.open(f) as pdf:
                        # Use existing _extract_pdf_info method if available
                        if hasattr(parser, '_extract_pdf_info'):
                            pdf_info = parser._extract_pdf_info(pdf)
                            
                            clabe = pdf_info.get('clabe')
                            if clabe:
                                # Find account by CLABE
                                account_id, account_config = get_account_by_identifier(clabe)
                                
                                if account_config and account_config['type'] == 'bbva':
                                    return {
                                        'success': True,
                                        'detected_info': {
                                            'account_id': account_id,
                                            'clabe': clabe,
                                            'account_name': account_config['name'],
                                            'folder_path': account_config['folder_path'],
                                            'year': pdf_info.get('period_year', 'unknown'),
                                            'auto_detected': True
                                        }
                                    }
                
                return {
                    'success': False,
                    'error': 'Could not extract CLABE from PDF or CLABE not recognized'
                }
                
            except ImportError:
                return {
                    'success': False,
                    'error': 'BBVA PDF analysis not available - upload any PDF to BBVA folder manually'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'PDF analysis failed: {str(e)}'
            }
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def _clear_cache_if_available(self):
        """Clear performance cache if available"""
        try:
            from modules.shared.performance_cache import unified_cache
            unified_cache.cache.clear()
            self.logger.info("Cache cleared after upload")
        except ImportError:
            self.logger.debug("Performance cache not available")
    
    def validate_file_format(self, filename: str) -> Dict[str, Any]:
        """
        Validate file format without processing upload
        Useful for frontend validation
        """
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
                'pattern': 'YYMM [AccountName].pdf or any PDF for auto-detection',
                'example': '2501 FSA BBVA MXN.pdf',
                'extensions': ['pdf'],
                'description': 'BBVA PDF bank statements with auto-detection support'
            }
        }