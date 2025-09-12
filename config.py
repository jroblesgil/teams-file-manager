"""
Configuration settings for Teams File Manager
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    AZURE_CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
    AZURE_TENANT_ID = os.getenv('AZURE_TENANT_ID')
    
    # Teams configuration
    TEAM_ID = '077539b3-b3af-4646-994f-dd642c9a1190'  # FIADO Main Office
    
    # Microsoft Graph API settings
    GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
    SCOPES = [
        'User.Read',
        'Files.Read.All',
        'Sites.Read.All',
        'Group.Read.All'
    ]
    
    # File settings
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'pdf', 'docx'}
    
    # Analysis settings
    ANALYSIS_CACHE_TIMEOUT = 3600  # 1 hour
    MAX_ANALYSIS_ROWS = 100000  # Limit for large datasets

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'
    
    # Production-specific settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}