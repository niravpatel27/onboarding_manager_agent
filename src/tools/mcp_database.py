"""
Database abstraction using real MCP (Model Context Protocol) with proper CRUD tools
"""

from typing import Dict, List, Any, Optional
from .mcp_client import MCPDatabaseOperations
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class OnboardingDatabaseToolsMCP:
    """
    High-level database tools using MCP's CRUD operations properly.
    No raw SQL queries - only MCP tool calls.
    """
    
    def __init__(self, db_path: str = "./local_onboarding.db"):
        self.mcp_ops = MCPDatabaseOperations(db_path)
        self._initialized = False
    
    async def initialize(self) -> Dict:
        """Initialize the database schema using MCP tools"""
        try:
            # First check if tables exist by trying to read their schema
            tables_to_check = ['onboarding_sessions', 'contact_onboarding', 'onboarding_events']
            existing_tables = []
            
            for table in tables_to_check:
                result = await self.mcp_ops.get_table_schema(table)
                if result["status"] == "success":
                    existing_tables.append(table)
            
            if len(existing_tables) == len(tables_to_check):
                self._initialized = True
                return {"status": "success", "message": "Schema already initialized"}
            
            # If tables don't exist, we need to create them
            # MCP SQLite doesn't have a create_table tool, so we'll need custom SQL for this
            # This is the ONLY place where custom SQL is acceptable
            init_result = await self.mcp_ops.initialize_schema()
            if init_result["status"] == "success":
                self._initialized = True
            return init_result
            
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            return {"status": "error", "message": str(e)}
    
    async def create_onboarding_session(self, org_name: str, project_slug: str,
                                       member_id: str, project_id: str) -> Dict:
        """Create a new onboarding session using MCP create_record"""
        if not self._initialized:
            await self.initialize()
        
        session_data = {
            "organization_name": org_name,
            "project_slug": project_slug,
            "member_id": member_id,
            "project_id": project_id,
            "started_at": datetime.now().isoformat(),
            "status": "in_progress",
            "total_contacts": 0,
            "successful_contacts": 0,
            "failed_contacts": 0
        }
        
        result = await self.mcp_ops.create_record("onboarding_sessions", session_data)
        
        if result["status"] == "success":
            # Get the created session ID
            sessions = await self.mcp_ops.read_records(
                "onboarding_sessions",
                {
                    "organization_name": org_name,
                    "project_slug": project_slug,
                    "member_id": member_id,
                    "project_id": project_id
                },
                order_by="id DESC",
                limit=1
            )
            
            if sessions["status"] == "success" and sessions.get("data"):
                session_id = sessions["data"][0]["id"]
                return {
                    "status": "success",
                    "session_id": session_id,
                    "message": f"Created onboarding session for {org_name} -> {project_slug}"
                }
        
        return result
    
    async def add_contact_to_session(self, session_id: int, contact: Dict) -> Dict:
        """Add a contact to an onboarding session using MCP create_record"""
        contact_data = {
            "session_id": session_id,
            "contact_id": contact['contact_id'],
            "email": contact['email'],
            "first_name": contact.get('first_name'),
            "last_name": contact.get('last_name'),
            "title": contact.get('title'),
            "contact_type": contact.get('contact_type'),
            "committee_status": "pending",
            "slack_status": "pending",
            "email_status": "pending",
            "overall_status": "pending",
            "started_at": datetime.now().isoformat()
        }
        
        result = await self.mcp_ops.create_record("contact_onboarding", contact_data)
        
        if result["status"] == "success":
            # Get the created contact ID
            contacts = await self.mcp_ops.read_records(
                "contact_onboarding",
                {
                    "session_id": session_id,
                    "contact_id": contact['contact_id']
                },
                order_by="id DESC",
                limit=1
            )
            
            if contacts["status"] == "success" and contacts.get("data"):
                contact_id = contacts["data"][0]["id"]
                return {
                    "status": "success",
                    "contact_onboarding_id": contact_id,
                    "message": f"Added contact {contact['email']} to session"
                }
        
        return result
    
    async def update_contact_committee_status(self, contact_id: int, 
                                            status: str, committee_id: str = None) -> Dict:
        """Update contact's committee status using MCP update_records"""
        updates = {
            "committee_status": status
        }
        if committee_id:
            updates["committee_id"] = committee_id
        
        result = await self.mcp_ops.update_records(
            "contact_onboarding",
            updates,
            {"id": contact_id}
        )
        
        # Log the event
        if result["status"] == "success":
            await self._log_event(contact_id, "committee", status, {"committee_id": committee_id})
        
        return result
    
    async def update_contact_slack_status(self, contact_id: int,
                                         status: str, slack_user_id: str = None) -> Dict:
        """Update contact's Slack status using MCP update_records"""
        updates = {
            "slack_status": status
        }
        if slack_user_id:
            updates["slack_user_id"] = slack_user_id
        
        result = await self.mcp_ops.update_records(
            "contact_onboarding",
            updates,
            {"id": contact_id}
        )
        
        # Log the event
        if result["status"] == "success":
            await self._log_event(contact_id, "slack", status, {"slack_user_id": slack_user_id})
        
        return result
    
    async def update_contact_email_status(self, contact_id: int, status: str) -> Dict:
        """Update contact's email status using MCP update_records"""
        result = await self.mcp_ops.update_records(
            "contact_onboarding",
            {"email_status": status},
            {"id": contact_id}
        )
        
        # Log the event
        if result["status"] == "success":
            await self._log_event(contact_id, "email", status, {})
        
        return result
    
    async def update_overall_status(self, contact_id: int) -> Dict:
        """Update overall status based on individual statuses"""
        # Read the contact's current statuses
        contact_result = await self.mcp_ops.read_records(
            "contact_onboarding",
            {"id": contact_id}
        )
        
        if contact_result["status"] == "success" and contact_result.get("data"):
            contact = contact_result["data"][0]
            
            # Determine overall status
            statuses = [
                contact.get("committee_status"),
                contact.get("slack_status"),
                contact.get("email_status")
            ]
            
            if all(s in ["completed", "success"] for s in statuses):
                overall = "completed"
                completed_at = datetime.now().isoformat()
            elif any(s == "failed" for s in statuses):
                overall = "failed"
                completed_at = None
            elif any(s in ["completed", "success"] for s in statuses):
                overall = "partial"
                completed_at = None
            else:
                overall = "pending"
                completed_at = None
            
            # Update the overall status
            updates = {"overall_status": overall}
            if completed_at:
                updates["completed_at"] = completed_at
            
            return await self.mcp_ops.update_records(
                "contact_onboarding",
                updates,
                {"id": contact_id}
            )
        
        return contact_result
    
    async def update_session_statistics(self, session_id: int) -> Dict:
        """Update session statistics using MCP tools"""
        # Get all contacts for this session
        contacts_result = await self.mcp_ops.read_records(
            "contact_onboarding",
            {"session_id": session_id}
        )
        
        if contacts_result["status"] == "success" and contacts_result.get("data"):
            contacts = contacts_result["data"]
            
            # Calculate statistics
            total = len(contacts)
            successful = sum(1 for c in contacts if c.get("overall_status") == "completed")
            failed = sum(1 for c in contacts if c.get("overall_status") == "failed")
            
            # Check if all contacts are processed
            pending = sum(1 for c in contacts if c.get("overall_status") == "pending")
            session_status = "completed" if pending == 0 else "in_progress"
            
            updates = {
                "total_contacts": total,
                "successful_contacts": successful,
                "failed_contacts": failed,
                "status": session_status
            }
            
            if session_status == "completed":
                updates["completed_at"] = datetime.now().isoformat()
            
            # Update session
            return await self.mcp_ops.update_records(
                "onboarding_sessions",
                updates,
                {"id": session_id}
            )
        
        return contacts_result
    
    async def get_session_report(self, session_id: int) -> Dict:
        """Get comprehensive session report using MCP read tools"""
        report = {"status": "success", "report": {}}
        
        # Get session details
        session_result = await self.mcp_ops.read_records(
            "onboarding_sessions",
            {"id": session_id}
        )
        
        if session_result["status"] == "success" and session_result.get("data"):
            report["report"]["session"] = session_result["data"][0]
        
        # Get all contacts
        contacts_result = await self.mcp_ops.read_records(
            "contact_onboarding",
            {"session_id": session_id},
            order_by="contact_type, email"
        )
        
        if contacts_result["status"] == "success":
            report["report"]["contacts"] = contacts_result.get("data", [])
            
            # Generate type summary
            contacts = contacts_result.get("data", [])
            type_summary = {}
            
            for contact in contacts:
                contact_type = contact.get("contact_type", "unknown")
                if contact_type not in type_summary:
                    type_summary[contact_type] = {"total": 0, "successful": 0}
                
                type_summary[contact_type]["total"] += 1
                if contact.get("overall_status") == "completed":
                    type_summary[contact_type]["successful"] += 1
            
            report["report"]["type_summary"] = [
                {"contact_type": k, **v} for k, v in type_summary.items()
            ]
        
        return report
    
    async def find_contacts_by_status(self, session_id: int, 
                                     status_filters: Dict) -> Dict:
        """Find contacts based on status criteria using MCP read_records"""
        # Build filter including session_id
        filters = {"session_id": session_id}
        filters.update(status_filters)
        
        return await self.mcp_ops.read_records(
            "contact_onboarding",
            filters,
            order_by="contact_type, email"
        )
    
    async def get_contact_timeline(self, contact_id: int) -> Dict:
        """Get timeline of events for a contact using MCP read_records"""
        return await self.mcp_ops.read_records(
            "onboarding_events",
            {"contact_onboarding_id": contact_id},
            order_by="created_at"
        )
    
    async def _log_event(self, contact_id: int, event_type: str, 
                        status: str, details: Dict) -> Dict:
        """Log an event using MCP create_record"""
        event_data = {
            "contact_onboarding_id": contact_id,
            "event_type": event_type,
            "event_status": status,
            "event_details": json.dumps(details),
            "created_at": datetime.now().isoformat()
        }
        
        return await self.mcp_ops.create_record("onboarding_events", event_data)