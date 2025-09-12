# modules/bbva/bbva_batch.py
"""
BBVA Batch Processing Engine

Handles batch processing of BBVA PDF files with transaction extraction.
Mirrors the STP system architecture for consistency and reliability.
"""

import os
import logging
import tempfile
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from .bbva_files import get_bbva_files
from .bbva_parser import BBVAParser
from .bbva_database import (
    get_bbva_database, update_bbva_database,
    get_bbva_parse_tracking_data, update_bbva_parse_tracking_data,
    remove_file_transactions, synchronize_database_with_files,
    cleanup_tracking_data
)
from .bbva_config import get_account_by_clabe
from ..stp.stp_files import get_file_content_by_ids

logger = logging.getLogger(__name__)

# ============================================================================
# CORE BATCH PROCESSING FUNCTIONS
# ============================================================================

def process_bbva_account(account_clabe: str, access_token: str, progress_callback=None) -> Dict[str, Any]:
    """
    Process all PDF files for a BBVA account with database synchronization
    
    Args:
        account_clabe: BBVA account CLABE number
        access_token: Microsoft Graph API access token
        progress_callback: Function to call with progress updates
        
    Returns:
        Dictionary with processing results and statistics
    """
    try:
        # Validate account
        account_info = get_account_by_clabe(account_clabe)
        if not account_info:
            raise ValueError(f"Invalid BBVA account CLABE: {account_clabe}")
        
        logger.info(f"Starting BBVA batch processing for account {account_info['name']} ({account_clabe})")
        
        # Initialize progress tracking
        progress = {
            'status': 'initializing',
            'current_file': None,
            'files_processed': 0,
            'files_checked': 0,
            'files_skipped': 0,
            'total_files': 0,
            'transactions_added': 0,
            'orphaned_transactions_removed': 0,
            'errors': [],
            'details': 'Starting BBVA parse process...',
            'progress_percentage': 5,
            'account_clabe': account_clabe,
            'account_type': account_info['name']
        }
        
        if progress_callback:
            progress_callback(progress)
        
        time.sleep(0.5)
        
        # PHASE 1: Get all current PDF files from SharePoint
        progress['status'] = 'fetching_files'
        progress['details'] = 'Retrieving current PDF files from SharePoint...'
        progress['progress_percentage'] = 10
        
        if progress_callback:
            progress_callback(progress)
        
        all_files = get_bbva_files(account_clabe, access_token)
        pdf_files = [f for f in all_files if f.get('filename', '').lower().endswith('.pdf')]
        
        progress['total_files'] = len(pdf_files)
        progress['files_checked'] = len(pdf_files)
        progress['details'] = f'Found {len(pdf_files)} PDF files'
        
        logger.info(f"Found {len(pdf_files)} PDF files for account {account_clabe}")
        
        if progress_callback:
            progress_callback(progress)
        
        # PHASE 2: Database Synchronization
        progress['status'] = 'synchronizing_database'
        progress['details'] = 'Synchronizing database with current files...'
        progress['progress_percentage'] = 15
        
        if progress_callback:
            progress_callback(progress)
        
        # Load existing database
        database = get_bbva_database(account_clabe, access_token)
        
        # Synchronize database with current files (removes orphaned transactions)
        original_transaction_count = len(database['transactions'])
        database = synchronize_database_with_files(database, all_files, account_clabe)
        new_transaction_count = len(database['transactions'])
        orphaned_removed = original_transaction_count - new_transaction_count
        
        progress['orphaned_transactions_removed'] = orphaned_removed
        if orphaned_removed > 0:
            progress['details'] = f'Removed {orphaned_removed} orphaned transactions from deleted files'
            logger.info(f"Removed {orphaned_removed} orphaned transactions during synchronization")
        else:
            progress['details'] = 'Database synchronized - no orphaned transactions found'
        
        if progress_callback:
            progress_callback(progress)
        
        time.sleep(0.5)
        
        # PHASE 3: Check which files need parsing
        progress['status'] = 'checking_files'
        progress['details'] = f'Checking {len(pdf_files)} files for updates...'
        progress['progress_percentage'] = 20
        
        if progress_callback:
            progress_callback(progress)
        
        tracking_data = get_bbva_parse_tracking_data(access_token)
        
        # Clean up tracking data (remove references to deleted files)
        tracking_data = cleanup_tracking_data(tracking_data, all_files, account_clabe)
        
        # Check which files need parsing
        files_to_parse = check_bbva_file_parsing_status(pdf_files, tracking_data, account_clabe)
        
        progress['total_files'] = len(files_to_parse)
        progress['files_skipped'] = len(pdf_files) - len(files_to_parse)
        
        logger.info(f"Files to parse: {len(files_to_parse)}, Files to skip: {progress['files_skipped']}")
        
        if not files_to_parse:
            progress['status'] = 'completed'
            progress['details'] = f'All {len(pdf_files)} files are already up to date'
            progress['progress_percentage'] = 100
            
            if progress_callback:
                progress_callback(progress)
            
            # Save synchronized database even if no files to parse
            update_bbva_database(account_clabe, database, access_token)
            update_bbva_parse_tracking_data(tracking_data, access_token)
            
            return {
                'success': True,
                'message': f'All {len(pdf_files)} files are already up to date',
                'files_processed': 0,
                'files_checked': len(pdf_files),
                'files_skipped': len(pdf_files),
                'transactions_added': 0,
                'orphaned_transactions_removed': orphaned_removed,
                'account_clabe': account_clabe,
                'account_type': account_info['name']
            }
        
        # PHASE 4: Initialize tracking for this account if not exists
        if account_clabe not in tracking_data:
            tracking_data[account_clabe] = {}
        
        files_processed = 0
        total_transactions_added = 0
        processing_errors = []
        
        # Initialize BBVA parser
        bbva_parser = BBVAParser()
        
        # PHASE 5: Process each PDF file that needs parsing
        progress['status'] = 'processing_files'
        
        for idx, file_info in enumerate(files_to_parse):
            try:
                filename = file_info['filename']
                drive_id = file_info['drive_id']
                file_id = file_info['file_id']
                
                # Update progress
                progress['current_file'] = filename
                progress['details'] = f'Processing {filename} ({idx + 1}/{len(files_to_parse)})'
                progress['progress_percentage'] = 25 + int((idx / len(files_to_parse)) * 60)
                
                if progress_callback:
                    progress_callback(progress)
                
                logger.info(f"Processing BBVA file {filename}")
                
                # Download PDF file content
                progress['details'] = f'Downloading {filename}...'
                if progress_callback:
                    progress_callback(progress)
                
                time.sleep(0.2)
                
                file_content = get_file_content_by_ids(drive_id, file_id, access_token)
                
                if not file_content:
                    error_msg = f"Failed to download {filename}"
                    processing_errors.append(error_msg)
                    progress['errors'].append(error_msg)
                    logger.error(error_msg)
                    continue
                
                # Remove old transactions from this file (if any)
                progress['details'] = f'Updating transactions from {filename}...'
                if progress_callback:
                    progress_callback(progress)
                
                database = remove_file_transactions(database, filename)
                
                # Parse PDF file using existing BBVAParser
                progress['details'] = f'Parsing {filename}...'
                if progress_callback:
                    progress_callback(progress)
                
                time.sleep(0.2)
                
                try:
                    # Save PDF to temporary file for parsing
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                        temp_file.write(file_content)
                        temp_path = temp_file.name
                    
                    try:
                        # Parse PDF using existing BBVAParser
                        parsed_result = bbva_parser.parse_pdf(temp_path)
                        
                        if parsed_result.get('success'):
                            transactions = parsed_result.get('transactions', [])
                            
                            if transactions:
                                # ✅ FIX: Override file_source with real filename
                                for transaction in transactions:
                                    transaction['file_source'] = filename  # Use REAL filename
                                
                                # Add new transactions
                                database['transactions'].extend(transactions)
                                total_transactions_added += len(transactions)
                                progress['transactions_added'] = total_transactions_added
                                
                                # Sort transactions by date (newest first)
                                database['transactions'].sort(
                                    key=lambda x: x.get('date') or '1900-01-01',
                                    reverse=True
                                )
                                
                                logger.info(f"Added {len(transactions)} transactions from {filename}")
                            else:
                                logger.warning(f"No transactions found in {filename}")
                            
                            # Update tracking
                            tracking_data[account_clabe][filename] = {
                                'last_parsed': datetime.now().isoformat(),
                                'file_last_modified': file_info.get('last_modified_formatted'),
                                'transaction_count': len(transactions),
                                'parse_status': 'success'
                            }
                            
                            files_processed += 1
                            progress['files_processed'] = files_processed
                            
                        else:
                            error_msg = f"Failed to parse {filename}: {parsed_result.get('error', 'Unknown error')}"
                            processing_errors.append(error_msg)
                            progress['errors'].append(error_msg)
                            logger.error(error_msg)
                            
                            # Track failed parse
                            tracking_data[account_clabe][filename] = {
                                'last_parsed': datetime.now().isoformat(),
                                'file_last_modified': file_info.get('last_modified_formatted'),
                                'transaction_count': 0,
                                'parse_status': 'failed',
                                'error': parsed_result.get('error', 'Unknown error')
                            }
                    
                    finally:
                        # Clean up temporary file
                        try:
                            os.unlink(temp_path)
                        except Exception as cleanup_error:
                            logger.warning(f"Failed to clean up temp file: {cleanup_error}")
                
                except Exception as parse_error:
                    error_msg = f"Failed to parse {filename}: {str(parse_error)}"
                    processing_errors.append(error_msg)
                    progress['errors'].append(error_msg)
                    logger.error(error_msg)
                    
                    # Track failed parse
                    tracking_data[account_clabe][filename] = {
                        'last_parsed': datetime.now().isoformat(),
                        'file_last_modified': file_info.get('last_modified_formatted'),
                        'transaction_count': 0,
                        'parse_status': 'failed',
                        'error': str(parse_error)
                    }
                    continue
                    
            except Exception as file_error:
                error_msg = f"Error processing file {file_info.get('filename', 'unknown')}: {str(file_error)}"
                processing_errors.append(error_msg)
                progress['errors'].append(error_msg)
                logger.error(error_msg)
                continue
        
        # PHASE 6: Update database metadata and save
        progress['status'] = 'saving_database'
        progress['details'] = 'Saving synchronized data to database...'
        progress['progress_percentage'] = 95
        
        if progress_callback:
            progress_callback(progress)
        
        database['metadata']['files_parsed'] = len([f for f in tracking_data.get(account_clabe, {}).values() 
                                                   if f.get('transaction_count', 0) > 0])
        
        time.sleep(0.5)
        
        # Save updated database and tracking
        database_saved = update_bbva_database(account_clabe, database, access_token)
        tracking_saved = update_bbva_parse_tracking_data(tracking_data, access_token)
        
        if not database_saved or not tracking_saved:
            error_msg = 'Failed to save synchronized data'
            progress['status'] = 'error'
            progress['details'] = error_msg
            
            if progress_callback:
                progress_callback(progress)
            
            raise Exception(error_msg)
        
        # Mark as completed
        progress['status'] = 'completed'
        if orphaned_removed > 0:
            progress['details'] = f'Successfully processed {files_processed} files with {total_transactions_added} transactions. Removed {orphaned_removed} orphaned transactions.'
        else:
            progress['details'] = f'Successfully processed {files_processed} files with {total_transactions_added} transactions'
        progress['progress_percentage'] = 100
        progress['current_file'] = None
        
        if progress_callback:
            progress_callback(progress)
        
        # Prepare response
        result = {
            'success': True,
            'message': f'Successfully processed {files_processed} files',
            'files_processed': files_processed,
            'files_checked': len(pdf_files),
            'files_skipped': progress['files_skipped'],
            'transactions_added': total_transactions_added,
            'orphaned_transactions_removed': orphaned_removed,
            'total_transactions': database['metadata']['total_transactions'],
            'files_to_parse': len(files_to_parse),
            'errors': processing_errors,
            'account_clabe': account_clabe,
            'account_type': account_info['name']
        }
        
        logger.info(f"BBVA parse complete for account {account_clabe}: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"BBVA parse process error for account {account_clabe}: {e}")
        raise

# Fix for bbva_batch.py - Add time tolerance to prevent false re-parsing

def check_bbva_file_parsing_status(account_files: List[Dict[str, Any]], 
                                 tracking_data: Dict[str, Any], 
                                 account_clabe: str) -> List[Dict[str, Any]]:
    """
    Identify BBVA PDF files that need parsing with time tolerance
    
    FIXED: Add tolerance for minor timestamp differences to prevent
    false positives from SharePoint auto-processing
    """
    files_to_parse = []
    account_tracking = tracking_data.get(account_clabe, {})
    
    logger.info(f"Checking parsing status for {len(account_files)} BBVA files")
    logger.info(f"Account tracking has {len(account_tracking)} tracked files: {list(account_tracking.keys())}")
    
    for file_info in account_files:
        filename = file_info.get('filename')
        if not filename:
            logger.warning(f"File info missing filename: {file_info}")
            continue
            
        if not filename.lower().endswith('.pdf'):
            logger.info(f"Skipping non-PDF file: {filename}")
            continue
        
        file_last_modified = file_info.get('last_modified_formatted')
        tracked_info = account_tracking.get(filename, {})
        tracked_last_parsed = tracked_info.get('last_parsed')
        parse_status = tracked_info.get('parse_status')
        
        logger.info(f"Checking BBVA file: {filename}")
        logger.info(f"  File last modified: {file_last_modified}")
        logger.info(f"  Last parsed: {tracked_last_parsed}")
        logger.info(f"  Parse status: {parse_status}")
        
        # Parse if file is new, modified, or previously failed
        needs_parsing = False
        reason = ""
        
        if not tracked_info:
            needs_parsing = True
            reason = "new file"
        elif parse_status == 'failed':
            needs_parsing = True
            reason = "previous parse failed"
        elif file_last_modified and tracked_last_parsed:
            # ✅ FIX: Add time tolerance for timestamp comparison
            try:
                from datetime import datetime, timedelta
                
                # Parse timestamps
                file_time = datetime.fromisoformat(file_last_modified.replace('Z', '+00:00'))
                parsed_time = datetime.fromisoformat(tracked_last_parsed.replace('Z', '+00:00'))
                
                # ✅ KEY FIX: Add 2-hour tolerance for SharePoint timestamp variations
                TOLERANCE_HOURS = 2
                tolerance = timedelta(hours=TOLERANCE_HOURS)
                
                # Only consider file "modified" if change is significant
                if file_time > (parsed_time + tolerance):
                    needs_parsing = True
                    reason = f"file modified significantly since last parse (>{TOLERANCE_HOURS}h)"
                    logger.info(f"  -> File time: {file_time}, Parsed time: {parsed_time}, Difference: {file_time - parsed_time}")
                else:
                    # File time is within tolerance - consider it unchanged
                    logger.info(f"  -> File time within tolerance ({file_time - parsed_time} < {tolerance})")
                    
            except Exception as e:
                logger.warning(f"Error comparing dates for {filename}: {e}")
                # ✅ FIX: Default to NOT parsing on date comparison errors
                logger.info(f"  -> Skipping due to date comparison error (defaulting to no re-parse)")
        elif not tracked_last_parsed:
            needs_parsing = True
            reason = "never parsed"
        
        if needs_parsing:
            logger.info(f"  -> NEEDS PARSING ({reason})")
            files_to_parse.append(file_info)
        else:
            logger.info(f"  -> SKIP (up to date)")
    
    logger.info(f"Files to parse: {len(files_to_parse)} out of {len(account_files)}")
    return files_to_parse

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_bbva_parse_summary(account_clabe: str, access_token: str) -> Dict[str, Any]:
    """
    Get parsing summary for a BBVA account
    
    Args:
        account_clabe: BBVA account CLABE number
        access_token: Microsoft Graph API access token
        
    Returns:
        Dictionary with parsing summary
    """
    try:
        # Get account info
        account_info = get_account_by_clabe(account_clabe)
        if not account_info:
            raise ValueError(f"Invalid BBVA account CLABE: {account_clabe}")
        
        # Get database and tracking data
        database = get_bbva_database(account_clabe, access_token)
        tracking_data = get_bbva_parse_tracking_data(access_token)
        account_tracking = tracking_data.get(account_clabe, {})
        
        # Get current files
        all_files = get_bbva_files(account_clabe, access_token)
        pdf_files = [f for f in all_files if f.get('filename', '').lower().endswith('.pdf')]
        
        # Calculate statistics
        total_files = len(pdf_files)
        parsed_files = len([f for f in account_tracking.values() if f.get('transaction_count', 0) > 0])
        failed_files = len([f for f in account_tracking.values() if f.get('parse_status') == 'failed'])
        pending_files = total_files - len(account_tracking)
        
        return {
            'account_clabe': account_clabe,
            'account_type': account_info['name'],
            'total_files': total_files,
            'parsed_files': parsed_files,
            'failed_files': failed_files,
            'pending_files': pending_files,
            'total_transactions': database['metadata']['total_transactions'],
            'last_updated': database['metadata']['last_updated'],
            'files_parsed_metadata': database['metadata']['files_parsed']
        }
        
    except Exception as e:
        logger.error(f"Error getting BBVA parse summary: {e}")
        raise