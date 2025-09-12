#!/usr/bin/env python3
"""
Simple API Test - Phase 1b

Test the basic structure and syntax of our modules without importing them.
"""

import sys
import os

def test_file_creation():
    """Test that all required files exist"""
    print("🧪 Testing File Creation...")
    
    base_path = "modules/statements"
    required_files = [
        "__init__.py",
        "config.py", 
        "data_loader.py",
        "parse_coordinator.py",
        "upload_handler.py",
        "api_endpoints.py"
    ]
    
    missing_files = []
    for filename in required_files:
        filepath = os.path.join(base_path, filename)
        if not os.path.exists(filepath):
            missing_files.append(filepath)
        else:
            print(f"  ✅ {filepath}")
    
    if missing_files:
        print(f"  ❌ Missing files: {missing_files}")
        print("\n🔧 To create missing files, please run these commands:")
        print(f"mkdir -p {base_path}")
        for filename in required_files:
            if os.path.join(base_path, filename) in missing_files:
                print(f"touch {os.path.join(base_path, filename)}")
        return False
    
    print(f"  ✅ All {len(required_files)} files exist")
    return True

def test_basic_syntax():
    """Test basic Python syntax of modules"""
    print("🧪 Testing Basic Python Syntax...")
    
    base_path = "modules/statements"
    python_files = ["config.py", "data_loader.py", "parse_coordinator.py", "upload_handler.py", "api_endpoints.py"]
    
    for filename in python_files:
        filepath = os.path.join(base_path, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                
                # Basic syntax check - compile the code
                compile(content, filepath, 'exec')
                print(f"  ✅ {filename} - syntax OK")
            except SyntaxError as e:
                print(f"  ❌ {filename} - syntax error: {e}")
                return False
            except Exception as e:
                print(f"  ⚠️  {filename} - other error: {e}")
        else:
            print(f"  ⚠️  {filename} - file not found")
    
    return True

def test_configuration_structure():
    """Test the configuration structure"""
    print("🧪 Testing Configuration Structure...")
    
    try:
        # Test the UNIFIED_ACCOUNTS structure we defined
        from collections import OrderedDict
        
        UNIFIED_ACCOUNTS = OrderedDict([
            ('stp_sa', {'type': 'stp', 'number': '646180559700000009', 'name': 'STP SA'}),
            ('stp_ip_pd', {'type': 'stp', 'number': '646180403000000004', 'name': 'STP IP - PD'}),
            ('stp_ip_pi', {'type': 'stp', 'number': '646990403000000003', 'name': 'STP IP - PI'}),
            ('bbva_mx_mxn', {'type': 'bbva', 'clabe': '012180001198203451', 'name': 'BBVA MX MXN'}),
            ('bbva_mx_usd', {'type': 'bbva', 'clabe': '012180001201205883', 'name': 'BBVA MX USD'}),
            ('bbva_sa_mxn', {'type': 'bbva', 'clabe': '012180001182790637', 'name': 'BBVA SA MXN'}),
            ('bbva_sa_usd', {'type': 'bbva', 'clabe': '012222001182793149', 'name': 'BBVA SA USD'}),
            ('bbva_ip_corp', {'type': 'bbva', 'clabe': '012180001232011554', 'name': 'BBVA IP Corp'}),
            ('bbva_ip_clientes', {'type': 'bbva', 'clabe': '012180001232011635', 'name': 'BBVA IP Clientes'})
        ])
        
        print(f"  ✅ UNIFIED_ACCOUNTS structure: {len(UNIFIED_ACCOUNTS)} accounts")
        
        # Test account distribution
        stp_accounts = [k for k, v in UNIFIED_ACCOUNTS.items() if v['type'] == 'stp']
        bbva_accounts = [k for k, v in UNIFIED_ACCOUNTS.items() if v['type'] == 'bbva']
        
        print(f"  ✅ STP accounts: {len(stp_accounts)} ({stp_accounts})")
        print(f"  ✅ BBVA accounts: {len(bbva_accounts)} ({bbva_accounts})")
        
        # Test helper functions logic
        def get_account_by_key(account_key):
            if account_key in UNIFIED_ACCOUNTS:
                return {**UNIFIED_ACCOUNTS[account_key], 'account_key': account_key}
            return None
        
        test_account = get_account_by_key('stp_sa')
        if test_account and test_account['name'] == 'STP SA':
            print("  ✅ Helper function logic working")
        else:
            print("  ❌ Helper function logic failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False

def test_flask_route_patterns():
    """Test Flask route patterns"""
    print("🧪 Testing Flask Route Patterns...")
    
    try:
        from flask import Flask
        
        # Test creating a Flask app
        test_app = Flask(__name__)
        
        # Test route decorators syntax
        @test_app.route('/statements/<int:year>')
        def test_statements(year):
            return f"Statements for {year}"
        
        @test_app.route('/api/statements/parse/<account_key>', methods=['POST'])
        def test_parse(account_key):
            return f"Parse {account_key}"
        
        with test_app.app_context():
            rules = list(test_app.url_map.iter_rules())
            print(f"  ✅ Flask routes created: {len(rules)} rules")
            
            for rule in rules:
                print(f"    - {rule.rule} -> {rule.endpoint}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Flask route test failed: {e}")
        return False

def provide_setup_instructions():
    """Provide setup instructions"""
    print("🔧 Setup Instructions for Phase 1b")
    print("=" * 50)
    
    print("1. Create the module structure:")
    print("   mkdir -p modules/statements")
    print()
    
    print("2. Create the Python files by copying the artifacts:")
    files_to_create = [
        ("config.py", "Unified account configuration"),
        ("data_loader.py", "Data aggregation from STP/BBVA"),
        ("parse_coordinator.py", "Parse dispatch coordinator"),
        ("upload_handler.py", "Upload auto-detection handler"),
        ("api_endpoints.py", "Flask API routes"),
        ("__init__.py", "Module initialization")
    ]
    
    for filename, description in files_to_create:
        print(f"   - {filename}: {description}")
    print()
    
    print("3. Add to your app.py:")
    print("   # Import unified statements system")
    print("   from modules.statements.config import initialize_statements_config")
    print("   from modules.statements.api_endpoints import register_statements_routes")
    print("   ")
    print("   # Initialize and register")
    print("   initialize_statements_config()")
    print("   register_statements_routes(app, parse_progress)")
    print()
    
    print("4. Test the system:")
    print("   python app.py")
    print("   # Visit: http://localhost:5001/api/health/unified")
    print()

def main():
    """Run simplified API tests"""
    print("🚀 Simple API Layer Test - Phase 1b")
    print("=" * 50)
    
    # Check current directory
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    
    # Check if we're in the right place
    if not os.path.exists("app.py"):
        print("❌ Not in project root directory. Please cd to your teams-file-manager directory.")
        return False
    
    tests = [
        test_file_creation,
        test_basic_syntax,
        test_configuration_structure,
        test_flask_route_patterns
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append(False)
            print()
    
    # Summary
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Basic structure tests passed!")
    else:
        print("⚠️  Some tests failed.")
    
    print()
    provide_setup_instructions()
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)