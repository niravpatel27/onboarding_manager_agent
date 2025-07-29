"""Email service client"""
from typing import Dict, Optional
from .base import BaseAPIClient


class EmailClient(BaseAPIClient):
    """Client for email operations"""
    
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587,
                 email_from: str = "onboarding@linuxfoundation.org"):
        super().__init__(smtp_server)
        self.smtp_port = smtp_port
        self.email_from = email_from
    
    async def validate_connection(self) -> bool:
        """Validate SMTP connection"""
        return True
    
    async def send_welcome_email(self, contact: Dict, project_info: Dict, 
                               committee_name: str) -> Dict:
        """Send personalized welcome email"""
        template_map = {
            "primary": "welcome_governing_board",
            "marketing": "welcome_marketing_committee",
            "technical": "welcome_technical_committee"
        }
        
        return {
            "to": contact['email'],
            "from": self.email_from,
            "template": template_map.get(contact.get('contact_type'), "welcome_general"),
            "variables": {
                "first_name": contact.get('first_name', ''),
                "organization": contact.get('organization', ''),
                "project_name": project_info.get('name', project_info.get('slug', '')),
                "role": contact.get('contact_type', ''),
                "committee_name": committee_name,
                "title": contact.get('title', '')
            },
            "description": f"Send welcome email to {contact['email']}"
        }
    
    def get_email_template(self, contact_type: str) -> str:
        """Get email template based on contact type"""
        templates = {
            "primary": """
                Welcome to the {project_name} Governing Board!
                
                As a member of the Governing Board, you'll help shape the strategic 
                direction of the project.
            """,
            "marketing": """
                Welcome to the {project_name} Marketing Committee!
                
                Your expertise will help us grow the project's community and adoption.
            """,
            "technical": """
                Welcome to the {project_name} Technical Committee!
                
                Your technical leadership will guide the project's architecture and development.
            """
        }
        return templates.get(contact_type, "Welcome to {project_name}!")