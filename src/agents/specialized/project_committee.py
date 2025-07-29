"""Project Committee Management Agent"""
from typing import Dict, List, Any
from agno.agent import Agent
from datetime import datetime
from ...tools.api_clients.project_service import ProjectServiceClient


class ProjectCommitteeAgent(Agent):
    """Agent responsible for managing project committees"""
    
    def __init__(self, client: ProjectServiceClient = None):
        self.client = client or ProjectServiceClient()
        
        super().__init__(
            name="ProjectCommitteeManager",
            instructions="""You manage project committee memberships.
            Your tasks:
            1. Get project details using the provided project slug
            2. Identify appropriate committees:
               - Governing Board for primary contacts
               - Marketing Committee for marketing contacts
               - Technical Committee for technical contacts
            3. Check if committees exist, note if any are missing
            4. For each contact:
               - Verify they're not already a committee member
               - Add them to the appropriate committee based on their contact_type
               - Include relevant metadata (organization, role, join date)
            5. Handle any committee-specific onboarding requirements
            6. Report successful additions and any issues
            """,
            tools=[
                self.client.get_project_by_slug,
                self.client.get_project_committees,
                self.client.add_committee_member,
                self.client.check_committee_membership
            ]
        )
    
    async def run(self, task: str, context: Dict = None) -> Any:
        """Execute the agent task"""
        context = context or {}
        
        if "Get project details" in task:
            project_slug = context.get('project_slug')
            if not project_slug:
                return {"status": "error", "message": "project_slug required"}
            
            # Simulated response
            return {
                "status": "success",
                "project_id": "proj-001",
                "project_info": {
                    "id": "proj-001",
                    "slug": project_slug,
                    "name": project_slug.upper(),
                    "description": f"{project_slug} project"
                }
            }
        
        elif "Get all committees" in task:
            project_id = context.get('project_id')
            if not project_id:
                return {"status": "error", "message": "project_id required"}
            
            # Simulated committees
            committees = [
                {"id": "comm-001", "name": "Governing Board", "type": "governance", "project_id": project_id},
                {"id": "comm-002", "name": "Marketing Committee", "type": "marketing", "project_id": project_id},
                {"id": "comm-003", "name": "Technical Steering Committee", "type": "technical", "project_id": project_id}
            ]
            
            return {
                "status": "success",
                "committees": committees
            }
        
        elif "Check if" in task and "already in committee" in task:
            # Check membership
            return {
                "status": "success",
                "is_member": False
            }
        
        elif "Add" in task and "to committee" in task:
            committee_id = context.get('committee_id')
            member_data = context.get('member_data')
            
            if not committee_id or not member_data:
                return {"status": "error", "message": "committee_id and member_data required"}
            
            # Simulated successful addition
            return {
                "status": "success",
                "member_id": f"mem-{datetime.now().timestamp()}",
                "message": f"Added {member_data.get('email')} to committee {committee_id}"
            }
        
        return {"status": "error", "message": "Unknown task"}