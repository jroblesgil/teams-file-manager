"""
Shared Module Package

This package contains shared utilities used across different modules:
- Azure OAuth integration (azure_oauth)
- Teams API functionality (teams_api)
- Common helper functions
"""

try:
    from .azure_oauth import AzureOAuth
    from .teams_api import TeamsAPI
except ImportError:
    # Graceful handling if some modules aren't available yet
    pass

__all__ = ['AzureOAuth', 'TeamsAPI']
