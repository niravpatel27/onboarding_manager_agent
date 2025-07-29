"""
MCP Client implementation for executing database operations
"""

import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class MCPSQLiteClient:
    """
    MCP Client that executes database operations on local SQLite database.
    This translates MCP-style calls into actual SQLite operations.
    """
    
    def __init__(self, db_path: str = "./local_onboarding.db"):
        self.db_path = db_path
        self.connection = None
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database exists and is properly initialized"""
        if not os.path.exists(self.db_path):
            logger.info(f"Creating new database at {self.db_path}")
            self._initialize_schema()
    
    def _get_connection(self):
        """Get database connection"""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
        return self.connection
    
    def _initialize_schema(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
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
        """)
        
        cursor.execute("""
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
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS onboarding_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_onboarding_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_status TEXT NOT NULL,
                event_details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contact_onboarding_id) REFERENCES contact_onboarding(id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_org_project ON onboarding_sessions(organization_name, project_slug)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_contacts ON contact_onboarding(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contact_email ON contact_onboarding(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_contact ON onboarding_events(contact_onboarding_id)")
        
        conn.commit()
        conn.close()
        logger.info("Database schema initialized")
    
    async def execute(self, mcp_call: Dict) -> Dict:
        """Execute an MCP call and return the result"""
        if not isinstance(mcp_call, dict) or "mcp_call" not in mcp_call:
            # If it's not an MCP call, return it as is
            return mcp_call
        
        call_spec = mcp_call["mcp_call"]
        method = call_spec.get("method")
        params = call_spec.get("params", {})
        
        logger.info(f"Executing MCP method: {method}")
        
        # Route to appropriate handler
        if method == "schema.define":
            return await self._handle_schema_define(params)
        elif method == "record.create":
            return await self._handle_record_create(params)
        elif method == "record.update":
            return await self._handle_record_update(params)
        elif method == "record.find":
            return await self._handle_record_find(params)
        elif method == "record.aggregate":
            return await self._handle_record_aggregate(params)
        elif method == "transaction.execute":
            return await self._handle_transaction(params)
        elif method == "record.upsert":
            return await self._handle_record_upsert(params)
        elif method == "report.generate":
            return await self._handle_report_generate(params)
        elif method == "function.call":
            return await self._handle_function_call(params)
        else:
            raise ValueError(f"Unknown MCP method: {method}")
    
    async def _handle_schema_define(self, params: Dict) -> Dict:
        """Handle schema definition (already done in initialization)"""
        return {"status": "success", "message": "Schema already defined"}
    
    async def _handle_record_create(self, params: Dict) -> Dict:
        """Create a new record"""
        table = params["table"]
        data = params["data"]
        return_fields = params.get("return_fields", ["id"])
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build INSERT query
        columns = list(data.keys())
        placeholders = ["?" for _ in columns]
        values = [data[col] for col in columns]
        
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        
        try:
            cursor.execute(query, values)
            conn.commit()
            record_id = cursor.lastrowid
            
            # Return requested fields
            result = {"id": record_id}
            if len(return_fields) > 1:
                cursor.execute(f"SELECT {', '.join(return_fields)} FROM {table} WHERE id = ?", (record_id,))
                row = cursor.fetchone()
                result = dict(zip(return_fields, row))
            
            logger.info(f"Created record in {table} with id {record_id}")
            return {"status": "success", "data": result}
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating record: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_record_update(self, params: Dict) -> Dict:
        """Update an existing record"""
        table = params["table"]
        record_id = params["id"]
        data = params["data"]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build UPDATE query
        set_clauses = [f"{col} = ?" for col in data.keys()]
        values = list(data.values()) + [record_id]
        
        query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE id = ?"
        
        try:
            cursor.execute(query, values)
            conn.commit()
            logger.info(f"Updated record {record_id} in {table}")
            return {"status": "success", "rows_affected": cursor.rowcount}
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating record: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_record_find(self, params: Dict) -> Dict:
        """Find records based on filters"""
        table = params["table"]
        filters = params.get("filters", {})
        limit = params.get("limit")
        order_by = params.get("order_by", [])
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build WHERE clause
        where_clauses = []
        values = []
        for col, val in filters.items():
            where_clauses.append(f"{col} = ?")
            values.append(val)
        
        query = f"SELECT * FROM {table}"
        if where_clauses:
            query += f" WHERE {' AND '.join(where_clauses)}"
        if order_by:
            query += f" ORDER BY {', '.join(order_by)}"
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            cursor.execute(query, values)
            rows = cursor.fetchall()
            
            # Convert rows to dictionaries
            results = []
            for row in rows:
                results.append(dict(row))
            
            return {"status": "success", "data": results}
            
        except Exception as e:
            logger.error(f"Error finding records: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_transaction(self, params: Dict) -> Dict:
        """Execute multiple operations in a transaction"""
        operations = params["operations"]
        rollback_on_error = params.get("rollback_on_error", True)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            conn.execute("BEGIN TRANSACTION")
            
            results = []
            for op in operations:
                method = op["method"]
                op_params = op["params"]
                
                if method == "record.update":
                    result = await self._handle_record_update(op_params)
                elif method == "record.create":
                    result = await self._handle_record_create(op_params)
                else:
                    raise ValueError(f"Unsupported transaction operation: {method}")
                
                if result["status"] == "error" and rollback_on_error:
                    raise Exception(f"Transaction failed: {result['message']}")
                
                results.append(result)
            
            conn.commit()
            return {"status": "success", "results": results}
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_function_call(self, params: Dict) -> Dict:
        """Handle custom function calls"""
        function = params["function"]
        args = params["args"]
        
        if function == "calculate_overall_status":
            # Determine overall status based on individual statuses
            contact_id = args["contact_id"]
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT committee_status, slack_status, email_status 
                FROM contact_onboarding WHERE id = ?
            """, (contact_id,))
            
            row = cursor.fetchone()
            if row:
                statuses = [row["committee_status"], row["slack_status"], row["email_status"]]
                
                if all(s in ["completed", "success"] for s in statuses):
                    overall = "completed"
                elif any(s == "failed" for s in statuses):
                    overall = "failed"
                elif any(s in ["completed", "success"] for s in statuses):
                    overall = "partial"
                else:
                    overall = "pending"
                
                # Update overall status
                cursor.execute("""
                    UPDATE contact_onboarding 
                    SET overall_status = ?, completed_at = ?
                    WHERE id = ?
                """, (overall, datetime.now() if overall in ["completed", "failed"] else None, contact_id))
                
                conn.commit()
                return {"status": "success", "overall_status": overall}
        
        elif function == "update_session_with_stats":
            # Update session statistics
            session_id = args["session_id"]
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Calculate statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN overall_status = 'completed' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN overall_status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM contact_onboarding
                WHERE session_id = ?
            """, (session_id,))
            
            stats = cursor.fetchone()
            
            # Update session
            cursor.execute("""
                UPDATE onboarding_sessions
                SET total_contacts = ?, successful_contacts = ?, failed_contacts = ?
                WHERE id = ?
            """, (stats["total"], stats["successful"], stats["failed"], session_id))
            
            conn.commit()
            return {"status": "success", "stats": dict(stats)}
        
        return {"status": "error", "message": f"Unknown function: {function}"}
    
    async def _handle_report_generate(self, params: Dict) -> Dict:
        """Generate a report"""
        report_type = params["report_type"]
        filters = params.get("filters", {})
        
        if report_type == "onboarding_session":
            session_id = filters.get("session_id")
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get session details
            cursor.execute("SELECT * FROM onboarding_sessions WHERE id = ?", (session_id,))
            session = dict(cursor.fetchone()) if cursor.rowcount > 0 else None
            
            # Get contacts
            cursor.execute("""
                SELECT * FROM contact_onboarding 
                WHERE session_id = ? 
                ORDER BY contact_type, email
            """, (session_id,))
            contacts = [dict(row) for row in cursor.fetchall()]
            
            # Get type summary
            cursor.execute("""
                SELECT 
                    contact_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN overall_status = 'completed' THEN 1 ELSE 0 END) as successful
                FROM contact_onboarding
                WHERE session_id = ?
                GROUP BY contact_type
            """, (session_id,))
            type_summary = [dict(row) for row in cursor.fetchall()]
            
            return {
                "status": "success",
                "report": {
                    "session": session,
                    "contacts": contacts,
                    "type_summary": type_summary
                }
            }
        
        return {"status": "error", "message": f"Unknown report type: {report_type}"}
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def get_db_path(self):
        """Get the database file path"""
        return self.db_path