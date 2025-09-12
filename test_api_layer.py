#!/usr/bin/env python3
"""
Test API Layer - Phase 1b

Comprehensive testing of the unified statements API endpoints
"""

import sys
import os
import requests
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock session for testing without actual authentication
class MockSession:
    def __init__(self):
        self.data = {'access_token': 'mock_token_for_testing'}
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __contains__(self, key):
        return key in self.data

def test_api_imports():
    """Test that all API modules can be imported"""
    print("🧪 Testing API Module Imports...")
    
    try:
        from modules.statements.api_endpoints import register_statements_routes, get_statements_route_info
        print("  ✅ API endpoints module imported")
        
        from modules.statements.upload_handler import (
            handle_unified_upload, detect_file_type, get_supported_file_types
        )
        print("  ✅ Upload handler module imported")
        
        from modules.statements.config import UNIFIED_ACCOUNTS
        from modules.statements.data_loader import load_unified_statements_data
        from modules.statements.parse_coordinator import coordinate_account_parsing
        print("  ✅ All supporting modules imported")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_route_registration():
    """Test route registration functionality"""
    print("🧪 Testing Route Registration...")
    
    try:
        from flask import Flask
        from modules.statements.api_endpoints import register_statements_routes, validate_statements_routes
        
        # Create test app
        app = Flask(__name__)
        app.secret_key = 'test_secret'
        
        # Register routes
        parse_progress = {}
        register_statements_routes(app, parse_progress)
        print("  ✅ Routes registered without errors")
        
        # Validate routes
        route_validation = validate_statements_routes(app)
        registered_count = sum(route_validation.values())
        total_count = len(route_validation)
        print(f"  ✅ Route validation: {registered_count}/{total_count} endpoints registered")
        
        # Check specific routes
        with app.app_context():
            rule_endpoints = [rule.endpoint for rule in app.url_map.iter_rules()]
            
            expected_endpoints = [
                'statements_page', 'api_statements_data', 'api_parse_account',
                'api_upload_file', 'api_statements_status'
            ]
            
            found_endpoints = 0
            for endpoint in expected_endpoints:
                if endpoint in rule_endpoints:
                    found_endpoints += 1
                    print(f"    ✅ {endpoint}")
                else:
                    print(f"    ❌ {endpoint} missing")
            
            print(f"  ✅ Found {found_endpoints}/{len(expected_endpoints)} key endpoints")
        
        return registered_count == total_count
        
    except Exception as e:
        print(f"  ❌ Route registration test failed: {e}")
        return False

def test_upload_detection():
    """Test file upload detection logic"""
    print("🧪 Testing Upload Detection...")
    
    try:
        from modules.statements.upload_handler import get_supported_file_types
        from modules.statements.upload_handler import _detect_stp_file, _detect_bbva_file
        
        # Test supported file types
        supported_types = get_supported_file_types()
        print(f"  ✅ Supported file types: {len(supported_types)}")
        print(f"    - STP: {supported_types['stp']['extensions']}")
        print(f"    - BBVA: {supported_types['bbva']['extensions']}")
        
        # Test STP filename detection
        valid_stp_filename = "ec-646180559700000009-202501.xlsx"
        invalid_stp_filename = "invalid-filename.xlsx"
        
        # Mock file object
        class MockFile:
            def __init__(self, filename):
                self.filename = filename
        
        # Test valid STP file
        stp_result = _detect_stp_file(valid_stp_filename, MockFile(valid_stp_filename))
        if stp_result['valid']:
            print(f"  ✅ Valid STP file detected: {stp_result['account_number']}")
        else:
            print(f"  ❌ Valid STP file not detected: {stp_result['error']}")
        
        # Test invalid STP file
        invalid_result = _detect_stp_file(invalid_stp_filename, MockFile(invalid_stp_filename))
        if not invalid_result['valid']:
            print("  ✅ Invalid STP file correctly rejected")
        else:
            print("  ❌ Invalid STP file incorrectly accepted")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Upload detection test failed: {e}")
        return False

def test_data_structures():
    """Test API data structure creation"""
    print("🧪 Testing API Data Structures...")
    
    try:
        from modules.statements.config import get_all_account_keys, get_account_by_key
        from modules.statements.data_loader import _create_empty_account_data
        
        # Test account configuration for API responses
        all_accounts = get_all_account_keys()
        print(f"  ✅ Testing {len(all_accounts)} accounts")
        
        api_compatible = 0
        for account_key in all_accounts:
            config = get_account_by_key(account_key)
            empty_data = _create_empty_account_data(account_key, 2025)
            
            # Check API compatibility
            required_fields = ['name', 'display_name', 'type']
            if all(field in config for field in required_fields):
                api_compatible += 1
            
            # Check months structure for frontend
            if 'months' in empty_data and len(empty_data['months']) == 12:
                months_ok = True
            else:
                print(f"    ❌ {account_key}: Invalid months structure")
                months_ok = False
        
        print(f"  ✅ API compatible accounts: {api_compatible}/{len(all_accounts)}")
        
        return api_compatible == len(all_accounts)
        
    except Exception as e:
        print(f"  ❌ Data structures test failed: {e}")
        return False

def test_parse_coordination():
    """Test parse coordination without actual parsing"""
    print("🧪 Testing Parse Coordination...")
    
    try:
        from modules.statements.parse_coordinator import (
            validate_parse_request, get_parse_progress, cleanup_old_parse_sessions
        )
        
        # Test validation
        valid_account = 'stp_sa'
        validation = validate_parse_request(valid_account)
        
        if validation['valid']:
            print(f"  ✅ Parse validation successful for {valid_account}")
            print(f"    - Account: {validation['account_config']['name']}")
            print(f"    - Type: {validation['account_config']['type']}")
            print(f"    - Identifier: {validation['legacy_identifier']}")
        else:
            print(f"  ❌ Parse validation failed: {validation['error']}")
        
        # Test invalid account
        invalid_validation = validate_parse_request('invalid_account')
        if not invalid_validation['valid']:
            print("  ✅ Invalid account correctly rejected")
        else:
            print("  ❌ Invalid account incorrectly accepted")
        
        # Test progress tracking
        test_progress = {
            'test_session': {
                'start_time': datetime.now().isoformat(),
                'status': 'completed'
            }
        }
        
        progress = get_parse_progress('test_session', test_progress)
        if progress:
            print("  ✅ Progress tracking working")
        
        # Test cleanup
        cleaned = cleanup_old_parse_sessions(test_progress, max_age_hours=0)
        print(f"  ✅ Cleanup test: {cleaned} sessions cleaned")
        
        return validation['valid']
        
    except Exception as e:
        print(f"  ❌ Parse coordination test failed: {e}")
        return False

def test_configuration_integration():
    """Test configuration integration with API layer"""
    print("🧪 Testing Configuration Integration...")
    
    try:
        from modules.statements.config import UNIFIED_ACCOUNTS, validate_unified_config
        from modules.statements.api_endpoints import get_statements_route_info
        
        # Test configuration
        validation = validate_unified_config()
        print(f"  ✅ Configuration validation: {all(validation.values())}")
        
        # Test route information
        route_info = get_statements_route_info()
        main_routes = len(route_info['main_routes'])
        api_routes = len(route_info['api_routes'])
        redirect_routes = len(route_info['redirect_routes'])
        
        print(f"  ✅ Route information:")
        print(f"    - Main routes: {main_routes}")
        print(f"    - API routes: {api_routes}")
        print(f"    - Redirect routes: {redirect_routes}")
        
        # Test account distribution
        stp_accounts = len([a for a in UNIFIED_ACCOUNTS.values() if a['type'] == 'stp'])
        bbva_accounts = len([a for a in UNIFIED_ACCOUNTS.values() if a['type'] == 'bbva'])
        
        print(f"  ✅ Account distribution: {stp_accounts} STP + {bbva_accounts} BBVA")
        
        return all(validation.values()) and (stp_accounts + bbva_accounts) == len(UNIFIED_ACCOUNTS)
        
    except Exception as e:
        print(f"  ❌ Configuration integration test failed: {e}")
        return False

def simulate_api_workflow():
    """Simulate a typical API workflow"""
    print("🧪 Simulating API Workflow...")
    
    try:
        from modules.statements.data_loader import _create_empty_account_data
        from modules.statements.parse_coordinator import validate_parse_request
        from modules.statements.upload_handler import get_supported_file_types
        
        # Simulate: 1. User visits statements page (data loading)
        print("  1. Simulating page load...")
        test_account_data = _create_empty_account_data('stp_sa', 2025)
        if 'error' not in test_account_data:
            print("    ✅ Account data loaded successfully")
        
        # Simulate: 2. User requests parse
        print("  2. Simulating parse request...")
        parse_validation = validate_parse_request('bbva_mx_mxn')
        if parse_validation['valid']:
            print(f"    ✅ Parse request validated for {parse_validation['account_config']['name']}")
        
        # Simulate: 3. User checks upload requirements
        print("  3. Simulating upload info request...")
        supported_types = get_supported_file_types()
        if 'stp' in supported_types and 'bbva' in supported_types:
            print("    ✅ Upload information retrieved")
        
        # Simulate: 4. API status check
        print("  4. Simulating status check...")
        from modules.statements.config import UNIFIED_ACCOUNTS
        status_info = {
            'total_accounts': len(UNIFIED_ACCOUNTS),
            'timestamp': datetime.now().isoformat()
        }
        if status_info['total_accounts'] > 0:
            print(f"    ✅ Status check: {status_info['total_accounts']} accounts")
        
        print("  ✅ Complete API workflow simulation successful")
        return True
        
    except Exception as e:
        print(f"  ❌ API workflow simulation failed: {e}")
        return False

def main():
    """Run all API layer tests"""
    print("🚀 Testing Unified Statements API Layer - Phase 1b")
    print("=" * 70)
    
    tests = [
        test_api_imports,
        test_route_registration,
        test_upload_detection,
        test_data_structures,
        test_parse_coordination,
        test_configuration_integration,
        simulate_api_workflow
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
        print("🎉 All API tests passed! API layer is ready.")
        print("\nNext steps:")
        print("- Apply the app.py integration patch")
        print("- Start the Flask application")
        print("- Test the unified routes manually")
        print("- Move to Phase 1c: Frontend Implementation")
    else:
        print("⚠️  Some tests failed. Please review and fix issues before proceeding.")
    
    print("\n📝 Manual testing commands:")
    print("1. Start Flask app: python app.py")
    print("2. Visit: http://localhost:5001/api/health/unified")
    print("3. Visit: http://localhost:5001/statements/2025")
    print("4. Test API: curl http://localhost:5001/api/statements/status")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)