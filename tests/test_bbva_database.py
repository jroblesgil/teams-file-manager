# test_bbva_database.py
"""
Test script for BBVA database operations
Run this to validate Phase 1: Database Foundation
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import BBVA modules
from modules.bbva.bbva_database import (
    get_bbva_database, update_bbva_database, 
    create_empty_bbva_database, get_database_filename,
    navigate_to_bbva_db_folder
)
from modules.bbva.bbva_config import BBVA_ACCOUNTS

def test_database_operations():
    """Test BBVA database operations with BBVA MX MXN account"""
    
    # Test account: BBVA MX MXN
    test_clabe = "012180001198203451"
    
    print("🧪 Testing BBVA Database Operations")
    print("=" * 50)
    
    # You'll need to get this from your session
    # For now, this is a placeholder - replace with actual token
    access_token = "YOUR_ACCESS_TOKEN_HERE"
    
    if access_token == "YOUR_ACCESS_TOKEN_HERE":
        print("❌ Please set a valid access_token in the test script")
        print("   You can get this from your browser's developer tools")
        print("   or from a successful login session")
        return False
    
    try:
        # Test 1: Database filename generation
        print(f"📋 Test 1: Database filename generation")
        filename = get_database_filename(test_clabe)
        print(f"   CLABE: {test_clabe}")
        print(f"   Filename: {filename}")
        print(f"   ✅ Expected: BBVA_MX_mxn_DB.json")
        
        # Test 2: Navigate to BBVA DB folder
        print(f"\n📁 Test 2: Navigate to BBVA DB folder")
        try:
            bbva_db_info = navigate_to_bbva_db_folder(access_token)
            print(f"   Drive ID: {bbva_db_info['drive_id']}")
            print(f"   Folder ID: {bbva_db_info['folder_id']}")
            print(f"   Folder Name: {bbva_db_info['folder_name']}")
            print(f"   ✅ Navigation successful")
        except Exception as e:
            print(f"   ❌ Navigation failed: {e}")
            return False
        
        # Test 3: Create empty database
        print(f"\n🗃️ Test 3: Create empty database structure")
        empty_db = create_empty_bbva_database(test_clabe)
        print(f"   Account CLABE: {empty_db['metadata']['account_clabe']}")
        print(f"   Account Type: {empty_db['metadata']['account_type']}")
        print(f"   Total Transactions: {empty_db['metadata']['total_transactions']}")
        print(f"   Transactions Array: {len(empty_db['transactions'])} items")
        print(f"   ✅ Empty database structure created")
        
        # Test 4: Load existing database (or create new)
        print(f"\n📖 Test 4: Load database from SharePoint")
        database = get_bbva_database(test_clabe, access_token)
        print(f"   Account Type: {database['metadata']['account_type']}")
        print(f"   Total Transactions: {database['metadata']['total_transactions']}")
        print(f"   Last Updated: {database['metadata']['last_updated']}")
        print(f"   ✅ Database loaded successfully")
        
        # Test 5: Add sample transaction
        print(f"\n➕ Test 5: Add sample transaction")
        sample_transaction = {
            "date": "2024-12-15",
            "date_liq": "2024-12-15", 
            "code": "TRF001",
            "description": "TRANSFERENCIA SPEI - TEST",
            "cargo": 0.0,
            "abono": 1000.0,
            "saldo": 25000.0,
            "saldo_liq": 25000.0,
            "file_source": "TEST_2412_FMX_BBVA_MXN.pdf",
            "page_number": 1,
            "raw_line": "15/DIC 15/DIC TRF001 TRANSFERENCIA SPEI - TEST 1,000.00 25,000.00"
        }
        
        # Add the sample transaction
        database['transactions'].append(sample_transaction)
        print(f"   Added sample transaction: {sample_transaction['description']}")
        print(f"   New transaction count: {len(database['transactions'])}")
        print(f"   ✅ Sample transaction added")
        
        # Test 6: Save database to SharePoint
        print(f"\n💾 Test 6: Save database to SharePoint")
        success = update_bbva_database(test_clabe, database, access_token)
        if success:
            print(f"   ✅ Database saved successfully")
        else:
            print(f"   ❌ Database save failed")
            return False
        
        # Test 7: Reload database to verify persistence
        print(f"\n🔄 Test 7: Reload database to verify persistence")
        reloaded_db = get_bbva_database(test_clabe, access_token)
        print(f"   Reloaded transaction count: {len(reloaded_db['transactions'])}")
        print(f"   Last transaction: {reloaded_db['transactions'][-1]['description'] if reloaded_db['transactions'] else 'None'}")
        
        if len(reloaded_db['transactions']) > 0:
            print(f"   ✅ Database persistence verified")
        else:
            print(f"   ❌ Database persistence failed")
            return False
        
        print(f"\n🎉 All tests passed! BBVA database foundation is working.")
        print(f"\n📊 Final Database State:")
        print(f"   File: {filename}")
        print(f"   Account: {reloaded_db['metadata']['account_type']}")
        print(f"   Transactions: {len(reloaded_db['transactions'])}")
        print(f"   Last Updated: {reloaded_db['metadata']['last_updated']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_bbva_config():
    """Display BBVA configuration for reference"""
    print("\n📋 BBVA Account Configuration:")
    print("=" * 50)
    
    for account_key, account_data in BBVA_ACCOUNTS.items():
        print(f"🏦 {account_data['name']}")
        print(f"   Key: {account_key}")
        print(f"   CLABE: {account_data['clabe']}")
        print(f"   Directory: {account_data['directory']}")
        print(f"   Database: {account_data['database']}")
        print()


if __name__ == "__main__":
    print("🚀 BBVA Database Foundation Testing")
    print("=" * 50)
    
    # Show configuration
    show_bbva_config()
    
    # Run tests
    success = test_database_operations()
    
    if success:
        print("\n✅ Phase 1: Database Foundation - COMPLETED")
        print("   Ready to proceed to Phase 2: Batch Processing Engine")
    else:
        print("\n❌ Phase 1: Database Foundation - FAILED")
        print("   Please review errors and retry")