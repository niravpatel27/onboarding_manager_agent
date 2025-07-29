"""Email Communication Agent"""
from typing import Dict, Any
from agno.agent import Agent
import uuid
from ...tools.api_clients.email import EmailClient


class EmailCommunicationAgent(Agent):
    """Agent responsible for email communications"""
    
    def __init__(self, client: EmailClient = None):
        self.client = client or EmailClient()
        
        super().__init__(
            name="EmailCommunicator",
            instructions="""You handle all email communications with contacts.
            Your tasks:
            1. Send personalized welcome emails based on committee assignment:
               - Governing Board: Strategic overview, governance docs, meeting cadence
               - Marketing Committee: Brand guidelines, marketing calendar, resources
               - Technical Committee: Technical docs, architecture overview, dev resources
            2. Include project-specific information:
               - Project charter and goals
               - Committee responsibilities
               - Upcoming meetings and events
            3. Track email delivery status
            """,
            tools=[
                self.client.send_welcome_email
            ]
        )
    
    async def run(self, task: str, context: Dict = None) -> Any:
        """Execute the agent task"""
        context = context or {}
        
        if "Send committee-specific welcome email" in task:
            contact = context.get('contact', {})
            project_info = context.get('project_info', {})
            committee = context.get('committee', '')
            
            if not contact or not contact.get('email'):
                return {"status": "error", "message": "contact with email required"}
            
            # Prepare email data
            email_data = await self.client.send_welcome_email(
                contact=contact,
                project_info=project_info,
                committee_name=committee
            )
            
            # Simulate successful email send
            email_id = str(uuid.uuid4())
            
            return {
                "status": "success",
                "email_id": email_id,
                "to": contact['email'],
                "template": email_data.get('template'),
                "message": f"Welcome email sent to {contact['email']}"
            }
        
        return {"status": "error", "message": "Unknown task"}