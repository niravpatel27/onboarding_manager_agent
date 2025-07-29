"""
This module provides a clean abstraction over MCP's database capabilities
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
from .mcp_client import MCPSQLiteClient

@dataclass
class Table:
    """Represents a database table structure"""
    name: str
    fields: Dict[str, str]
    indexes: List[str] = None
    foreign_keys: List[str] = None

class MCPDatabaseAbstraction:
    """
    Database abstraction using MCP's native capabilities.
    No SQL queries are written - everything uses MCP's abstraction layer.
    """
    
    def __init__(self, server_name: str = "sqlite-mcp-server"):
        self.server = server_name
        self.schema_defined = False
        self.client = MCPSQLiteClient()
    
    async def define_schema(self) -> Dict:
        """Define database schema using MCP's schema definition capabilities"""
        tables = [
            Table(
                name="onboarding_sessions",
                fields={
                    "id": "auto_increment",
                    "organization_name": "string.required",
                    "project_slug": "string.required",
                    "member_id": "string.required",
                    "project_id": "string.required",
                    "started_at": "timestamp.auto",
                    "completed_at": "timestamp.nullable",
                    "status": "string.default:in_progress",
                    "total_contacts": "integer.default:0",
                    "successful_contacts": "integer.default:0",
                    "failed_contacts": "integer.default:0"
                },
                indexes=["organization_name", "project_slug", "member_id"]
            ),
            Table(
                name="contact_onboarding",
                fields={
                    "id": "auto_increment",
                    "session_id": "integer.required",
                    "contact_id": "string.required",
                    "email": "string.required",
                    "first_name": "string.nullable",
                    "last_name": "string.nullable",
                    "title": "string.nullable",
                    "contact_type": "string.nullable",
                    "committee_status": "string.default:pending",
                    "committee_id": "string.nullable",
                    "slack_status": "string.default:pending",
                    "slack_user_id": "string.nullable",
                    "email_status": "string.default:pending",
                    "overall_status": "string.default:pending",
                    "error_details": "text.nullable",
                    "started_at": "timestamp.auto",
                    "completed_at": "timestamp.nullable"
                },
                foreign_keys=["session_id->onboarding_sessions.id"],
                indexes=["session_id", "email", "contact_type", "overall_status"]
            ),
            Table(
                name="onboarding_events",
                fields={
                    "id": "auto_increment",
                    "contact_onboarding_id": "integer.required",
                    "event_type": "string.required",
                    "event_status": "string.required",
                    "event_details": "text.nullable",
                    "created_at": "timestamp.auto"
                },
                foreign_keys=["contact_onboarding_id->contact_onboarding.id"],
                indexes=["contact_onboarding_id", "event_type", "created_at"]
            )
        ]
        
        mcp_call = {
            "mcp_call": {
                "server": self.server,
                "method": "schema.define",
                "params": {
                    "tables": [self._table_to_mcp_format(t) for t in tables],
                    "create_if_not_exists": True
                }
            }
        }
        
        # Execute through MCP client
        return await self.client.execute(mcp_call)
    
    def _table_to_mcp_format(self, table: Table) -> Dict:
        """Convert our table definition to MCP format"""
        return {
            "name": table.name,
            "fields": table.fields,
            "indexes": table.indexes or [],
            "foreign_keys": table.foreign_keys or []
        }
    
    async def create_record(self, table: str, data: Dict) -> Dict:
        """Create a new record using MCP's create method"""
        mcp_call = {
            "mcp_call": {
                "server": self.server,
                "method": "record.create",
                "params": {
                    "table": table,
                    "data": data,
                    "return_fields": ["id"]
                }
            }
        }
        
        # Execute through MCP client
        return await self.client.execute(mcp_call)
    
    async def update_record(self, table: str, record_id: Any, data: Dict) -> Dict:
        """Update a record using MCP's update method"""
        mcp_call = {
            "mcp_call": {
                "server": self.server,
                "method": "record.update",
                "params": {
                    "table": table,
                    "id": record_id,
                    "data": data
                }
            }
        }
        
        # Execute through MCP client
        return await self.client.execute(mcp_call)
    
    async def find_records(self, table: str, filters: Dict = None, 
                          options: Dict = None) -> Dict:
        """Find records using MCP's query builder"""
        params = {
            "table": table,
            "filters": filters or {}
        }
        
        if options:
            params.update(options)
        
        mcp_call = {
            "mcp_call": {
                "server": self.server,
                "method": "record.find",
                "params": params
            }
        }
        
        # Execute through MCP client
        return await self.client.execute(mcp_call)
    
    async def aggregate(self, table: str, aggregations: List[Dict], 
                       filters: Dict = None, group_by: List[str] = None) -> Dict:
        """Perform aggregations using MCP's aggregation capabilities"""
        return {
            "mcp_call": {
                "server": self.server,
                "method": "record.aggregate",
                "params": {
                    "table": table,
                    "aggregations": aggregations,
                    "filters": filters or {},
                    "group_by": group_by or []
                }
            }
        }
    
    async def run_transaction(self, operations: List[Dict]) -> Dict:
        """Execute multiple operations in a transaction"""
        mcp_call = {
            "mcp_call": {
                "server": self.server,
                "method": "transaction.execute",
                "params": {
                    "operations": operations,
                    "rollback_on_error": True
                }
            }
        }
        
        # Execute through MCP client
        return await self.client.execute(mcp_call)
    
    async def create_or_update(self, table: str, match_fields: Dict, 
                              data: Dict) -> Dict:
        """Create or update a record based on matching criteria"""
        return {
            "mcp_call": {
                "server": self.server,
                "method": "record.upsert",
                "params": {
                    "table": table,
                    "match": match_fields,
                    "data": data,
                    "return_fields": ["id", "created", "updated"]
                }
            }
        }

class OnboardingDatabaseTools:
    """
    High-level database tools for onboarding operations.
    All operations use MCP's abstraction - no SQL queries.
    """
    
    def __init__(self):
        self.db = MCPDatabaseAbstraction()
    
    async def initialize(self) -> Dict:
        """Initialize the database schema"""
        return await self.db.define_schema()
    
    async def create_onboarding_session(self, org_name: str, project_slug: str,
                                       member_id: str, project_id: str) -> Dict:
        """Create a new onboarding session"""
        result = await self.db.create_record(
            table="onboarding_sessions",
            data={
                "organization_name": org_name,
                "project_slug": project_slug,
                "member_id": member_id,
                "project_id": project_id
            }
        )
        
        # Extract session_id from result
        if result.get("status") == "success" and result.get("data"):
            return {
                "status": "success",
                "session_id": result["data"]["id"],
                "message": f"Created onboarding session for {org_name} -> {project_slug}"
            }
        else:
            return {
                "status": "error",
                "message": result.get("message", "Failed to create session")
            }
    
    async def add_contact_to_session(self, session_id: int, contact: Dict) -> Dict:
        """Add a contact to an onboarding session"""
        result = await self.db.create_record(
            table="contact_onboarding",
            data={
                "session_id": session_id,
                "contact_id": contact['contact_id'],
                "email": contact['email'],
                "first_name": contact.get('first_name'),
                "last_name": contact.get('last_name'),
                "title": contact.get('title'),
                "contact_type": contact.get('contact_type')
            }
        )
        
        # Extract contact_onboarding_id from result
        if result.get("status") == "success" and result.get("data"):
            return {
                "status": "success",
                "contact_onboarding_id": result["data"]["id"],
                "message": f"Added contact {contact['email']} to session"
            }
        else:
            return {
                "status": "error",
                "message": result.get("message", "Failed to add contact")
            }
    
    async def update_contact_committee_status(self, contact_id: int, 
                                            status: str, committee_id: str = None) -> Dict:
        """Update contact's committee status"""
        operations = [
            {
                "method": "record.update",
                "params": {
                    "table": "contact_onboarding",
                    "id": contact_id,
                    "data": {
                        "committee_status": status,
                        "committee_id": committee_id
                    }
                }
            },
            {
                "method": "record.create",
                "params": {
                    "table": "onboarding_events",
                    "data": {
                        "contact_onboarding_id": contact_id,
                        "event_type": "committee",
                        "event_status": status,
                        "event_details": json.dumps({"committee_id": committee_id})
                    }
                }
            }
        ]
        
        return await self.db.run_transaction(operations)
    
    async def update_contact_slack_status(self, contact_id: int,
                                         status: str, slack_user_id: str = None) -> Dict:
        """Update contact's Slack status"""
        operations = [
            {
                "method": "record.update",
                "params": {
                    "table": "contact_onboarding",
                    "id": contact_id,
                    "data": {
                        "slack_status": status,
                        "slack_user_id": slack_user_id
                    }
                }
            },
            {
                "method": "record.create",
                "params": {
                    "table": "onboarding_events",
                    "data": {
                        "contact_onboarding_id": contact_id,
                        "event_type": "slack",
                        "event_status": status,
                        "event_details": json.dumps({"slack_user_id": slack_user_id})
                    }
                }
            }
        ]
        
        return await self.db.run_transaction(operations)
    
    async def update_contact_email_status(self, contact_id: int, status: str) -> Dict:
        """Update contact's email status"""
        operations = [
            {
                "method": "record.update",
                "params": {
                    "table": "contact_onboarding",
                    "id": contact_id,
                    "data": {"email_status": status}
                }
            },
            {
                "method": "record.create",
                "params": {
                    "table": "onboarding_events",
                    "data": {
                        "contact_onboarding_id": contact_id,
                        "event_type": "email",
                        "event_status": status
                    }
                }
            }
        ]
        
        return await self.db.run_transaction(operations)
    
    async def update_overall_status(self, contact_id: int) -> Dict:
        """Update overall status based on individual statuses"""
        # First get the contact's current statuses
        contact = await self.db.find_records(
            table="contact_onboarding",
            filters={"id": contact_id},
            options={"limit": 1}
        )
        
        # MCP will handle the logic to determine overall status
        mcp_call = {
            "mcp_call": {
                "server": self.db.server,
                "method": "function.call",
                "params": {
                    "function": "calculate_overall_status",
                    "args": {
                        "contact_id": contact_id,
                        "current_data": contact
                    }
                }
            }
        }
        
        # Execute through MCP client
        return await self.db.client.execute(mcp_call)
    
    async def update_session_statistics(self, session_id: int) -> Dict:
        """Update session statistics using MCP aggregations"""
        # MCP will handle statistics calculation and update
        mcp_call = {
            "mcp_call": {
                "server": self.db.server,
                "method": "function.call",
                "params": {
                    "function": "update_session_with_stats",
                    "args": {
                        "session_id": session_id
                    }
                }
            }
        }
        
        # Execute through MCP client
        return await self.db.client.execute(mcp_call)
    
    async def get_session_report(self, session_id: int) -> Dict:
        """Get comprehensive session report"""
        mcp_call = {
            "mcp_call": {
                "server": self.db.server,
                "method": "report.generate",
                "params": {
                    "report_type": "onboarding_session",
                    "filters": {"session_id": session_id},
                    "include": [
                        "session_details",
                        "contact_list",
                        "type_summary",
                        "status_breakdown",
                        "timeline"
                    ]
                }
            }
        }
        
        # Execute through MCP client
        return await self.db.client.execute(mcp_call)
    
    async def find_contacts_by_status(self, session_id: int, 
                                     status_filters: Dict) -> Dict:
        """Find contacts based on status criteria"""
        filters = {"session_id": session_id}
        filters.update(status_filters)
        
        return await self.db.find_records(
            table="contact_onboarding",
            filters=filters,
            options={
                "order_by": ["contact_type", "email"],
                "include_related": ["events"]
            }
        )
    
    async def get_contact_timeline(self, contact_id: int) -> Dict:
        """Get timeline of events for a contact"""
        return await self.db.find_records(
            table="onboarding_events",
            filters={"contact_onboarding_id": contact_id},
            options={
                "order_by": ["created_at"],
                "include_fields": ["event_type", "event_status", "event_details", "created_at"]
            }
        )