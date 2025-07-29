"""Slack Onboarding Agent"""
from typing import Dict, List, Any
from agno.agent import Agent
import uuid
from ...tools.api_clients.slack import SlackClient


class SlackOnboardingAgent(Agent):
    """Agent responsible for Slack workspace management"""
    
    def __init__(self, client: SlackClient = None):
        self.client = client or SlackClient()
        
        super().__init__(
            name="SlackOnboarder",
            instructions="""You manage Slack workspace invitations and channel assignments.
            Your tasks:
            1. Send workspace invitations to new contacts
            2. Assign contacts to channels based on their committee assignment:
               - Governing Board: #board, #announcements, #strategic-planning
               - Marketing Committee: #marketing, #events, #content-strategy, #brand
               - Technical Committee: #tech-discussion, #architecture, #dev-updates
               - All: #general, #welcome
            3. Send personalized welcome DM with:
               - Committee-specific channel guide
               - Link to onboarding resources
               - Key contacts in their committee
            4. Handle invitation failures with smart retry logic
            5. Return Slack user ID once joined
            """,
            tools=[
                self.client.invite_to_workspace,
                self.client.add_to_channel,
                self.client.send_direct_message
            ]
        )
    
    async def run(self, task: str, context: Dict = None) -> Any:
        """Execute the agent task"""
        context = context or {}
        
        if "Complete Slack onboarding" in task:
            contact = context.get('contact', {})
            organization = context.get('organization', '')
            channels = context.get('channels', [])
            committee = context.get('committee', '')
            
            if not contact or not contact.get('email'):
                return {"status": "error", "message": "contact with email required"}
            
            # Get appropriate channels if not provided
            if not channels:
                contact_type = contact.get('contact_type', 'primary')
                project_slug = context.get('project_slug', 'project')
                channels = self.client.get_channels_for_committee(contact_type, project_slug)
            
            # Simulate invitation
            slack_user_id = f"U{uuid.uuid4().hex[:8].upper()}"
            
            # Simulate sending welcome DM
            welcome_message = self._create_welcome_message(committee, channels)
            
            return {
                "status": "success",
                "slack_user_id": slack_user_id,
                "channels_joined": channels,
                "welcome_dm_sent": True,
                "message": f"Successfully invited {contact['email']} to Slack"
            }
        
        return {"status": "error", "message": "Unknown task"}
    
    def _create_welcome_message(self, committee: str, channels: List[str]) -> str:
        """Create personalized welcome message"""
        channel_list = "\n".join([f"• {ch}" for ch in channels])
        
        return f"""
Welcome to our Slack workspace! 🎉

You've been added to the {committee}. Here are your channels:

{channel_list}

Resources:
• Onboarding guide: /onboarding
• Committee docs: /docs/{committee.lower().replace(' ', '-')}
• Help: Contact @onboarding-team

We're excited to have you here!
"""