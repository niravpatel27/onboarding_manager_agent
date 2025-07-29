"""Slack API client"""
from typing import Dict, List, Optional
from .base import BaseAPIClient


class SlackClient(BaseAPIClient):
    """Client for Slack API"""
    
    def __init__(self, bot_token: Optional[str] = None):
        base_url = "https://slack.com/api"
        super().__init__(base_url, bot_token)
    
    async def validate_connection(self) -> bool:
        """Validate API connection"""
        return True
    
    async def invite_to_workspace(self, email: str, channels: List[str], 
                                 organization: str, full_name: str = "") -> Dict:
        """Send Slack workspace invitation"""
        return {
            "endpoint": "POST /users.admin.invite",
            "payload": {
                "email": email,
                "channels": ",".join(channels),
                "real_name": full_name,
                "team_id": f"{organization.lower().replace(' ', '_')}_workspace"
            },
            "description": "Invite user to Slack workspace"
        }
    
    async def add_to_channel(self, user_id: str, channel: str) -> Dict:
        """Add user to specific Slack channel"""
        return {
            "endpoint": "POST /conversations.invite",
            "payload": {
                "channel": channel,
                "users": user_id
            },
            "description": "Add user to channel"
        }
    
    async def send_direct_message(self, user_id: str, message: str) -> Dict:
        """Send a direct message to a user"""
        return {
            "endpoint": "POST /chat.postMessage",
            "payload": {
                "channel": user_id,
                "text": message
            },
            "description": "Send DM to user"
        }
    
    def get_channels_for_committee(self, contact_type: str, project_slug: str) -> List[str]:
        """Get Slack channels based on committee type"""
        base_channels = ["#general", "#welcome", f"#{project_slug}"]
        
        type_channels = {
            "primary": ["#board", "#announcements", "#strategic-planning"],
            "marketing": ["#marketing", "#events", "#content-strategy", "#brand"],
            "technical": ["#tech-discussion", "#architecture", "#dev-updates"]
        }
        
        return base_channels + type_channels.get(contact_type, [])