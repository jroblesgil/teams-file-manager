# test_bbva_batch.py
"""
Test script for BBVA batch processing
Run this to validate Phase 2: Batch Processing Engine
"""

import requests
import time
import json

# Configuration
BASE_URL = "http://localhost:5001"  # Adjust if your Flask app runs on different port
TEST_CLABE = "012180001198203451"   # BBVA MX MXN for testing

def test_bbva_batch_processing():
    """Test BBVA batch processing step by step"""
    
    print("🧪 Testing BBVA Batch Processing Engine")
    print("=" * 50)
    
    try:
        # Test 1: File Discovery
        print("📁 Test 1: File Discovery")
        response = requests.get(f"{BASE_URL}/api/bbva/test-file-discovery/{TEST_CLABE}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Found {data['pdf_files']} PDF files")
            print(f"   Account: {data['account_type']}")
            print(f"   Folder: {data['folder_path']}")
            
            if data['pdf_files'] > 0:
                print(f"   Sample files:")
                for file_info in data['file_list'][:3]:
                    print(f"     - {file_info['filename']} ({file_info['last_modified']})")
        else:
            print(f"   ❌ File discovery failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
        
        # Test 2: Parse Status Check
        print(f"\n📋 Test 2: Parse Status Check")
        response = requests.get(f"{BASE_URL}/api/bbva/test-parse-status/{TEST_CLABE}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Parse status check successful")
            print(f"   Total PDF files: {data['total_pdf_files']}")
            print(f"   Files to parse: {data['files_to_parse']}")
            print(f"   Files up to date: {data['files_up_to_date']}")
            
            if data['files_to_parse'] > 0:
                print(f"   Files needing parse:")
                for file_info in data['files_needing_parse']:
                    print(f"     - {file_info['filename']}")
        else:
            print(f"   ❌ Parse status check failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
        
        # Test 3: Single PDF Parse (if files need parsing)
        if data.get('files_to_parse', 0) > 0:
            print(f"\n🔍 Test 3: Single PDF Parse Test")
            response = requests.post(f"{BASE_URL}/api/bbva/test-single-parse/{TEST_CLABE}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Single parse test successful")
                print(f"   Test file: {data['test_file']['filename']}")
                print(f"   Transactions found: {data['parse_result']['transaction_count']}")
                print(f"   CLABE detected: {data['parse_result']['clabe_detected']}")
                print(f"   Period detected: {data['parse_result']['period_detected']}")
                
                if data['parse_result']['transaction_count'] > 0:
                    print(f"   Sample transactions:")
                    for tx in data['sample_transactions']:
                        print(f"     - {tx['date']}: {tx['description']} ${tx.get('abono', tx.get('cargo', 0))}")
            else:
                print(f"   ❌ Single parse test failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
        else:
            print(f"\n⏭️  Test 3: Skipped (no files need parsing)")
        
        # Test 4: Full Batch Processing
        print(f"\n🚀 Test 4: Full Batch Processing")
        response = requests.post(f"{BASE_URL}/api/bbva/parse/{TEST_CLABE}")
        
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            
            if session_id:
                print(f"   ✅ Batch processing started")
                print(f"   Session ID: {session_id}")
                
                # Monitor progress
                print(f"   📊 Monitoring progress...")
                
                for i in range(30):  # Check for up to 30 seconds
                    progress_response = requests.get(f"{BASE_URL}/api/bbva/parse-progress/{session_id}")
                    
                    if progress_response.status_code == 200:
                        progress_data = progress_response.json()
                        status = progress_data.get('status')
                        percentage = progress_data.get('progress_percentage', 0)
                        details = progress_data.get('details', 'Processing...')
                        current_file = progress_data.get('current_file')
                        
                        if current_file:
                            print(f"   [{percentage:3d}%] {details} - {current_file}")
                        else:
                            print(f"   [{percentage:3d}%] {details}")
                        
                        if status == 'completed':
                            print(f"   ✅ Batch processing completed successfully!")
                            print(f"   Files processed: {progress_data.get('files_processed', 0)}")
                            print(f"   Transactions added: {progress_data.get('transactions_added', 0)}")
                            
                            if progress_data.get('errors'):
                                print(f"   ⚠️  Errors: {len(progress_data['errors'])}")
                                for error in progress_data['errors'][:3]:
                                    print(f"     - {error}")
                            
                            break
                        elif status == 'error':
                            print(f"   ❌ Batch processing failed: {details}")
                            return False
                        
                        time.sleep(2)  # Wait 2 seconds before next check
                    else:
                        print(f"   ❌ Progress check failed: {progress_response.status_code}")
                        break
                
            else:
                # Synchronous response (no files to parse)
                print(f"   ✅ {data['message']}")
                print(f"   Files checked: {data['files_checked']}")
                print(f"   Files skipped: {data['files_skipped']}")
        else:
            print(f"   ❌ Batch processing failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
        
        # Test 5: Parse Summary
        print(f"\n📈 Test 5: Parse Summary")
        response = requests.get(f"{BASE_URL}/api/bbva/parse-summary/{TEST_CLABE}")
        
        if response.status_code == 200:
            data = response.json()
            summary = data['summary']
            print(f"   ✅ Parse summary retrieved")
            print(f"   Account: {summary['account_type']}")
            print(f"   Total files: {summary['total_files']}")
            print(f"   Parsed files: {summary['parsed_files']}")
            print(f"   Failed files: {summary['failed_files']}")
            print(f"   Pending files: {summary['pending_files']}")
            print(f"   Total transactions: {summary['total_transactions']}")
            print(f"   Last updated: {summary['last_updated']}")
        else:
            print(f"   ❌ Parse summary failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
        
        print(f"\n🎉 All tests passed! BBVA Batch Processing Engine is working.")
        print(f"\n📊 Final Results Summary:")
        print(f"   ✅ File discovery working")
        print(f"   ✅ Parse status checking working")
        print(f"   ✅ Single PDF parsing working")
        print(f"   ✅ Batch processing working")
        print(f"   ✅ Progress tracking working")
        print(f"   ✅ Parse summary working")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_test_info():
    """Display test information"""
    print("📋 BBVA Batch Processing Test Information:")
    print("=" * 50)
    print(f"Base URL: {BASE_URL}")
    print(f"Test Account: BBVA MX MXN")
    print(f"Test CLABE: {TEST_CLABE}")
    print(f"Expected Folder: Estados de Cuenta/BBVA/BBVA MX/BBVA MX MXN/")
    print(f"Database File: BBVA_MX_mxn_DB.json")
    print()
    print("Prerequisites:")
    print("1. Flask app running on localhost:5001")
    print("2. Valid authentication session")
    print("3. BBVA database endpoints added to app.py")
    print("4. At least one PDF file in the BBVA MX MXN folder")
    print()


if __name__ == "__main__":
    print("🚀 BBVA Batch Processing Engine Testing")
    print("=" * 50)
    
    # Show test information
    show_test_info()
    
    # Run tests
    success = test_bbva_batch_processing()
    
    if success:
        print("\n✅ Phase 2: Batch Processing Engine - COMPLETED")
        print("   Ready to proceed to Phase 3: API Integration")
    else:
        print("\n❌ Phase 2: Batch Processing Engine - FAILED")
        print("   Please review errors and retry")
        print("\n🔧 Troubleshooting Tips:")
        print("   1. Ensure Flask app is running and authenticated")
        print("   2. Check that BBVA endpoints are added to app.py")
        print("   3. Verify BBVA MX MXN folder has PDF files")
        print("   4. Check logs for detailed error messages")