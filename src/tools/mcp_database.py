"""
Database abstraction using real MCP (Model Context Protocol)
"""

from typing import Dict, List, Any, Optional
from .mcp_client import MCPDatabaseOperations
import json
import logging

logger = logging.getLogger(__name__)

class OnboardingDatabaseToolsMCP:
    """
    High-level database tools for onboarding operations using real MCP.
    All operations use MCP's protocol to communicate with the SQLite server.
    """
    
    def __init__(self, db_path: str = "./local_onboarding.db"):
        self.mcp_ops = MCPDatabaseOperations(db_path)
        self._initialized = False
    
    async def initialize(self) -> Dict:
        """Initialize the database schema"""
        result = await self.mcp_ops.initialize_schema()
        if result["status"] == "success":
            self._initialized = True
        return result
    
    async def create_onboarding_session(self, org_name: str, project_slug: str,
                                       member_id: str, project_id: str) -> Dict:
        """Create a new onboarding session"""
        if not self._initialized:
            await self.initialize()
        
        return await self.mcp_ops.create_onboarding_session(
            org_name, project_slug, member_id, project_id
        )
    
    async def add_contact_to_session(self, session_id: int, contact: Dict) -> Dict:
        """Add a contact to an onboarding session"""
        return await self.mcp_ops.add_contact_to_session(session_id, contact)
    
    async def update_contact_committee_status(self, contact_id: int, 
                                            status: str, committee_id: str = None) -> Dict:
        """Update contact's committee status"""
        updates = {
            "committee_status": status,
            "committee_id": committee_id
        }
        return await self.mcp_ops.update_contact_status(contact_id, updates)
    
    async def update_contact_slack_status(self, contact_id: int,
                                         status: str, slack_user_id: str = None) -> Dict:
        """Update contact's Slack status"""
        updates = {
            "slack_status": status,
            "slack_user_id": slack_user_id
        }
        return await self.mcp_ops.update_contact_status(contact_id, updates)
    
    async def update_contact_email_status(self, contact_id: int, status: str) -> Dict:
        """Update contact's email status"""
        updates = {"email_status": status}
        return await self.mcp_ops.update_contact_status(contact_id, updates)
    
    async def update_overall_status(self, contact_id: int) -> Dict:
        """Update overall status based on individual statuses"""
        # First get the contact's current statuses
        result = await self.mcp_ops.client.execute_query(
            """
            SELECT committee_status, slack_status, email_status 
            FROM contact_onboarding WHERE id = ?
            """,
            [contact_id]
        )
        
        if result["status"] == "success":
            data = json.loads(result["data"]) if isinstance(result["data"], str) else result["data"]
            if data:
                statuses = data[0]
                status_values = [
                    statuses.get("committee_status"),
                    statuses.get("slack_status"),
                    statuses.get("email_status")
                ]
                
                # Determine overall status
                if all(s in ["completed", "success"] for s in status_values):
                    overall = "completed"
                elif any(s == "failed" for s in status_values):
                    overall = "failed"
                elif any(s in ["completed", "success"] for s in status_values):
                    overall = "partial"
                else:
                    overall = "pending"
                
                # Update overall status
                return await self.mcp_ops.update_contact_status(
                    contact_id,
                    {"overall_status": overall}
                )
        
        return result
    
    async def update_session_statistics(self, session_id: int) -> Dict:
        """Update session statistics"""
        return await self.mcp_ops.update_session_statistics(session_id)
    
    async def get_session_report(self, session_id: int) -> Dict:
        """Get comprehensive session report"""
        return await self.mcp_ops.get_session_report(session_id)
    
    async def find_contacts_by_status(self, session_id: int, 
                                     status_filters: Dict) -> Dict:
        """Find contacts based on status criteria"""
        # Build WHERE clause
        where_clauses = ["session_id = ?"]
        values = [session_id]
        
        for key, value in status_filters.items():
            where_clauses.append(f"{key} = ?")
            values.append(value)
        
        query = f"""
        SELECT * FROM contact_onboarding
        WHERE {' AND '.join(where_clauses)}
        ORDER BY contact_type, email
        """
        
        result = await self.mcp_ops.client.execute_query(query, values)
        
        if result["status"] == "success":
            data = json.loads(result["data"]) if isinstance(result["data"], str) else result["data"]
            return {"status": "success", "data": data}
        
        return result
    
    async def get_contact_timeline(self, contact_id: int) -> Dict:
        """Get timeline of events for a contact"""
        result = await self.mcp_ops.client.execute_query(
            """
            SELECT event_type, event_status, event_details, created_at
            FROM onboarding_events
            WHERE contact_onboarding_id = ?
            ORDER BY created_at
            """,
            [contact_id]
        )
        
        if result["status"] == "success":
            data = json.loads(result["data"]) if isinstance(result["data"], str) else result["data"]
            return {"status": "success", "data": data}
        
        return result