import requests
import json
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Custom exceptions
class AuthenticationError(Exception):
    """Authentication related errors"""
    pass

class PermissionError(Exception):
    """Permission related errors"""
    pass

class RateLimitError(Exception):
    """Rate limiting errors"""
    pass

class APIError(Exception):
    """Base API error"""
    pass

class NetworkError(Exception):
    """Network related errors"""
    pass

class TeamsAPI:
    def __init__(self, access_token: str):
        if not access_token or access_token == 'placeholder_token':
            raise ValueError("Invalid or missing access token")
            
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Simple token validation without AuthDebugger dependency
        try:
            test_response = requests.get(
                f"{self.base_url}/me",
                headers=self.headers,
                timeout=10
            )
            if test_response.status_code == 401:
                raise ValueError("Token expired or invalid - please re-authenticate")
            elif test_response.status_code not in [200, 403]:  # 403 might be permission issue, not auth
                logger.warning(f"Token validation returned status {test_response.status_code}")
        except requests.exceptions.RequestException:
            # Network issues - continue anyway, will fail later with better error handling
            logger.warning("Unable to validate token due to network issues")
    
    def _make_request(self, url: str, method: str = 'GET', **kwargs):
        """Make API request with comprehensive error handling"""
        try:
            logger.info(f"Making {method} request to: {url}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.error("Access token expired or invalid")
                raise AuthenticationError("Token expired - please re-authenticate")
            elif response.status_code == 403:
                logger.error("Insufficient permissions")
                raise PermissionError("Insufficient permissions for this operation")
            elif response.status_code == 404:
                logger.error("Resource not found")
                return None
            elif response.status_code == 429:
                logger.error("Rate limit exceeded")
                raise RateLimitError("Too many requests - please try again later")
            else:
                error_text = response.text
                logger.error(f"API error {response.status_code}: {error_text}")
                raise APIError(f"API request failed: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            raise NetworkError("Request timed out")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            raise NetworkError("Unable to connect to Microsoft Graph")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise NetworkError(f"Network error: {str(e)}")
    
    def get_user_info(self) -> Dict:
        """Get current user information"""
        url = f"{self.base_url}/me"
        return self._make_request(url)
    
    def get_joined_teams(self) -> List[Dict]:
        """Get teams the user has joined with pagination support"""
        teams = []
        url = f"{self.base_url}/me/joinedTeams"
        
        while url:
            result = self._make_request(url)
            if result:
                teams.extend(result.get('value', []))
                url = result.get('@odata.nextLink')  # Handle pagination
            else:
                break
                
        return teams
    
    def get_team_channels(self, team_id: str) -> List[Dict]:
        """Get channels for a specific team"""
        url = f"{self.base_url}/teams/{team_id}/channels"
        result = self._make_request(url)
        return result.get('value', []) if result else []
    
    def get_channel_files(self, team_id: str, channel_id: str) -> List[Dict]:
        """Get files from a specific channel"""
        try:
            # Get the drive for this team/channel
            url = f"{self.base_url}/teams/{team_id}/channels/{channel_id}/filesFolder"
            files_folder = self._make_request(url)
            
            if not files_folder:
                return []
            
            # Get the drive ID and folder ID
            drive_id = files_folder.get('parentReference', {}).get('driveId')
            folder_id = files_folder.get('id')
            
            if not drive_id or not folder_id:
                return []
            
            # Get files from the folder
            url = f"{self.base_url}/drives/{drive_id}/items/{folder_id}/children"
            result = self._make_request(url)
            return result.get('value', []) if result else []
            
        except Exception as e:
            logger.error(f"Error getting channel files: {e}")
            return []
    
    def get_team_drive_files(self, team_id: str, folder_path: str = None) -> List[Dict]:
        """Get files from team's main document library"""
        try:
            # Get the team's default drive
            url = f"{self.base_url}/groups/{team_id}/drive"
            drive = self._make_request(url)
            
            if not drive:
                return []
                
            drive_id = drive.get('id')
            if not drive_id:
                return []
            
            # Get files from root or specific folder
            if folder_path:
                url = f"{self.base_url}/drives/{drive_id}/root:/{folder_path}:/children"
            else:
                url = f"{self.base_url}/drives/{drive_id}/root/children"
            
            result = self._make_request(url)
            return result.get('value', []) if result else []
            
        except Exception as e:
            logger.error(f"Error getting team drive files: {e}")
            return []
    
    def search_files(self, query: str, team_id: str = None) -> List[Dict]:
        """Search for files across teams or specific team"""
        try:
            if team_id:
                # Search within specific team's drive
                url = f"{self.base_url}/groups/{team_id}/drive/root/search(q='{query}')"
            else:
                # Search across all accessible drives
                url = f"{self.base_url}/me/drive/root/search(q='{query}')"
            
            result = self._make_request(url)
            return result.get('value', []) if result else []
            
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return []
    
    def get_file_download_url(self, drive_id: str, file_id: str) -> Optional[str]:
        """Get download URL for a file"""
        try:
            url = f"{self.base_url}/drives/{drive_id}/items/{file_id}"
            file_info = self._make_request(url)
            return file_info.get('@microsoft.graph.downloadUrl') if file_info else None
            
        except Exception as e:
            logger.error(f"Error getting file download URL: {e}")
            return None
    
    def get_file_content(self, drive_id: str, file_id: str) -> Optional[bytes]:
        """Download file content"""
        try:
            download_url = self.get_file_download_url(drive_id, file_id)
            if not download_url:
                return None
            
            response = requests.get(download_url, timeout=60)
            response.raise_for_status()
            return response.content
            
        except Exception as e:
            logger.error(f"Error downloading file content: {e}")
            return None
    
    def validate_token(self) -> bool:
        """Validate if the current token is still valid"""
        try:
            self.get_user_info()
            return True
        except (AuthenticationError, NetworkError):
            return False