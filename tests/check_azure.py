"""
Azure Configuration Checker
Helps verify your Azure App Registration is set up correctly
"""

import os
from dotenv import load_dotenv

def check_azure_setup():
    load_dotenv()
    
    client_id = os.getenv('AZURE_CLIENT_ID')
    tenant_id = os.getenv('AZURE_TENANT_ID')
    
    print("🔍 Azure Configuration Checklist")
    print("=" * 50)
    
    print("📋 Your Configuration:")
    print(f"   Client ID: {client_id[:8]}...{client_id[-4:] if client_id else 'Missing'}")
    print(f"   Tenant ID: {tenant_id[:8]}...{tenant_id[-4:] if tenant_id else 'Missing'}")
    
    print("\n✅ Required Azure App Registration Settings:")
    print("   1. App Registration created in Azure Portal")
    print("   2. Redirect URI: http://localhost:5000")
    print("   3. API Permissions (Delegated):")
    print("      - Microsoft Graph > User.Read")
    print("      - Microsoft Graph > Files.Read.All") 
    print("      - Microsoft Graph > Sites.Read.All")
    print("      - Microsoft Graph > Group.Read.All")
    print("   4. Admin consent granted for permissions")
    
    print("\n🔗 Quick Links:")
    if tenant_id:
        print(f"   Azure Portal: https://portal.azure.com")
        print(f"   App Registrations: https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/RegisteredApps")
        if client_id:
            print(f"   Your App: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/{client_id}")
    
    print("\n🛠️  If you need to create/modify your Azure app:")
    print("   1. Go to Azure Portal > App registrations")
    print("   2. Create new registration or select existing")
    print("   3. Set redirect URI to: http://localhost:5000")
    print("   4. Add API permissions as listed above")
    print("   5. Grant admin consent")
    print("   6. Copy Client ID and Tenant ID to your .env file")

if __name__ == "__main__":
    check_azure_setup()