"""Configuration settings for the onboarding system"""
import os
from typing import Optional


class Settings:
    """Application settings"""
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    RUN_MODE = os.getenv('RUN_MODE', 'local')  # local or production
    
    # Database
    DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
    DB_CONNECTION = os.getenv('DB_CONNECTION', 'onboarding.db')
    
    # API Endpoints
    MEMBER_SERVICE_URL = os.getenv('MEMBER_SERVICE_URL', 
                                   'https://api.lfx.linuxfoundation.org/v1/member-service')
    PROJECT_SERVICE_URL = os.getenv('PROJECT_SERVICE_URL', 
                                    'https://api.lfx.linuxfoundation.org/v1/project-service')
    SLACK_API_URL = os.getenv('SLACK_API_URL', 'https://slack.com/api')
    
    # API Keys
    LFX_API_KEY = os.getenv('LFX_API_KEY')
    SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    
    # Email Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    EMAIL_FROM = os.getenv('EMAIL_FROM', 'onboarding@linuxfoundation.org')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    
    # Agent Behavior
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '10'))
    
    # SLA Configuration
    MAX_PROCESSING_TIME = int(os.getenv('MAX_PROCESSING_TIME', '3600'))  # 1 hour
    MAX_FAILURE_RATE = float(os.getenv('MAX_FAILURE_RATE', '0.2'))  # 20%
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE')
    
    @classmethod
    def is_local_mode(cls) -> bool:
        """Check if running in local mode"""
        return cls.RUN_MODE.lower() == 'local'
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production"""
        return cls.ENVIRONMENT.lower() == 'production'
    
    @classmethod
    def validate(cls):
        """Validate required settings"""
        if cls.is_production():
            required = ['LFX_API_KEY', 'SLACK_BOT_TOKEN']
            missing = []
            
            for setting in required:
                if not getattr(cls, setting):
                    missing.append(setting)
            
            if missing:
                raise ValueError(f"Missing required settings for production: {', '.join(missing)}")


# Create settings instance
settings = Settings()