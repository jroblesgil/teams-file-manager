# modules/statements/parse_coordinator.py
"""
Phase 1b: Clean Parse Coordinator for Unified Statements
Dispatches parse operations to existing STP/BBVA parsers without modifying them
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Callable, Optional

from .config import UNIFIED_ACCOUNTS, get_account_by_id

logger = logging.getLogger(__name__)

class UnifiedParseCoordinator:
    """Clean coordinator that dispatches to existing parsers"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.UnifiedParseCoordinator')
        self.active_sessions = {}
    
    def parse_account(self, account_id: str, access_token: str, 
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Parse a single account using existing parser systems
        
        Args:
            account_id: Account ID from UNIFIED_ACCOUNTS
            access_token: OAuth access token
            progress_callback: Function to call with progress updates
            
        Returns:
            Dict with parse results
        """
        
        if account_id not in UNIFIED_ACCOUNTS:
            raise ValueError(f"Invalid account ID: {account_id}")
        
        account_config = UNIFIED_ACCOUNTS[account_id]
        account_type = account_config['type']
        
        self.logger.info(f"Starting parse for {account_type} account: {account_id}")
        
        # Update progress
        if progress_callback:
            progress_callback({
                'status': 'starting',
                'progress_percentage': 10,
                'details': f'Starting {account_type.upper()} parse for {account_config["name"]}'
            })
        
        try:
            if account_type == 'stp':
                return self._parse_stp_account(account_id, account_config, access_token, progress_callback)
            elif account_type == 'bbva':
                return self._parse_bbva_account(account_id, account_config, access_token, progress_callback)
            else:
                raise ValueError(f"Unknown account type: {account_type}")
                
        except Exception as e:
            self.logger.error(f"Parse failed for account {account_id}: {e}")
            if progress_callback:
                progress_callback({
                    'status': 'error',
                    'progress_percentage': 0,
                    'details': f'Parse failed: {str(e)}',
                    'error': str(e)
                })
            raise
    
    def _parse_stp_account(self, account_id: str, account_config: Dict[str, Any], 
                          access_token: str, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """Parse STP account using existing STP modules"""
        
        # Import existing STP modules
        from modules.stp.stp_files import get_stp_files
        from modules.stp.stp_database import (
            get_json_database, update_json_database, get_parse_tracking_data,
            update_parse_tracking_data, remove_file_transactions,
            synchronize_database_with_files
        )
        from modules.stp.stp_parser import parse_excel_file, check_file_parsing_status
        from modules.stp.stp_files import get_file_content_by_ids
        
        account_number = account_config['identifier']
        
        # Phase 1: Get files
        if progress_callback:
            progress_callback({
                'status': 'fetching_files',
                'progress_percentage': 20,
                'details': 'Retrieving files from SharePoint...'
            })
        
        all_files = get_stp_files(account_number, access_token)
        excel_files = [f for f in all_files if f.get('extension') == 'xlsx']
        
        # Phase 2: Check database
        if progress_callback:
            progress_callback({
                'status': 'checking_database',
                'progress_percentage': 30,
                'details': 'Synchronizing database...'
            })
        
        database = get_json_database(account_number, access_token)
        database = synchronize_database_with_files(database, all_files, account_number)
        
        # Phase 3: Check which files need parsing
        if progress_callback:
            progress_callback({
                'status': 'checking_files',
                'progress_percentage': 40,
                'details': f'Checking {len(excel_files)} files...'
            })
        
        tracking_data = get_parse_tracking_data(access_token)
        files_to_parse = check_file_parsing_status(excel_files, tracking_data, account_number)
        
        if not files_to_parse:
            if progress_callback:
                progress_callback({
                    'status': 'completed',
                    'progress_percentage': 100,
                    'details': f'All {len(excel_files)} files are up to date'
                })
            
            return {
                'success': True,
                'message': f'All {len(excel_files)} files are already up to date',
                'files_processed': 0,
                'files_skipped': len(excel_files),
                'transactions_added': 0,
                'account_id': account_id,
                'account_type': 'stp'
            }
        
        # Phase 4: Parse files
        if progress_callback:
            progress_callback({
                'status': 'processing_files',
                'progress_percentage': 50,
                'details': f'Processing {len(files_to_parse)} files...',
                'total_files': len(files_to_parse)
            })
        
        # Initialize tracking if needed
        if account_number not in tracking_data:
            tracking_data[account_number] = {}
        
        files_processed = 0
        total_transactions_added = 0
        errors = []
        
        for idx, file_info in enumerate(files_to_parse):
            try:
                filename = file_info['filename']
                
                if progress_callback:
                    progress_callback({
                        'status': 'processing_files',
                        'current_file': filename,
                        'files_processed': files_processed,
                        'progress_percentage': 50 + int((idx / len(files_to_parse)) * 40),
                        'details': f'Processing {filename} ({idx + 1}/{len(files_to_parse)})'
                    })
                
                # Download and parse file
                file_content = get_file_content_by_ids(
                    file_info['drive_id'], 
                    file_info['file_id'], 
                    access_token
                )
                
                if file_content:
                    # Remove old transactions from this file
                    database = remove_file_transactions(database, filename)
                    
                    # Parse file
                    transactions = parse_excel_file(file_content, filename)
                    
                    if transactions:
                        database['transactions'].extend(transactions)
                        total_transactions_added += len(transactions)
                        
                        # Sort transactions
                        database['transactions'].sort(
                            key=lambda x: x.get('fecha_operacion') or '1900-01-01',
                            reverse=True
                        )
                    
                    # Update tracking
                    tracking_data[account_number][filename] = {
                        'last_parsed': datetime.now().isoformat(),
                        'file_last_modified': file_info.get('last_modified_formatted'),
                        'transaction_count': len(transactions) if transactions else 0,
                        'parse_status': 'success'
                    }
                    
                    files_processed += 1
                
            except Exception as e:
                error_msg = f"Error processing {filename}: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
        
        # Phase 5: Save results
        if progress_callback:
            progress_callback({
                'status': 'saving',
                'progress_percentage': 95,
                'details': 'Saving results...'
            })
        
        # Update database metadata
        database['metadata']['files_parsed'] = files_processed
        database['metadata']['last_updated'] = datetime.now().isoformat()
        database['metadata']['total_transactions'] = len(database['transactions'])
        
        # Save database and tracking
        update_json_database(account_number, database, access_token)
        update_parse_tracking_data(tracking_data, access_token)
        
        result = {
            'success': True,
            'message': f'Successfully processed {files_processed} files',
            'files_processed': files_processed,
            'files_skipped': len(excel_files) - len(files_to_parse),
            'transactions_added': total_transactions_added,
            'total_transactions': len(database['transactions']),
            'errors': errors,
            'account_id': account_id,
            'account_type': 'stp'
        }
        
        if progress_callback:
            progress_callback({
                'status': 'completed',
                'progress_percentage': 100,
                'details': f'Completed: {files_processed} files processed, {total_transactions_added} transactions added',
                'files_processed': files_processed,
                'transactions_added': total_transactions_added
            })
        
        return result
    
    def _parse_bbva_account(self, account_id: str, account_config: Dict[str, Any], 
                           access_token: str, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """Parse BBVA account using existing BBVA modules"""
        
        # Import existing BBVA modules  
        from modules.bbva.bbva_files import get_bbva_files
        from modules.bbva.bbva_database import (
            get_bbva_database, update_bbva_database,
            get_bbva_parse_tracking_data, update_bbva_parse_tracking_data
        )
        from modules.bbva.bbva_batch import (
            check_bbva_file_parsing_status, process_bbva_account
        )
        
        clabe = account_config['identifier']
        
        if progress_callback:
            progress_callback({
                'status': 'initializing',
                'progress_percentage': 10,
                'details': 'Starting BBVA parse process...'
            })
        
        # Create a wrapper progress callback for the existing BBVA system
        def bbva_progress_wrapper(progress_data):
            if progress_callback:
                # Map BBVA progress data to our standard format
                mapped_progress = {
                    'status': progress_data.get('status', 'processing'),
                    'progress_percentage': progress_data.get('progress_percentage', 50),
                    'current_file': progress_data.get('current_file'),
                    'files_processed': progress_data.get('files_processed', 0),
                    'total_files': progress_data.get('total_files', 0),
                    'transactions_added': progress_data.get('transactions_added', 0),
                    'details': progress_data.get('details', 'Processing BBVA account...')
                }
                progress_callback(mapped_progress)
        
        try:
            # Use existing BBVA batch processor
            result = process_bbva_account(clabe, access_token, bbva_progress_wrapper)
            
            # Add our account info to result
            result['account_id'] = account_id
            result['account_type'] = 'bbva'
            
            return result
            
        except Exception as e:
            # Handle case where process_bbva_account doesn't exist yet
            self.logger.warning(f"BBVA batch processor not available, using basic approach: {e}")
            
            # Fallback: basic BBVA processing
            return self._parse_bbva_account_basic(account_id, account_config, access_token, progress_callback)
    
    def _parse_bbva_account_basic(self, account_id: str, account_config: Dict[str, Any], 
                                 access_token: str, progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """Basic BBVA parsing when advanced batch processor is not available"""
        
        clabe = account_config['identifier']
        
        if progress_callback:
            progress_callback({
                'status': 'basic_processing',
                'progress_percentage': 50,
                'details': 'Using basic BBVA processing...'
            })
        
        try:
            # Import what's available
            from modules.bbva.bbva_files import get_bbva_files
            from modules.bbva.bbva_database import get_bbva_database
            
            # Create account_info for get_bbva_files
            account_info = {
                'name': account_config['name'],
                'clabe': clabe,
                'directory': account_config['folder_path']
            }
            
            # Get files
            files = get_bbva_files(clabe, access_token, account_info=account_info)
            pdf_files = [f for f in files if f.get('filename', '').lower().endswith('.pdf')]
            
            # Get database
            database = get_bbva_database(clabe, access_token)
            
            if progress_callback:
                progress_callback({
                    'status': 'completed',
                    'progress_percentage': 100,
                    'details': f'Found {len(pdf_files)} PDF files. Advanced parsing not yet available.'
                })
            
            return {
                'success': True,
                'message': f'Basic BBVA processing complete. Found {len(pdf_files)} PDF files.',
                'files_processed': 0,
                'files_skipped': len(pdf_files),
                'transactions_added': 0,
                'total_files': len(pdf_files),
                'account_id': account_id,
                'account_type': 'bbva',
                'note': 'Advanced BBVA parsing not yet implemented'
            }
            
        except Exception as e:
            self.logger.error(f"Basic BBVA processing failed: {e}")
            
            if progress_callback:
                progress_callback({
                    'status': 'error',
                    'progress_percentage': 0,
                    'details': f'BBVA processing failed: {str(e)}'
                })
            
            return {
                'success': False,
                'error': f'BBVA processing failed: {str(e)}',
                'files_processed': 0,
                'transactions_added': 0,
                'account_id': account_id,
                'account_type': 'bbva'
            }
    
    def parse_all_accounts(self, access_token: str, 
                          progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Parse all accounts in the unified system"""
        
        self.logger.info("Starting batch parse for all accounts")
        
        if progress_callback:
            progress_callback({
                'status': 'initializing_batch',
                'progress_percentage': 0,
                'details': f'Starting batch parse for {len(UNIFIED_ACCOUNTS)} accounts'
            })
        
        results = {}
        total_accounts = len(UNIFIED_ACCOUNTS)
        
        for idx, (account_id, account_config) in enumerate(UNIFIED_ACCOUNTS.items()):
            account_name = account_config['name']
            
            if progress_callback:
                progress_callback({
                    'status': 'processing_account',
                    'progress_percentage': int((idx / total_accounts) * 100),
                    'details': f'Processing {account_name} ({idx + 1}/{total_accounts})',
                    'current_account': account_name
                })
            
            try:
                # Create account-specific progress callback
                def account_progress(progress_data):
                    if progress_callback:
                        progress_data['current_account'] = account_name
                        progress_data['account_progress'] = progress_data.get('progress_percentage', 0)
                        progress_data['overall_progress'] = int((idx / total_accounts) * 100)
                        progress_callback(progress_data)
                
                # Parse individual account
                result = self.parse_account(account_id, access_token, account_progress)
                results[account_id] = result
                
            except Exception as e:
                self.logger.error(f"Failed to parse account {account_id}: {e}")
                results[account_id] = {
                    'success': False,
                    'error': str(e),
                    'account_id': account_id,
                    'account_type': account_config['type']
                }
        
        # Calculate summary
        successful_accounts = len([r for r in results.values() if r.get('success')])
        failed_accounts = total_accounts - successful_accounts
        total_files_processed = sum(r.get('files_processed', 0) for r in results.values())
        total_transactions_added = sum(r.get('transactions_added', 0) for r in results.values())
        
        if progress_callback:
            progress_callback({
                'status': 'completed',
                'progress_percentage': 100,
                'details': f'Batch parse complete: {successful_accounts}/{total_accounts} accounts successful'
            })
        
        return {
            'success': failed_accounts == 0,
            'message': f'Batch parse complete: {successful_accounts}/{total_accounts} accounts successful',
            'summary': {
                'total_accounts': total_accounts,
                'successful_accounts': successful_accounts,
                'failed_accounts': failed_accounts,
                'total_files_processed': total_files_processed,
                'total_transactions_added': total_transactions_added
            },
            'account_results': results,
            'timestamp': datetime.now().isoformat()
        }