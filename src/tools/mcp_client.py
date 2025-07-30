"""
Real MCP Client implementation using the Model Context Protocol
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

class RealMCPClient:
    """
    MCP Client that connects to an actual MCP server for database operations.
    This uses the Model Context Protocol to communicate with external servers.
    """
    
    def __init__(self, db_path: str = "./local_onboarding.db"):
        self.db_path = db_path
        self.session: Optional[ClientSession] = None
        self.server_params = StdioServerParameters(
            command="npx",
            args=["-y", "mcp-sqlite", db_path],
            env=None
        )
    
    async def connect(self):
        """Connect to the MCP SQLite server"""
        if self.session:
            return
        
        logger.info("Connecting to MCP SQLite server...")
        
        # Create client session
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                await session.initialize()
                
                # Get available tools
                tools = await session.list_tools()
                if hasattr(tools, '__iter__'):
                    logger.info(f"Available tools: {[getattr(tool, 'name', str(tool)) for tool in tools]}")
                else:
                    logger.info(f"Available tools: {tools}")
                
                # Get available resources (optional - not all servers support this)
                try:
                    resources = await session.list_resources()
                    if hasattr(resources, '__iter__'):
                        logger.info(f"Available resources: {[getattr(r, 'uri', str(r)) for r in resources]}")
                    else:
                        logger.info(f"Available resources: {resources}")
                except Exception as e:
                    logger.debug(f"Server does not support list_resources: {e}")
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.session:
            # Session cleanup handled by context manager
            self.session = None
            logger.info("Disconnected from MCP server")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        if not self.session:
            await self.connect()
        
        logger.debug(f"Calling tool: {tool_name} with args: {arguments}")
        
        # Use stdio client context manager for each operation
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Call the tool
                result = await session.call_tool(tool_name, arguments)
                
                if result.isError:
                    logger.error(f"Tool error: {result.content}")
                    return {"status": "error", "message": str(result.content)}
                
                # Parse the result
                try:
                    content = result.content
                    if isinstance(content, list) and len(content) > 0:
                        return {"status": "success", "data": content[0].text}
                    return {"status": "success", "data": content}
                except Exception as e:
                    logger.error(f"Error parsing result: {e}")
                    return {"status": "error", "message": str(e)}
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        logger.debug(f"Reading resource: {uri}")
        
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.read_resource(uri)
                
                if isinstance(result.contents, list) and len(result.contents) > 0:
                    return {"status": "success", "data": result.contents[0].text}
                return {"status": "success", "data": result.contents}
    
    async def execute_query(self, query: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute a SQL query using the MCP server's query tool"""
        args = {"sql": query}
        if params:
            args["values"] = params
        return await self.call_tool("query", args)
    
    async def list_tables(self) -> Dict[str, Any]:
        """List all tables in the database"""
        # Try to read schema resource
        try:
            return await self.read_resource("sqlite:///schema")
        except Exception as e:
            # Fallback to query
            return await self.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
    
    async def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Get table schema information"""
        return await self.execute_query(f"PRAGMA table_info({table_name})")


class MCPDatabaseOperations:
    """
    High-level database operations using the real MCP client.
    This replaces direct SQL with MCP tool calls.
    """
    
    def __init__(self, db_path: str = "./local_onboarding.db"):
        self.client = RealMCPClient(db_path)
    
    async def initialize_schema(self) -> Dict[str, Any]:
        """Initialize the database schema"""
        # Create tables using MCP query tool
        queries = [
            """
            CREATE TABLE IF NOT EXISTS onboarding_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_name TEXT NOT NULL,
                project_slug TEXT NOT NULL,
                member_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'in_progress',
                total_contacts INTEGER DEFAULT 0,
                successful_contacts INTEGER DEFAULT 0,
                failed_contacts INTEGER DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS contact_onboarding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                contact_id TEXT NOT NULL,
                email TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                title TEXT,
                contact_type TEXT,
                committee_status TEXT DEFAULT 'pending',
                committee_id TEXT,
                slack_status TEXT DEFAULT 'pending',
                slack_user_id TEXT,
                email_status TEXT DEFAULT 'pending',
                overall_status TEXT DEFAULT 'pending',
                error_details TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES onboarding_sessions(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS onboarding_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_onboarding_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_status TEXT NOT NULL,
                event_details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contact_onboarding_id) REFERENCES contact_onboarding(id)
            )
            """
        ]
        
        for query in queries:
            result = await self.client.execute_query(query)
            if result["status"] == "error":
                return result
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_org_project ON onboarding_sessions(organization_name, project_slug)",
            "CREATE INDEX IF NOT EXISTS idx_session_contacts ON contact_onboarding(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_contact_email ON contact_onboarding(email)",
            "CREATE INDEX IF NOT EXISTS idx_events_contact ON onboarding_events(contact_onboarding_id)"
        ]
        
        for index in indexes:
            await self.client.execute_query(index)
        
        return {"status": "success", "message": "Schema initialized"}
    
    async def create_onboarding_session(self, org_name: str, project_slug: str,
                                       member_id: str, project_id: str) -> Dict[str, Any]:
        """Create a new onboarding session"""
        result = await self.client.execute_query(
            """
            INSERT INTO onboarding_sessions 
            (organization_name, project_slug, member_id, project_id)
            VALUES (?, ?, ?, ?)
            """,
            [org_name, project_slug, member_id, project_id]
        )
        
        if result["status"] == "success":
            # Get the inserted ID
            id_result = await self.client.execute_query("SELECT last_insert_rowid()")
            if id_result["status"] == "success":
                data = json.loads(id_result["data"]) if isinstance(id_result["data"], str) else id_result["data"]
                session_id = data[0]["last_insert_rowid()"] if data else None
                return {
                    "status": "success",
                    "session_id": session_id,
                    "message": f"Created onboarding session for {org_name} -> {project_slug}"
                }
        
        return result
    
    async def add_contact_to_session(self, session_id: int, contact: Dict) -> Dict[str, Any]:
        """Add a contact to an onboarding session"""
        result = await self.client.execute_query(
            """
            INSERT INTO contact_onboarding 
            (session_id, contact_id, email, first_name, last_name, title, contact_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                session_id,
                contact['contact_id'],
                contact['email'],
                contact.get('first_name'),
                contact.get('last_name'),
                contact.get('title'),
                contact.get('contact_type')
            ]
        )
        
        if result["status"] == "success":
            # Get the inserted ID
            id_result = await self.client.execute_query("SELECT last_insert_rowid()")
            if id_result["status"] == "success":
                data = json.loads(id_result["data"]) if isinstance(id_result["data"], str) else id_result["data"]
                contact_id = data[0]["last_insert_rowid()"] if data else None
                return {
                    "status": "success",
                    "contact_onboarding_id": contact_id,
                    "message": f"Added contact {contact['email']} to session"
                }
        
        return result
    
    async def update_contact_status(self, contact_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update contact status fields"""
        # Build UPDATE query dynamically
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)
        
        values.append(contact_id)
        
        query = f"""
        UPDATE contact_onboarding 
        SET {', '.join(set_clauses)}
        WHERE id = ?
        """
        
        result = await self.client.execute_query(query, values)
        
        # Log event if status update
        if result["status"] == "success" and any(k.endswith('_status') for k in updates):
            for key in updates:
                if key.endswith('_status'):
                    event_type = key.replace('_status', '')
                    await self.client.execute_query(
                        """
                        INSERT INTO onboarding_events 
                        (contact_onboarding_id, event_type, event_status, event_details)
                        VALUES (?, ?, ?, ?)
                        """,
                        [contact_id, event_type, updates[key], json.dumps(updates)]
                    )
        
        return result
    
    async def update_session_statistics(self, session_id: int) -> Dict[str, Any]:
        """Update session statistics"""
        # Get statistics
        stats_result = await self.client.execute_query(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN overall_status = 'completed' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN overall_status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM contact_onboarding
            WHERE session_id = ?
            """,
            [session_id]
        )
        
        if stats_result["status"] == "success":
            data = json.loads(stats_result["data"]) if isinstance(stats_result["data"], str) else stats_result["data"]
            stats = data[0] if data else {"total": 0, "successful": 0, "failed": 0}
            
            # Update session
            return await self.client.execute_query(
                """
                UPDATE onboarding_sessions
                SET total_contacts = ?, successful_contacts = ?, failed_contacts = ?
                WHERE id = ?
                """,
                [stats["total"], stats["successful"], stats["failed"], session_id]
            )
        
        return stats_result
    
    async def get_session_report(self, session_id: int) -> Dict[str, Any]:
        """Generate comprehensive session report"""
        # Get session details
        session_result = await self.client.execute_query(
            "SELECT * FROM onboarding_sessions WHERE id = ?",
            [session_id]
        )
        
        # Get contacts
        contacts_result = await self.client.execute_query(
            """
            SELECT * FROM contact_onboarding 
            WHERE session_id = ? 
            ORDER BY contact_type, email
            """,
            [session_id]
        )
        
        # Get type summary
        summary_result = await self.client.execute_query(
            """
            SELECT 
                contact_type,
                COUNT(*) as total,
                SUM(CASE WHEN overall_status = 'completed' THEN 1 ELSE 0 END) as successful
            FROM contact_onboarding
            WHERE session_id = ?
            GROUP BY contact_type
            """,
            [session_id]
        )
        
        # Parse results
        report = {"status": "success", "report": {}}
        
        if session_result["status"] == "success":
            data = json.loads(session_result["data"]) if isinstance(session_result["data"], str) else session_result["data"]
            report["report"]["session"] = data[0] if data else None
        
        if contacts_result["status"] == "success":
            data = json.loads(contacts_result["data"]) if isinstance(contacts_result["data"], str) else contacts_result["data"]
            report["report"]["contacts"] = data
        
        if summary_result["status"] == "success":
            data = json.loads(summary_result["data"]) if isinstance(summary_result["data"], str) else summary_result["data"]
            report["report"]["type_summary"] = data
        
        return report