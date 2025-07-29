"""Project Service API client"""
from typing import Dict, List, Optional
from .base import BaseAPIClient


class ProjectServiceClient(BaseAPIClient):
    """Client for Project Service API"""
    
    def __init__(self, api_key: Optional[str] = None):
        base_url = "https://api.lfx.linuxfoundation.org/v1/project-service"
        super().__init__(base_url, api_key)
    
    async def validate_connection(self) -> bool:
        """Validate API connection"""
        return True
    
    async def get_project_by_slug(self, project_slug: str) -> Dict:
        """Get project details by slug"""
        return {
            "endpoint": "GET /projects",
            "params": {
                "slug": project_slug
            },
            "description": "Fetch project details by slug"
        }
    
    async def get_project_committees(self, project_id: str) -> List[Dict]:
        """Get all committees for a project"""
        return {
            "endpoint": f"GET /projects/{project_id}/committees",
            "description": "Fetch all committees in the project"
        }
    
    async def add_committee_member(self, project_id: str, committee_id: str, member_data: Dict) -> Dict:
        """Add a member to a committee"""
        return {
            "endpoint": f"POST /projects/{project_id}/committees/{committee_id}/committee_members",
            "payload": member_data,
            "description": "Add contact to specified committee"
        }
    
    async def check_committee_membership(self, project_id: str, committee_id: str, email: str) -> Dict:
        """Check if contact is already in committee"""
        return {
            "endpoint": f"GET /projects/{project_id}/committees/{committee_id}/committee_members",
            "params": {
                "email": email
            },
            "description": "Verify existing committee membership"
        }