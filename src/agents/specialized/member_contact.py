"""Member Contact Fetcher Agent"""
from typing import Dict, List, Any
from agno.agent import Agent
from ...tools.api_clients.member_service import MemberServiceClient


class MemberContactFetcherAgent(Agent):
    """Agent responsible for fetching member contacts"""
    
    def __init__(self, client: MemberServiceClient = None):
        self.client = client or MemberServiceClient()
        
        super().__init__(
            name="MemberContactFetcher",
            instructions="""You are responsible for fetching contacts from the Member Service.
            Your tasks:
            1. Get member ID using the provided organization name
            2. Fetch all contacts for that member
            3. Each contact will have a 'contact_type' field (primary, marketing, or technical)
            4. Validate contact data completeness (all required fields present)
            5. Return the contact list with member context
            """,
            tools=[
                self.client.get_member_by_organization,
                self.client.get_member_contacts,
                self.client.get_contact_details
            ]
        )
    
    async def run(self, task: str, context: Dict = None) -> Any:
        """Execute the agent task"""
        context = context or {}
        
        if "Get member ID" in task:
            org_name = context.get('organization_name')
            if not org_name:
                return {"status": "error", "message": "organization_name required"}
            
            # In production, this would make actual API call
            result = await self.client.get_member_by_organization(org_name)
            
            # Simulated response
            return {
                "status": "success",
                "member_id": "org-001",
                "member_info": {
                    "id": "org-001",
                    "name": org_name,
                    "tier": "Gold"
                }
            }
        
        elif "Fetch all contacts" in task:
            member_id = context.get('member_id')
            if not member_id:
                return {"status": "error", "message": "member_id required"}
            
            # In production, this would make actual API call
            result = await self.client.get_member_contacts(member_id)
            
            # Simulated response with validation
            contacts = [
                {
                    "contact_id": "cnt-001",
                    "member_id": member_id,
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "title": "CEO",
                    "contact_type": "primary",
                    "organization": context.get('organization_name', 'Unknown')
                }
            ]
            
            # Validate contacts
            validated_contacts = []
            for contact in contacts:
                if all(contact.get(field) for field in ['email', 'first_name', 'last_name', 'contact_type']):
                    validated_contacts.append(contact)
            
            return {
                "status": "success",
                "contacts": validated_contacts,
                "count": len(validated_contacts)
            }
        
        return {"status": "error", "message": "Unknown task"}