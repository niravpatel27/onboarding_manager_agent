"""Configuration module for switching between stub and production services"""
import os
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ServiceConfig:
    """Configuration for individual service"""
    url: str
    api_key: str = ""
    use_stub: bool = False

class Config:
    """Main configuration class for the onboarding agent system"""
    
    def __init__(self):
        # Check if running in local/development mode
        self.is_local = os.getenv('RUN_MODE', 'local').lower() == 'local'
        
        # Database configuration
        self.database = {
            'type': 'sqlite' if self.is_local else os.getenv('DB_TYPE', 'postgres'),
            'connection': {
                'sqlite': {
                    'path': os.getenv('SQLITE_PATH', './local_onboarding.db')
                },
                'postgres': {
                    'host': os.getenv('DB_HOST', 'localhost'),
                    'port': int(os.getenv('DB_PORT', '5432')),
                    'database': os.getenv('DB_NAME', 'onboarding'),
                    'user': os.getenv('DB_USER', 'postgres'),
                    'password': os.getenv('DB_PASSWORD', '')
                }
            }
        }
        
        # Service configurations
        self.member_service = ServiceConfig(
            url=os.getenv('MEMBER_SERVICE_URL', 'https://api.lfx.linuxfoundation.org/v1/member-service'),
            api_key=os.getenv('LFX_API_KEY', ''),
            use_stub=self.is_local
        )
        
        self.project_service = ServiceConfig(
            url=os.getenv('PROJECT_SERVICE_URL', 'https://api.lfx.linuxfoundation.org/v1/project-service'),
            api_key=os.getenv('LFX_API_KEY', ''),
            use_stub=self.is_local
        )
        
        self.slack_service = ServiceConfig(
            url=os.getenv('SLACK_API_URL', 'https://slack.com/api'),
            api_key=os.getenv('SLACK_BOT_TOKEN', ''),
            use_stub=self.is_local
        )
        
        self.email_service = {
            'use_stub': self.is_local,
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'email_from': os.getenv('EMAIL_FROM', 'onboarding@linuxfoundation.org'),
            'email_password': os.getenv('EMAIL_PASSWORD', '')
        }
        
        self.landscape_service = {
            'use_stub': self.is_local,
            'github_token': os.getenv('GITHUB_TOKEN', ''),
            'github_org': os.getenv('GITHUB_ORG', 'cncf')
        }
        
        # Agent behavior configuration
        self.agent_config = {
            'max_retries': int(os.getenv('MAX_RETRIES', '3')),
            'retry_delay': int(os.getenv('RETRY_DELAY', '5')),
            'batch_size': int(os.getenv('BATCH_SIZE', '10')),
            'max_processing_time': int(os.getenv('MAX_PROCESSING_TIME', '3600')),
            'max_failure_rate': float(os.getenv('MAX_FAILURE_RATE', '0.2'))
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration based on type"""
        db_type = self.database['type']
        return {
            'type': db_type,
            **self.database['connection'][db_type]
        }
    
    def is_using_stubs(self) -> bool:
        """Check if system is using stub services"""
        return self.is_local

# Global config instance
config = Config()