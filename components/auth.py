# ============================================================================
# components/auth.py - Reuse authentication components
# ============================================================================

"""
Authentication components reused from existing system
Only the OAuth logic, not the routing
"""

from modules.shared.azure_oauth import AzureOAuth

class AuthManager:
    """Simplified auth manager for unified statements system"""
    
    def __init__(self, client_id, tenant_id, client_secret, redirect_uri):
        self.oauth = AzureOAuth(
            client_id=client_id,
            tenant_id=tenant_id,
            redirect_uri=redirect_uri,
            client_secret=client_secret
        )
    
    def get_auth_url(self):
        """Get authorization URL and state"""
        return self.oauth.get_auth_url()
    
    def exchange_code_for_token(self, code, code_verifier):
        """Exchange authorization code for access token"""
        return self.oauth.get_token_from_code(code, code_verifier)
