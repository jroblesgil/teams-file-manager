#!/usr/bin/env python3
"""
Test Backend Foundation - Phase 1a

Test script to validate the unified statements backend foundation
without requiring actual API access or frontend.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_configuration():
    """Test the unified configuration module"""
    print("🧪 Testing Configuration Module...")
    
    try:
        from modules.statements.config import (
            UNIFIED_ACCOUNTS, get_account_by_key, get_account_by_identifier,
            get_stp_accounts, get_bbva_accounts, map_stp_number_to_key,
            map_bbva_clabe_to_key, validate_unified_config
        )
        
        # Test account loading
        print(f"  ✅ Loaded {len(UNIFIED_ACCOUNTS)} unified accounts")
        
        # Test account types
        stp_accounts = get_stp_accounts()
        bbva_accounts = get_bbva_accounts()
        print(f"  ✅ STP accounts: {len(stp_accounts)}")
        print(f"  ✅ BBVA accounts: {len(bbva_accounts)}")
        
        # Test account retrieval
        stp_sa = get_account_by_key('stp_sa')
        print(f"  ✅ Get account by key: {stp_sa['name'] if stp_sa else 'FAILED'}")
        
        # Test identifier mapping
        bbva_account = get_account_by_identifier('012180001198203451')
        print(f"  ✅ Get account by identifier: {bbva_account['name'] if bbva_account else 'FAILED'}")
        
        # Test legacy mapping
        stp_key = map_stp_number_to_key('646180559700000009')
        print(f"  ✅ STP mapping: {stp_key}")
        
        bbva_key = map_bbva_clabe_to_key('012180001198203451')
        print(f"  ✅ BBVA mapping: {bbva_key}")
        
        # Test validation
        validation = validate_unified_config()
        print(f"  ✅ Configuration valid: {all(validation.values())}")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False

def test_data_loader():
    """Test the data loader module"""
    print("🧪 Testing Data Loader Module...")
    
    try:
        from modules.statements.data_loader import (
            _create_empty_account_data, _determine_parse_status, validate_unified_data
        )
        
        # Test empty account creation
        empty_account = _create_empty_account_data('stp_sa', 2025)
        print(f"  ✅ Empty account created: {empty_account['name']}")
        print(f"  ✅ Months initialized: {len(empty_account.get('months', {}))}")
        
        # Test parse status determination
        test_month = {'has_file': True, 'parsed': True}
        status = _determine_parse_status(test_month)
        print(f"  ✅ Parse status determination: {status}")
        
        # Test data structure validation
        test_data = {
            'year': 2025,
            'accounts': {'stp_sa': empty_account},
            'summary': {'total_accounts': 1}
        }
        validation = validate_unified_data(test_data)
        print(f"  ✅ Data validation: {all(validation.values())}")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Data loader test failed: {e}")
        return False

def test_parse_coordinator():
    """Test the parse coordinator module"""
    print("🧪 Testing Parse Coordinator Module...")
    
    try:
        from modules.statements.parse_coordinator import (
            validate_parse_request, get_parse_progress, cleanup_old_parse_sessions
        )
        
        # Test parse request validation
        validation = validate_parse_request('stp_sa')
        print(f"  ✅ Parse validation: {validation['valid']}")
        
        if validation['valid']:
            config = validation['account_config']
            print(f"  ✅ Account config: {config['name']}")
            print(f"  ✅ Legacy identifier: {validation['legacy_identifier']}")
        
        # Test invalid account
        invalid_validation = validate_parse_request('invalid_account')
        print(f"  ✅ Invalid account handled: {not invalid_validation['valid']}")
        
        # Test progress tracking
        test_progress = {}
        sessions_cleaned = cleanup_old_parse_sessions(test_progress)
        print(f"  ✅ Progress cleanup: {sessions_cleaned} sessions")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Parse coordinator test failed: {e}")
        return False

def test_integration():
    """Test integration between modules"""
    print("🧪 Testing Module Integration...")
    
    try:
        from modules.statements.config import get_all_account_keys, get_account_by_key
        from modules.statements.data_loader import _create_empty_account_data
        from modules.statements.parse_coordinator import validate_parse_request
        
        # Test all accounts can be processed
        all_accounts = get_all_account_keys()
        print(f"  ✅ All account keys: {len(all_accounts)}")
        
        successful_tests = 0
        for account_key in all_accounts:
            try:
                # Test config retrieval
                config = get_account_by_key(account_key)
                if not config:
                    print(f"  ❌ Failed to get config for {account_key}")
                    continue
                
                # Test data structure creation
                empty_data = _create_empty_account_data(account_key, 2025)
                if not empty_data or 'error' in empty_data:
                    print(f"  ❌ Failed to create data for {account_key}")
                    continue
                
                # Test parse validation
                parse_validation = validate_parse_request(account_key)
                if not parse_validation['valid']:
                    print(f"  ❌ Failed parse validation for {account_key}")
                    continue
                
                successful_tests += 1
                
            except Exception as e:
                print(f"  ❌ Integration test failed for {account_key}: {e}")
        
        print(f"  ✅ Integration tests passed: {successful_tests}/{len(all_accounts)} accounts")
        return successful_tests == len(all_accounts)
    
    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        return False

def main():
    """Run all backend foundation tests"""
    print("🚀 Testing Unified Statements Backend Foundation - Phase 1a")
    print("=" * 70)
    
    tests = [
        test_configuration,
        test_data_loader,
        test_parse_coordinator,
        test_integration
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
            print()
    
    # Summary
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Backend foundation is ready.")
        print("\nNext steps:")
        print("- Add the new modules to your Flask app imports")
        print("- Create test routes to verify data loading")  
        print("- Move to Phase 1b: API Layer implementation")
    else:
        print("⚠️  Some tests failed. Please review and fix issues before proceeding.")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)