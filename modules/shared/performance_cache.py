# modules/shared/performance_cache.py - Production Version
"""
Unified Performance Cache for STP and BBVA Systems

This module provides caching, async operations, and performance optimization
for both STP and BBVA file management systems.
"""

import time
import threading
import hashlib
import json
import logging
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List, Callable
from flask import g, has_request_context, copy_current_request_context

logger = logging.getLogger(__name__)

class UnifiedPerformanceCache:
    """Unified cache for STP and BBVA operations"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = {
            'file_list': 60,       # 1 minute - faster detection of changes
            'file_content': 1800,  # 30 minutes - keep long for actual file content
            'parse_status': 300,   # 5 minutes
            'calendar_data': 30    # 30 seconds - very fast calendar refresh
        }
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=6)
        
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key"""
        key_data = f"{prefix}_{str(args)}_{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_cached_data(self, key: str, cache_type: str = 'file_list') -> Optional[Any]:
        """Get cached data if valid"""
        with self.lock:
            if key in self.cache:
                data, timestamp = self.cache[key]
                timeout = self.cache_timeout.get(cache_type, 300)
                
                if time.time() - timestamp < timeout:
                    logger.debug(f"Cache HIT for key: {key[:20]}...")
                    return data
                else:
                    # Expired, remove from cache
                    del self.cache[key]
                    logger.debug(f"Cache EXPIRED for key: {key[:20]}...")
            
            logger.debug(f"Cache MISS for key: {key[:20]}...")
            return None
    
    def set_cached_data(self, key: str, data: Any, cache_type: str = 'file_list'):
        """Cache data with timestamp"""
        with self.lock:
            self.cache[key] = (data, time.time())
            logger.debug(f"Cache SET for key: {key[:20]}... (type: {cache_type})")
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all cache keys containing pattern"""
        with self.lock:
            keys_to_remove = [key for key in self.cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching '{pattern}'")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_entries = len(self.cache)
            current_time = time.time()
            
            valid_entries = 0
            expired_entries = 0
            
            for key, (data, timestamp) in self.cache.items():
                if current_time - timestamp < 300:  # Using default timeout
                    valid_entries += 1
                else:
                    expired_entries += 1
            
            return {
                'total_entries': total_entries,
                'valid_entries': valid_entries,
                'expired_entries': expired_entries,
                'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1)
            }

# Global cache instance
unified_cache = UnifiedPerformanceCache()

def cached_operation(cache_type: str = 'file_list', timeout: Optional[int] = None):
    """Decorator for caching operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = unified_cache._generate_cache_key(
                f"{func.__module__}.{func.__name__}", *args, **kwargs
            )
            
            # Try cache first
            cached_result = unified_cache.get_cached_data(cache_key, cache_type)
            if cached_result is not None:
                return cached_result
            
            # Make actual call and cache result
            try:
                result = func(*args, **kwargs)
                unified_cache.set_cached_data(cache_key, result, cache_type)
                return result
            except Exception as e:
                logger.error(f"Error in cached operation {func.__name__}: {e}")
                raise
        
        return wrapper
    return decorator

class ContextPreservingAsyncProcessor:
    """Async processor that preserves Flask request context"""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def process_accounts_parallel(self, accounts_config: Dict[str, Any], 
                                access_token: str, year: int, 
                                file_getter_func: Callable) -> Dict[str, Any]:
        """Process multiple accounts in parallel with request context"""
        
        results = {}
        
        # Process sequentially if no request context or small number of accounts
        if not has_request_context() or len(accounts_config) <= 2:
            logger.debug("Processing accounts sequentially (no request context or few accounts)")
            for account_key, account_info in accounts_config.items():
                try:
                    result = self._safe_account_processing(
                        account_key, account_info, access_token, year, file_getter_func
                    )
                    results[account_key] = result
                    logger.debug(f"Completed processing for account: {account_key}")
                except Exception as e:
                    logger.error(f"Error processing account {account_key}: {e}")
                    results[account_key] = self._create_fallback_data(account_key, year)
            
            return results
        
        # For parallel processing, copy request context
        futures = {}
        
        for account_key, account_info in accounts_config.items():
            # Copy the current request context for each thread
            @copy_current_request_context
            def process_with_context(key=account_key, info=account_info):
                return self._safe_account_processing(
                    key, info, access_token, year, file_getter_func
                )
            
            future = self.executor.submit(process_with_context)
            futures[future] = account_key
        
        # Collect results as they complete
        for future in as_completed(futures, timeout=60):
            account_key = futures[future]
            try:
                result = future.result(timeout=30)
                results[account_key] = result
                logger.debug(f"Completed processing for account: {account_key}")
            except Exception as e:
                logger.error(f"Error processing account {account_key}: {e}")
                # Provide fallback data
                results[account_key] = self._create_fallback_data(account_key, year)
        
        return results
    
    def _safe_account_processing(self, account_key: str, account_info: Any, 
                               access_token: str, year: int, 
                               file_getter_func: Callable) -> Dict[str, Any]:
        """Safely process single account with error handling"""
        try:
            # Use cached file getter function
            files = file_getter_func(account_key, access_token, year)
            return self._process_account_files(account_key, files, year, account_info)
        except Exception as e:
            logger.error(f"Error in safe account processing for {account_key}: {e}")
            raise
    
    def _process_account_files(self, account_key: str, files: List[Dict], 
                             year: int, account_info: Any) -> Dict[str, Any]:
        """Process files for an account into calendar format"""
        
        months_data = {}
        
        # Process each month
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            month_files = [f for f in files if f.get('date_string') == month_key]
            
            # Determine file types based on system
            pdf_file = next((f for f in month_files if f.get('extension') == 'pdf'), None)
            xlsx_file = next((f for f in month_files if f.get('extension') == 'xlsx'), None)
            
            # Different logic for BBVA vs STP
            if hasattr(account_info, 'get') and 'clabe' in str(account_info):
                # This is a BBVA account (uses CLABE)
                if pdf_file:
                    status = 'complete'  # BBVA only needs PDF
                else:
                    status = 'missing'
            else:
                # This is an STP account (needs both PDF and Excel)
                if pdf_file and xlsx_file:
                    status = 'complete'
                elif pdf_file or xlsx_file:
                    status = 'partial'
                else:
                    status = 'missing'

            months_data[month_key] = {
                'pdf': pdf_file,
                'xlsx': xlsx_file,
                'status': status,
                'month_name': self._get_month_name(month),
                'parse_status': 'not_parsed',
                'transaction_count': 0
            }
        
        return {
            'account_info': account_info,
            'months': months_data,
            'total_files': len(files)
        }
    
    def _create_fallback_data(self, account_key: str, year: int) -> Dict[str, Any]:
        """Create fallback data when account processing fails"""
        months_data = {}
        for month in range(1, 13):
            month_key = f"{year}-{month:02d}"
            months_data[month_key] = {
                'pdf': None,
                'xlsx': None,
                'status': 'error',
                'month_name': self._get_month_name(month),
                'parse_status': 'error',
                'transaction_count': 0
            }
        
        return {
            'account_info': {'name': f'Account {account_key}', 'error': True},
            'months': months_data,
            'total_files': 0
        }
    
    def _get_month_name(self, month: int) -> str:
        """Get month name"""
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        return months[month - 1]

# Global async processor
async_processor = ContextPreservingAsyncProcessor()

# Cached versions of common functions with proper error handling
@cached_operation(cache_type='file_list', timeout=300)
def get_stp_files_cached(account_number: str, access_token: str, year: int):
    """Cached version of STP file retrieval"""
    try:
        from modules.stp.stp_files import get_stp_files
        return get_stp_files(account_number, access_token, year)
    except Exception as e:
        logger.error(f"Error getting STP files for {account_number}: {e}")
        return []  # Return empty list instead of failing

@cached_operation(cache_type='file_list', timeout=300)
def get_bbva_files_cached(account_clabe: str, access_token: str, year: int):
    """Cached version of BBVA file retrieval"""
    try:
        from modules.bbva.bbva_files import get_bbva_files as get_bbva_files_module
        return get_bbva_files_module(account_clabe, access_token, year)
    except Exception as e:
        logger.error(f"Error getting BBVA files for {account_clabe}: {e}")
        return []  # Return empty list instead of failing

def create_stp_calendar_data_fast(access_token: str, year: int):
    """Fast STP calendar creation with transaction counts"""
    try:
        from collections import OrderedDict
        
        # Use ordered account mapping with correct names and order
        account_mapping = OrderedDict([
            ('646180559700000009', {'name': 'STP SA'}),        # First tab
            ('646180403000000004', {'name': 'STP IP - PD'}),   # Second tab  
            ('646990403000000003', {'name': 'STP IP - PI'})    # Third tab
        ])
        
        # Load tracking data AND record counts for all STP accounts
        logger.debug("Loading STP tracking data and record counts for complete calendar creation...")
        start_time = time.time()
        
        # Load tracking data for parse status
        from modules.stp.stp_database import get_parse_tracking_data
        tracking_data = get_parse_tracking_data(access_token)
        
        # Load record counts for transaction counts
        from modules.stp.stp_analytics import get_monthly_record_counts
        record_counts = get_monthly_record_counts(access_token, year)
        
        load_time = time.time() - start_time
        logger.debug(f"STP data loaded in {load_time:.2f}s - tracking: {len(tracking_data)} accounts, counts: {len(record_counts)} accounts")
        
        # Build calendar with all data
        results = OrderedDict()
        
        for account_key, account_info in account_mapping.items():
            try:
                # Get files for account (cached)
                files = get_stp_files_cached(account_key, access_token, year)
                
                # Get tracking and count data for this specific account
                account_tracking = tracking_data.get(account_key, {})
                account_counts = record_counts.get(account_key, {})
                
                # Create month structure with complete data integration
                month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December']
                
                months_data = {}
                for month_num, month_name in enumerate(month_names, 1):
                    month_key = f"{year}-{month_num:02d}"
                    
                    # Find files for this month
                    month_files = [f for f in files if f.get('date_string') == month_key]
                    pdf_file = next((f for f in month_files if f.get('extension') == 'pdf'), None)
                    xlsx_file = next((f for f in month_files if f.get('extension') == 'xlsx'), None)
                    
                    # Determine status (STP needs both PDF and Excel)
                    if pdf_file and xlsx_file:
                        status = 'complete'
                    elif pdf_file or xlsx_file:
                        status = 'partial'
                    else:
                        status = 'missing'
                    
                    # Get parse status AND transaction count
                    parse_status = 'not_parsed'
                    transaction_count = account_counts.get(month_key, 0)
                    
                    if xlsx_file:
                        filename = xlsx_file['filename']
                        if filename in account_tracking:
                            tracking_info = account_tracking[filename]
                            
                            if tracking_info.get('status') == 'different_format':
                                parse_status = 'different_format'
                            elif tracking_info.get('transaction_count', 0) >= 0:
                                parse_status = 'parsed'
                                # Use tracking data count if available, otherwise use analytics count
                                if 'transaction_count' in tracking_info:
                                    transaction_count = tracking_info.get('transaction_count', 0)
                    
                    months_data[month_key] = {
                        'pdf': pdf_file,
                        'xlsx': xlsx_file,
                        'status': status,
                        'month_name': month_name,
                        'parse_status': parse_status,
                        'transaction_count': transaction_count
                    }
                
                # Match the expected structure with complete data
                results[account_key] = {
                    'account_info': account_info,
                    'account_type': account_info['name'],
                    'months': months_data,
                    'total_files': len(files),
                    # Include account-level transaction summary
                    'total_transactions': sum(month['transaction_count'] for month in months_data.values()),
                    'parsed_months': sum(1 for month in months_data.values() if month['parse_status'] == 'parsed')
                }
                
                logger.debug(f"Complete STP data for {account_key} - {account_info['name']}: {len(files)} files, {results[account_key]['total_transactions']} transactions")
                
            except Exception as e:
                logger.error(f"Error processing STP account {account_key}: {e}")
                # Create fallback data with proper structure
                results[account_key] = {
                    'account_info': account_info,
                    'account_type': account_info['name'],
                    'total_files': 0,
                    'months': {
                        f"{year}-{month:02d}": {
                            'pdf': None, 'xlsx': None, 'status': 'missing',
                            'month_name': month_names[month-1],
                            'parse_status': 'not_parsed',
                            'transaction_count': 0
                        }
                        for month in range(1, 13)
                    },
                    'total_transactions': 0,
                    'parsed_months': 0
                }
        
        total_time = time.time() - start_time
        logger.debug(f"Complete STP calendar created in {total_time:.2f}s for {len(results)} accounts")
        return results
        
    except Exception as e:
        logger.error(f"Error in fast STP calendar creation: {e}")
        return {}

def create_bbva_calendar_data_fast(access_token: str, year: int):
    """Complete server-side BBVA calendar with parse status and transaction counts"""
    try:
        from collections import OrderedDict
        
        # Define accounts in the desired order
        ordered_bbva_accounts = OrderedDict([
            ('012180001198203451', {'name': 'BBVA MX MXN', 'clabe': '012180001198203451', 'account_key': 'bbva_mx_mxn'}),
            ('012180001201205883', {'name': 'BBVA MX USD', 'clabe': '012180001201205883', 'account_key': 'bbva_mx_usd'}),
            ('012180001182790637', {'name': 'BBVA SA MXN', 'clabe': '012180001182790637', 'account_key': 'bbva_sa_mxn'}),
            ('012222001182793149', {'name': 'BBVA SA USD', 'clabe': '012222001182793149', 'account_key': 'bbva_sa_usd'}),
            ('012180001232011554', {'name': 'BBVA IP Corp', 'clabe': '012180001232011554', 'account_key': 'bbva_ip_corp'}),
            ('012180001232011635', {'name': 'BBVA IP Clientes', 'clabe': '012180001232011635', 'account_key': 'bbva_ip_clientes'})
        ])
        
        # Load tracking data for all accounts
        from modules.bbva.bbva_database import get_bbva_parse_tracking_data
        logger.debug("Loading BBVA tracking data for complete calendar creation...")
        start_time = time.time()
        
        tracking_data = get_bbva_parse_tracking_data(access_token)
        
        load_time = time.time() - start_time
        logger.debug(f"Tracking data loaded in {load_time:.2f}s for {len(tracking_data)} accounts")
        
        # Build complete calendar with all data
        results = OrderedDict()
        
        for clabe, account_info in ordered_bbva_accounts.items():
            try:
                # Get files for account (cached)
                files = get_bbva_files_cached(clabe, access_token, year)
                
                # Get tracking data for this specific account
                account_tracking = tracking_data.get(clabe, {})
                
                # Create month structure with complete data integration
                month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December']
                
                months_data = {}
                for month_num, month_name in enumerate(month_names, 1):
                    month_key = f"{year}-{month_num:02d}"
                    pdf_file = next((f for f in files if f['date_string'] == month_key), None)
                    
                    # Determine basic status
                    status = 'complete' if pdf_file else 'missing'
                    
                    # Get both parse status AND transaction count
                    parse_status = 'not_parsed'
                    transaction_count = 0
                    
                    if pdf_file:
                        filename = pdf_file['filename']
                        if filename in account_tracking:
                            tracking_info = account_tracking[filename]
                            
                            if tracking_info.get('parse_status') == 'failed':
                                parse_status = 'parse_error'
                            elif tracking_info.get('transaction_count', 0) >= 0 and 'transaction_count' in tracking_info:
                                parse_status = 'parsed'
                                transaction_count = tracking_info.get('transaction_count', 0)
                    
                    months_data[month_key] = {
                        'pdf': pdf_file,
                        'xlsx': None,
                        'status': status,
                        'month_name': month_name,
                        'parse_status': parse_status,
                        'transaction_count': transaction_count,
                        'record_count': transaction_count  # Alternative field name for compatibility
                    }
                
                # Match the expected structure with complete data
                results[clabe] = {
                    'account_info': account_info,
                    'account_type': account_info['name'],
                    'months': months_data,
                    'total_files': len(files),
                    # Include account-level transaction summary
                    'total_transactions': sum(month['transaction_count'] for month in months_data.values()),
                    'parsed_months': sum(1 for month in months_data.values() if month['parse_status'] == 'parsed')
                }
                
                logger.debug(f"Complete data for {clabe} - {account_info['name']}: {len(files)} files, {results[clabe]['total_transactions']} transactions")
                
            except Exception as e:
                logger.error(f"Error processing BBVA account {clabe}: {e}")
                # Create fallback data with proper structure
                results[clabe] = {
                    'account_info': account_info,
                    'account_type': account_info['name'],
                    'total_files': 0,
                    'months': {
                        f"{year}-{month:02d}": {
                            'pdf': None, 'xlsx': None, 'status': 'missing',
                            'month_name': month_names[month-1],
                            'parse_status': 'not_parsed',
                            'transaction_count': 0,
                            'record_count': 0
                        }
                        for month in range(1, 13)
                    },
                    'total_transactions': 0,
                    'parsed_months': 0
                }
        
        total_time = time.time() - start_time
        logger.debug(f"Complete BBVA calendar created in {total_time:.2f}s for {len(results)} accounts")
        return results
        
    except Exception as e:
        logger.error(f"Error in complete BBVA calendar creation: {e}")
        return {}

def warm_cache_for_user(access_token: str, year: int):
    """Warm cache with commonly requested data"""
    logger.debug(f"Warming cache for year {year}")
    
    try:
        # Warm STP cache
        stp_data = create_stp_calendar_data_fast(access_token, year)
        if stp_data:
            logger.debug("STP cache warmed successfully")
        else:
            logger.warning("STP cache warming returned empty data")
        
        # Warm BBVA cache  
        bbva_data = create_bbva_calendar_data_fast(access_token, year)
        if bbva_data:
            logger.debug("BBVA cache warmed successfully")
        else:
            logger.warning("BBVA cache warming returned empty data")
        
    except Exception as e:
        logger.error(f"Error warming cache: {e}")

def get_performance_stats():
    """Get performance statistics"""
    return {
        'cache_stats': unified_cache.get_cache_stats(),
        'active_threads': threading.active_count(),
        'cache_size': len(unified_cache.cache)
    }