"""
Teams File Manager - Main Flask Application

Modularized STP (Sistema de Transferencias y Pagos) file management system
for processing Excel files from Microsoft Teams/SharePoint.
"""

import os
import logging
import time
import threading
import json
import traceback
import io
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, flash, Response
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import custom modules
from modules.shared.azure_oauth import AzureOAuth
from modules.shared.teams_api import TeamsAPI
from modules.stp.stp_database import (
    get_json_database, update_json_database, get_parse_tracking_data, 
    update_parse_tracking_data, remove_file_transactions,
    synchronize_database_with_files, cleanup_tracking_data
)
from modules.stp.stp_parser import (
    parse_excel_file, check_file_parsing_status, convert_dd_mm_yyyy_to_yyyy_mm_dd
)
from modules.stp.stp_files import (
    get_stp_files, create_stp_calendar_data, get_file_content_by_ids, upload_to_sharepoint
)
from modules.stp.stp_analytics import (
    get_monthly_record_counts, apply_export_filters, create_formatted_excel
)
from modules.stp.stp_helpers import (
    get_account_type, validate_account_number, get_account_folder_mapping
)
from modules.bbva.bbva_files import get_bbva_files as get_bbva_files_module
from modules.bbva.bbva_config import BBVA_ACCOUNTS, get_account_by_clabe

from modules.shared.performance_cache import (
    create_stp_calendar_data_fast, create_bbva_calendar_data_fast,
    warm_cache_for_user, get_performance_stats, unified_cache
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Global dictionary to track parse progress (in production, use Redis or similar)
parse_progress = {}

# Azure configuration
AZURE_CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
AZURE_TENANT_ID = os.getenv('AZURE_TENANT_ID')
AZURE_CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
PORT = int(os.getenv('PORT', 5001))
REDIRECT_URI = f'http://localhost:{PORT}/callback'

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

from modules.bbva.bbva_database import (
    get_bbva_database, update_bbva_database,
    create_empty_bbva_database, get_database_filename,
    navigate_to_bbva_db_folder
)

# Initialize Azure OAuth
oauth = AzureOAuth(
    client_id=AZURE_CLIENT_ID,
    tenant_id=AZURE_TENANT_ID,
    redirect_uri=REDIRECT_URI,
    client_secret=AZURE_CLIENT_SECRET
)

# ============================================================================
# HELPER DECORATORS
# ============================================================================

def require_oauth(f):
    """Decorator to require OAuth authentication"""
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            return redirect(url_for('login'))  # Changed from 'index' to 'login'
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# ============================================================================
# BBVA BATCH PROCESSING ENDPOINTS
# ============================================================================

@app.route('/api/bbva/test-file-discovery/<account_clabe>')
@require_oauth
def test_bbva_file_discovery(account_clabe):
    """Test BBVA file discovery for specific account"""
    try:
        access_token = session['access_token']
        
        # Import BBVA functions
        from modules.bbva.bbva_files import get_bbva_files
        from modules.bbva.bbva_config import get_account_by_clabe
        
        # Validate account
        account_info = get_account_by_clabe(account_clabe)
        if not account_info:
            return jsonify({
                'error': 'Invalid BBVA account CLABE',
                'account_clabe': account_clabe
            }), 400
        
        # Get files for this account
        all_files = get_bbva_files(account_clabe, access_token)
        pdf_files = [f for f in all_files if f.get('filename', '').lower().endswith('.pdf')]
        
        return jsonify({
            'success': True,
            'message': 'BBVA file discovery test successful',
            'account_clabe': account_clabe,
            'account_type': account_info['name'],
            'total_files': len(all_files),
            'pdf_files': len(pdf_files),
            'file_list': [
                {
                    'filename': f.get('filename'),
                    'size': f.get('size'),
                    'last_modified': f.get('last_modified_formatted'),
                    'date_string': f.get('date_string')
                }
                for f in pdf_files[:10]  # Show first 10 files
            ],
            'folder_path': account_info.get('directory')
        })
        
    except Exception as e:
        logger.error(f"BBVA file discovery test error: {e}")
        return jsonify({
            'error': 'File discovery test failed',
            'details': str(e)
        }), 500


@app.route('/api/bbva/test-parse-status/<account_clabe>')
@require_oauth
def test_bbva_parse_status(account_clabe):
    """Test BBVA parse status checking for specific account"""
    try:
        access_token = session['access_token']
        
        # Import BBVA functions
        from modules.bbva.bbva_batch import check_bbva_file_parsing_status, get_bbva_parse_summary
        from modules.bbva.bbva_files import get_bbva_files
        from modules.bbva.bbva_database import get_bbva_parse_tracking_data
        from modules.bbva.bbva_config import get_account_by_clabe
        
        # Validate account
        account_info = get_account_by_clabe(account_clabe)
        if not account_info:
            return jsonify({
                'error': 'Invalid BBVA account CLABE',
                'account_clabe': account_clabe
            }), 400
        
        # Get files and tracking data
        all_files = get_bbva_files(account_clabe, access_token)
        pdf_files = [f for f in all_files if f.get('filename', '').lower().endswith('.pdf')]
        tracking_data = get_bbva_parse_tracking_data(access_token)
        
        # Check which files need parsing
        files_to_parse = check_bbva_file_parsing_status(pdf_files, tracking_data, account_clabe)
        
        # Get parse summary
        parse_summary = get_bbva_parse_summary(account_clabe, access_token)
        
        return jsonify({
            'success': True,
            'message': 'BBVA parse status test successful',
            'account_clabe': account_clabe,
            'account_type': account_info['name'],
            'total_pdf_files': len(pdf_files),
            'files_to_parse': len(files_to_parse),
            'files_up_to_date': len(pdf_files) - len(files_to_parse),
            'files_needing_parse': [
                {
                    'filename': f.get('filename'),
                    'last_modified': f.get('last_modified_formatted')
                }
                for f in files_to_parse[:5]  # Show first 5 files
            ],
            'parse_summary': parse_summary,
            'tracking_status': {
                'tracked_files': len(tracking_data.get(account_clabe, {})),
                'has_tracking_data': account_clabe in tracking_data
            }
        })
        
    except Exception as e:
        logger.error(f"BBVA parse status test error: {e}")
        return jsonify({
            'error': 'Parse status test failed',
            'details': str(e)
        }), 500


@app.route('/api/bbva/test-single-parse/<account_clabe>', methods=['POST'])
@require_oauth
def test_bbva_single_parse(account_clabe):
    """Test parsing a single BBVA PDF file"""
    try:
        access_token = session['access_token']
        
        # Import BBVA functions
        from modules.bbva.bbva_files import get_bbva_files
        from modules.bbva.bbva_batch import check_bbva_file_parsing_status
        from modules.bbva.bbva_database import get_bbva_parse_tracking_data
        from modules.bbva.bbva_config import get_account_by_clabe
        from modules.stp.stp_files import get_file_content_by_ids
        from modules.bbva.bbva_parser import BBVAParser
        
        # Validate account
        account_info = get_account_by_clabe(account_clabe)
        if not account_info:
            return jsonify({
                'error': 'Invalid BBVA account CLABE',
                'account_clabe': account_clabe
            }), 400
        
        # Get files that need parsing
        all_files = get_bbva_files(account_clabe, access_token)
        pdf_files = [f for f in all_files if f.get('filename', '').lower().endswith('.pdf')]
        tracking_data = get_bbva_parse_tracking_data(access_token)
        files_to_parse = check_bbva_file_parsing_status(pdf_files, tracking_data, account_clabe)
        
        if not files_to_parse:
            return jsonify({
                'success': True,
                'message': 'No files need parsing - all are up to date',
                'account_clabe': account_clabe,
                'total_files': len(pdf_files)
            })
        
        # Test with the first file that needs parsing
        test_file = files_to_parse[0]
        filename = test_file['filename']
        
        logger.info(f"Testing single BBVA parse for file: {filename}")
        
        # Download file content
        file_content = get_file_content_by_ids(
            test_file['drive_id'], 
            test_file['file_id'], 
            access_token
        )
        
        if not file_content:
            return jsonify({
                'error': 'Failed to download test file',
                'filename': filename
            }), 500
        
        # Parse the PDF
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        
        try:
            bbva_parser = BBVAParser()
            parsed_result = bbva_parser.parse_pdf(temp_path)
            
            # Clean up temp file
            os.unlink(temp_path)
            
            if parsed_result.get('success'):
                transactions = parsed_result.get('transactions', [])
                
                return jsonify({
                    'success': True,
                    'message': 'Single BBVA parse test successful',
                    'account_clabe': account_clabe,
                    'account_type': account_info['name'],
                    'test_file': {
                        'filename': filename,
                        'size': test_file.get('size'),
                        'last_modified': test_file.get('last_modified_formatted')
                    },
                    'parse_result': {
                        'transaction_count': len(transactions),
                        'file_source': parsed_result.get('pdf_info', {}).get('file_path', '').split('/')[-1],
                        'clabe_detected': parsed_result.get('pdf_info', {}).get('clabe'),
                        'period_detected': parsed_result.get('pdf_info', {}).get('period_text'),
                        'validation_status': parsed_result.get('validation', {})
                    },
                    'sample_transactions': transactions[:3] if transactions else [],  # Show first 3 transactions
                    'summary': parsed_result.get('summary', {})
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Single BBVA parse test failed',
                    'error': parsed_result.get('error'),
                    'filename': filename,
                    'account_clabe': account_clabe
                }), 500
        
        except Exception as parse_error:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
            
            raise parse_error
        
    except Exception as e:
        logger.error(f"BBVA single parse test error: {e}")
        return jsonify({
            'error': 'Single parse test failed',
            'details': str(e)
        }), 500


# Main BBVA batch processing endpoint
@app.route('/api/bbva/parse/<account_clabe>', methods=['POST'])
@require_oauth
def parse_bbva_account(account_clabe):
    """Parse all PDF files for a BBVA account with progress tracking"""
    try:
        access_token = session['access_token']
        
        # Import BBVA functions
        from modules.bbva.bbva_batch import process_bbva_account
        from modules.bbva.bbva_config import get_account_by_clabe
        
        # Validate account
        account_info = get_account_by_clabe(account_clabe)
        if not account_info:
            return jsonify({
                'error': f'Invalid BBVA account CLABE: {account_clabe}'
            }), 400
        
        # Generate a unique parse session ID
        parse_session_id = f"bbva_{account_clabe}_{datetime.now().timestamp()}"
        
        # Initialize progress tracking in global dictionary
        parse_progress[parse_session_id] = {
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
        
        logger.info(f"Starting BBVA parse process for account {account_clabe} (session: {parse_session_id})")
        
        def update_progress(progress_data):
            """Update progress in global dictionary"""
            parse_progress[parse_session_id].update(progress_data)
        
        # Run the batch processing with progress callback
        try:
            result = process_bbva_account(account_clabe, access_token, update_progress)
            
            # Update final progress
            parse_progress[parse_session_id].update({
                'status': 'completed',
                'progress_percentage': 100,
                'current_file': None,
                'details': result['message']
            })
            
            # Add session ID to result
            result['session_id'] = parse_session_id
            
            # Clean up progress after 5 minutes
            def cleanup_progress():
                time.sleep(300)
                if parse_session_id in parse_progress:
                    del parse_progress[parse_session_id]
            
            cleanup_thread = threading.Thread(target=cleanup_progress)
            cleanup_thread.daemon = True
            cleanup_thread.start()
            
            return jsonify(result)
            
        except Exception as process_error:
            # Update progress with error
            parse_progress[parse_session_id].update({
                'status': 'error',
                'details': str(process_error),
                'progress_percentage': 0
            })
            
            raise process_error
        
    except Exception as e:
        logger.error(f"BBVA parse process error for account {account_clabe}: {e}")
        
        return jsonify({
            'error': f'BBVA parse process failed: {str(e)}',
            'session_id': parse_session_id if 'parse_session_id' in locals() else None,
            'account_clabe': account_clabe,
            'files_processed': 0,
            'transactions_added': 0
        }), 500


@app.route('/api/bbva/parse-progress/<session_id>')
@require_oauth
def get_bbva_parse_progress(session_id):
    """Get current BBVA parse progress for a session"""
    if session_id not in parse_progress:
        return jsonify({'error': 'Invalid or expired session ID'}), 404
    
    progress_data = parse_progress[session_id].copy()
    progress_data['timestamp'] = datetime.now().isoformat()
    
    return jsonify(progress_data)


@app.route('/api/bbva/parse-summary/<account_clabe>')
@require_oauth
def get_bbva_parse_summary(account_clabe):
    """Get parsing summary for a BBVA account"""
    try:
        access_token = session['access_token']
        
        # Import BBVA functions
        from modules.bbva.bbva_batch import get_bbva_parse_summary
        
        summary = get_bbva_parse_summary(account_clabe, access_token)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Error getting BBVA parse summary: {e}")
        return jsonify({
            'error': 'Failed to get parse summary',
            'details': str(e)
        }), 500

# Add this route to your app.py

@app.route('/api/bbva/validate-amounts/<account_clabe>')
@require_oauth
def validate_bbva_amounts(account_clabe):
    """Validate BBVA database amounts against original PDFs"""
    try:
        access_token = session['access_token']
        
        # Import BBVA functions
        from modules.bbva.bbva_database import get_bbva_database
        from modules.bbva.bbva_files import get_bbva_files
        from modules.bbva.bbva_parser import BBVAParser
        from modules.bbva.bbva_config import get_account_by_clabe
        from modules.stp.stp_files import get_file_content_by_ids
        import tempfile
        import os
        
        # Validate account
        account_info = get_account_by_clabe(account_clabe)
        if not account_info:
            return jsonify({'error': f'Invalid BBVA account CLABE: {account_clabe}'}), 400
        
        # Load database
        database = get_bbva_database(account_clabe, access_token)
        transactions = database.get('transactions', [])
        
        if not transactions:
            return jsonify({'error': 'No transactions found in database'}), 404
        
        # Get PDF files
        all_files = get_bbva_files(account_clabe, access_token, account_info=account_info)
        pdf_files = [f for f in all_files if f.get('filename', '').lower().endswith('.pdf')]
        
        # Group database transactions by file
        db_by_file = {}
        for transaction in transactions:
            file_source = transaction.get('file_source', 'unknown')
            if file_source not in db_by_file:
                db_by_file[file_source] = []
            db_by_file[file_source].append(transaction)
        
        # Validation results
        validation_results = {
            'account_clabe': account_clabe,
            'account_type': account_info['name'],
            'total_files_in_db': len(db_by_file),
            'total_files_in_sharepoint': len(pdf_files),
            'total_transactions_in_db': len(transactions),
            'files': [],
            'overall_summary': {
                'files_validated': 0,
                'files_with_errors': 0,
                'total_cargo_db': 0,
                'total_abono_db': 0,
                'total_cargo_pdf': 0,
                'total_abono_pdf': 0
            }
        }
        
        parser = BBVAParser()
        
        # Validate each file
        for pdf_file in pdf_files:
            filename = pdf_file['filename']
            file_validation = {
                'filename': filename,
                'found_in_database': filename in db_by_file,
                'transactions_in_db': len(db_by_file.get(filename, [])),
                'validation': None
            }
            
            if filename in db_by_file:
                # Calculate DB totals for this file
                db_transactions = db_by_file[filename]
                db_cargo_total = sum(t.get('cargo', 0) for t in db_transactions)
                db_abono_total = sum(t.get('abono', 0) for t in db_transactions)
                
                try:
                    # Re-parse PDF to get validation totals
                    file_content = get_file_content_by_ids(
                        pdf_file['drive_id'], 
                        pdf_file['file_id'], 
                        access_token
                    )
                    
                    if file_content:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                            temp_file.write(file_content)
                            temp_path = temp_file.name
                        
                        try:
                            # Parse PDF to get validation data
                            parsed_result = parser.parse_pdf(temp_path)
                            
                            if parsed_result.get('success'):
                                pdf_summary = parsed_result.get('summary', {})
                                pdf_validation = parsed_result.get('validation', {})
                                
                                file_validation['validation'] = {
                                    'pdf_cargo_total': pdf_summary.get('total_cargos', 0),
                                    'pdf_abono_total': pdf_summary.get('total_abonos', 0),
                                    'db_cargo_total': db_cargo_total,
                                    'db_abono_total': db_abono_total,
                                    'cargo_match': abs(pdf_summary.get('total_cargos', 0) - db_cargo_total) < 0.01,
                                    'abono_match': abs(pdf_summary.get('total_abonos', 0) - db_abono_total) < 0.01,
                                    'cargo_difference': pdf_summary.get('total_cargos', 0) - db_cargo_total,
                                    'abono_difference': pdf_summary.get('total_abonos', 0) - db_abono_total,
                                    'pdf_validation': pdf_validation
                                }
                                
                                # Update overall summary
                                validation_results['overall_summary']['files_validated'] += 1
                                validation_results['overall_summary']['total_cargo_db'] += db_cargo_total
                                validation_results['overall_summary']['total_abono_db'] += db_abono_total
                                validation_results['overall_summary']['total_cargo_pdf'] += pdf_summary.get('total_cargos', 0)
                                validation_results['overall_summary']['total_abono_pdf'] += pdf_summary.get('total_abonos', 0)
                                
                                if not (file_validation['validation']['cargo_match'] and file_validation['validation']['abono_match']):
                                    validation_results['overall_summary']['files_with_errors'] += 1
                            else:
                                file_validation['validation'] = {'error': f"Failed to parse PDF: {parsed_result.get('error')}"}
                                validation_results['overall_summary']['files_with_errors'] += 1
                        
                        finally:
                            os.unlink(temp_path)
                    else:
                        file_validation['validation'] = {'error': 'Failed to download PDF content'}
                        validation_results['overall_summary']['files_with_errors'] += 1
                        
                except Exception as e:
                    file_validation['validation'] = {'error': f'Validation error: {str(e)}'}
                    validation_results['overall_summary']['files_with_errors'] += 1
            
            validation_results['files'].append(file_validation)
        
        # Calculate overall differences
        overall = validation_results['overall_summary']
        overall['cargo_total_difference'] = overall['total_cargo_pdf'] - overall['total_cargo_db']
        overall['abono_total_difference'] = overall['total_abono_pdf'] - overall['total_abono_db']
        overall['overall_match'] = (
            abs(overall['cargo_total_difference']) < 0.01 and 
            abs(overall['abono_total_difference']) < 0.01
        )
        
        return jsonify({
            'success': True,
            'validation_results': validation_results
        })
        
    except Exception as e:
        logger.error(f"Error validating BBVA amounts: {e}")
        return jsonify({
            'error': 'Validation failed',
            'details': str(e)
        }), 500

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
                
                # ✅ KEY FIX: Add 5-minute tolerance for SharePoint timestamp variations
                TOLERANCE_MINUTES = 5
                tolerance = timedelta(minutes=TOLERANCE_MINUTES)
                
                # Only consider file "modified" if change is significant
                if file_time > (parsed_time + tolerance):
                    needs_parsing = True
                    reason = f"file modified significantly since last parse (>{TOLERANCE_MINUTES}min)"
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

# Add this GET version to your app.py (easier to test in browser)

@app.route('/api/bbva/fix-tracking-get/<account_clabe>')
@require_oauth
def fix_bbva_tracking_get(account_clabe):
    """GET version of fix tracking for easier browser testing"""
    try:
        access_token = session['access_token']
        
        from modules.bbva.bbva_database import (
            get_bbva_parse_tracking_data, 
            update_bbva_parse_tracking_data,
            get_bbva_database
        )
        from modules.bbva.bbva_files import get_bbva_files
        from modules.bbva.bbva_config import get_account_by_clabe
        
        # Validate account
        account_info = get_account_by_clabe(account_clabe)
        if not account_info:
            return jsonify({'error': f'Invalid BBVA account CLABE: {account_clabe}'}), 400
        
        # Get current files and database
        all_files = get_bbva_files(account_clabe, access_token, account_info=account_info)
        pdf_files = [f for f in all_files if f.get('filename', '').lower().endswith('.pdf')]
        database = get_bbva_database(account_clabe, access_token)
        
        # Group database transactions by file
        transactions_by_file = {}
        for transaction in database.get('transactions', []):
            file_source = transaction.get('file_source', '')
            if file_source not in transactions_by_file:
                transactions_by_file[file_source] = []
            transactions_by_file[file_source].append(transaction)
        
        # Load existing tracking data
        tracking_data = get_bbva_parse_tracking_data(access_token)
        
        if account_clabe not in tracking_data:
            tracking_data[account_clabe] = {}
        
        # Update tracking for each file that has transactions in database
        updated_files = []
        for pdf_file in pdf_files:
            filename = pdf_file['filename']
            file_transactions = transactions_by_file.get(filename, [])
            
            if file_transactions:  # Only update if file has transactions in database
                tracking_data[account_clabe][filename] = {
                    'last_parsed': datetime.now().isoformat(),
                    'file_last_modified': pdf_file.get('last_modified_formatted'),
                    'transaction_count': len(file_transactions),
                    'parse_status': 'success'
                }
                updated_files.append(filename)
        
        # Save updated tracking data
        success = update_bbva_parse_tracking_data(tracking_data, access_token)
        
        if success:
            return f"""
            <html>
            <head><title>BBVA Tracking Fixed</title></head>
            <body style="font-family: monospace; padding: 20px; line-height: 1.6;">
            <h2>✅ BBVA Tracking Fixed Successfully!</h2>
            <div style="background: #e6ffe6; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <strong>Account:</strong> {account_clabe} ({account_info['name']})<br>
            <strong>Files Updated:</strong> {len(updated_files)}<br>
            <strong>Updated Files:</strong><br>
            <ul>
            {''.join(f'<li>{filename} ({len(transactions_by_file.get(filename, []))} transactions)</li>' for filename in updated_files)}
            </ul>
            </div>
            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <strong>✅ Next Step:</strong> Go back to the BBVA calendar and try parsing again. 
            It should now say "All files are already up to date".
            </div>
            <div>
            <a href="/banks_parse" style="color: #007bff; text-decoration: none; padding: 10px 20px; background: #e7f3ff; border-radius: 5px;">
            🏦 Back to BBVA Calendar
            </a>
            </div>
            </body>
            </html>
            """
        else:
            return f"""
            <html>
            <body style="font-family: monospace; padding: 20px;">
            <h2>❌ Error</h2>
            <p>Failed to save tracking data</p>
            <a href="/banks_parse">← Back to BBVA Calendar</a>
            </body>
            </html>
            """
        
    except Exception as e:
        logger.error(f"Error fixing BBVA tracking: {e}")
        return f"""
        <html>
        <body style="font-family: monospace; padding: 20px;">
        <h2>❌ Error</h2>
        <p>Failed to fix tracking: {str(e)}</p>
        <a href="/banks_parse">← Back to BBVA Calendar</a>
        </body>
        </html>
        """

@app.route('/api/bbva/debug-tracking-file')
@require_oauth  
def debug_bbva_tracking_file():
    """Check the actual tracking file contents"""
    try:
        access_token = session['access_token']
        
        from modules.bbva.bbva_database import get_bbva_parse_tracking_data
        
        # Get raw tracking data
        tracking_data = get_bbva_parse_tracking_data(access_token)
        
        return jsonify({
            'success': True,
            'tracking_file_exists': bool(tracking_data),
            'accounts_in_tracking': list(tracking_data.keys()) if tracking_data else [],
            'full_tracking_data': tracking_data
        })
        
    except Exception as e:
        logger.error(f"Error reading tracking file: {e}")
        return jsonify({
            'error': f'Failed to read tracking file: {str(e)}'
        }), 500

@app.route('/api/bbva/debug-tracking/<account_clabe>')
@require_oauth
def debug_bbva_tracking(account_clabe):
    """Debug BBVA tracking data to see why files keep getting re-parsed"""
    try:
        access_token = session['access_token']
        
        # Import BBVA functions
        from modules.bbva.bbva_database import get_bbva_parse_tracking_data
        from modules.bbva.bbva_files import get_bbva_files
        from modules.bbva.bbva_batch import check_bbva_file_parsing_status
        from modules.bbva.bbva_config import get_account_by_clabe
        
        # Validate account
        account_info = get_account_by_clabe(account_clabe)
        if not account_info:
            return jsonify({'error': f'Invalid BBVA account CLABE: {account_clabe}'}), 400
        
        # Get current files
        all_files = get_bbva_files(account_clabe, access_token, account_info=account_info)
        pdf_files = [f for f in all_files if f.get('filename', '').lower().endswith('.pdf')]
        
        # Get tracking data
        tracking_data = get_bbva_parse_tracking_data(access_token)
        account_tracking = tracking_data.get(account_clabe, {})
        
        # Check which files need parsing
        files_to_parse = check_bbva_file_parsing_status(pdf_files, tracking_data, account_clabe)
        
        # Build detailed debug info
        debug_info = {
            'account_clabe': account_clabe,
            'account_type': account_info['name'],
            'tracking_file_exists': bool(tracking_data),
            'account_in_tracking': account_clabe in tracking_data,
            'tracked_files_count': len(account_tracking),
            'current_pdf_files_count': len(pdf_files),
            'files_needing_parse': len(files_to_parse),
            'detailed_file_analysis': []
        }
        
        # Analyze each PDF file
        for pdf_file in pdf_files:
            filename = pdf_file['filename']
            file_modified = pdf_file.get('last_modified_formatted')
            tracked_info = account_tracking.get(filename, {})
            
            needs_parsing = filename in [f['filename'] for f in files_to_parse]
            
            file_analysis = {
                'filename': filename,
                'file_last_modified': file_modified,
                'is_tracked': filename in account_tracking,
                'needs_parsing': needs_parsing,
                'tracking_info': tracked_info
            }
            
            if tracked_info:
                file_analysis['tracked_last_parsed'] = tracked_info.get('last_parsed')
                file_analysis['tracked_parse_status'] = tracked_info.get('parse_status')
                file_analysis['tracked_transaction_count'] = tracked_info.get('transaction_count')
                file_analysis['tracked_file_modified'] = tracked_info.get('file_last_modified')
                
                # Compare timestamps if both exist
                if file_modified and tracked_info.get('file_last_modified'):
                    file_analysis['modification_comparison'] = {
                        'current_file_time': file_modified,
                        'tracked_file_time': tracked_info.get('file_last_modified'),
                        'times_match': file_modified == tracked_info.get('file_last_modified')
                    }
            
            debug_info['detailed_file_analysis'].append(file_analysis)
        
        # Check if the problematic file (2501) is in the list
        problematic_file = next(
            (f for f in debug_info['detailed_file_analysis'] if '2501' in f['filename']), 
            None
        )
        
        if problematic_file:
            debug_info['problematic_file_2501'] = {
                'found': True,
                'details': problematic_file,
                'why_needs_parsing': 'Analyzing...'
            }
            
            # Determine why it needs parsing
            if not problematic_file['is_tracked']:
                debug_info['problematic_file_2501']['why_needs_parsing'] = 'File not in tracking data'
            elif problematic_file['tracking_info'].get('parse_status') != 'success':
                debug_info['problematic_file_2501']['why_needs_parsing'] = f"Parse status is '{problematic_file['tracking_info'].get('parse_status')}', not 'success'"
            elif problematic_file.get('modification_comparison', {}).get('times_match') == False:
                debug_info['problematic_file_2501']['why_needs_parsing'] = 'File modification time changed'
            else:
                debug_info['problematic_file_2501']['why_needs_parsing'] = 'Unknown reason - this should not happen'
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        logger.error(f"Error debugging BBVA tracking: {e}")
        return jsonify({
            'error': f'Debug failed: {str(e)}'
        }), 500

@app.route('/api/bbva/record-counts/<int:year>')
@require_oauth
def get_bbva_record_counts(year):
    """Get monthly record counts for all BBVA accounts"""
    try:
        access_token = session['access_token']
        logger.info(f"Getting BBVA record counts for year {year}")
        
        from modules.bbva.bbva_database import get_bbva_parse_tracking_data
        from modules.bbva.bbva_config import BBVA_ACCOUNTS
        
        # Load tracking data
        tracking_data = get_bbva_parse_tracking_data(access_token)
        
        # Build record counts structure
        record_counts = {}
        
        for account_key, account_info in BBVA_ACCOUNTS.items():
            clabe = account_info['clabe']
            account_tracking = tracking_data.get(clabe, {})
            
            # Initialize months for this account
            record_counts[clabe] = {}
            
            for month in range(1, 13):
                month_key = f"{year}-{month:02d}"
                record_counts[clabe][month_key] = 0
                
                # Find files for this month and sum transaction counts
                for filename, file_tracking in account_tracking.items():
                    # Extract month from filename (assuming format like "2501 FMX BBVA MXN.pdf")
                    if filename.startswith(f"{str(year)[2:]}{month:02d}"):
                        transaction_count = file_tracking.get('transaction_count', 0)
                        if file_tracking.get('parse_status') != 'failed':
                            record_counts[clabe][month_key] = transaction_count
                        break
        
        logger.info(f"BBVA record counts result: {record_counts}")
        
        return jsonify({
            'success': True,
            'year': year,
            'record_counts': record_counts,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting BBVA record counts for year {year}: {e}")
        return jsonify({'error': f'Failed to load BBVA record counts: {str(e)}'}), 500

# ============================================================================
# NEW AUTHENTICATION REDIRECT UPDATE
# ============================================================================

@app.route('/')
@require_oauth
def home():
    """Redirect to unified statements page"""
    current_year = datetime.now().year
    return redirect(url_for('statements_page', year=current_year))


@app.route('/login')
def login():
    """Initiate Azure OAuth login"""
    auth_url, state, code_verifier = oauth.get_auth_url()
    session['oauth_state'] = state
    session['code_verifier'] = code_verifier
    return redirect(auth_url)


@app.route('/callback')
def callback():
    """Handle OAuth callback from Azure"""
    try:
        # Verify state parameter
        state = request.args.get('state')
        if state != session.get('oauth_state'):
            flash('Invalid state parameter', 'error')
            return redirect(url_for('index'))
        
        # Check for error in callback
        error = request.args.get('error')
        if error:
            error_description = request.args.get('error_description', 'No description')
            flash(f'Authorization failed: {error} - {error_description}', 'error')
            return redirect(url_for('index'))
        
        # Get authorization code
        code = request.args.get('code')
        if not code:
            flash('No authorization code received', 'error')
            return redirect(url_for('index'))
        
        # Get code verifier from session
        code_verifier = session.get('code_verifier')
        if not code_verifier:
            flash('Missing code verifier', 'error')
            return redirect(url_for('index'))
        
        # Exchange code for token
        token_data = oauth.get_token_from_code(code, code_verifier)
        if not token_data:
            flash('Failed to get access token', 'error')
            return redirect(url_for('index'))
        
        # Store tokens in session
        access_token = token_data.get('access_token')
        session['access_token'] = access_token
        session['refresh_token'] = token_data.get('refresh_token')
        session['token_expires_at'] = (datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))).isoformat()
        
        # Clean up OAuth state
        session.pop('oauth_state', None)
        session.pop('code_verifier', None)
        
        flash('Successfully logged in!', 'success')
        return redirect(url_for('stp_calendar'))
        
    except Exception as e:
        logger.error(f"Callback exception: {e}")
        flash(f'Authentication error: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('Successfully logged out!', 'success')
    return redirect(url_for('index'))

# ============================================================================
# HEALTH CHECK ENDPOINT FOR UNIFIED SYSTEM
# ============================================================================

@app.route('/api/health/unified')
@require_oauth  
def unified_system_health():
    """Check health of unified statements system"""
    try:
        from modules.statements.config import validate_unified_config
        from modules.statements.api_endpoints import get_statements_route_info, validate_statements_routes
        
        # Test configuration
        config_validation = validate_unified_config()
        
        # Test routes
        route_validation = validate_statements_routes(app)
        
        # Count available accounts
        stp_count = len([a for a in UNIFIED_ACCOUNTS.values() if a['type'] == 'stp'])
        bbva_count = len([a for a in UNIFIED_ACCOUNTS.values() if a['type'] == 'bbva'])
        
        return jsonify({
            'status': 'healthy',
            'unified_system': {
                'configuration_valid': all(config_validation.values()),
                'total_accounts': len(UNIFIED_ACCOUNTS),
                'stp_accounts': stp_count,
                'bbva_accounts': bbva_count,
                'routes_registered': sum(route_validation.values()),
                'total_routes': len(route_validation)
            },
            'configuration_checks': config_validation,
            'route_checks': route_validation,
            'route_info': get_statements_route_info(),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ============================================================================
# BACKWARDS COMPATIBILITY ROUTES
# ============================================================================

# These routes ensure existing bookmarks and links continue to work
# They redirect to the new unified system

@app.route('/stp')
@require_oauth
def redirect_stp_root():
    """Redirect old STP root to unified statements"""
    current_year = datetime.now().year
    logger.info("Redirecting legacy STP root to unified statements")
    return redirect(url_for('statements_page', year=current_year))

@app.route('/bbva')
@require_oauth  
def redirect_bbva_root():
    """Redirect old BBVA root to unified statements"""
    current_year = datetime.now().year
    logger.info("Redirecting legacy BBVA root to unified statements")
    return redirect(url_for('statements_page', year=current_year))

@app.route('/banks')
@require_oauth
def redirect_banks_root():
    """Redirect old banks root to unified statements"""
    current_year = datetime.now().year
    logger.info("Redirecting legacy banks root to unified statements")
    return redirect(url_for('statements_page', year=current_year))

# ============================================================================
# MAIN APPLICATION ROUTES
# ============================================================================    
    return render_template('channel_files.html',
                         team_id=team_id,
                         channel_id=channel_id,
                         files=files)

@app.route('/search')
@require_oauth
def search():
    """Search for files"""
    query = request.args.get('q', '')
    team_id = request.args.get('team_id', '')
    
    if not query:
        return render_template('search.html', files=[], query='')
    
    teams_api = TeamsAPI(session['access_token'])
    files = teams_api.search_files(query, team_id if team_id else None)
    
    return render_template('search.html', 
                         files=files,
                         query=query,
                         team_id=team_id)


@app.route('/download/<drive_id>/<file_id>')
@require_oauth
def download_file(drive_id, file_id):
    """Download a file"""
    teams_api = TeamsAPI(session['access_token'])
    file_content = teams_api.get_file_content(drive_id, file_id)
    
    if not file_content:
        flash('Failed to download file', 'error')
        return redirect(url_for('stp_calendar'))
    
    # Get file info for filename
    try:
        import requests
        response = requests.get(
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}",
            headers={'Authorization': f'Bearer {session["access_token"]}'}
        )
        file_info = response.json()
        filename = file_info.get('name', 'download')
        mimetype = file_info.get('file', {}).get('mimeType', 'application/octet-stream')
    except:
        filename = 'download'
        mimetype = 'application/octet-stream'
    
    return send_file(
        io.BytesIO(file_content),
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )

# ============================================================================
# STP CALENDAR ROUTES
# ============================================================================

@app.route('/stp-calendar')
@require_oauth
def stp_calendar():
    """STP Calendar - Enhanced with performance optimization"""
    year = request.args.get('year', default=datetime.now().year, type=int)
    return stp_calendar_fast(year)

@app.route('/stp-account/<account_number>')
@require_oauth
def stp_account_detail(account_number):
    """Detailed view for individual STP account"""
    year = request.args.get('year', default=2025, type=int)
    
    try:
        files = get_stp_files(account_number, session['access_token'], year=year)
        account_type = get_account_type(account_number)
        
        # Organize files by month for detailed view
        months_detail = {}
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            month_files = [f for f in files if f['date_string'] == month_key]
            
            from modules.stp.stp_helpers import get_month_name
            months_detail[month_key] = {
                'month_name': get_month_name(month),
                'pdf_file': next((f for f in month_files if f['extension'] == 'pdf'), None),
                'xlsx_file': next((f for f in month_files if f['extension'] == 'xlsx'), None),
                'status': 'complete' if len(month_files) >= 2 else 'partial' if month_files else 'missing'
            }
        
        return render_template('stp/stp_account_detail.html',
                             account_number=account_number,
                             account_type=account_type,
                             year=year,
                             months_detail=months_detail,
                             total_files=len(files))
        
    except Exception as e:
        logger.error(f"Error loading account detail for {account_number}: {e}")
        flash(f'Error loading account details: {str(e)}', 'error')
        return redirect(url_for('stp_calendar'))

# ============================================================================
# STP PARSE ROUTES
# ============================================================================

@app.route('/api/stp/parse/<account_number>', methods=['POST'])
@require_oauth
def parse_account_documents(account_number):
    """Parse all Excel documents for an account with database synchronization"""
    try:
        access_token = session['access_token']
        
        # Validate account number
        if not validate_account_number(account_number):
            return jsonify({'error': f'Invalid account number: {account_number}'}), 400
        
        # Generate a unique parse session ID
        parse_session_id = f"{account_number}_{datetime.now().timestamp()}"
        
        # Initialize progress tracking
        parse_progress[parse_session_id] = {
            'status': 'initializing',
            'current_file': None,
            'files_processed': 0,
            'files_checked': 0,
            'files_skipped': 0,
            'total_files': 0,
            'transactions_added': 0,
            'orphaned_transactions_removed': 0,
            'errors': [],
            'details': 'Starting parse process...',
            'progress_percentage': 5,
            'account_number': account_number,
            'account_type': get_account_type(account_number)
        }
        
        logger.info(f"Starting parse process for account {account_number} (session: {parse_session_id})")
        
        # Small delay to show initialization
        time.sleep(0.5)
        
        # PHASE 1: Get all current files in SharePoint directory
        parse_progress[parse_session_id]['status'] = 'fetching_files'
        parse_progress[parse_session_id]['details'] = 'Retrieving current files from SharePoint...'
        parse_progress[parse_session_id]['progress_percentage'] = 10
        
        all_files = get_stp_files(account_number, access_token)
        excel_files = [f for f in all_files if f.get('extension') == 'xlsx']
        
        parse_progress[parse_session_id]['total_files'] = len(excel_files)
        parse_progress[parse_session_id]['details'] = f'Found {len(excel_files)} Excel files'
        
        # PHASE 2: Database Synchronization
        parse_progress[parse_session_id]['status'] = 'synchronizing_database'
        parse_progress[parse_session_id]['details'] = 'Synchronizing database with current files...'
        parse_progress[parse_session_id]['progress_percentage'] = 15
        
        # Load existing database
        database = get_json_database(account_number, access_token)
        
        # Synchronize database with current files (removes orphaned transactions)
        original_transaction_count = len(database['transactions'])
        database = synchronize_database_with_files(database, all_files, account_number)
        new_transaction_count = len(database['transactions'])
        orphaned_removed = original_transaction_count - new_transaction_count
        
        parse_progress[parse_session_id]['orphaned_transactions_removed'] = orphaned_removed
        if orphaned_removed > 0:
            parse_progress[parse_session_id]['details'] = f'Removed {orphaned_removed} orphaned transactions from deleted files'
            logger.info(f"Removed {orphaned_removed} orphaned transactions during synchronization")
        else:
            parse_progress[parse_session_id]['details'] = 'Database synchronized - no orphaned transactions found'
        
        time.sleep(0.5)
        
        # PHASE 3: Check which files need parsing
        parse_progress[parse_session_id]['status'] = 'checking_files'
        parse_progress[parse_session_id]['details'] = f'Checking {len(excel_files)} files for updates...'
        parse_progress[parse_session_id]['progress_percentage'] = 20
        
        tracking_data = get_parse_tracking_data(access_token)
        
        # Clean up tracking data (remove references to deleted files)
        tracking_data = cleanup_tracking_data(tracking_data, all_files, account_number)
        
        # Check which files need parsing
        files_to_parse = check_file_parsing_status(excel_files, tracking_data, account_number)
        
        parse_progress[parse_session_id]['total_files'] = len(files_to_parse)
        parse_progress[parse_session_id]['files_skipped'] = len(excel_files) - len(files_to_parse)
        
        if not files_to_parse:
            parse_progress[parse_session_id]['status'] = 'completed'
            parse_progress[parse_session_id]['details'] = f'All {len(excel_files)} files are already up to date'
            parse_progress[parse_session_id]['progress_percentage'] = 100
            
            # Save synchronized database even if no files to parse
            update_json_database(account_number, database, access_token)
            update_parse_tracking_data(tracking_data, access_token)
            
            return jsonify({
                'success': True,
                'session_id': parse_session_id,
                'message': f'All {len(excel_files)} files are already up to date',
                'files_processed': 0,
                'files_checked': len(excel_files),
                'files_skipped': len(excel_files),
                'transactions_added': 0,
                'orphaned_transactions_removed': orphaned_removed
            })
        
        # PHASE 4: Initialize tracking for this account if not exists
        if account_number not in tracking_data:
            tracking_data[account_number] = {}
        
        files_processed = 0
        total_transactions_added = 0
        processing_errors = []
        
        # PHASE 5: Process each file that needs parsing
        parse_progress[parse_session_id]['status'] = 'processing_files'
        
        for idx, file_info in enumerate(files_to_parse):
            try:
                filename = file_info['filename']
                drive_id = file_info['drive_id']
                file_id = file_info['file_id']
                
                # Update progress
                parse_progress[parse_session_id]['current_file'] = filename
                parse_progress[parse_session_id]['details'] = f'Processing {filename} ({idx + 1}/{len(files_to_parse)})'
                parse_progress[parse_session_id]['progress_percentage'] = 25 + int((idx / len(files_to_parse)) * 60)
                
                logger.info(f"Processing file {filename}")
                
                # Download file content
                parse_progress[parse_session_id]['details'] = f'Downloading {filename}...'
                time.sleep(0.2)
                
                file_content = get_file_content_by_ids(drive_id, file_id, access_token)
                
                if not file_content:
                    error_msg = f"Failed to download {filename}"
                    processing_errors.append(error_msg)
                    parse_progress[parse_session_id]['errors'].append(error_msg)
                    continue
                
                # Remove old transactions from this file (if any)
                parse_progress[parse_session_id]['details'] = f'Updating transactions from {filename}...'
                database = remove_file_transactions(database, filename)
                
                # Parse Excel file
                parse_progress[parse_session_id]['details'] = f'Parsing {filename}...'
                time.sleep(0.2)
                
                try:
                    transactions = parse_excel_file(file_content, filename)
                    
                    if transactions:
                        # Add new transactions
                        database['transactions'].extend(transactions)
                        total_transactions_added += len(transactions)
                        parse_progress[parse_session_id]['transactions_added'] = total_transactions_added
                        
                        # Sort transactions by date (newest first)
                        database['transactions'].sort(
                            key=lambda x: x.get('fecha_operacion') or '1900-01-01',
                            reverse=True
                        )
                        
                        logger.info(f"Added {len(transactions)} transactions from {filename}")
                    
                    # Update tracking
                    tracking_data[account_number][filename] = {
                        'last_parsed': datetime.now().isoformat(),
                        'file_last_modified': file_info.get('last_modified_formatted'),
                        'transaction_count': len(transactions) if transactions else 0
                    }
                    
                    files_processed += 1
                    parse_progress[parse_session_id]['files_processed'] = files_processed
                    
                except Exception as parse_error:
                    error_msg = f"Failed to parse {filename}: {str(parse_error)}"
                    processing_errors.append(error_msg)
                    parse_progress[parse_session_id]['errors'].append(error_msg)
                    logger.error(error_msg)
                    continue
                    
            except Exception as file_error:
                error_msg = f"Error processing file {file_info.get('filename', 'unknown')}: {str(file_error)}"
                processing_errors.append(error_msg)
                parse_progress[parse_session_id]['errors'].append(error_msg)
                logger.error(error_msg)
                continue
        
        # PHASE 6: Update database metadata and save
        parse_progress[parse_session_id]['status'] = 'saving_database'
        parse_progress[parse_session_id]['details'] = 'Saving synchronized data to database...'
        parse_progress[parse_session_id]['progress_percentage'] = 95
        
        database['metadata']['files_parsed'] = len([f for f in tracking_data.get(account_number, {}).values() 
                                                   if f.get('transaction_count', 0) > 0])
        
        time.sleep(0.5)
        
        # Save updated database and tracking
        database_saved = update_json_database(account_number, database, access_token)
        tracking_saved = update_parse_tracking_data(tracking_data, access_token)
        
        if not database_saved or not tracking_saved:
            parse_progress[parse_session_id]['status'] = 'error'
            parse_progress[parse_session_id]['details'] = 'Failed to save synchronized data'
            
            return jsonify({
                'error': 'Failed to save synchronized data',
                'session_id': parse_session_id,
                'files_processed': files_processed,
                'transactions_added': total_transactions_added,
                'orphaned_transactions_removed': orphaned_removed,
                'errors': processing_errors
            }), 500
        
        # Mark as completed
        parse_progress[parse_session_id]['status'] = 'completed'
        if orphaned_removed > 0:
            parse_progress[parse_session_id]['details'] = f'Successfully processed {files_processed} files with {total_transactions_added} transactions. Removed {orphaned_removed} orphaned transactions.'
        else:
            parse_progress[parse_session_id]['details'] = f'Successfully processed {files_processed} files with {total_transactions_added} transactions'
        parse_progress[parse_session_id]['progress_percentage'] = 100
        parse_progress[parse_session_id]['current_file'] = None
        
        # Prepare response
        response_data = {
            'success': True,
            'session_id': parse_session_id,
            'message': f'Successfully processed {files_processed} files',
            'files_processed': files_processed,
            'files_checked': len(excel_files),
            'files_skipped': parse_progress[parse_session_id].get('files_skipped', 0),
            'transactions_added': total_transactions_added,
            'orphaned_transactions_removed': orphaned_removed,
            'total_transactions': database['metadata']['total_transactions'],
            'files_to_parse': len(files_to_parse),
            'errors': processing_errors
        }
        
        logger.info(f"Parse complete for account {account_number}: {response_data}")
        
        # Clean up progress after 5 minutes
        def cleanup_progress():
            time.sleep(300)
            if parse_session_id in parse_progress:
                del parse_progress[parse_session_id]
        
        cleanup_thread = threading.Thread(target=cleanup_progress)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Parse process error for account {account_number}: {e}")
        
        if 'parse_session_id' in locals() and parse_session_id in parse_progress:
            parse_progress[parse_session_id]['status'] = 'error'
            parse_progress[parse_session_id]['details'] = str(e)
        
        return jsonify({
            'error': f'Parse process failed: {str(e)}',
            'session_id': parse_session_id if 'parse_session_id' in locals() else None,
            'files_processed': 0,
            'transactions_added': 0
        }), 500


@app.route('/api/stp/parse-progress/<session_id>')
@require_oauth
def get_parse_progress(session_id):
    """Get current parse progress for a session"""
    if session_id not in parse_progress:
        return jsonify({'error': 'Invalid or expired session ID'}), 404
    
    progress_data = parse_progress[session_id].copy()
    progress_data['timestamp'] = datetime.now().isoformat()
    
    return jsonify(progress_data)


@app.route('/api/stp/parse-cancel/<session_id>', methods=['POST'])
@require_oauth
def cancel_parse(session_id):
    """Cancel an ongoing parse operation"""
    if session_id not in parse_progress:
        return jsonify({'error': 'Invalid or expired session ID'}), 404
    
    parse_progress[session_id]['status'] = 'cancelled'
    parse_progress[session_id]['details'] = 'Parse operation cancelled by user'
    
    return jsonify({'success': True, 'message': 'Parse operation cancelled'})

# ============================================================================
# STP REVIEW ROUTES
# ============================================================================

@app.route('/api/stp/review-data/<account_number>')
@require_oauth
def get_review_data(account_number):
    """Get transaction data for review page with date filtering support"""
    try:
        access_token = session['access_token']
        
        # Validate account number
        if not validate_account_number(account_number):
            return jsonify({'error': f'Invalid account number: {account_number}'}), 400
        
        # Load database
        database = get_json_database(account_number, access_token)
        transactions = database.get('transactions', [])
        
        # Convert dates for all transactions to ensure proper filtering
        for transaction in transactions:
            if transaction.get('fecha_operacion'):
                # Store original date
                transaction['fecha_operacion_original'] = transaction['fecha_operacion']
                # Convert DD/MM/YYYY to YYYY-MM-DD for filtering
                transaction['fecha_operacion_converted'] = convert_dd_mm_yyyy_to_yyyy_mm_dd(transaction['fecha_operacion'])
        
        return jsonify({
            'success': True,
            'account_number': account_number,
            'account_type': database['metadata']['account_type'],
            'transactions': transactions,
            'total_transactions': database['metadata']['total_transactions'],
            'last_updated': database['metadata']['last_updated']
        })
        
    except Exception as e:
        logger.error(f"Error getting review data for account {account_number}: {e}")
        return jsonify({'error': f'Failed to load review data: {str(e)}'}), 500

# ============================================================================
# STP ANALYTICS ROUTES
# ============================================================================

@app.route('/api/stp/record-counts/<int:year>')
@require_oauth
def get_record_counts(year):
    """Get monthly record counts for all accounts"""
    try:
        access_token = session['access_token']
        logger.info(f"Getting record counts for year {year}")
        
        # Use the analytics module to get actual record counts
        record_counts = get_monthly_record_counts(access_token, year)
        
        logger.info(f"Record counts result: {record_counts}")
        
        return jsonify({
            'success': True,
            'year': year,
            'record_counts': record_counts,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting record counts for year {year}: {e}")
        return jsonify({'error': f'Failed to load record counts: {str(e)}'}), 500

# ============================================================================
# STP UPLOAD ROUTES
# ============================================================================

@app.route('/api/stp/upload', methods=['POST'])
@require_oauth
def upload_stp_file():
    """Upload STP files to SharePoint"""
    try:
        # Get uploaded file and metadata
        file = request.files['file']
        account = request.form['account']
        year = request.form['year']
        month = request.form['month']
        
        logger.info(f"Uploading file: {file.filename} for account {account}")
        
        # Validate account
        account_folder_map = get_account_folder_mapping()
        target_folder_name = account_folder_map.get(account)
        
        if not target_folder_name:
            return jsonify({'error': f'Invalid account number: {account}'}), 400
        
        # Read file content
        file_content = file.read()
        if not file_content:
            return jsonify({'error': 'Empty file'}), 400
        
        # Upload to SharePoint
        success = upload_to_sharepoint(
            file.filename, 
            file_content, 
            target_folder_name, 
            session['access_token']
        )
        
        if success:
            logger.info(f"Successfully uploaded {file.filename}")
            
            # 🎯 PERFECT FIX: Use the method we proved works
            try:
                from modules.shared.performance_cache import unified_cache
                
                # Get cache size before clearing
                cache_size_before = len(unified_cache.cache)
                
                # Use the PROVEN working method: complete cache clear
                unified_cache.cache.clear()
                
                # Verify it worked
                cache_size_after = len(unified_cache.cache)
                
                logger.info(f"✅ Cache cleared after upload: {cache_size_before} → {cache_size_after} entries")
                
            except Exception as cache_error:
                logger.warning(f"⚠️ Failed to clear cache after upload: {cache_error}")
                # Don't fail the upload if cache clearing fails
            
            return jsonify({
                'success': True, 
                'message': f'File uploaded successfully to {target_folder_name}',
                'filename': file.filename,
                'target_folder': target_folder_name,
                'cache_cleared': True,
                'cache_entries_cleared': cache_size_before if 'cache_size_before' in locals() else 'unknown'
            })
        else:
            logger.error(f"Failed to upload {file.filename}")
            return jsonify({'error': 'Upload failed'}), 500
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

# ============================================================================
# STP EXPORT ROUTES
# ============================================================================

@app.route('/api/stp/export-excel/<account_number>')
@require_oauth
def export_to_excel(account_number):
    """Export JSON database to Excel with formatting and filters"""
    try:
        access_token = session['access_token']
        
        # Validate account number
        if not validate_account_number(account_number):
            return jsonify({'error': f'Invalid account number: {account_number}'}), 400
        
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        export_type = request.args.get('type', 'all')
        
        # Load database
        database = get_json_database(account_number, access_token)
        transactions = database.get('transactions', [])
        
        if not transactions:
            return jsonify({'error': 'No transactions found'}), 404
        
        # Apply filters
        filtered_transactions = apply_export_filters(transactions, start_date, end_date, export_type)
        
        if not filtered_transactions:
            return jsonify({'error': 'No transactions match the specified criteria'}), 404
        
        # Create Excel file
        excel_file = create_formatted_excel(filtered_transactions, database['metadata'], export_type)
        
        # Generate filename
        account_type = database['metadata']['account_type'].replace(' - ', '_').replace(' ', '_')
        if export_type == 'current_year':
            filename = f"{account_type}_DB_{datetime.now().year}.xlsx"
        elif export_type == 'last_12_months':
            filename = f"{account_type}_DB_Last_12_Months.xlsx"
        elif start_date and end_date:
            filename = f"{account_type}_DB_{start_date}_to_{end_date}.xlsx"
        else:
            filename = f"{account_type}_DB_Complete.xlsx"
        
        return send_file(
            io.BytesIO(excel_file),
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Export error for account {account_number}: {e}")
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

# ============================================================================
# BBVA ROUTES
# ============================================================================

@app.route('/api/bbva/calendar-status/<int:year>')
@require_oauth
def bbva_calendar_status(year):
    """Get BBVA calendar status using real file scanning"""
    try:
        logger.info(f"Getting real BBVA calendar status for year {year}")
        
        # Use real BBVA file scanning
        bbva_calendar_data = create_bbva_calendar_data(session['access_token'], year)
        
        return jsonify({
            'year': year,
            'calendar_data': bbva_calendar_data,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting BBVA calendar status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/bbva-account/<account_clabe>')
@require_oauth
def bbva_account_detail(account_clabe):
    """BBVA account detail page using real file data"""
    year = request.args.get('year', default=2025, type=int)
    
    try:
        # UPDATED: Use centralized config
        account_info = get_account_by_clabe(account_clabe)
        
        if not account_info:
            flash(f'Invalid BBVA account: {account_clabe}', 'error')
            return redirect(url_for('banks_calendar'))
        
        # Get real BBVA files for this account
        files = get_bbva_files_module(account_clabe, session['access_token'], year, account_info=account_info)
        
        # Rest of function stays the same...
        months_detail = {}
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            month_file = next((f for f in files if f['date_string'] == month_key), None)
            
            if month_file:
                status = 'complete'  # BBVA only needs PDF to be complete
            else:
                status = 'missing'
            
            months_detail[month_key] = {
                'month_name': month_names[month-1],
                'pdf_file': month_file,
                'xlsx_file': None,
                'status': status
            }
        
        total_files = len(files)
        
        return render_template('stp/stp_account_detail.html',
                             account_number=account_clabe,
                             account_type=account_info['name'],
                             year=year,
                             months_detail=months_detail,
                             total_files=total_files)
        
    except Exception as e:
        logger.error(f"Error loading BBVA account detail for {account_clabe}: {e}")
        flash(f'Error loading account details: {str(e)}', 'error')
        return redirect(url_for('banks_calendar'))

@app.route('/banks_parse')
@require_oauth
def banks_calendar():
    """Banks Parse - Enhanced with performance optimization"""
    year = request.args.get('year', default=datetime.now().year, type=int)
    return banks_calendar_fast(year)

# ============================================================================
# OTHER API ROUTES
# ============================================================================

@app.route('/api/user')
@require_oauth
def api_user():
    """API endpoint to get current user info"""
    teams_api = TeamsAPI(session['access_token'])
    user_info = teams_api.get_user_info()
    return jsonify(user_info)


@app.route('/api/teams')
@require_oauth
def api_teams():
    """API endpoint to get user's teams"""
    teams_api = TeamsAPI(session['access_token'])
    teams = teams_api.get_joined_teams()
    return jsonify(teams)


@app.route('/api/stp-calendar/<int:year>')
@require_oauth
def api_stp_calendar(year):
    """API endpoint for STP calendar data"""
    try:
        calendar_data = create_stp_calendar_data(session['access_token'], year)
        return jsonify({
            'year': year,
            'calendar_data': calendar_data,
            'generated_at': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stp/calendar-status/<int:year>')
@require_oauth
def get_calendar_status(year):
    """Get parsing status for calendar indicators"""
    try:
        access_token = session['access_token']
        
        # Load tracking data
        tracking_data = get_parse_tracking_data(access_token)
        
        # Get calendar data with parsing status
        calendar_data = create_stp_calendar_data(access_token, year)
        
        # Add parsing status to calendar data
        for account_number, account_data in calendar_data.items():
            account_tracking = tracking_data.get(account_number, {})
            
            for month_key, month_data in account_data['months'].items():
                month_data['parse_status'] = 'not_parsed'
                
                # Check if files for this month have been parsed
                if month_data.get('xlsx'):
                    filename = month_data['xlsx']['filename']
                    if filename in account_tracking:
                        tracking_info = account_tracking[filename]
                        if tracking_info.get('status') == 'different_format':
                            month_data['parse_status'] = 'different_format'
                        elif tracking_info.get('transaction_count', 0) >= 0:
                            month_data['parse_status'] = 'parsed'
                        else:
                            month_data['parse_status'] = 'parse_error'
        
        return jsonify({
            'year': year,
            'calendar_data': calendar_data,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting calendar status: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# BBVA UPLOAD ROUTES - Smart Detection Implementation
# ============================================================================

@app.route('/api/bbva/upload', methods=['POST'])
@require_oauth
def upload_bbva_file():
    """Smart BBVA file upload with automatic detection and conflict resolution"""
    try:
        # Get uploaded file and options
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        
        # Get conflict resolution options
        force_overwrite = request.form.get('force_overwrite') == 'true'
        custom_filename = request.form.get('custom_filename')
        
        # Validate file is PDF
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        logger.info(f"Processing BBVA upload: {file.filename} (overwrite={force_overwrite}, custom={custom_filename})")
        
        # Save file temporarily for analysis
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Step 1: Extract PDF information using existing BBVAParser
            from modules.bbva.bbva_parser import BBVAParser
            parser = BBVAParser()
            
            # Use existing _extract_pdf_info method for smart detection
            import pdfplumber
            with pdfplumber.open(temp_path) as pdf:
                pdf_info = parser._extract_pdf_info(pdf)
            
            # Step 2: Validate extracted information
            if not pdf_info.get('clabe'):
                return jsonify({
                    'error': 'Could not find CLABE number in statement',
                    'details': 'This file does not appear to be a BBVA Estado de Cuenta'
                }), 400
            
            clabe = pdf_info['clabe']
            account_type = pdf_info.get('account_type')
            
            if not account_type:
                return jsonify({
                    'error': f'CLABE not found in your accounts: {clabe}',
                    'details': 'This CLABE number is not configured for your BBVA accounts'
                }), 400
            
            # Step 3: Extract period for filename generation
            period_year = pdf_info.get('period_year')
            if not period_year:
                return jsonify({
                    'error': 'Could not determine statement period',
                    'details': 'Unable to extract period information from PDF'
                }), 400
            
            # Extract YYMM from period
            yy = str(period_year)[2:]  # 2025 -> 25
            
            # Extract month from period text
            import re
            period_text = pdf_info.get('period_text', '')
            month_match = re.search(r'DEL\s+\d{1,2}/(\d{1,2})/\d{4}', period_text)
            if month_match:
                mm = month_match.group(1).zfill(2)  # Ensure 2 digits
            else:
                return jsonify({
                    'error': 'Could not extract month from statement period',
                    'details': f'Period format not recognized: {period_text}'
                }), 400
            
            yymm = f"{yy}{mm}"
            
            # Get account info for this CLABE (needed for both conflict check and response)
            from modules.bbva.bbva_config import BBVA_ACCOUNTS
            account_info = None
            for acc_key, acc_data in BBVA_ACCOUNTS.items():
                if acc_data['clabe'] == clabe:
                    account_info = acc_data
                    break
            
            if not account_info:
                return jsonify({
                    'error': f'Account configuration not found for CLABE: {clabe}'
                }), 400

            # Step 4: Generate filename (use custom if provided)
            if custom_filename:
                generated_filename = custom_filename
                logger.info(f"Using custom filename: {generated_filename}")
            else:
                # Use standard filename mapping
                FILENAME_MAPPING = {
                    '012180001182790637': lambda yymm: f"{yymm} FSA BBVA MXN.pdf",      # BBVA SA MXN
                    '012222001182793149': lambda yymm: f"{yymm} FSA BBVA USD.pdf",      # BBVA SA USD  
                    '012180001198203451': lambda yymm: f"{yymm} FMX BBVA MXN.pdf",      # BBVA MX MXN
                    '012180001201205883': lambda yymm: f"{yymm} FMX BBVA USD.pdf",      # BBVA MX USD
                    '012180001232011635': lambda yymm: f"{yymm} BBVA MXN IP Corp.pdf",  # BBVA IP Corp
                    '012180001232011554': lambda yymm: f"{yymm} BBVA MXN IP Clientes.pdf" # BBVA IP Clientes
                }
                
                filename_generator = FILENAME_MAPPING.get(clabe)
                if not filename_generator:
                    return jsonify({
                        'error': f'No filename mapping found for CLABE: {clabe}',
                        'details': 'This account is not configured for auto-upload'
                    }), 400
                
                generated_filename = filename_generator(yymm)
            
            # Step 5: Check for existing file conflict (unless forcing overwrite)
            if not force_overwrite:
                from modules.bbva.bbva_files import get_bbva_files as get_bbva_files_module
                
                # Get existing files to check for conflicts
                year = int(period_year)
                month = int(mm)
                existing_files = get_bbva_files_module(
                    clabe, 
                    session['access_token'], 
                    year=year, 
                    month=month, 
                    account_info=account_info
                )
                
                # Check if file with same name already exists
                existing_file = next(
                    (f for f in existing_files if f['filename'] == generated_filename), 
                    None
                )
                
                if existing_file:
                    return jsonify({
                        'error': 'File already exists',
                        'details': f'A file named "{generated_filename}" already exists',
                        'existing_file': existing_file,
                        'suggested_filename': generated_filename,
                        'conflict': True
                    }), 409
            
            # Step 6: Upload to SharePoint
            with open(temp_path, 'rb') as f:
                file_content = f.read()
            
            # Use existing upload infrastructure
            success = upload_bbva_to_sharepoint(
                generated_filename,
                file_content,
                clabe,
                session['access_token']
            )
            
            if success:
                action_message = "replaced existing file" if force_overwrite else "uploaded successfully"
                custom_message = f" as {generated_filename}" if custom_filename else ""
                
                logger.info(f"✅ Successfully {action_message}: {generated_filename} to {account_type}")
                
                # Clear cache after successful upload
                try:
                    from modules.shared.performance_cache import unified_cache
                    cache_size_before = len(unified_cache.cache)
                    unified_cache.cache.clear()
                    cache_size_after = len(unified_cache.cache)
                    logger.info(f"✅ Cache cleared after BBVA upload: {cache_size_before} → {cache_size_after} entries")
                except Exception as cache_error:
                    logger.warning(f"⚠️ Failed to clear cache after BBVA upload: {cache_error}")
                
                return jsonify({
                    'success': True,
                    'message': f'✅ File {action_message}{custom_message} to {account_type}',
                    'filename': generated_filename,
                    'account_type': account_type,
                    'clabe': clabe,
                    'period': f"{yy}{mm}",
                    'folder_path': account_info['directory'],
                    'action': 'overwritten' if force_overwrite else 'uploaded'
                })
            else:
                return jsonify({
                    'error': 'Upload failed',
                    'details': 'Failed to upload file to SharePoint'
                }), 500
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")
        
    except Exception as e:
        logger.error(f"Error in BBVA upload: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Upload processing failed',
            'details': str(e)
        }), 500

def upload_bbva_to_sharepoint(filename: str, file_content: bytes, account_clabe: str, access_token: str) -> bool:
    """Upload BBVA file to correct SharePoint folder based on CLABE"""
    try:
        from modules.bbva.bbva_config import get_folder_path_mapping
        
        # Get target folder path for this CLABE
        folder_mapping = get_folder_path_mapping()
        target_folder_path = folder_mapping.get(account_clabe)
        
        if not target_folder_path:
            logger.error(f"No folder path found for CLABE: {account_clabe}")
            return False
        
        logger.info(f"Uploading BBVA file {filename} to {target_folder_path}")
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # SharePoint structure configuration
        drive_id = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
        bancos_folder_id = "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"
        
        # Navigate to target folder
        # 04 Bancos → Estados de Cuenta → BBVA → [Account Specific Path]
        target_folder_id = _navigate_to_bbva_upload_folder(
            target_folder_path, headers, drive_id, bancos_folder_id
        )
        
        if not target_folder_id:
            logger.error(f"Could not navigate to target folder: {target_folder_path}")
            return False
        
        # Upload file to target folder
        upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{target_folder_id}:/{filename}:/content"
        
        upload_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/octet-stream'
        }
        
        upload_response = requests.put(upload_url, headers=upload_headers, data=file_content)
        
        if upload_response.status_code in [200, 201]:
            logger.info(f"✅ BBVA file {filename} uploaded successfully")
            return True
        else:
            logger.error(f"❌ BBVA upload failed: {upload_response.status_code} - {upload_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"SharePoint BBVA upload error: {str(e)}")
        return False


def _navigate_to_bbva_upload_folder(target_folder_path: str, headers: dict, drive_id: str, bancos_folder_id: str) -> str:
    """Navigate through SharePoint hierarchy to find BBVA upload folder"""
    try:
        # Start from Bancos folder and navigate to target path
        # target_folder_path example: "Estados de Cuenta/BBVA/BBVA SA/BBVA SA MXN"
        
        # Step 1: Get Estados de Cuenta folder from Bancos
        bancos_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{bancos_folder_id}/children"
        bancos_response = requests.get(bancos_url, headers=headers)
        
        if bancos_response.status_code != 200:
            logger.error(f"Failed to access Bancos folder: {bancos_response.status_code}")
            return None
        
        bancos_items = bancos_response.json().get('value', [])
        estados_folder = next(
            (item for item in bancos_items 
             if item.get('folder') and 'estado' in item.get('name', '').lower()), 
            None
        )
        
        if not estados_folder:
            logger.error("Estados de Cuenta folder not found")
            return None
        
        # Step 2: Navigate through the path
        current_folder_id = estados_folder.get('id')
        path_parts = target_folder_path.split('/')
        
        # Skip "Estados de Cuenta" as we're already there
        if path_parts[0] == "Estados de Cuenta":
            path_parts = path_parts[1:]
        
        # Navigate through each folder in the path
        for folder_name in path_parts:
            current_folder_id = _find_subfolder_for_upload(current_folder_id, folder_name, headers, drive_id)
            if not current_folder_id:
                logger.error(f"Folder '{folder_name}' not found in path: {target_folder_path}")
                return None
        
        return current_folder_id
        
    except Exception as e:
        logger.error(f"Error navigating to BBVA upload folder: {e}")
        return None


def _find_subfolder_for_upload(parent_folder_id: str, folder_name: str, headers: dict, drive_id: str) -> str:
    """Find a specific subfolder for upload navigation"""
    try:
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_folder_id}/children"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to access folder {folder_name}: {response.status_code}")
            return None
        
        items = response.json().get('value', [])
        target_folder = next(
            (item for item in items 
             if item.get('folder') and item.get('name') == folder_name), 
            None
        )
        
        return target_folder.get('id') if target_folder else None
        
    except Exception as e:
        logger.error(f"Error finding subfolder {folder_name}: {e}")
        return None

# ============================================================================
# BBVA DATABASE TEST ENDPOINTS
# ============================================================================

@app.route('/api/bbva/test-db-create/<account_clabe>')
def test_bbva_db_create(account_clabe):
    """Test BBVA database creation for specific account"""
    try:
        if 'access_token' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        access_token = session['access_token']
        
        # Import BBVA database functions
        from modules.bbva.bbva_database import (
            create_empty_bbva_database, get_database_filename,
            navigate_to_bbva_db_folder
        )
        
        # Test database filename generation
        filename = get_database_filename(account_clabe)
        
        # Test folder navigation
        bbva_db_info = navigate_to_bbva_db_folder(access_token)
        
        # Create empty database structure
        empty_db = create_empty_bbva_database(account_clabe)
        
        return jsonify({
            'success': True,
            'message': 'BBVA database foundation test successful',
            'account_clabe': account_clabe,
            'database_filename': filename,
            'folder_info': {
                'drive_id': bbva_db_info['drive_id'],
                'folder_id': bbva_db_info['folder_id'],
                'folder_name': bbva_db_info['folder_name']
            },
            'empty_database': {
                'metadata': empty_db['metadata'],
                'transaction_count': len(empty_db['transactions'])
            }
        })
        
    except Exception as e:
        logger.error(f"BBVA database test error: {e}")
        return jsonify({
            'error': 'Database test failed',
            'details': str(e)
        }), 500


@app.route('/api/bbva/test-db-operations/<account_clabe>')
def test_bbva_db_operations(account_clabe):
    """Test complete BBVA database operations (create, read, update)"""
    try:
        if 'access_token' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        access_token = session['access_token']
        
        # Import BBVA database functions
        from modules.bbva.bbva_database import (
            get_bbva_database, update_bbva_database
        )
        
        # Step 1: Load or create database
        database = get_bbva_database(account_clabe, access_token)
        original_count = len(database['transactions'])
        
        # Step 2: Add a test transaction
        test_transaction = {
            "date": "2024-12-15",
            "date_liq": "2024-12-15", 
            "code": "TEST001",
            "description": "DATABASE TEST TRANSACTION",
            "cargo": 0.0,
            "abono": 999.99,
            "saldo": 50000.0,
            "saldo_liq": 50000.0,
            "file_source": "DATABASE_TEST.pdf",
            "page_number": 1,
            "raw_line": "15/DIC 15/DIC TEST001 DATABASE TEST TRANSACTION 999.99 50,000.00"
        }
        
        database['transactions'].append(test_transaction)
        
        # Step 3: Save database
        save_success = update_bbva_database(account_clabe, database, access_token)
        
        if not save_success:
            raise Exception("Failed to save database")
        
        # Step 4: Reload to verify persistence
        reloaded_db = get_bbva_database(account_clabe, access_token)
        new_count = len(reloaded_db['transactions'])
        
        return jsonify({
            'success': True,
            'message': 'BBVA database operations test successful',
            'account_clabe': account_clabe,
            'account_type': database['metadata']['account_type'],
            'operations_performed': [
                'Database loaded/created',
                'Test transaction added',
                'Database saved to SharePoint',
                'Database reloaded for verification'
            ],
            'transaction_counts': {
                'original': original_count,
                'after_addition': len(database['transactions']),
                'after_reload': new_count
            },
            'test_transaction': test_transaction,
            'database_metadata': reloaded_db['metadata'],
            'persistence_verified': new_count > original_count
        })
        
    except Exception as e:
        logger.error(f"BBVA database operations test error: {e}")
        return jsonify({
            'error': 'Database operations test failed',
            'details': str(e)
        }), 500


@app.route('/api/bbva/db-status')
def bbva_database_status():
    """Get status of all BBVA databases"""
    try:
        if 'access_token' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        access_token = session['access_token']
        
        # Import BBVA functions
        from modules.bbva.bbva_database import get_bbva_database
        from modules.bbva.bbva_config import BBVA_ACCOUNTS
        
        database_status = {}
        
        for account_key, account_info in BBVA_ACCOUNTS.items():
            account_clabe = account_info['clabe']
            account_name = account_info['name']
            
            try:
                database = get_bbva_database(account_clabe, access_token)
                
                database_status[account_clabe] = {
                    'account_name': account_name,
                    'account_key': account_key,
                    'status': 'exists',
                    'total_transactions': database['metadata']['total_transactions'],
                    'files_parsed': database['metadata']['files_parsed'],
                    'last_updated': database['metadata']['last_updated'],
                    'database_file': account_info['database']
                }
                
            except Exception as account_error:
                database_status[account_clabe] = {
                    'account_name': account_name,
                    'account_key': account_key,
                    'status': 'error',
                    'error': str(account_error),
                    'database_file': account_info['database']
                }
        
        return jsonify({
            'success': True,
            'message': 'BBVA database status retrieved',
            'databases': database_status,
            'total_accounts': len(BBVA_ACCOUNTS)
        })
        
    except Exception as e:
        logger.error(f"BBVA database status error: {e}")
        return jsonify({
            'error': 'Failed to get database status',
            'details': str(e)
        }), 500

# ============================================================================
# UTILITY ROUTES
# ============================================================================

@app.route('/debug/routes')
def list_routes():
    """List all available routes (development only)"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"{rule.rule} -> {rule.endpoint} ({', '.join(rule.methods)})")
    return "<br>".join(sorted(routes))

# ============================================================================
# BBVA HELPER FUNCTIONS
# ============================================================================

def create_bbva_calendar_data(access_token, year):
    """Create BBVA calendar data structure (similar to STP)"""
    try:
        logger.info(f"Creating BBVA calendar data for year {year}")
        
        bbva_calendar_data = {}
        
        # Process each BBVA account (now uses centralized config)
        for account_key, account_info in BBVA_ACCOUNTS.items():
            account_clabe = account_info['clabe']
            account_name = account_info['name']
            
            logger.info(f"Processing BBVA account: {account_name} ({account_clabe})")
            
            # Get files for this account
            files = get_bbva_files_module(account_clabe, access_token, year, account_info=account_info)
            
            # Initialize account data
            bbva_calendar_data[account_clabe] = {
                'account_type': account_name,
                'total_files': len(files),
                'months': {}
            }
            
            # Create month structure (same as STP)
            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            
            for month_num, month_name in enumerate(month_names, 1):
                month_key = f"{year}-{month_num:02d}"
                
                # Find PDF file for this month
                pdf_file = next((f for f in files if f['date_string'] == month_key), None)
                
                # Determine status
                if pdf_file:
                    status = 'complete'  # BBVA only needs PDF files to be complete
                else:
                    status = 'missing'
                
                bbva_calendar_data[account_clabe]['months'][month_key] = {
                    'pdf': pdf_file,
                    'xlsx': None,  # BBVA doesn't use Excel files
                    'status': status,
                    'month_name': month_name,
                    'parse_status': 'not_parsed'  # Will be updated after parsing
                }
        
        logger.info(f"BBVA calendar data created successfully for {len(bbva_calendar_data)} accounts")
        return bbva_calendar_data
        
    except Exception as e:
        logger.error(f"Error creating BBVA calendar data: {e}")
        raise

def validate_bbva_account_clabe(account_clabe):
    """Validate if the account CLABE exists in BBVA_ACCOUNTS"""
    return any(acc_data['clabe'] == account_clabe for acc_data in BBVA_ACCOUNTS.values())

# ============================================================================
# FIXED PERFORMANCE-ENHANCED ROUTES
# ============================================================================

@app.route('/stp-calendar/<int:year>')
@require_oauth
def stp_calendar_fast(year):
    """Enhanced STP calendar with performance optimization - FIXED"""
    try:
        logger.info(f"Loading STP calendar with performance optimization for year {year}")
        
        # FIXED: Pass access token directly, not through session in thread
        access_token = session['access_token']
        calendar_data = create_stp_calendar_data_fast(access_token, year)
        
        # Calculate summary statistics
        summary = {
            'total_files': sum(account.get('total_files', 0) for account in calendar_data.values()),
            'accounts_count': len(calendar_data),
            'complete_months': 0,
            'partial_months': 0,
            'missing_months': 0
        }
        
        for account_data in calendar_data.values():
            for month_data in account_data.get('months', {}).values():
                status = month_data.get('status', 'missing')
                if status == 'complete':
                    summary['complete_months'] += 1
                elif status == 'partial':
                    summary['partial_months'] += 1
                else:
                    summary['missing_months'] += 1
        
        logger.info(f"STP calendar loaded: {summary}")
        
        return render_template('stp/stp_calendar.html',
                             calendar_data=calendar_data,
                             year=year,
                             summary=summary,
                             current_year=datetime.now().year,
                             current_month=datetime.now().month,
                             performance_mode=False)
        
    except Exception as e:
        logger.error(f"Error creating STP calendar: {e}")
        flash(f'Error loading STP calendar: {str(e)}', 'error')
        return redirect(url_for('stp_calendar'))

@app.route('/banks_parse/<int:year>')
@require_oauth
def banks_calendar_fast(year):
    """Enhanced BBVA calendar with performance optimization - FIXED"""
    try:
        logger.info(f"Loading BBVA calendar with performance optimization for year {year}")
        
        # FIXED: Pass access token directly, not through session in thread
        access_token = session['access_token']
        calendar_data = create_bbva_calendar_data_fast(access_token, year)
        
        # Calculate summary statistics
        summary = {
            'total_files': sum(account.get('total_files', 0) for account in calendar_data.values()),
            'accounts_count': len(calendar_data),
            'complete_months': 0,
            'partial_months': 0,
            'missing_months': 0
        }
        
        for account_data in calendar_data.values():
            for month_data in account_data.get('months', {}).values():
                status = month_data.get('status', 'missing')
                if status == 'complete':
                    summary['complete_months'] += 1
                elif status == 'partial':
                    summary['partial_months'] += 1
                else:
                    summary['missing_months'] += 1
        
        logger.info(f"BBVA calendar loaded: {summary}")
        
        return render_template('stp/stp_calendar.html',
                             calendar_data=calendar_data,
                             year=year,
                             summary=summary,
                             current_year=datetime.now().year,
                             current_month=datetime.now().month,
                             system_type='bbva',
                             page_title='Banks Parse - BBVA',
                             file_type='PDF',
                             performance_mode=False)
        
    except Exception as e:
        logger.error(f"Error creating BBVA calendar: {e}")
        flash(f'Error loading BBVA calendar: {str(e)}', 'error')
        return redirect(url_for('stp_calendar'))

# ============================================================================
# FIXED PROGRESSIVE LOADING API ROUTES
# ============================================================================

@app.route('/api/stp/calendar-progressive/<int:year>')
@require_oauth
def api_stp_calendar_progressive(year):
    """Progressive loading API for STP calendar - FIXED"""
    def generate_progressive_data():
        try:
            # Get access token from session immediately
            access_token = session['access_token']
            
            # Send initialization
            yield f"data: {json.dumps({'type': 'init', 'total_accounts': 3, 'year': year})}\n\n"
            
            from modules.stp.stp_helpers import get_account_folder_mapping
            from modules.shared.performance_cache import get_stp_files_cached
            
            account_mapping = get_account_folder_mapping()
            calendar_data = {}
            
            for i, (account_number, folder_info) in enumerate(account_mapping.items()):
                # Send account start notification
                yield f"data: {json.dumps({'type': 'account_start', 'account': account_number, 'account_name': folder_info.get('name', account_number), 'progress': 20 + (i * 20)})}\n\n"
                
                try:
                    # Load account data with timing - FIXED: Sequential processing
                    start_time = time.time()
                    files = get_stp_files_cached(account_number, access_token, year)
                    load_time = time.time() - start_time
                    
                    # Process files into calendar format
                    months_data = {}
                    for month in range(1, 13):
                        month_key = f"{year}-{month:02d}"
                        month_files = [f for f in files if f.get('date_string') == month_key]
                        
                        pdf_file = next((f for f in month_files if f.get('extension') == 'pdf'), None)
                        xlsx_file = next((f for f in month_files if f.get('extension') == 'xlsx'), None)
                        
                        status = 'complete' if (pdf_file and xlsx_file) else 'partial' if (pdf_file or xlsx_file) else 'missing'
                        
                        months_data[month_key] = {
                            'pdf': pdf_file,
                            'xlsx': xlsx_file,
                            'status': status,
                            'month_name': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month-1],
                            'parse_status': 'not_parsed'
                        }
                    
                    account_data = {
                        'account_info': folder_info,
                        'months': months_data,
                        'total_files': len(files)
                    }
                    
                    calendar_data[account_number] = account_data
                    
                    # Send account completion
                    yield f"data: {json.dumps({'type': 'account_loaded', 'account': account_number, 'account_name': folder_info.get('name', account_number), 'account_data': account_data, 'load_time': load_time, 'progress': 20 + ((i + 1) * 25)})}\n\n"
                    
                except Exception as e:
                    logger.error(f"Error loading account {account_number}: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'account': account_number, 'error': str(e)})}\n\n"
            
            # Send completion
            yield f"data: {json.dumps({'type': 'completed', 'calendar_data': calendar_data})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in progressive STP loading: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return Response(generate_progressive_data(), mimetype='text/plain')

@app.route('/api/bbva/calendar-progressive/<int:year>')
@require_oauth
def api_bbva_calendar_progressive(year):
    """Progressive loading API for BBVA calendar - FIXED"""
    def generate_progressive_data():
        try:
            # Get access token from session immediately
            access_token = session['access_token']
            
            from modules.bbva.bbva_config import BBVA_ACCOUNTS
            
            # Send initialization
            yield f"data: {json.dumps({'type': 'init', 'total_accounts': len(BBVA_ACCOUNTS), 'year': year})}\n\n"
            
            calendar_data = {}
            
            for i, (account_key, account_info) in enumerate(BBVA_ACCOUNTS.items()):
                # Send account start notification
                yield f"data: {json.dumps({'type': 'account_start', 'account': account_key, 'account_name': account_info.get('name', account_key), 'progress': 10 + (i * 15)})}\n\n"
                
                try:
                    # Load account data with timing - FIXED: Sequential processing
                    start_time = time.time()
                    from modules.shared.performance_cache import get_bbva_files_cached
                    files = get_bbva_files_cached(account_info['clabe'], access_token, year)
                    load_time = time.time() - start_time
                    
                    # Process files into calendar format
                    months_data = {}
                    for month in range(1, 13):
                        month_key = f"{year}-{month:02d}"
                        month_files = [f for f in files if f.get('date_string') == month_key]
                        
                        pdf_file = next((f for f in month_files if f.get('extension') == 'pdf'), None)
                        
                        status = 'complete' if pdf_file else 'missing'
                        
                        months_data[month_key] = {
                            'pdf': pdf_file,
                            'xlsx': None,  # BBVA uses PDF only
                            'status': status,
                            'month_name': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month-1],
                            'parse_status': 'not_parsed'
                        }
                    
                    account_data = {
                        'account_info': account_info,
                        'months': months_data,
                        'total_files': len(files)
                    }
                    
                    calendar_data[account_key] = account_data
                    
                    # Send account completion
                    yield f"data: {json.dumps({'type': 'account_loaded', 'account': account_key, 'account_name': account_info.get('name', account_key), 'account_data': account_data, 'load_time': load_time, 'progress': 10 + ((i + 1) * 13)})}\n\n"
                    
                except Exception as e:
                    logger.error(f"Error loading BBVA account {account_key}: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'account': account_key, 'error': str(e)})}\n\n"
            
            # Send completion
            yield f"data: {json.dumps({'type': 'completed', 'calendar_data': calendar_data})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in progressive BBVA loading: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return Response(generate_progressive_data(), mimetype='text/plain')

# ============================================================================
# FIXED CACHED API ROUTES  
# ============================================================================

@app.route('/api/stp/calendar-cached/<int:year>')
@require_oauth
def api_stp_calendar_cached(year):
    """Get cached STP calendar data if available - FIXED"""
    try:
        access_token = session['access_token']
        
        # Try to get from cache first
        cache_key = unified_cache._generate_cache_key('stp_calendar', access_token, year)
        cached_data = unified_cache.get_cached_data(cache_key, 'calendar_data')
        
        if cached_data:
            return jsonify({
                'calendar_data': cached_data,
                'year': year,
                'cached': True,
                'generated_at': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'calendar_data': {},
                'year': year,
                'cached': False,
                'message': 'No cached data available'
            })
            
    except Exception as e:
        logger.error(f"Error getting cached STP calendar: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bbva/calendar-cached/<int:year>')
@require_oauth
def api_bbva_calendar_cached(year):
    """Get cached BBVA calendar data if available - FIXED"""
    try:
        access_token = session['access_token']
        
        # Try to get from cache first
        cache_key = unified_cache._generate_cache_key('bbva_calendar', access_token, year)
        cached_data = unified_cache.get_cached_data(cache_key, 'calendar_data')
        
        if cached_data:
            return jsonify({
                'calendar_data': cached_data,
                'year': year,
                'cached': True,
                'generated_at': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'calendar_data': {},
                'year': year,
                'cached': False,
                'message': 'No cached data available'
            })
            
    except Exception as e:
        logger.error(f"Error getting cached BBVA calendar: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# FIXED CACHE MANAGEMENT ROUTES
# ============================================================================

@app.route('/api/cache/warm', methods=['POST'])
@require_oauth
def warm_cache():
    """Warm cache with current year data - FIXED"""
    try:
        current_year = datetime.now().year
        access_token = session['access_token']
        
        # FIXED: Do cache warming in current request context
        warm_cache_for_user(access_token, current_year)
        
        return jsonify({
            'status': 'completed',
            'message': f'Cache warming completed for year {current_year}',
            'year': current_year
        })
        
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/stats')
@require_oauth
def cache_stats():
    """Get cache performance statistics"""
    try:
        stats = get_performance_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/clear', methods=['POST'])
@require_oauth
def clear_cache():
    """Clear application cache"""
    try:
        pattern = request.json.get('pattern', '') if request.json else ''
        
        if pattern:
            unified_cache.invalidate_pattern(pattern)
            message = f'Cleared cache entries matching "{pattern}"'
        else:
            unified_cache.cache.clear()
            message = 'Cleared all cache entries'
        
        return jsonify({
            'status': 'success',
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({'error': str(e)}), 500
    
# Add this route to your app.py

@app.route('/api/refresh-calendar', methods=['POST'])
@require_oauth
def refresh_calendar():
    """Manually refresh calendar by clearing cache"""
    try:
        from modules.shared.performance_cache import unified_cache
        
        cache_size_before = len(unified_cache.cache)
        unified_cache.cache.clear()
        
        logger.info(f"🔄 Manual calendar refresh: cleared {cache_size_before} cache entries")
        
        return jsonify({
            'success': True,
            'message': 'Calendar refreshed successfully',
            'cache_entries_cleared': cache_size_before
        })
        
    except Exception as e:
        logger.error(f"Error refreshing calendar: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================================
# Debuggin ROUTES
# ============================================================================

"""
Azure Permissions Debugging Tool
Add this route to your app.py to debug permission issues
"""

import requests
import logging
from flask import session, jsonify

logger = logging.getLogger(__name__)

@app.route('/debug/permissions')
@require_oauth
def debug_permissions():
    """Debug Azure permissions and access token"""
    try:
        access_token = session.get('access_token')
        if not access_token:
            return jsonify({'error': 'No access token found'})
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        results = {}
        
        # Test 1: Basic user info
        print("🔍 Testing basic user access...")
        user_response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers=headers,
            timeout=10
        )
        
        results['user_info'] = {
            'status': user_response.status_code,
            'success': user_response.status_code == 200,
            'data': user_response.json() if user_response.status_code == 200 else user_response.text[:200]
        }
        
        # Test 2: Teams access
        print("🔍 Testing Teams access...")
        teams_response = requests.get(
            'https://graph.microsoft.com/v1.0/me/joinedTeams',
            headers=headers,
            timeout=10
        )
        
        results['teams_access'] = {
            'status': teams_response.status_code,
            'success': teams_response.status_code == 200,
            'data': teams_response.json() if teams_response.status_code == 200 else teams_response.text[:200]
        }
        
        # Test 3: Specific team access
        team_id = '077539b3-b3af-4646-994f-dd642c9a1190'  # FIADO Main Office
        print(f"🔍 Testing specific team access: {team_id}")
        
        team_response = requests.get(
            f'https://graph.microsoft.com/v1.0/teams/{team_id}',
            headers=headers,
            timeout=10
        )
        
        results['specific_team'] = {
            'team_id': team_id,
            'status': team_response.status_code,
            'success': team_response.status_code == 200,
            'data': team_response.json() if team_response.status_code == 200 else team_response.text[:200]
        }
        
        # Test 4: Team drive access
        print(f"🔍 Testing team drive access...")
        drive_response = requests.get(
            f'https://graph.microsoft.com/v1.0/groups/{team_id}/drive',
            headers=headers,
            timeout=10
        )
        
        results['team_drive'] = {
            'status': drive_response.status_code,
            'success': drive_response.status_code == 200,
            'data': drive_response.json() if drive_response.status_code == 200 else drive_response.text[:200]
        }
        
        # Test 5: Drive root items
        if drive_response.status_code == 200:
            drive_id = drive_response.json().get('id')
            print(f"🔍 Testing drive items access...")
            
            items_response = requests.get(
                f'https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children',
                headers=headers,
                timeout=10
            )
            
            results['drive_items'] = {
                'drive_id': drive_id,
                'status': items_response.status_code,
                'success': items_response.status_code == 200,
                'data': items_response.json() if items_response.status_code == 200 else items_response.text[:200]
            }
            
            # Test 6: Look for Bancos folder specifically
            if items_response.status_code == 200:
                items_data = items_response.json()
                folders = [item for item in items_data.get('value', []) if item.get('folder')]
                folder_names = [folder.get('name') for folder in folders]
                
                results['folder_list'] = {
                    'status': 200,
                    'success': True,
                    'data': {
                        'total_items': len(items_data.get('value', [])),
                        'folders': folder_names,
                        'has_bancos': 'Bancos' in folder_names
                    }
                }
                
                # Test 7: Try to access Bancos folder if it exists
                bancos_folder = next((item for item in items_data.get('value', []) if item.get('name') == 'Bancos'), None)
                if bancos_folder:
                    bancos_id = bancos_folder.get('id')
                    bancos_response = requests.get(
                        f'https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{bancos_id}/children',
                        headers=headers,
                        timeout=10
                    )
                    
                    results['bancos_access'] = {
                        'status': bancos_response.status_code,
                        'success': bancos_response.status_code == 200,
                        'data': bancos_response.json() if bancos_response.status_code == 200 else bancos_response.text[:200]
                    }
                else:
                    results['bancos_access'] = {
                        'status': 404,
                        'success': False,
                        'data': 'Bancos folder not found in root directory'
                    }
        
        # Log results
        for test_name, test_result in results.items():
            if test_result.get('success'):
                logger.info(f"✅ {test_name}: SUCCESS")
            else:
                logger.error(f"❌ {test_name}: FAILED (Status: {test_result.get('status')})")
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'summary': {
                'total_tests': len(results),
                'passed': sum(1 for r in results.values() if r.get('success')),
                'failed': sum(1 for r in results.values() if not r.get('success'))
            }
        })
        
    except Exception as e:
        logger.error(f"Debug permissions error: {e}")
        return jsonify({'error': str(e)}), 500

# Add this simple debug route to your app.py

@app.route('/test-permissions')
@require_oauth
def test_permissions():
    """Simple test for SharePoint permissions"""
    import requests
    
    access_token = session.get('access_token')
    headers = {'Authorization': f'Bearer {access_token}'}
    
    results = []
    
    # Test 1: Basic user info
    try:
        response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers, timeout=10)
        results.append(f"User Info: {response.status_code} - {response.json().get('displayName', 'Unknown') if response.status_code == 200 else 'FAILED'}")
    except Exception as e:
        results.append(f"User Info: ERROR - {str(e)}")
    
    # Test 2: Teams access
    try:
        response = requests.get('https://graph.microsoft.com/v1.0/me/joinedTeams', headers=headers, timeout=10)
        results.append(f"Teams Access: {response.status_code} - {'SUCCESS' if response.status_code == 200 else 'FAILED'}")
        if response.status_code == 200:
            teams = response.json().get('value', [])
            results.append(f"Teams Count: {len(teams)}")
            for team in teams[:3]:  # Show first 3 teams
                results.append(f"  - Team: {team.get('displayName', 'Unknown')}")
    except Exception as e:
        results.append(f"Teams Access: ERROR - {str(e)}")
    
    # Test 3: Specific team
    team_id = '077539b3-b3af-4646-994f-dd642c9a1190'
    try:
        response = requests.get(f'https://graph.microsoft.com/v1.0/groups/{team_id}/drive', headers=headers, timeout=10)
        results.append(f"Team Drive: {response.status_code} - {'SUCCESS' if response.status_code == 200 else 'FAILED'}")
        
        if response.status_code == 200:
            drive_id = response.json().get('id')
            results.append(f"Drive ID: {drive_id}")
            
            # Test 4: Drive contents
            items_response = requests.get(f'https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children', headers=headers, timeout=10)
            results.append(f"Drive Contents: {items_response.status_code} - {'SUCCESS' if items_response.status_code == 200 else 'FAILED'}")
            
            if items_response.status_code == 200:
                items = items_response.json().get('value', [])
                results.append(f"Items Count: {len(items)}")
                folder_names = [item.get('name') for item in items if item.get('folder')]
                results.append(f"Folders: {', '.join(folder_names)}")
                results.append(f"Has Bancos: {'YES' if 'Bancos' in folder_names else 'NO'}")
            else:
                results.append(f"Drive Contents Error: {items_response.text[:200]}")
        else:
            results.append(f"Team Drive Error: {response.text[:200]}")
    except Exception as e:
        results.append(f"Team Drive: ERROR - {str(e)}")
    
    # Return as plain text for easy reading
    return '<br>'.join(results), 200, {'Content-Type': 'text/html'}

# Add this debug route to your app.py to test file detection

@app.route('/debug/file-detection/<account_number>')
@require_oauth
def debug_file_detection(account_number):
    """Debug file detection for specific account"""
    import requests
    import re
    
    access_token = session.get('access_token')  # Simple session access
    if not access_token:
        return "❌ No valid access token available."
    
    headers = {'Authorization': f'Bearer {access_token}'}
    results = []
    
    try:
        # Use the same logic as get_stp_files
        drive_id = "b!q3bruib_D0WIZS7yprZMBAUi_U53mb1KkFHHY5SmVTuIet9KaCuESqLv_QwsGcVu"
        bancos_folder_id = "01YH7LZSZL4O2ZOMG4RVH2Y7NLUTM5M33V"
        
        results.append(f"🔍 Debugging file detection for account: {account_number}")
        
        # Get account folder mapping
        account_folder_map = {
            '646180559700000009': 'STP SA New',
            '646180403000000004': 'STP IP',
            '646990403000000003': 'STP IP'
        }
        
        target_folder_name = account_folder_map.get(account_number)
        results.append(f"📁 Target folder: {target_folder_name}")
        
        if not target_folder_name:
            return "❌ Invalid account number"
        
        # Navigate through folders (same as get_stp_files)
        # Step 1: Get Estados de Cuenta folder
        bancos_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{bancos_folder_id}/children"
        bancos_response = requests.get(bancos_url, headers=headers)
        
        if bancos_response.status_code != 200:
            results.append(f"❌ Failed to access Bancos folder: {bancos_response.status_code}")
            return '<br>'.join(results)
        
        bancos_items = bancos_response.json().get('value', [])
        estados_folder = next((item for item in bancos_items if item.get('folder') and 'estado' in item.get('name', '').lower()), None)
        
        if not estados_folder:
            results.append("❌ Estados de Cuenta folder not found")
            return '<br>'.join(results)
        
        results.append(f"✅ Found Estados folder: {estados_folder.get('name')}")
        
        # Step 2: Get STP folder
        estados_id = estados_folder.get('id')
        estados_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{estados_id}/children"
        estados_response = requests.get(estados_url, headers=headers)
        
        if estados_response.status_code != 200:
            results.append(f"❌ Failed to access Estados folder: {estados_response.status_code}")
            return '<br>'.join(results)
        
        estados_items = estados_response.json().get('value', [])
        stp_folder = next((item for item in estados_items if item.get('folder') and 'stp' in item.get('name', '').lower()), None)
        
        if not stp_folder:
            results.append("❌ STP folder not found")
            return '<br>'.join(results)
        
        results.append(f"✅ Found STP folder: {stp_folder.get('name')}")
        
        # Step 3: Get account folder
        stp_id = stp_folder.get('id')
        stp_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{stp_id}/children"
        stp_response = requests.get(stp_url, headers=headers)
        
        if stp_response.status_code != 200:
            results.append(f"❌ Failed to access STP folder: {stp_response.status_code}")
            return '<br>'.join(results)
        
        stp_items = stp_response.json().get('value', [])
        account_folder = next((item for item in stp_items if item.get('folder') and item.get('name') == target_folder_name), None)
        
        if not account_folder:
            results.append(f"❌ Account folder '{target_folder_name}' not found")
            results.append(f"📂 Available folders: {[item.get('name') for item in stp_items if item.get('folder')]}")
            return '<br>'.join(results)
        
        results.append(f"✅ Found account folder: {account_folder.get('name')}")
        
        # Step 4: Get files from account folder
        account_id = account_folder.get('id')
        files_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{account_id}/children"
        files_response = requests.get(files_url, headers=headers)
        
        if files_response.status_code != 200:
            results.append(f"❌ Failed to access account files: {files_response.status_code}")
            return '<br>'.join(results)
        
        files = files_response.json().get('value', [])
        results.append(f"📊 Total items in folder: {len(files)}")
        
        # Test pattern matching
        pattern = rf"ec-{account_number}-(\d{{4}})(\d{{2}})\.(.+)$"
        results.append(f"🔍 Pattern: {pattern}")
        
        matched_files = []
        unmatched_files = []
        
        for file in files:
            if file.get('folder'):
                continue
                
            filename = file.get('name', '')
            match = re.match(pattern, filename)
            
            if match:
                file_year = match.group(1)
                file_month = match.group(2)
                extension = match.group(3).lower()
                
                matched_files.append({
                    'filename': filename,
                    'year': file_year,
                    'month': file_month,
                    'extension': extension,
                    'size': file.get('size', 0),
                    'modified': file.get('lastModifiedDateTime')
                })
            else:
                unmatched_files.append(filename)
        
        results.append(f"✅ Matched files: {len(matched_files)}")
        for file in matched_files:
            results.append(f"  📄 {file['filename']} - {file['year']}-{file['month']} - {file['extension']} - {file['size']} bytes")
        
        results.append(f"❌ Unmatched files: {len(unmatched_files)}")
        for filename in unmatched_files[:10]:  # Show first 10 unmatched files
            results.append(f"  📄 {filename}")
        if len(unmatched_files) > 10:
            results.append(f"  ... and {len(unmatched_files) - 10} more files")
        
        # Specifically look for the August 2025 files
        august_files = [f for f in matched_files if f['year'] == '2025' and f['month'] == '08']
        results.append(f"🎯 August 2025 files: {len(august_files)}")
        for file in august_files:
            results.append(f"  📄 {file['filename']} - {file['extension']} - Modified: {file['modified']}")
        
        # Test the specific filename
        test_filename = f"ec-{account_number}-202508.xlsx"
        results.append(f"🔍 Testing specific file: {test_filename}")
        specific_file = next((f for f in files if f.get('name') == test_filename), None)
        if specific_file:
            results.append(f"✅ Found specific file: {specific_file.get('name')} - Size: {specific_file.get('size')} - Modified: {specific_file.get('lastModifiedDateTime')}")
        else:
            results.append(f"❌ Specific file '{test_filename}' not found")
        
    except Exception as e:
        results.append(f"❌ Error: {str(e)}")
        import traceback
        results.append(f"   Traceback: {traceback.format_exc()}")
    
    html = f"""
    <html>
    <head><title>File Detection Debug</title></head>
    <body style="font-family: monospace; padding: 20px; line-height: 1.6;">
    <h2>🔍 File Detection Debug for Account {account_number}</h2>
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
    {'<br>'.join(results)}
    </div>
    <br>
    <a href="/stp-calendar" style="color: #007bff;">← Back to STP Calendar</a> | 
    <a href="/debug/clear-cache" style="color: #dc3545;">🗑️ Clear Cache</a>
    </div>
    </body>
    </html>
    """
    
    return html

# Add this route to clear the performance cache

@app.route('/debug/clear-cache')
@require_oauth
def clear_cache_debug():
    """Clear all performance cache"""
    try:
        from modules.shared.performance_cache import unified_cache
        
        # Clear all cache
        unified_cache.cache.clear()
        
        return f"""
        <html>
        <head><title>Cache Cleared</title></head>
        <body style="font-family: monospace; padding: 20px;">
        <h2>✅ Cache Cleared Successfully</h2>
        <p>All performance cache has been cleared.</p>
        <br>
        <a href="/stp-calendar" style="color: #007bff;">← Back to STP Calendar</a>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <html>
        <head><title>Cache Clear Error</title></head>
        <body style="font-family: monospace; padding: 20px;">
        <h2>❌ Error Clearing Cache</h2>
        <p>Error: {str(e)}</p>
        <br>
        <a href="/stp-calendar" style="color: #007bff;">← Back to STP Calendar</a>
        </body>
        </html>
        """
    
# Add this route to discover what cache keys are actually being used

@app.route('/debug/discover-cache-keys')
@require_oauth
def discover_cache_keys():
    """Discover actual cache keys being used"""
    try:
        from modules.shared.performance_cache import unified_cache
        
        results = []
        results.append("🔍 Discovering Actual Cache Keys")
        
        # Get all cache keys
        all_keys = list(unified_cache.cache.keys())
        results.append(f"📊 Total cache entries: {len(all_keys)}")
        
        # Show all keys
        results.append("")
        results.append("🔑 All Cache Keys:")
        for i, key in enumerate(all_keys):
            results.append(f"  {i+1:2d}. {key}")
        
        # Test cache clearing with actual patterns
        results.append("")
        results.append("🧪 Testing Cache Clear with Different Patterns:")
        
        test_patterns = [
            '',  # Empty pattern (should match all)
            'stp',
            'calendar',
            'file',
            'account',
            '646180559700000009',
            '2025'
        ]
        
        for pattern in test_patterns:
            matching_keys = [k for k in all_keys if pattern in k]
            results.append(f"  Pattern '{pattern}': {len(matching_keys)} matches")
            for key in matching_keys:
                results.append(f"    🔑 {key}")
        
        # Show cache content for key patterns
        stp_keys = [k for k in all_keys if 'stp' in k.lower()]
        if stp_keys:
            results.append("")
            results.append("📋 Sample STP Cache Content:")
            sample_key = stp_keys[0]
            try:
                content = unified_cache.cache.get(sample_key)
                if isinstance(content, dict):
                    results.append(f"  Key '{sample_key}': Dict with {len(content)} entries")
                    for sub_key in list(content.keys())[:5]:
                        results.append(f"    - {sub_key}")
                else:
                    results.append(f"  Key '{sample_key}': {type(content).__name__}")
            except Exception as e:
                results.append(f"  Key '{sample_key}': Error accessing - {e}")
        
    except Exception as e:
        results.append(f"❌ Error: {str(e)}")
        import traceback
        results.append(f"   Traceback: {traceback.format_exc()}")
    
    html = f"""
    <html>
    <head><title>Cache Keys Discovery</title></head>
    <body style="font-family: monospace; padding: 20px; line-height: 1.6;">
    <h2>🔍 Cache Keys Discovery</h2>
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; max-height: 600px; overflow-y: auto;">
    {'<br>'.join(results)}
    </div>
    <br>
    <div>
    <a href="/debug/nuclear-cache-clear" style="color: #dc3545; text-decoration: none; padding: 10px 20px; background: #ffe6e6; border-radius: 5px;">
    💥 Nuclear Cache Clear
    </a>
    <a href="/stp-calendar-no-cache" style="color: #28a745; text-decoration: none; padding: 10px 20px; background: #e6ffe6; border-radius: 5px; margin-left: 10px;">
    🔍 No-Cache Calendar
    </a>
    </div>
    </body>
    </html>
    """
    
    return html

# Add this route for complete cache destruction

@app.route('/debug/nuclear-cache-clear')
@require_oauth  
def nuclear_cache_clear():
    """Completely destroy all cache using multiple methods"""
    try:
        from modules.shared.performance_cache import unified_cache
        import gc
        
        results = []
        results.append("💥 Nuclear Cache Clear - Destroying Everything")
        
        # Get initial state
        initial_keys = list(unified_cache.cache.keys())
        results.append(f"📊 Initial cache entries: {len(initial_keys)}")
        
        # Method 1: Clear the unified cache completely
        try:
            unified_cache.cache.clear()
            results.append("✅ Method 1: unified_cache.cache.clear() - EXECUTED")
        except Exception as e:
            results.append(f"❌ Method 1 failed: {e}")
        
        # Method 2: Delete all keys manually
        try:
            remaining_keys = list(unified_cache.cache.keys())
            for key in remaining_keys:
                try:
                    del unified_cache.cache[key]
                except:
                    pass
            results.append(f"✅ Method 2: Manual key deletion - {len(remaining_keys)} keys processed")
        except Exception as e:
            results.append(f"❌ Method 2 failed: {e}")
        
        # Method 3: Recreate the cache object
        try:
            cache_type = type(unified_cache.cache)
            unified_cache.cache = cache_type()
            results.append(f"✅ Method 3: Cache object recreation - {cache_type.__name__}")
        except Exception as e:
            results.append(f"❌ Method 3 failed: {e}")
        
        # Method 4: Force garbage collection
        try:
            gc.collect()
            results.append("✅ Method 4: Garbage collection - EXECUTED")
        except Exception as e:
            results.append(f"❌ Method 4 failed: {e}")
        
        # Method 5: Try to clear any module-level variables
        try:
            import sys
            modules_to_clear = [
                'modules.shared.performance_cache',
                'modules.stp.stp_files',
                'modules.stp.stp_database'
            ]
            
            cleared_modules = 0
            for module_name in modules_to_clear:
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                    # Look for cache-like variables
                    for attr_name in dir(module):
                        if 'cache' in attr_name.lower():
                            try:
                                attr = getattr(module, attr_name)
                                if hasattr(attr, 'clear'):
                                    attr.clear()
                                    cleared_modules += 1
                                elif isinstance(attr, dict):
                                    attr.clear()
                                    cleared_modules += 1
                            except:
                                pass
            
            results.append(f"✅ Method 5: Module cache clearing - {cleared_modules} cleared")
        except Exception as e:
            results.append(f"❌ Method 5 failed: {e}")
        
        # Check final state
        final_keys = list(unified_cache.cache.keys())
        results.append(f"📊 Final cache entries: {len(final_keys)}")
        
        if final_keys:
            results.append("⚠️  Remaining entries:")
            for key in final_keys:
                results.append(f"    🔑 {key}")
        else:
            results.append("🎉 SUCCESS: All cache completely destroyed!")
        
        return f"""
        <html>
        <head><title>Nuclear Cache Clear Results</title></head>
        <body style="font-family: monospace; padding: 20px; line-height: 1.6;">
        <h2>💥 Nuclear Cache Clear Results</h2>
        <div style="background: #ffe6e6; padding: 20px; border-radius: 8px; border: 2px solid #dc3545;">
        {'<br>'.join(results)}
        </div>
        <br>
        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <strong>⚠️ Warning:</strong> All cache has been destroyed. The next page load will be slower as cache rebuilds.
        </div>
        <div>
        <a href="/stp-calendar-no-cache" style="color: #28a745; text-decoration: none; padding: 10px 20px; background: #e6ffe6; border-radius: 5px;">
        🔍 Test No-Cache Calendar
        </a>
        <a href="/stp-calendar" style="color: #007bff; text-decoration: none; padding: 10px 20px; background: #e7f3ff; border-radius: 5px; margin-left: 10px;">
        🏠 Regular STP Calendar
        </a>
        </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <html>
        <head><title>Nuclear Clear Error</title></head>
        <body style="font-family: monospace; padding: 20px;">
        <h2>❌ Nuclear Cache Clear Failed</h2>
        <p>Error: {str(e)}</p>
        <br>
        <a href="/stp-calendar" style="color: #007bff;">← Back to STP Calendar</a>
        </body>
        </html>
        """

# Add this route to your app.py (it was missing, causing the 404)

@app.route('/stp-calendar-no-cache')
@require_oauth
def stp_calendar_no_cache():
    """STP Calendar without any caching - shows real-time data"""
    year = request.args.get('year', default=datetime.now().year, type=int)
    
    try:
        access_token = session['access_token']
        
        # Use the original create_stp_calendar_data function (no cache)
        from modules.stp.stp_files import create_stp_calendar_data
        calendar_data = create_stp_calendar_data(access_token, year)
        
        # Calculate summary statistics
        summary = {
            'total_files': sum(account.get('total_files', 0) for account in calendar_data.values()),
            'accounts_count': len(calendar_data),
            'complete_months': 0,
            'partial_months': 0,
            'missing_months': 0
        }
        
        for account_data in calendar_data.values():
            for month_data in account_data.get('months', {}).values():
                status = month_data.get('status', 'missing')
                if status == 'complete':
                    summary['complete_months'] += 1
                elif status == 'partial':
                    summary['partial_months'] += 1
                else:
                    summary['missing_months'] += 1
        
        logger.info(f"No-cache STP calendar loaded: {summary}")
        
        return render_template('stp/stp_calendar.html',
                             calendar_data=calendar_data,
                             year=year,
                             summary=summary,
                             current_year=datetime.now().year,
                             cache_disabled=True)  # Flag to show this is no-cache version
        
    except Exception as e:
        logger.error(f"Error loading no-cache STP calendar: {e}")
        flash(f'Error loading calendar: {str(e)}', 'error')
        return redirect(url_for('index'))

# Add these simple routes to your app.py file

@app.route('/clear-cache-now')
@require_oauth
def clear_cache_now():
    """Simple cache clear"""
    try:
        from modules.shared.performance_cache import unified_cache
        before = len(unified_cache.cache)
        unified_cache.cache.clear()
        after = len(unified_cache.cache)
        
        return f"""
        <html>
        <body style="font-family: monospace; padding: 20px;">
        <h2>Cache Cleared!</h2>
        <p>Before: {before} entries</p>
        <p>After: {after} entries</p>
        <br>
        <a href="/stp-calendar">Go to STP Calendar</a>
        </body>
        </html>
        """
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/no-cache-calendar')
@require_oauth
def no_cache_calendar():
    """No cache calendar"""
    try:
        access_token = session['access_token']
        year = 2025
        
        from modules.stp.stp_files import create_stp_calendar_data
        calendar_data = create_stp_calendar_data(access_token, year)
        
        summary = {
            'total_files': sum(account.get('total_files', 0) for account in calendar_data.values()),
            'accounts_count': len(calendar_data),
            'complete_months': 0,
            'partial_months': 0,
            'missing_months': 0
        }
        
        for account_data in calendar_data.values():
            for month_data in account_data.get('months', {}).values():
                status = month_data.get('status', 'missing')
                if status == 'complete':
                    summary['complete_months'] += 1
                elif status == 'partial':
                    summary['partial_months'] += 1
                else:
                    summary['missing_months'] += 1
        
        return render_template('stp/stp_calendar.html',
                             calendar_data=calendar_data,
                             year=year,
                             summary=summary,
                             current_year=datetime.now().year)
        
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/bbva'):
        return jsonify({'success': False, 'error': 'API endpoint not found'}), 404
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/bbva'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500

# ============================================================================
# APPLICATION STARTUP
# ============================================================================

#if __name__ == '__main__':
#    # Check if all required environment variables are set
#    required_vars = ['AZURE_CLIENT_ID', 'AZURE_TENANT_ID', 'SECRET_KEY']
#    missing_vars = [var for var in required_vars if not os.getenv(var)]
#    
#    if missing_vars:
#        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
#        logger.error("Please check your .env file")
#        exit(1)
#    
#    port = int(os.getenv('PORT', 5001))
#    debug = os.getenv('FLASK_ENV') == 'development'
#    
#    logger.info(f"Starting Teams File Manager on port {port}")
#    logger.info(f"Debug mode: {debug}")
#    logger.info("All STP modules loaded successfully")
#    
#    app.run(host='127.0.0.1', port=port, debug=debug)

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 FLASK APPLICATION STARTING")
    print("="*70)
    print(f"📊 Unified Statements System: {len(UNIFIED_ACCOUNTS)} accounts configured")
    print(f"🏦 STP Accounts: {len([a for a in UNIFIED_ACCOUNTS.values() if a['type'] == 'stp'])}")
    print(f"🏧 BBVA Accounts: {len([a for a in UNIFIED_ACCOUNTS.values() if a['type'] == 'bbva'])}")
    print(f"🌐 Server starting on http://localhost:{PORT}")
    print(f"📄 Main page: http://localhost:{PORT}/statements")
    print(f"⚕️  Health check: http://localhost:{PORT}/api/health/unified")
    print("="*70)
    
    app.run(host='0.0.0.0', port=PORT, debug=True)