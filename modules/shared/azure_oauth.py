"""
Enhanced OAuth configuration with better error handling
Complete implementation with all required methods
"""

import base64
import hashlib
import secrets
import urllib.parse
import logging
import requests
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class AzureOAuth:
    def __init__(self, client_id: str, tenant_id: str, redirect_uri: str, client_secret: str = None):
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.redirect_uri = redirect_uri
        self.client_secret = client_secret
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        
        # Enhanced scope list for SharePoint/Teams access
        self.scope = [
            "User.Read",
            "Files.Read.All", 
            "Sites.Read.All",
            "Group.Read.All",
            "Team.ReadBasic.All",
            "Directory.Read.All"  # Additional scope for better Teams access
        ]
    
    def _generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge"""
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code challenge
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_auth_url(self) -> Tuple[str, str, str]:
        """Generate authorization URL, state, and code verifier"""
        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = self._generate_pkce_pair()
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scope),
            'state': state,
            'response_mode': 'query',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'prompt': 'login'  # Add this line
        }
        
        auth_url = f"{self.authority}/oauth2/v2.0/authorize?" + urllib.parse.urlencode(params)
        logger.info(f"🔗 Generated auth URL with scopes: {', '.join(self.scope)}")
        return auth_url, state, code_verifier
    
    def get_token_from_code(self, code: str, code_verifier: str) -> Optional[Dict]:
        """Exchange authorization code for access token with enhanced error handling"""
        try:
            token_url = f"{self.authority}/oauth2/v2.0/token"
            
            data = {
                'client_id': self.client_id,
                'scope': ' '.join(self.scope),
                'code': code,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code',
                'code_verifier': code_verifier
            }
            
            if self.client_secret:
                data['client_secret'] = self.client_secret
            
            logger.info(f"🔄 Requesting token from: {token_url}")
            logger.info(f"📝 Scopes requested: {', '.join(self.scope)}")
            
            response = requests.post(
                token_url, 
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            logger.info(f"🔍 Token response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                logger.info("✅ Token obtained successfully")
                
                # Validate token immediately
                validation_result = self.validate_token(token_data.get('access_token'))
                if validation_result.get('valid'):
                    logger.info(f"✅ Token validated for user: {validation_result.get('user')}")
                    return token_data
                else:
                    logger.error(f"❌ Token validation failed: {validation_result.get('error')}")
                    return None
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                logger.error(f"❌ Token request failed: {error_data}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error during token request: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error during token request: {str(e)}")
            return None
    
    def validate_token(self, access_token: str) -> Dict:
        """Validate access token with detailed error reporting"""
        if not access_token:
            return {'valid': False, 'error': 'No access token provided'}
        
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Test basic user access first
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Test Teams access
                teams_response = requests.get(
                    'https://graph.microsoft.com/v1.0/me/joinedTeams',
                    headers=headers,
                    timeout=10
                )
                
                teams_access = teams_response.status_code == 200
                
                return {
                    'valid': True,
                    'user': user_data.get('displayName'),
                    'email': user_data.get('mail') or user_data.get('userPrincipalName'),
                    'teams_access': teams_access,
                    'teams_status': teams_response.status_code
                }
            elif response.status_code == 401:
                return {
                    'valid': False,
                    'error': 'Token expired or invalid - user needs to re-authenticate',
                    'status_code': 401
                }
            elif response.status_code == 403:
                return {
                    'valid': False,
                    'error': 'Insufficient permissions - check Azure app registration',
                    'status_code': 403,
                    'suggestion': 'Verify API permissions and admin consent in Azure Portal'
                }
            else:
                return {
                    'valid': False,
                    'error': f'API returned status {response.status_code}',
                    'status_code': response.status_code,
                    'response': response.text[:500]
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'valid': False,
                'error': f'Network error: {str(e)}',
                'suggestion': 'Check internet connection and firewall settings'
            }

# Helper function for backwards compatibility
def validate_access_token(access_token: str) -> Dict:
    """Standalone function to validate access token"""
    if not access_token:
        return {'valid': False, 'error': 'No access token provided'}
    
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            return {
                'valid': True,
                'user': user_data.get('displayName'),
                'email': user_data.get('mail') or user_data.get('userPrincipalName')
            }
        elif response.status_code == 401:
            return {
                'valid': False,
                'error': 'Token expired or invalid',
                'suggestion': 'User needs to re-authenticate'
            }
        else:
            return {
                'valid': False,
                'error': f'API returned status {response.status_code}',
                'response': response.text[:200]
            }
            
    except requests.exceptions.RequestException as e:
        return {
            'valid': False,
            'error': f'Network error: {str(e)}',
            'suggestion': 'Check internet connection'
        }