"""Database Agent for managing onboarding state"""
from typing import Dict, Any
from agno.agent import Agent
from ...tools.mcp.database import OnboardingDatabase


class DatabaseAgent(Agent):
    """Agent responsible for database operations via MCP"""
    
    def __init__(self, db: OnboardingDatabase = None):
        self.db = db or OnboardingDatabase()
        
        super().__init__(
            name="DatabaseManager",
            instructions="""You manage the onboarding database state.
            Your tasks:
            1. Initialize database schema
            2. Create onboarding sessions
            3. Track contact progress
            4. Update status for each step
            5. Generate reports
            """
        )
    
    async def run(self, task: str, context: Dict = None) -> Any:
        """Execute the agent task"""
        context = context or {}
        
        if "Initialize database schema" in task:
            # Schema already initialized in __init__
            return {"status": "success", "message": "Database schema initialized"}
        
        elif "Create new onboarding session" in task:
            session_id = await self.db.create_onboarding_session(
                org_name=context.get('org_name'),
                project_slug=context.get('project_slug'),
                member_id=context.get('member_id'),
                project_id=context.get('project_id')
            )
            return {"status": "success", "session_id": session_id}
        
        elif "Add contact to onboarding session" in task:
            contact_id = await self.db.add_contact_to_session(
                session_id=context.get('session_id'),
                contact=context.get('contact')
            )
            return {"status": "success", "contact_onboarding_id": contact_id}
        
        elif "Update contact status" in task:
            await self.db.update_contact_status(
                contact_onboarding_id=context.get('contact_onboarding_id'),
                status_type=context.get('status_type'),
                status=context.get('status'),
                additional_data=context.get('additional_data')
            )
            return {"status": "success"}
        
        elif "Update session statistics" in task:
            result = await self.db.update_session_stats(
                session_id=context.get('session_id')
            )
            return result
        
        elif "Generate session report" in task:
            report = await self.db.get_session_report(
                session_id=context.get('session_id')
            )
            return {"status": "success", "report": report}
        
        return {"status": "error", "message": "Unknown task"}