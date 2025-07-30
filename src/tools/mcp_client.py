"""
Real MCP Client implementation using the Model Context Protocol with proper CRUD tools
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
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.session:
            # Session cleanup handled by context manager
            self.session = None
            logger.info("Disconnected from MCP server")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
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
                        # Handle text content
                        if hasattr(content[0], 'text'):
                            data = json.loads(content[0].text) if content[0].text else None
                            return {"status": "success", "data": data}
                        # Handle direct data
                        return {"status": "success", "data": content[0]}
                    return {"status": "success", "data": content}
                except Exception as e:
                    logger.error(f"Error parsing result: {e}")
                    return {"status": "error", "message": str(e)}
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get table schema information using MCP tool"""
        return await self.call_tool("get_table_schema", {"tableName": table_name})
    
    async def create_record(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record using MCP create_record tool"""
        return await self.call_tool("create_record", {"table": table, "data": data})
    
    async def read_records(self, table: str, filter: Optional[Dict] = None, 
                          order_by: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Read records using MCP read_records tool"""
        args = {"table": table}
        if filter:
            args["filter"] = filter
        if order_by:
            args["orderBy"] = order_by
        if limit:
            args["limit"] = limit
        
        return await self.call_tool("read_records", args)
    
    async def update_records(self, table: str, updates: Dict[str, Any], 
                           filter: Dict[str, Any]) -> Dict[str, Any]:
        """Update records using MCP update_records tool"""
        return await self.call_tool("update_records", {
            "table": table,
            "updates": updates,
            "filter": filter
        })
    
    async def delete_records(self, table: str, filter: Dict[str, Any]) -> Dict[str, Any]:
        """Delete records using MCP delete_records tool"""
        return await self.call_tool("delete_records", {"table": table, "filter": filter})
    
    async def execute_custom_sql(self, sql: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute custom SQL for complex queries only when CRUD tools aren't sufficient"""
        args = {"sql": sql}
        if params:
            args["params"] = params
        return await self.call_tool("execute_custom_sql", args)


class MCPDatabaseOperations:
    """
    High-level database operations using the real MCP client with proper CRUD tools.
    """
    
    def __init__(self, db_path: str = "./local_onboarding.db"):
        self.client = RealMCPClient(db_path)
    
    async def initialize_schema(self) -> Dict[str, Any]:
        """Initialize the database schema - only place where custom SQL is needed"""
        # Create tables using custom SQL since MCP doesn't have create_table tool
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
            result = await self.client.execute_custom_sql(query)
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
            await self.client.execute_custom_sql(index)
        
        return {"status": "success", "message": "Schema initialized"}
    
    async def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get table schema information"""
        return await self.client.get_table_schema(table_name)
    
    async def create_record(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record"""
        return await self.client.create_record(table, data)
    
    async def read_records(self, table: str, filter: Optional[Dict] = None,
                          order_by: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Read records from table"""
        return await self.client.read_records(table, filter, order_by, limit)
    
    async def update_records(self, table: str, updates: Dict[str, Any],
                           filter: Dict[str, Any]) -> Dict[str, Any]:
        """Update records in table"""
        return await self.client.update_records(table, updates, filter)