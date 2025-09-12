# ============================================================================
# modules/statements/api_endpoints.py
"""
Clean API Endpoints for Unified Statements - Phase 1b
Flask routes that use the clean Phase 1a/1b components
"""

import logging
import threading
import time
import os
import tempfile
from pathlib import Path
from datetime import datetime
from flask import send_file, abort, request, jsonify, session

from .config import UNIFIED_ACCOUNTS, validate_unified_config
from .data_loader import UnifiedDataLoader
from .parse_coordinator import UnifiedParseCoordinator
from .upload_handler import UnifiedUploadHandler
from .inventory_manager import InventoryManager
from .inventory_scanner import InventoryScanner

logger = logging.getLogger(__name__)

# Global instances
data_loader = UnifiedDataLoader()
parse_coordinator = UnifiedParseCoordinator() 
upload_handler = UnifiedUploadHandler()
inventory_manager = InventoryManager()
inventory_scanner = InventoryScanner()


# Progress tracking for parse operations
parse_progress = {}

# Progress tracking for inventory operations
inventory_progress = {}

def require_auth(f):
    """Authentication decorator"""
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def register_routes(app):
    """Register all statements API routes"""
    
    @app.route('/api/statements/config')
    @require_auth
    def api_statements_config():
        """Get unified statements configuration"""
        try:
            return jsonify({
                'success': True,
                'accounts': UNIFIED_ACCOUNTS,
                'validation': validate_unified_config(),
                'summary': {
                    'total_accounts': len(UNIFIED_ACCOUNTS),
                    'stp_accounts': len([a for a in UNIFIED_ACCOUNTS.values() if a['type'] == 'stp']),
                    'bbva_accounts': len([a for a in UNIFIED_ACCOUNTS.values() if a['type'] == 'bbva'])
                }
            })
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/statements/data/<int:year>')
    @require_auth  
    def api_statements_data(year):
        """Get unified statements data for year"""
        try:
            access_token = session['access_token']
            data = data_loader.load_unified_statements_data(access_token, year)
            
            return jsonify({
                'success': True,
                'year': year,
                'data': data,
                'summary': {
                    'total_accounts': len(data),
                    'accounts_with_data': len([a for a in data.values() if a.get('total_files', 0) > 0]),
                    'total_files': sum(a.get('total_files', 0) for a in data.values()),
                    'total_transactions': sum(a.get('total_transactions', 0) for a in data.values())
                },
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/statements/load-account-data/<account_id>')
    @require_auth
    def api_load_account_data(account_id):
        """Load data for specific account - used by frontend"""
        try:
            if account_id not in UNIFIED_ACCOUNTS:
                return jsonify({'success': False, 'error': 'Invalid account ID'}), 400
            
            access_token = session['access_token']
            year = request.args.get('year', datetime.now().year, type=int)
            
            account_data = data_loader.load_account_files_data(account_id, access_token, year)
            
            return jsonify({
                'success': True,
                'account_data': account_data
            })
            
        except Exception as e:
            logger.error(f"Error loading account data: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/statements/account/<account_id>/summary')
    @require_auth
    def api_account_summary(account_id):
        """Get detailed summary for specific account"""
        try:
            if account_id not in UNIFIED_ACCOUNTS:
                return jsonify({'success': False, 'error': 'Invalid account ID'}), 400
            
            access_token = session['access_token']
            year = request.args.get('year', datetime.now().year, type=int)
            
            summary = data_loader.get_account_summary(account_id, access_token, year)
            
            return jsonify({
                'success': True,
                'summary': summary
            })
            
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/statements/system-summary/<int:year>')
    @require_auth
    def api_system_summary(year):
        """Get system-wide summary"""
        try:
            access_token = session['access_token']
            summary = data_loader.get_system_summary(access_token, year)
            
            return jsonify({
                'success': True,
                'summary': summary
            })
            
        except Exception as e:
            logger.error(f"Error getting system summary: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/statements/parse/<account_id>', methods=['POST'])
    @require_auth
    def api_parse_account(account_id):
        """Parse specific account"""
        try:
            if account_id not in UNIFIED_ACCOUNTS:
                return jsonify({'success': False, 'error': 'Invalid account ID'}), 400
            
            access_token = session['access_token']
            
            # Generate session ID
            session_id = f"{account_id}_{datetime.now().timestamp()}"
            
            # Initialize progress
            parse_progress[session_id] = {
                'status': 'initializing',
                'account_id': account_id,
                'account_name': UNIFIED_ACCOUNTS[account_id]['name'],
                'progress_percentage': 0,
                'current_file': None,
                'files_processed': 0,
                'total_files': 0,
                'transactions_added': 0,
                'errors': [],
                'start_time': datetime.now().isoformat()
            }
            
            def progress_callback(progress_data):
                """Update progress"""
                parse_progress[session_id].update(progress_data)
                parse_progress[session_id]['last_update'] = datetime.now().isoformat()
            
            def run_parse():
                """Parse in background thread"""
                try:
                    result = parse_coordinator.parse_account(
                        account_id, access_token, progress_callback
                    )
                    
                    parse_progress[session_id].update({
                        'status': 'completed',
                        'progress_percentage': 100,
                        'result': result,
                        'end_time': datetime.now().isoformat()
                    })
                    
                    # Auto-cleanup after 5 minutes
                    def cleanup():
                        time.sleep(300)
                        if session_id in parse_progress:
                            del parse_progress[session_id]
                    
                    cleanup_thread = threading.Thread(target=cleanup)
                    cleanup_thread.daemon = True
                    cleanup_thread.start()
                    
                except Exception as e:
                    parse_progress[session_id].update({
                        'status': 'error',
                        'error': str(e),
                        'end_time': datetime.now().isoformat()
                    })
            
            # Start background parsing
            parse_thread = threading.Thread(target=run_parse)
            parse_thread.daemon = True
            parse_thread.start()
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': 'Parse operation started'
            })
            
        except Exception as e:
            logger.error(f"Error starting parse: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/statements/parse-progress/<session_id>')
    @require_auth
    def api_parse_progress(session_id):
        """Get parse progress"""
        if session_id not in parse_progress:
            return jsonify({'success': False, 'error': 'Invalid session ID'}), 404
        
        progress_data = parse_progress[session_id].copy()
        progress_data['timestamp'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'progress': progress_data
        })
    
    @app.route('/api/statements/parse-all', methods=['POST'])
    @require_auth
    def api_parse_all():
        """Parse all accounts"""
        try:
            access_token = session['access_token']
            
            # Generate batch session ID
            session_id = f"batch_{datetime.now().timestamp()}"
            
            # Initialize batch progress
            parse_progress[session_id] = {
                'status': 'initializing_batch',
                'session_type': 'batch',
                'total_accounts': len(UNIFIED_ACCOUNTS),
                'accounts_processed': 0,
                'accounts_successful': 0,
                'accounts_failed': 0,
                'current_account': None,
                'progress_percentage': 0,
                'account_results': {},
                'start_time': datetime.now().isoformat()
            }
            
            def batch_progress_callback(progress_data):
                """Update batch progress"""
                parse_progress[session_id].update(progress_data)
                parse_progress[session_id]['last_update'] = datetime.now().isoformat()
            
            def run_batch_parse():
                """Run batch parse in background"""
                try:
                    result = parse_coordinator.parse_all_accounts(
                        access_token, batch_progress_callback
                    )
                    
                    parse_progress[session_id].update({
                        'status': 'completed',
                        'progress_percentage': 100,
                        'batch_result': result,
                        'end_time': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    parse_progress[session_id].update({
                        'status': 'error',
                        'error': str(e),
                        'end_time': datetime.now().isoformat()
                    })
            
            # Start batch parsing
            batch_thread = threading.Thread(target=run_batch_parse)
            batch_thread.daemon = True
            batch_thread.start()
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': f'Batch parse started for {len(UNIFIED_ACCOUNTS)} accounts'
            })
            
        except Exception as e:
            logger.error(f"Error starting batch parse: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/statements/upload', methods=['POST'])
    @require_auth
    def api_upload_files():
        """Handle file uploads"""
        try:
            if 'files' not in request.files:
                return jsonify({'success': False, 'error': 'No files provided'}), 400
            
            files = request.files.getlist('files')
            if not files or files[0].filename == '':
                return jsonify({'success': False, 'error': 'No files selected'}), 400
            
            access_token = session['access_token']
            results = []
            
            for file in files:
                try:
                    result = upload_handler.process_upload(file, access_token)
                    results.append(result)
                except Exception as e:
                    results.append({
                        'success': False,
                        'filename': file.filename,
                        'error': str(e)
                    })
            
            # Calculate summary
            successful = len([r for r in results if r.get('success')])
            failed = len(results) - successful
            
            return jsonify({
                'success': failed == 0,
                'total_files': len(files),
                'successful_uploads': successful,
                'failed_uploads': failed,
                'results': results,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error processing uploads: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/statements/upload/validate', methods=['POST'])
    @require_auth
    def api_validate_upload():
        """Validate file format without uploading"""
        try:
            data = request.get_json()
            if not data or 'filename' not in data:
                return jsonify({'success': False, 'error': 'Filename required'}), 400
            
            result = upload_handler.validate_file_format(data['filename'])
            
            return jsonify({
                'success': True,
                'validation': result
            })
            
        except Exception as e:
            logger.error(f"Error validating upload: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/statements/upload/formats')
    @require_auth
    def api_upload_formats():
        """Get supported upload formats"""
        try:
            formats = upload_handler.get_supported_formats()
            
            return jsonify({
                'success': True,
                'formats': formats
            })
            
        except Exception as e:
            logger.error(f"Error getting formats: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/statements/download-file/<account_id>/<int:month>/<file_type>')
    @require_auth
    def api_download_statement_file(account_id, month, file_type):
        """Download a statement file from Teams/SharePoint"""
        try:
            year = request.args.get('year', type=int)
            if not year:
                return jsonify({'success': False, 'error': 'Year parameter is required'}), 400
            
            # Validate file type
            if file_type not in ['xlsx', 'pdf']:
                return jsonify({'success': False, 'error': 'Invalid file type'}), 400
                
            # Validate account exists in our unified config
            if account_id not in UNIFIED_ACCOUNTS:
                return jsonify({'success': False, 'error': 'Invalid account ID'}), 400
                
            # Get account configuration
            account_config = UNIFIED_ACCOUNTS[account_id]
            account_type = account_config['type']  # 'stp' or 'bbva'
            
            # Get the access token for file operations
            access_token = session['access_token']
            
            # Use your existing data loader to get file information
            account_data = data_loader.load_account_files_data(account_id, access_token, year)
            
            if not account_data or not account_data.get('months'):
                return jsonify({
                    'success': False, 
                    'error': 'No data found for this account and year'
                }), 404
            
            # Get month data
            month_key = f"{year}-{month:02d}"
            month_data = account_data['months'].get(month_key)
            
            if not month_data or month_data.get('status') == 'missing':
                return jsonify({
                    'success': False, 
                    'error': f'No files found for {account_id} {month_key}'
                }), 404
            
            # Get the file information based on type
            file_info = None
            if file_type == 'xlsx' and month_data.get('xlsx'):
                file_info = month_data['xlsx']
            elif file_type == 'pdf' and month_data.get('pdf'):
                file_info = month_data['pdf']
                
            if not file_info:
                return jsonify({
                    'success': False, 
                    'error': f'{file_type.upper()} file not available for this month'
                }), 404
            
            # Get file content from Teams/SharePoint using statements file access module
            from .file_access import get_statement_file_content, validate_file_identifiers
            
            # Get file IDs from the file info
            drive_id = file_info.get('drive_id')
            file_id = file_info.get('file_id')
            
            if not validate_file_identifiers(drive_id, file_id):
                # Debug: show what's actually in file_info
                logger.error(f"Invalid file IDs for {account_type} file. Available keys: {list(file_info.keys())}")
                logger.error(f"File info content: {file_info}")
                return jsonify({
                    'success': False,
                    'error': f'Invalid or missing file IDs. Available data: {list(file_info.keys())}'
                }), 404
            
            # Download file content using unified statements file access
            file_content = get_statement_file_content(drive_id, file_id, access_token)
            
            if not file_content:
                return jsonify({
                    'success': False,
                    'error': 'Failed to retrieve file from Teams'
                }), 500
            
            # Generate appropriate filename for download
            month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            month_name = month_names[month]
            filename = f"{account_id}_{year}_{month_name}.{file_type}"
            
            # Create a temporary file to send
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = tmp_file.name
            
            # Send file with appropriate mimetype
            mimetype_map = {
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'pdf': 'application/pdf'
            }
            
            logger.info(f"Downloading file: {filename} for {account_id} {month_key}")
            
            try:
                response = send_file(
                    tmp_file_path,
                    as_attachment=True,
                    download_name=filename,
                    mimetype=mimetype_map.get(file_type, 'application/octet-stream')
                )
                
                # Clean up temp file after sending
                @response.call_on_close
                def cleanup():
                    try:
                        os.unlink(tmp_file_path)
                    except:
                        pass
                
                return response
                
            except Exception as e:
                # Clean up temp file if send_file fails
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                raise e
            
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False, 
                'error': f'Download failed: {str(e)}'
            }), 500
    
    @app.route('/api/statements/health')
    @require_auth
    def api_health():
        """System health check"""
        try:
            validation = validate_unified_config()
            
            health_status = {
                'status': 'healthy' if all(validation.values()) else 'degraded',
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'configuration': all(validation.values()),
                    'data_loader': True,
                    'parse_coordinator': True,
                    'upload_handler': True
                },
                'validation': validation,
                'accounts': {
                    'total': len(UNIFIED_ACCOUNTS),
                    'stp': len([a for a in UNIFIED_ACCOUNTS.values() if a['type'] == 'stp']),
                    'bbva': len([a for a in UNIFIED_ACCOUNTS.values() if a['type'] == 'bbva'])
                }
            }
            
            return jsonify(health_status)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
        
    @app.route('/api/statements/inventory/<int:year>')
    @require_auth
    def api_get_inventory(year):
        """Get inventory for specific year"""
        try:
            access_token = session['access_token']
            inventory = inventory_manager.read_inventory(access_token)
            
            # Filter by year and format for frontend
            year_data = {}
            for account_id, account_data in inventory.get('accounts', {}).items():
                account_months = {}
                for month_key, month_data in account_data.items():
                    if month_key.startswith(str(year)):
                        account_months[month_key] = month_data
                
                if account_months:
                    year_data[account_id] = account_months
            
            return jsonify({
                'success': True,
                'year': year,
                'inventory': inventory,
                'year_data': year_data,
                'summary': {
                    'accounts_with_data': len(year_data),
                    'total_months': sum(len(months) for months in year_data.values()),
                    'last_updated': inventory.get('last_updated')
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting inventory: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/statements/refresh-inventory/<account_id>', methods=['POST'])
    @require_auth
    def api_refresh_account_inventory(account_id):
        """Refresh inventory for specific account"""
        try:
            if account_id not in UNIFIED_ACCOUNTS:
                return jsonify({'success': False, 'error': 'Invalid account ID'}), 400
            
            access_token = session['access_token']
            
            # Generate session ID for progress tracking
            session_id = f"refresh_{account_id}_{datetime.now().timestamp()}"
            
            # Initialize progress
            inventory_progress[session_id] = {
                'status': 'initializing',
                'account_id': account_id,
                'account_name': UNIFIED_ACCOUNTS[account_id]['name'],
                'progress_percentage': 0,
                'start_time': datetime.now().isoformat(),
                'operation': 'refresh_account'
            }
            
            def progress_callback(progress_data):
                """Update progress"""
                inventory_progress[session_id].update(progress_data)
                inventory_progress[session_id]['last_update'] = datetime.now().isoformat()
            
            def run_refresh():
                """Refresh in background thread"""
                try:
                    result = inventory_scanner.scan_single_account(
                        account_id, access_token, progress_callback
                    )
                    
                    inventory_progress[session_id].update({
                        'status': 'completed',
                        'progress_percentage': 100,
                        'result': result,
                        'end_time': datetime.now().isoformat()
                    })
                    
                    # Auto-cleanup after 5 minutes
                    def cleanup():
                        time.sleep(300)
                        if session_id in inventory_progress:
                            del inventory_progress[session_id]
                    
                    cleanup_thread = threading.Thread(target=cleanup)
                    cleanup_thread.daemon = True
                    cleanup_thread.start()
                    
                except Exception as e:
                    inventory_progress[session_id].update({
                        'status': 'error',
                        'error': str(e),
                        'end_time': datetime.now().isoformat()
                    })
            
            # Start background refresh
            refresh_thread = threading.Thread(target=run_refresh)
            refresh_thread.daemon = True
            refresh_thread.start()
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': f'Inventory refresh started for {UNIFIED_ACCOUNTS[account_id]["name"]}'
            })
            
        except Exception as e:
            logger.error(f"Error starting inventory refresh: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/statements/refresh-all-inventories', methods=['POST'])
    @require_auth
    def api_refresh_all_inventories():
        """Refresh inventory for all accounts"""
        try:
            access_token = session['access_token']
            
            # Generate batch session ID
            session_id = f"refresh_all_{datetime.now().timestamp()}"
            
            # Initialize batch progress
            inventory_progress[session_id] = {
                'status': 'initializing_batch',
                'session_type': 'batch',
                'total_accounts': len(UNIFIED_ACCOUNTS),
                'accounts_processed': 0,
                'accounts_successful': 0,
                'accounts_failed': 0,
                'current_account': None,
                'progress_percentage': 0,
                'account_results': {},
                'start_time': datetime.now().isoformat(),
                'operation': 'refresh_all'
            }
            
            def batch_progress_callback(progress_data):
                """Update batch progress"""
                inventory_progress[session_id].update(progress_data)
                inventory_progress[session_id]['last_update'] = datetime.now().isoformat()
            
            def run_batch_refresh():
                """Run batch refresh in background"""
                try:
                    result = inventory_scanner.scan_all_accounts(
                        access_token, batch_progress_callback
                    )
                    
                    inventory_progress[session_id].update({
                        'status': 'completed',
                        'progress_percentage': 100,
                        'batch_result': result,
                        'end_time': datetime.now().isoformat()
                    })
                    
                    # Auto-cleanup after 10 minutes for batch operations
                    def cleanup():
                        time.sleep(600)
                        if session_id in inventory_progress:
                            del inventory_progress[session_id]
                    
                    cleanup_thread = threading.Thread(target=cleanup)
                    cleanup_thread.daemon = True
                    cleanup_thread.start()
                    
                except Exception as e:
                    inventory_progress[session_id].update({
                        'status': 'error',
                        'error': str(e),
                        'end_time': datetime.now().isoformat()
                    })
            
            # Start batch refresh
            batch_thread = threading.Thread(target=run_batch_refresh)
            batch_thread.daemon = True
            batch_thread.start()
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': f'Batch inventory refresh started for {len(UNIFIED_ACCOUNTS)} accounts'
            })
            
        except Exception as e:
            logger.error(f"Error starting batch refresh: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/statements/inventory-progress/<session_id>')
    @require_auth
    def api_inventory_progress(session_id):
        """Get inventory refresh progress"""
        if session_id not in inventory_progress:
            return jsonify({'success': False, 'error': 'Invalid session ID'}), 404
        
        progress_data = inventory_progress[session_id].copy()
        progress_data['timestamp'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'progress': progress_data
        })

    @app.route('/api/statements/inventory/clear-cache', methods=['POST'])
    @require_auth
    def api_clear_inventory_cache():
        """Clear inventory cache to force refresh"""
        try:
            inventory_manager.clear_cache()
            
            return jsonify({
                'success': True,
                'message': 'Inventory cache cleared'
            })
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/statements/ui-data/<int:year>')
    @require_auth
    def api_statements_ui_data(year):
        """Get statements data formatted for UI display"""
        try:
            access_token = session['access_token']
            statements_data = data_loader.load_unified_statements_data(access_token, year)
            
            # Convert to UI-friendly format
            ui_data = {}
            for account_id, account_data in statements_data.items():
                if account_data.get('total_files', 0) > 0:
                    ui_data[account_id] = {
                        'total_files': account_data['total_files'],
                        'months': []
                    }
                    
                    for month_key, month_data in account_data.get('months', {}).items():
                        if month_data.get('status') != 'missing':
                            month_num = int(month_key.split('-')[1])
                            ui_data[account_id]['months'].append({
                                'month': month_num,
                                'has_pdf': bool(month_data.get('pdf')),
                                'has_xlsx': bool(month_data.get('xlsx'))
                            })
            
            return jsonify({
                'success': True,
                'ui_data': ui_data,
                'year': year
            })
            
        except Exception as e:
            logger.error(f"Error getting UI data: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

def get_statements_route_info():
    """Get information about registered routes"""
    return {
        'config_routes': [
            'GET /api/statements/config',
            'GET /api/statements/health'
        ],
        'data_routes': [
            'GET /api/statements/data/<year>',
            'GET /api/statements/load-account-data/<account_id>',
            'GET /api/statements/account/<id>/summary',
            'GET /api/statements/system-summary/<year>'
        ],
        'inventory_routes': [  # NEW SECTION
            'GET /api/statements/inventory/<year>',
            'POST /api/statements/refresh-inventory/<account_id>',
            'POST /api/statements/refresh-all-inventories',
            'GET /api/statements/inventory-progress/<session_id>',
            'POST /api/statements/inventory/clear-cache'
        ],
        'parse_routes': [
            'POST /api/statements/parse/<account_id>',
            'GET /api/statements/parse-progress/<session_id>',
            'POST /api/statements/parse-all'
        ],
        'upload_routes': [
            'POST /api/statements/upload',
            'POST /api/statements/upload/validate',
            'GET /api/statements/upload/formats'
        ],
        'download_routes': [
            'GET /api/statements/download-file/<account_id>/<month>/<file_type>'
        ]
    }

def validate_statements_routes(app):
    """Validate that all routes are properly registered"""
    expected_routes = [
        'api_statements_config',
        'api_statements_data', 
        'api_load_account_data',
        'api_account_summary',
        'api_system_summary',
        'api_parse_account',
        'api_parse_progress',
        'api_parse_all',
        'api_upload_files',
        'api_validate_upload',
        'api_upload_formats',
        'api_download_statement_file',
        'api_health'
    ]
    
    registered_routes = [rule.endpoint for rule in app.url_map.iter_rules()]
    
    validation = {}
    for route in expected_routes:
        validation[route] = route in registered_routes
    
    return validation