"""Stub services for local testing and development"""
import asyncio
import json
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime
import random
import uuid
from contextlib import contextmanager

# Sample data for testing
SAMPLE_ORGANIZATIONS = [
    {"id": "org-001", "name": "Acme Corp", "tier": "Gold"},
    {"id": "org-002", "name": "Tech Innovations Inc", "tier": "Silver"},
    {"id": "org-003", "name": "Cloud Systems Ltd", "tier": "Platinum"}
]

SAMPLE_CONTACTS = [
    # Acme Corp contacts
    {"contact_id": "cnt-001", "member_id": "org-001", "first_name": "John", "last_name": "Doe", 
     "email": "john.doe@acmecorp.com", "title": "CEO", "contact_type": "primary", "organization": "Acme Corp"},
    {"contact_id": "cnt-002", "member_id": "org-001", "first_name": "Jane", "last_name": "Smith", 
     "email": "jane.smith@acmecorp.com", "title": "VP Marketing", "contact_type": "marketing", "organization": "Acme Corp"},
    {"contact_id": "cnt-003", "member_id": "org-001", "first_name": "Bob", "last_name": "Johnson", 
     "email": "bob.johnson@acmecorp.com", "title": "CTO", "contact_type": "technical", "organization": "Acme Corp"},
    
    # Tech Innovations contacts
    {"contact_id": "cnt-004", "member_id": "org-002", "first_name": "Alice", "last_name": "Williams", 
     "email": "alice.williams@techinnovations.com", "title": "President", "contact_type": "primary", "organization": "Tech Innovations Inc"},
    {"contact_id": "cnt-005", "member_id": "org-002", "first_name": "Charlie", "last_name": "Brown", 
     "email": "charlie.brown@techinnovations.com", "title": "Marketing Director", "contact_type": "marketing", "organization": "Tech Innovations Inc"},
    {"contact_id": "cnt-006", "member_id": "org-002", "first_name": "David", "last_name": "Lee", 
     "email": "david.lee@techinnovations.com", "title": "Engineering Lead", "contact_type": "technical", "organization": "Tech Innovations Inc"},
]

SAMPLE_PROJECTS = [
    {"id": "proj-001", "slug": "cncf", "name": "CNCF", "description": "Cloud Native Computing Foundation"},
    {"id": "proj-002", "slug": "prometheus", "name": "Prometheus", "description": "Monitoring and alerting toolkit"},
    {"id": "proj-003", "slug": "envoy", "name": "Envoy", "description": "Cloud-native high-performance proxy"}
]

SAMPLE_COMMITTEES = {
    "proj-001": [
        {"id": "comm-001", "name": "Governing Board", "type": "governance", "project_id": "proj-001"},
        {"id": "comm-002", "name": "Marketing Committee", "type": "marketing", "project_id": "proj-001"},
        {"id": "comm-003", "name": "Technical Steering Committee", "type": "technical", "project_id": "proj-001"}
    ],
    "proj-002": [
        {"id": "comm-004", "name": "Governing Board", "type": "governance", "project_id": "proj-002"},
        {"id": "comm-005", "name": "Marketing Committee", "type": "marketing", "project_id": "proj-002"},
        {"id": "comm-006", "name": "Technical Committee", "type": "technical", "project_id": "proj-002"}
    ]
}

class StubMemberService:
    """Stub implementation of Member Service API"""
    
    async def get_member_by_organization(self, org_name: str) -> Dict:
        """Get member ID by organization name"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        for org in SAMPLE_ORGANIZATIONS:
            if org['name'].lower() == org_name.lower():
                return {
                    "status": "success",
                    "member_id": org['id'],
                    "member_info": org
                }
        
        return {
            "status": "error",
            "message": f"Organization '{org_name}' not found"
        }
    
    async def get_member_contacts(self, member_id: str) -> List[Dict]:
        """Fetch all contacts for a specific member"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        contacts = [c for c in SAMPLE_CONTACTS if c['member_id'] == member_id]
        return {
            "status": "success",
            "contacts": contacts,
            "count": len(contacts)
        }
    
    async def get_contact_details(self, member_id: str, contact_id: str) -> Dict:
        """Get detailed information about a specific contact"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        for contact in SAMPLE_CONTACTS:
            if contact['contact_id'] == contact_id and contact['member_id'] == member_id:
                return {
                    "status": "success",
                    "contact": contact
                }
        
        return {
            "status": "error",
            "message": f"Contact {contact_id} not found"
        }

class StubProjectService:
    """Stub implementation of Project Service API"""
    
    # Track committee members in memory
    committee_members = {}
    
    async def get_project_by_slug(self, project_slug: str) -> Dict:
        """Get project details by slug"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        for project in SAMPLE_PROJECTS:
            if project['slug'] == project_slug:
                return {
                    "status": "success",
                    "project_id": project['id'],
                    "project_info": project
                }
        
        return {
            "status": "error",
            "message": f"Project '{project_slug}' not found"
        }
    
    async def get_project_committees(self, project_id: str) -> List[Dict]:
        """Get all committees for a project"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        committees = SAMPLE_COMMITTEES.get(project_id, [])
        return {
            "status": "success",
            "committees": committees,
            "count": len(committees)
        }
    
    async def add_committee_member(self, project_id: str, committee_id: str, member_data: Dict) -> Dict:
        """Add a member to a committee"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Simulate occasional failures
        if random.random() < 0.05:  # 5% failure rate
            return {
                "status": "error",
                "message": "Temporary service unavailable"
            }
        
        # Store in memory
        key = f"{committee_id}:{member_data['email']}"
        StubProjectService.committee_members[key] = {
            **member_data,
            "committee_id": committee_id,
            "project_id": project_id,
            "added_at": datetime.now().isoformat()
        }
        
        return {
            "status": "success",
            "member_id": str(uuid.uuid4()),
            "message": f"Added {member_data['email']} to committee {committee_id}"
        }
    
    async def check_committee_membership(self, project_id: str, committee_id: str, email: str) -> Dict:
        """Check if contact is already in committee"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        key = f"{committee_id}:{email}"
        is_member = key in StubProjectService.committee_members
        
        return {
            "status": "success",
            "is_member": is_member,
            "member_data": StubProjectService.committee_members.get(key) if is_member else None
        }

class StubSlackService:
    """Stub implementation of Slack API"""
    
    # Track Slack users in memory
    slack_users = {}
    channel_members = {}
    
    async def invite_to_workspace(self, email: str, channels: List[str], organization: str) -> Dict:
        """Send Slack workspace invitation"""
        await asyncio.sleep(0.2)  # Simulate network delay
        
        # Simulate occasional failures
        if random.random() < 0.1:  # 10% failure rate
            return {
                "status": "error",
                "error": "user_already_invited",
                "message": f"User {email} already has pending invitation"
            }
        
        # Generate fake Slack user ID
        user_id = f"U{str(uuid.uuid4())[:8].upper()}"
        
        StubSlackService.slack_users[email] = {
            "user_id": user_id,
            "email": email,
            "organization": organization,
            "joined_at": datetime.now().isoformat()
        }
        
        # Add to channels
        for channel in channels:
            if channel not in StubSlackService.channel_members:
                StubSlackService.channel_members[channel] = []
            StubSlackService.channel_members[channel].append(user_id)
        
        return {
            "status": "success",
            "slack_user_id": user_id,
            "message": f"Invited {email} to workspace"
        }
    
    async def add_to_channel(self, user_id: str, channel: str) -> Dict:
        """Add user to specific Slack channel"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        if channel not in StubSlackService.channel_members:
            StubSlackService.channel_members[channel] = []
        
        if user_id not in StubSlackService.channel_members[channel]:
            StubSlackService.channel_members[channel].append(user_id)
        
        return {
            "status": "success",
            "message": f"Added user {user_id} to channel {channel}"
        }
    
    async def send_direct_message(self, user_id: str, message: str) -> Dict:
        """Send a direct message to a user"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        return {
            "status": "success",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }

class StubEmailService:
    """Stub implementation of Email service"""
    
    # Track sent emails in memory
    sent_emails = []
    
    async def send_welcome_email(self, contact: Dict, project_info: Dict) -> Dict:
        """Send personalized welcome email"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Simulate occasional failures
        if random.random() < 0.05:  # 5% failure rate
            return {
                "status": "error",
                "error": "smtp_connection_failed",
                "message": "Failed to connect to SMTP server"
            }
        
        email_record = {
            "id": str(uuid.uuid4()),
            "to": contact['email'],
            "subject": f"Welcome to {project_info.get('name', 'Project')} - {contact['contact_type'].title()} Committee",
            "template": f"welcome_{contact['contact_type']}",
            "sent_at": datetime.now().isoformat(),
            "status": "delivered"
        }
        
        StubEmailService.sent_emails.append(email_record)
        
        return {
            "status": "success",
            "email_id": email_record['id'],
            "message": f"Email sent to {contact['email']}"
        }
    
    def get_sent_emails() -> List[Dict]:
        """Get list of sent emails for testing"""
        return StubEmailService.sent_emails

class StubLandscapeService:
    """Stub implementation of Landscape update service"""
    
    # Track landscape updates in memory
    landscape_updates = []
    
    async def update_member_logo(self, project: str, organization: str, logo_url: str) -> Dict:
        """Update organization logo on project landscape"""
        await asyncio.sleep(0.2)  # Simulate network delay
        
        pr_id = f"PR-{random.randint(1000, 9999)}"
        
        update_record = {
            "pr_id": pr_id,
            "project": project,
            "organization": organization,
            "file": f"hosted_logos/{organization.lower().replace(' ', '_')}.svg",
            "logo_url": logo_url or f"https://placeholder.com/logo/{organization.lower()}.svg",
            "created_at": datetime.now().isoformat(),
            "status": "open"
        }
        
        StubLandscapeService.landscape_updates.append(update_record)
        
        return {
            "status": "success",
            "pr_url": f"https://github.com/{project}/landscape/pull/{pr_id}",
            "pr_id": pr_id,
            "message": f"Created PR to update {organization} logo"
        }
    
    async def check_landscape_entry(self, project: str, organization: str) -> Dict:
        """Check if organization exists in landscape"""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Randomly decide if org exists (70% chance it does)
        exists = random.random() < 0.7
        
        return {
            "status": "success",
            "exists": exists,
            "entry": {
                "name": organization,
                "logo": f"hosted_logos/{organization.lower().replace(' ', '_')}.svg",
                "membership": "gold"
            } if exists else None
        }

class StubDatabaseService:
    """Stub implementation of database operations using SQLite"""
    
    def __init__(self, db_path: str = "./local_onboarding.db"):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
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
            ''')
            
            cursor.execute('''
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
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS onboarding_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_onboarding_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    event_status TEXT NOT NULL,
                    event_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (contact_onboarding_id) REFERENCES contact_onboarding(id)
                )
            ''')
    
    async def create_session(self, data: Dict) -> Dict:
        """Create a new onboarding session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO onboarding_sessions 
                (organization_name, project_slug, member_id, project_id)
                VALUES (?, ?, ?, ?)
            ''', (data['org_name'], data['project_slug'], data['member_id'], data['project_id']))
            
            return {
                "status": "success",
                "session_id": cursor.lastrowid
            }
    
    async def add_contact(self, session_id: int, contact: Dict) -> Dict:
        """Add a contact to onboarding session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO contact_onboarding 
                (session_id, contact_id, email, first_name, last_name, title, contact_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                contact['contact_id'],
                contact['email'],
                contact.get('first_name', ''),
                contact.get('last_name', ''),
                contact.get('title', ''),
                contact.get('contact_type', '')
            ))
            
            return {
                "status": "success",
                "contact_onboarding_id": cursor.lastrowid
            }
    
    async def update_contact_status(self, contact_id: int, status_type: str, 
                                  status: str, additional_data: Dict = None) -> Dict:
        """Update contact status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Update contact status
            if status_type == "committee":
                cursor.execute('''
                    UPDATE contact_onboarding 
                    SET committee_status = ?, committee_id = ?
                    WHERE id = ?
                ''', (status, additional_data.get('committee_id') if additional_data else None, contact_id))
            elif status_type == "slack":
                cursor.execute('''
                    UPDATE contact_onboarding 
                    SET slack_status = ?, slack_user_id = ?
                    WHERE id = ?
                ''', (status, additional_data.get('slack_user_id') if additional_data else None, contact_id))
            elif status_type == "email":
                cursor.execute('''
                    UPDATE contact_onboarding 
                    SET email_status = ?
                    WHERE id = ?
                ''', (status, contact_id))
            
            # Log event
            cursor.execute('''
                INSERT INTO onboarding_events 
                (contact_onboarding_id, event_type, event_status, event_details)
                VALUES (?, ?, ?, ?)
            ''', (
                contact_id,
                status_type,
                status,
                json.dumps(additional_data) if additional_data else None
            ))
            
            # Update overall status
            cursor.execute('''
                UPDATE contact_onboarding 
                SET overall_status = CASE
                    WHEN committee_status IN ('success', 'already_member') 
                         AND (slack_status = 'success' OR email_status = 'success')
                    THEN 'completed'
                    WHEN committee_status = 'failed' AND slack_status = 'failed' AND email_status = 'failed'
                    THEN 'failed'
                    ELSE 'partial'
                END
                WHERE id = ?
            ''', (contact_id,))
            
            return {"status": "success"}
    
    async def update_session_stats(self, session_id: int) -> Dict:
        """Update session statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate stats
            cursor.execute('''
                UPDATE onboarding_sessions 
                SET total_contacts = (
                    SELECT COUNT(*) FROM contact_onboarding WHERE session_id = ?
                ),
                successful_contacts = (
                    SELECT COUNT(*) FROM contact_onboarding 
                    WHERE session_id = ? AND overall_status = 'completed'
                ),
                failed_contacts = (
                    SELECT COUNT(*) FROM contact_onboarding 
                    WHERE session_id = ? AND overall_status = 'failed'
                )
                WHERE id = ?
            ''', (session_id, session_id, session_id, session_id))
            
            return {"status": "success"}
    
    async def get_session_report(self, session_id: int) -> Dict:
        """Get session report"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get session info
            cursor.execute('SELECT * FROM onboarding_sessions WHERE id = ?', (session_id,))
            session = dict(cursor.fetchone())
            
            # Get contacts
            cursor.execute('''
                SELECT * FROM contact_onboarding 
                WHERE session_id = ? 
                ORDER BY contact_type, email
            ''', (session_id,))
            contacts = [dict(row) for row in cursor.fetchall()]
            
            # Get summary by type
            cursor.execute('''
                SELECT 
                    contact_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN overall_status = 'completed' THEN 1 ELSE 0 END) as successful
                FROM contact_onboarding 
                WHERE session_id = ?
                GROUP BY contact_type
            ''', (session_id,))
            type_summary = [dict(row) for row in cursor.fetchall()]
            
            return {
                "status": "success",
                "report": {
                    "session": session,
                    "contacts": contacts,
                    "type_summary": type_summary
                }
            }

# Factory functions to get stub services
def get_stub_member_service():
    return StubMemberService()

def get_stub_project_service():
    return StubProjectService()

def get_stub_slack_service():
    return StubSlackService()

def get_stub_email_service():
    return StubEmailService()

def get_stub_landscape_service():
    return StubLandscapeService()

def get_stub_database_service(db_path: str = "./local_onboarding.db"):
    return StubDatabaseService(db_path)