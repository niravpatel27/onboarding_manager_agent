import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from contextlib import asynccontextmanager
from agno.agent import Agent, Function, Message
from agno.models.openai import OpenAIChat
from src.tools.mcp_database import OnboardingDatabaseToolsMCP
import os
from dotenv import load_dotenv
from enhanced_logger import onboarding_logger as workflow_logger

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check for API key
api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    logger.error("OPENAI_API_KEY not found in environment variables")

# Additional check with instructions
if not os.getenv("OPENAI_API_KEY"):
    logger.warning("Please set it with: export OPENAI_API_KEY='your-api-key-here'")
    logger.warning("Or create a .env file with: OPENAI_API_KEY=your-api-key-here")

# Data Models
@dataclass
class Contact:
    first_name: str
    last_name: str
    title: str
    email: str
    contact_type: str  # primary, marketing, or technical
    organization: str
    contact_id: str
    
    def to_dict(self):
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'title': self.title,
            'email': self.email,
            'contact_type': self.contact_type,
            'organization': self.organization,
            'contact_id': self.contact_id
        }

@dataclass
class ProjectContext:
    organization_name: str
    project_slug: str
    member_id: Optional[str] = None
    project_id: Optional[str] = None
    committees: Optional[Dict[str, str]] = None  # contact_type -> committee_id mapping

# Database operations are now handled by OnboardingDatabaseTools
# from mcp_database_abstraction module - no SQL queries needed

# Database Agent for MCP interactions
class DatabaseAgent(Agent):
    """Agent responsible for database operations via MCP"""
    
    def __init__(self, mcp_server_type: str = "sqlite"):
        self.db_tools = OnboardingDatabaseToolsMCP()
        super().__init__(
            name="DatabaseManager",
            model=OpenAIChat(id="gpt-4o-mini"),
            instructions=f"""You manage all database operations through MCP's abstraction layer.
            Your tasks:
            1. Initialize database schema if not exists
            2. Create and manage onboarding sessions
            3. Track contact onboarding progress
            4. Update statuses and log events
            5. Generate reports from stored data
            6. Handle transactions for data consistency
            
            IMPORTANT: When asked to "Add contact to onboarding session":
            - Look at the message context which contains 'session_id' and 'contact' 
            - You MUST call add_contact_to_session with BOTH parameters: 
              - session_id (from context.session_id)
              - contact (from context.contact - pass the entire contact dictionary)
            - Do NOT call with just session_id
            
            The message will have context like: {{"session_id": 123, "contact": {{"email": "test@test.com", ...}}}}
            You MUST call: add_contact_to_session(session_id=123, contact={{"email": "test@test.com", ...}})
            
            Use the MCP abstraction methods - no SQL queries needed.
            All database operations are handled through MCP's native capabilities.
            """,
            tools=[
                Function.from_callable(self.db_tools.initialize),
                Function.from_callable(self.db_tools.create_onboarding_session),
                Function.from_callable(self.db_tools.add_contact_to_session),
                Function.from_callable(self.db_tools.update_contact_committee_status),
                Function.from_callable(self.db_tools.update_contact_slack_status),
                Function.from_callable(self.db_tools.update_contact_email_status),
                Function.from_callable(self.db_tools.update_overall_status),
                Function.from_callable(self.db_tools.update_session_statistics),
                Function.from_callable(self.db_tools.get_session_report),
                Function.from_callable(self.db_tools.find_contacts_by_status),
                Function.from_callable(self.db_tools.get_contact_timeline)
            ]
        )
        self.mcp_server_type = mcp_server_type

# Import config and stub services
from config import config
from stub_services import (
    get_stub_member_service,
    get_stub_project_service,
    get_stub_slack_service,
    get_stub_email_service,
    get_stub_landscape_service,
    get_stub_database_service
)

# Tool Definitions
class MemberServiceTools:
    """Tools for Member Service API interactions"""
    
    @staticmethod
    async def get_member_by_organization(org_name: str) -> Dict:
        """Get member ID by organization name"""
        if config.is_using_stubs():
            service = get_stub_member_service()
            return await service.get_member_by_organization(org_name)
        
        # Production API call would go here
        return {
            "endpoint": "GET /member-service/members",
            "params": {
                "organization_name": org_name,
                "status": "active"
            },
            "description": "Fetch member record by organization name"
        }
    
    @staticmethod
    async def get_member_contacts(member_id: str) -> List[Dict]:
        """Fetch all contacts for a specific member"""
        if config.is_using_stubs():
            service = get_stub_member_service()
            result = await service.get_member_contacts(member_id)
            return result
        
        return {
            "endpoint": f"GET /member-service/members/{member_id}/contacts",
            "description": "Fetch all contacts associated with the member organization"
        }
    
    @staticmethod
    async def get_contact_details(member_id: str, contact_id: str) -> Dict:
        """Get detailed information about a specific contact"""
        return {
            "endpoint": f"GET /member-service/members/{member_id}/contacts/{contact_id}",
            "description": "Retrieve full contact details"
        }

class ProjectServiceTools:
    """Tools for Project Service API interactions"""
    
    @staticmethod
    async def get_project_by_slug(project_slug: str) -> Dict:
        """Get project details by slug"""
        if config.is_using_stubs():
            service = get_stub_project_service()
            return await service.get_project_by_slug(project_slug)
        
        return {
            "endpoint": f"GET /project-service/projects",
            "params": {
                "slug": project_slug
            },
            "description": "Fetch project details by slug"
        }
    
    @staticmethod
    async def get_project_committees(project_id: str) -> List[Dict]:
        """Get all committees for a project"""
        if config.is_using_stubs():
            service = get_stub_project_service()
            return await service.get_project_committees(project_id)
        
        return {
            "endpoint": f"GET /project-service/projects/{project_id}/committees",
            "description": "Fetch all committees in the project"
        }
    
    @staticmethod
    async def add_committee_member(project_id: str, committee_id: str, member_data: Dict) -> Dict:
        """Add a member to a committee"""
        if config.is_using_stubs():
            service = get_stub_project_service()
            return await service.add_committee_member(project_id, committee_id, member_data)
        
        return {
            "endpoint": f"POST /project-service/projects/{project_id}/committees/{committee_id}/committee_members",
            "payload": member_data,
            "description": "Add contact to specified committee"
        }
    
    @staticmethod
    async def check_committee_membership(project_id: str, committee_id: str, email: str) -> Dict:
        """Check if contact is already in committee"""
        if config.is_using_stubs():
            service = get_stub_project_service()
            return await service.check_committee_membership(project_id, committee_id, email)
        
        return {
            "endpoint": f"GET /project-service/projects/{project_id}/committees/{committee_id}/committee_members",
            "params": {
                "email": email
            },
            "description": "Verify existing committee membership"
        }

class SlackTools:
    """Tools for Slack operations"""
    
    @staticmethod
    async def invite_to_workspace(email: str, channels: List[str], organization: str) -> Dict:
        """Send Slack workspace invitation"""
        return {
            "endpoint": "POST /api/users.admin.invite",
            "payload": {
                "email": email,
                "channels": channels,
                "real_name": "full_name",
                "team_id": f"{organization.lower()}_workspace"
            }
        }
    
    @staticmethod
    async def add_to_channel(user_id: str, channel: str) -> Dict:
        """Add user to specific Slack channel"""
        return {
            "endpoint": "POST /api/conversations.invite",
            "payload": {
                "channel": channel,
                "users": user_id
            }
        }
    
    @staticmethod
    async def send_direct_message(user_id: str, message: str) -> Dict:
        """Send a direct message to a user"""
        return {
            "endpoint": "POST /api/chat.postMessage",
            "payload": {
                "channel": user_id,
                "text": message
            }
        }

class EmailTools:
    """Tools for email operations"""
    
    @staticmethod
    async def send_welcome_email(contact: Dict, project_info: Dict) -> Dict:
        """Send personalized welcome email"""
        template_map = {
            "primary": "welcome_governing_board",
            "marketing": "welcome_marketing_committee",
            "technical": "welcome_technical_committee"
        }
        
        return {
            "to": contact['email'],
            "template": template_map.get(contact['contact_type'], "welcome_general"),
            "variables": {
                "first_name": contact['first_name'],
                "organization": contact['organization'],
                "project_name": project_info.get('name'),
                "role": contact['contact_type'],
                "committee_name": EmailTools.get_committee_name(contact['contact_type'])
            }
        }
    
    @staticmethod
    def get_committee_name(contact_type: str) -> str:
        """Get committee name based on contact type"""
        committee_map = {
            "primary": "Governing Board",
            "marketing": "Marketing Committee",
            "technical": "Technical Committee"
        }
        return committee_map.get(contact_type, "Project Committee")

class LandscapeTools:
    """Tools for Project Landscape operations"""
    
    @staticmethod
    async def update_member_logo(project: str, organization: str, logo_url: str) -> Dict:
        """Update organization logo on project landscape"""
        return {
            "action": "create_pr",
            "repository": f"{project}/landscape",
            "changes": {
                "file": f"hosted_logos/{organization.lower()}.svg",
                "content": logo_url,
                "message": f"Update {organization} logo"
            }
        }
    
    @staticmethod
    async def check_landscape_entry(project: str, organization: str) -> Dict:
        """Check if organization exists in landscape"""
        return {
            "query": f"landscape.yml contains '{organization}'",
            "project": project,
            "description": "Verify organization presence in project landscape"
        }

# Agent Definitions
class MemberContactFetcherAgent(Agent):
    """Agent responsible for fetching member contacts"""
    
    def __init__(self):
        super().__init__(
            name="MemberContactFetcher",
            model=OpenAIChat(id="gpt-4o-mini"),
            instructions="""You are responsible for fetching contacts from the Member Service.
            
            IMPORTANT: You handle TWO different types of requests:
            
            1. "Get member ID for organization X" - Use get_member_by_organization tool
               - This returns: {"status": "success", "member_id": "...", "member_info": {...}}
               
            2. "Fetch all contacts for organization X" - First get member_id, then use get_member_contacts tool
               - This returns: {"status": "success", "contacts": [...], "count": N}
            
            CRITICAL: 
            - When asked to "Get member ID", ONLY use get_member_by_organization
            - When asked to "Fetch all contacts", use BOTH tools in sequence
            - Return the EXACT JSON response from the tool
            - DO NOT interpret or modify the response
            """,
            tools=[
                Function.from_callable(MemberServiceTools.get_member_by_organization),
                Function.from_callable(MemberServiceTools.get_member_contacts),
                Function.from_callable(MemberServiceTools.get_contact_details)
            ]
        )

class ProjectCommitteeAgent(Agent):
    """Agent responsible for managing project committees"""
    
    def __init__(self):
        super().__init__(
            name="ProjectCommitteeManager",
            model=OpenAIChat(id="gpt-4o-mini"),
            instructions="""You manage project committee memberships.
            
            IMPORTANT: You handle different types of requests:
            
            1. "Get project details for slug X" - Use get_project_by_slug tool
               Returns: {"status": "success", "project_id": "...", "project_info": {...}}
            
            2. "Get all committees for project X" - Use get_project_committees tool with project_id
               Returns: {"status": "success", "committees": [...], "count": N}
               
            3. "Add contact to committee" - First check membership, then add if not already member
            
            CRITICAL:
            - Return the EXACT JSON response from tools
            - Do NOT interpret or summarize
            - When asked for committees, you MUST call get_project_committees with the project_id
            """,
            tools=[
                Function.from_callable(ProjectServiceTools.get_project_by_slug),
                Function.from_callable(ProjectServiceTools.get_project_committees),
                Function.from_callable(ProjectServiceTools.add_committee_member),
                Function.from_callable(ProjectServiceTools.check_committee_membership)
            ]
        )

class SlackOnboardingAgent(Agent):
    """Agent responsible for Slack workspace management"""
    
    def __init__(self):
        super().__init__(
            name="SlackOnboarder",
            model=OpenAIChat(id="gpt-4o-mini"),
            instructions="""You manage Slack workspace invitations and channel assignments.
            Your tasks:
            1. Send workspace invitations to new contacts
            2. Assign contacts to channels based on their committee assignment:
               - Governing Board: #board, #announcements, #strategic-planning
               - Marketing Committee: #marketing, #events, #content-strategy, #brand
               - Technical Committee: #tech-discussion, #architecture, #dev-updates
               - All: #general, #welcome
            3. Send personalized welcome DM with:
               - Committee-specific channel guide
               - Link to onboarding resources
               - Key contacts in their committee
            4. Handle invitation failures with smart retry logic
            5. Return Slack user ID once joined
            """,
            tools=[
                Function.from_callable(SlackTools.invite_to_workspace),
                Function.from_callable(SlackTools.add_to_channel),
                Function.from_callable(SlackTools.send_direct_message)
            ]
        )

class EmailCommunicationAgent(Agent):
    """Agent responsible for email communications"""
    
    def __init__(self):
        super().__init__(
            name="EmailCommunicator",
            model=OpenAIChat(id="gpt-4o-mini"),
            instructions="""You handle all email communications with contacts.
            
            IMPORTANT: The send_welcome_email tool expects EXACTLY 2 parameters:
            - contact: The contact dictionary with email, first_name, organization, contact_type
            - project_info: The project information dictionary
            
            DO NOT add any extra parameters like 'committee', 'committee_type', 'committee_assignment', etc.
            The tool will automatically determine the committee based on contact['contact_type'].
            
            Your tasks:
            1. Send personalized welcome emails based on contact_type:
               - primary → Governing Board template
               - marketing → Marketing Committee template
               - technical → Technical Committee template
            2. The tool handles all the template selection and personalization
            3. Just pass the contact and project_info exactly as provided
            """,
            tools=[
                Function.from_callable(EmailTools.send_welcome_email)
            ]
        )

class LandscapeUpdateAgent(Agent):
    """Agent responsible for updating project landscape"""
    
    def __init__(self):
        super().__init__(
            name="LandscapeUpdater",
            model=OpenAIChat(id="gpt-4o-mini"),
            instructions="""You manage updates to the project landscape.
            Your tasks:
            1. Check if organization entry exists in project landscape
            2. Update or add organization logo
            3. Update member data including:
               - Membership level/tier
               - Key contacts by committee
               - Join date
            4. Create pull request with changes
            5. Monitor PR status
            """,
            tools=[
                Function.from_callable(LandscapeTools.update_member_logo),
                Function.from_callable(LandscapeTools.check_landscape_entry)
            ]
        )

class OrchestratorAgent(Agent):
    """Master agent that coordinates all other agents"""
    
    def __init__(self, project_context: ProjectContext, mcp_server_type: str = "sqlite"):
        super().__init__(
            name="Orchestrator",
            model=OpenAIChat(id="gpt-4o-mini"),
            instructions=f"""You are the master coordinator for onboarding contacts from {project_context.organization_name} 
            to the {project_context.project_slug} project.
            
            Your responsibilities:
            1. Coordinate work between all specialized agents
            2. Maintain workflow state in the database
            3. Handle error recovery with intelligent retry strategies
            4. Ensure all contacts are properly onboarded to their committees
            5. Generate comprehensive status reports
            6. Make autonomous decisions on workflow progression
            
            Workflow order:
            1. Fetch member ID and contacts from Member Service
            2. Get project details and identify committees
            3. For each contact batch (process in batches of 10):
               - Add to appropriate committee based on contact_type
               - Update database with progress
               - Parallel process:
                 * Send Slack invitation with role-specific channels
                 * Send committee-specific welcome email
               - Track all status in database
            4. After all contacts processed:
               - Update project landscape with organization data
               - Generate completion report from database
            
            Decision rules:
            - If contact missing required data: Log and skip
            - If committee doesn't exist: Alert and use default committee
            - If Slack invitation fails 3 times: Mark as failed
            - If >20% failure rate: Pause, analyze, and alert
            """,
        )
        
        self.project_context = project_context
        self.mcp_server_type = mcp_server_type
        self.session_id = None
        self.workflow_logger = workflow_logger  # Add enhanced logger
        
        # Initialize sub-agents
        self.contact_fetcher = MemberContactFetcherAgent()
        self.committee_manager = ProjectCommitteeAgent()
        self.slack_onboarder = SlackOnboardingAgent()
        self.email_communicator = EmailCommunicationAgent()
        self.landscape_updater = LandscapeUpdateAgent()
        self.db_manager = DatabaseAgent(mcp_server_type)
    
    async def process_contacts(self):
        """Main workflow orchestration method"""
        try:
            # Start workflow tracking
            self.workflow_logger.workflow_start(
                self.project_context.organization_name,
                self.project_context.project_slug
            )
            
            # Step 1: Get member ID and project details
            self.workflow_logger.stage_start("INITIALIZATION PHASE", "🔍")
            
            member_data = await self.get_member_and_project_info()
            if not member_data:
                return {"status": "error", "message": "Failed to find member or project"}
            
            # Initialize database via MCP
            await self.delegate_to_agent(
                self.db_manager,
                f"Initialize database schema for {self.mcp_server_type}"
            )
            
            # Create onboarding session in database via MCP
            session_result = await self.delegate_to_agent(
                self.db_manager,
                "Create new onboarding session",
                {
                    "org_name": self.project_context.organization_name,
                    "project_slug": self.project_context.project_slug,
                    "member_id": self.project_context.member_id,
                    "project_id": self.project_context.project_id
                }
            )
            self.session_id = session_result.get('session_id')
            
            # Step 2: Fetch contacts
            self.workflow_logger.stage_start("FETCHING CONTACTS", "👥")
            self.workflow_logger.info("Retrieving contact list...", "  📋")
            
            contacts_result = await self.delegate_to_agent(
                self.contact_fetcher,
                f"Fetch all contacts for organization '{self.project_context.organization_name}'",
                {"member_id": self.project_context.member_id}
            )
            
            logger.debug(f"Contact fetch result: {contacts_result}")
            contacts = contacts_result.get('contacts', [])
            self.workflow_logger.contact_info(contacts)
            
            # Add contacts to database via MCP
            contact_db_mapping = {}
            for contact in contacts:
                add_result = await self.delegate_to_agent(
                    self.db_manager,
                    "Add contact to onboarding session",
                    {
                        "session_id": self.session_id,
                        "contact": contact
                    }
                )
                contact_db_mapping[contact['contact_id']] = add_result.get('contact_onboarding_id')
            
            # Step 3: Setup committees
            self.workflow_logger.stage_start("COMMITTEE ASSIGNMENTS", "🏛️")
            committee_setup = await self.setup_committees()
            if not committee_setup.get('success'):
                self.workflow_logger.warning("Committee setup incomplete, proceeding with available committees")
            
            # Step 4: Process contacts in batches
            batch_size = 3  # Reduced to avoid rate limits
            all_results = []
            
            for i in range(0, len(contacts), batch_size):
                batch = contacts[i:i + batch_size]
                self.workflow_logger.batch_progress(
                    i//batch_size + 1, 
                    (len(contacts)-1)//batch_size + 1
                )
                
                batch_results = await self.process_contact_batch(batch, contact_db_mapping)
                all_results.extend(batch_results)
                
                # Update session stats via MCP
                await self.delegate_to_agent(
                    self.db_manager,
                    "Update session statistics",
                    {"session_id": self.session_id}
                )
                
                # Check failure rate
                failure_rate = self.calculate_failure_rate(all_results)
                if failure_rate > 0.2:
                    self.workflow_logger.warning(f"High failure rate detected: {failure_rate:.2%}")
                    await self.handle_high_failure_rate(all_results)
            
            # Step 5: Update project landscape
            self.workflow_logger.stage_start("LANDSCAPE UPDATE", "🌍")
            self.workflow_logger.landscape_update(
                self.project_context.organization_name,
                self.project_context.project_slug,
                "checking"
            )
            landscape_result = await self.delegate_to_agent(
                self.landscape_updater,
                f"Update {self.project_context.organization_name} entry in {self.project_context.project_slug} landscape"
            )
            if landscape_result.get('status') == 'success':
                self.workflow_logger.landscape_update(
                    self.project_context.organization_name,
                    self.project_context.project_slug,
                    "success"
                )
            
            # Step 6: Generate final report from database via MCP
            report_result = await self.delegate_to_agent(
                self.db_manager,
                "Generate session report",
                {"session_id": self.session_id}
            )
            report = report_result.get('report', {})
            report['landscape_update'] = landscape_result
            
            # Final session update via MCP
            await self.delegate_to_agent(
                self.db_manager,
                "Update session statistics",
                {"session_id": self.session_id}
            )
            
            # Complete workflow
            stats = {
                'total_contacts': report.get('session', {}).get('total_contacts', 0),
                'successful_contacts': report.get('session', {}).get('successful_contacts', 0),
                'failed_contacts': report.get('session', {}).get('failed_contacts', 0),
                'session_id': self.session_id,
                'landscape_pr': landscape_result.get('pr_url')
            }
            self.workflow_logger.workflow_complete(stats)
            
            return report
            
        except Exception as e:
            logger.error(f"Orchestration error: {str(e)}")
            self.workflow_logger.error(f"Orchestration error: {str(e)}")
            return {"status": "error", "message": str(e), "context": self.project_context.__dict__}
    
    async def get_member_and_project_info(self) -> Dict:
        """Get member ID and project details"""
        # Get member ID
        member_result = await self.delegate_to_agent(
            self.contact_fetcher,
            f"Get member ID for organization '{self.project_context.organization_name}'",
            {"organization_name": self.project_context.organization_name}
        )
        
        logger.debug(f"Member result: {member_result}")
        
        if not member_result.get('member_id'):
            self.workflow_logger.error(f"Member not found: {self.project_context.organization_name}")
            return None
        
        self.project_context.member_id = member_result['member_id']
        member_info = member_result.get('member_info', {})
        self.workflow_logger.success(f"Found: {member_info.get('name')} (ID: {member_result.get('member_id')})")
        
        # Get project details
        self.workflow_logger.info(f"Finding project: {self.project_context.project_slug}", "  🎯")
        project_result = await self.delegate_to_agent(
            self.committee_manager,
            f"Get project details for slug '{self.project_context.project_slug}'",
            {"project_slug": self.project_context.project_slug}
        )
        
        logger.debug(f"Project result: {project_result}")
        
        if not project_result.get('project_id'):
            self.workflow_logger.error(f"Project not found: {self.project_context.project_slug}")
            return None
        
        self.project_context.project_id = project_result['project_id']
        project_info = project_result.get('project_info', {})
        self.workflow_logger.success(f"Found: {project_info.get('name')} - {project_info.get('description')}")
        
        return {
            "member_id": self.project_context.member_id,
            "project_id": self.project_context.project_id,
            "member_info": member_result.get('member_info', {}),
            "project_info": project_result.get('project_info', {})
        }
    
    async def setup_committees(self) -> Dict:
        """Setup committee mappings"""
        logger.info(f"Getting committees for project ID: {self.project_context.project_id}")
        committees_result = await self.delegate_to_agent(
            self.committee_manager,
            f"Get all committees for project {self.project_context.project_id}",
            {"project_id": self.project_context.project_id}
        )
        logger.info(f"Committee result: {committees_result}")
        
        committee_map = {}
        committees = committees_result.get('committees', [])
        logger.info(f"Found {len(committees)} committees: {committees}")
        
        for committee in committees:
            name_lower = committee.get('name', '').lower()
            if 'governing' in name_lower or 'board' in name_lower:
                committee_map['primary'] = committee['id']
            elif 'marketing' in name_lower:
                committee_map['marketing'] = committee['id']
            elif 'technical' in name_lower or 'tech' in name_lower:
                committee_map['technical'] = committee['id']
        
        self.project_context.committees = committee_map
        logger.info(f"Committee mapping: {committee_map}")
        
        # Check if all committees are found
        missing = []
        for contact_type in ['primary', 'marketing', 'technical']:
            if contact_type not in committee_map:
                missing.append(contact_type)
        
        return {
            "success": len(missing) == 0,
            "committee_map": committee_map,
            "missing_committees": missing
        }
    
    async def process_contact_batch(self, batch: List[Dict], contact_db_mapping: Dict) -> List[Dict]:
        """Process a batch of contacts with rate limiting"""
        results = []
        for contact in batch:
            db_id = contact_db_mapping[contact['contact_id']]
            # Process contacts sequentially to avoid rate limits
            result = await self.process_single_contact(contact, db_id)
            results.append(result)
            # Add a small delay between contacts to avoid rate limits
            await asyncio.sleep(0.5)
        
        return results
    
    async def process_single_contact(self, contact: Dict, db_id: int) -> Dict:
        """Process a single contact through all systems"""
        contact_id = contact.get('contact_id', contact.get('id'))
        results = {
            "contact": contact,
            "db_id": db_id,
            "committee": None,
            "slack": None,
            "email": None,
            "status": "processing",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Add to committee based on contact_type
            committee_id = self.project_context.committees.get(contact['contact_type'])
            logger.info(f"Processing {contact['first_name']} {contact['last_name']} ({contact['contact_type']}) - Committee ID: {committee_id}")
            if committee_id:
                results['committee'] = await self.add_to_committee(contact, committee_id, db_id)
            else:
                logger.warning(f"No committee found for contact type: {contact['contact_type']}")
                results['committee'] = {"status": "skipped", "reason": "committee_not_found"}
                await self.delegate_to_agent(
                    self.db_manager,
                    "Update contact status",
                    {
                        "contact_id": db_id,
                        "status_type": "committee",
                        "status": "skipped",
                        "additional_data": {"reason": "committee_not_found"}
                    }
                )
            
            # Parallel processing for Slack and Email
            slack_task = self.process_slack_onboarding(contact, db_id)
            email_task = self.process_email_onboarding(contact, db_id)
            
            results['slack'], results['email'] = await asyncio.gather(
                slack_task, email_task,
                return_exceptions=True
            )
            
            # Determine final status
            if self.is_onboarding_successful(results):
                results['status'] = 'completed'
            else:
                results['status'] = 'partial_failure'
                
        except Exception as e:
            logger.error(f"Error processing contact {contact_id}: {str(e)}")
            self.workflow_logger.error(f"Error processing contact {contact_id}: {str(e)}")
            self.workflow_logger.contact_progress(contact, "Failed", "error")
            results['status'] = 'error'
            results['error'] = str(e)
            await self.delegate_to_agent(
                self.db_manager,
                "Update contact status",
                {
                    "contact_id": db_id,
                    "status_type": "overall",
                    "status": "failed",
                    "additional_data": {"error": str(e)}
                }
            )
        
        return results
    
    async def add_to_committee(self, contact: Dict, committee_id: str, db_id: int) -> Dict:
        """Add contact to committee with retry logic"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Check if already a member
                check_result = await self.delegate_to_agent(
                    self.committee_manager,
                    f"Check if {contact['email']} is already in committee {committee_id}",
                    {
                        "project_id": self.project_context.project_id,
                        "committee_id": committee_id,
                        "email": contact['email']
                    }
                )
                
                if check_result.get('is_member'):
                    await self.delegate_to_agent(
                        self.db_manager,
                        "Update contact status",
                        {
                            "contact_id": db_id,
                            "status_type": "committee",
                            "status": "already_member",
                            "additional_data": {"committee_id": committee_id}
                        }
                    )
                    return {"status": "already_member", "committee_id": committee_id}
                
                # Add to committee
                result = await self.delegate_to_agent(
                    self.committee_manager,
                    f"Add {contact['email']} to committee {committee_id}",
                    {
                        "project_id": self.project_context.project_id,
                        "committee_id": committee_id,
                        "member_data": {
                            "name": f"{contact['first_name']} {contact['last_name']}",
                            "email": contact['email'],
                            "organization": self.project_context.organization_name,
                            "title": contact['title'],
                            "role": contact['contact_type'],
                            "join_date": datetime.now().isoformat()
                        }
                    }
                )
                
                if result.get('status') == 'success':
                    await self.delegate_to_agent(
                        self.db_manager,
                        "Update contact status",
                        {
                            "contact_id": db_id,
                            "status_type": "committee",
                            "status": "success",
                            "additional_data": {"committee_id": committee_id}
                        }
                    )
                    return result
                
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    await self.delegate_to_agent(
                        self.db_manager,
                        "Update contact status",
                        {
                            "contact_id": db_id,
                            "status_type": "committee",
                            "status": "failed",
                            "additional_data": {"error": str(e)}
                        }
                    )
                    return {"status": "failed", "error": str(e)}
        
        await self.delegate_to_agent(
            self.db_manager,
            "Update contact status",
            {
                "contact_id": db_id,
                "status_type": "committee",
                "status": "failed",
                "additional_data": {"error": "retries_exhausted"}
            }
        )
        return {"status": "failed", "retries_exhausted": True}
    
    async def process_slack_onboarding(self, contact: Dict, db_id: int) -> Dict:
        """Handle Slack onboarding with appropriate channels"""
        try:
            # Show Slack stage if not already shown
            if not hasattr(self, '_slack_stage_started'):
                self.workflow_logger.stage_start("SLACK INVITATIONS", "💬")
                self._slack_stage_started = True
            
            self.workflow_logger.slack_invitation(contact['email'])
            
            # Get channels based on committee
            channels = self.get_slack_channels(contact['contact_type'])
            
            result = await self.delegate_to_agent(
                self.slack_onboarder,
                f"Complete Slack onboarding for {contact['email']} with committee-specific channels",
                {
                    "contact": contact,
                    "organization": self.project_context.organization_name,
                    "channels": channels,
                    "committee": self.get_committee_name(contact['contact_type'])
                }
            )
            
            if result.get('status') == 'success':
                slack_user_id = result.get('slack_user_id')
                await self.delegate_to_agent(
                    self.db_manager,
                    "Update contact status",
                    {
                        "contact_id": db_id,
                        "status_type": "slack",
                        "status": "success",
                        "additional_data": {"slack_user_id": slack_user_id}
                    }
                )
            else:
                await self.delegate_to_agent(
                    self.db_manager,
                    "Update contact status",
                    {
                        "contact_id": db_id,
                        "status_type": "slack",
                        "status": "failed",
                        "additional_data": {"error": result.get('error', 'Unknown error')}
                    }
                )
            
            return result
            
        except Exception as e:
            await self.delegate_to_agent(
                self.db_manager,
                "Update contact status",
                {
                    "contact_id": db_id,
                    "status_type": "slack",
                    "status": "failed",
                    "additional_data": {"error": str(e)}
                }
            )
            return {"status": "failed", "error": str(e)}
    
    async def process_email_onboarding(self, contact: Dict, db_id: int) -> Dict:
        """Handle email onboarding with committee-specific content"""
        try:
            # Show email stage if not already shown
            if not hasattr(self, '_email_stage_started'):
                self.workflow_logger.stage_start("WELCOME EMAILS", "📧")
                self._email_stage_started = True
            
            self.workflow_logger.email_sent(contact['email'])
            
            # Get the actual project name from the context
            project_info = {
                "name": getattr(self.project_context, 'project_name', self.project_context.project_slug),
                "id": self.project_context.project_id,
                "slug": self.project_context.project_slug
            }
            
            result = await self.delegate_to_agent(
                self.email_communicator,
                f"Send committee-specific welcome email to {contact['email']}",
                {
                    "contact": contact,
                    "project_info": project_info
                }
            )
            
            if result.get('status') == 'success':
                await self.delegate_to_agent(
                    self.db_manager,
                    "Update contact status",
                    {
                        "contact_id": db_id,
                        "status_type": "email",
                        "status": "success"
                    }
                )
            else:
                await self.delegate_to_agent(
                    self.db_manager,
                    "Update contact status",
                    {
                        "contact_id": db_id,
                        "status_type": "email",
                        "status": "failed",
                        "additional_data": {"error": result.get('error', 'Unknown error')}
                    }
                )
            
            return result
            
        except Exception as e:
            await self.delegate_to_agent(
                self.db_manager,
                "Update contact status",
                {
                    "contact_id": db_id,
                    "status_type": "email",
                    "status": "failed",
                    "additional_data": {"error": str(e)}
                }
            )
            return {"status": "failed", "error": str(e)}
    
    def get_committee_name(self, contact_type: str) -> str:
        """Get committee name based on contact type"""
        committee_names = {
            "primary": "Governing Board",
            "marketing": "Marketing Committee",
            "technical": "Technical Committee"
        }
        return committee_names.get(contact_type, "Project Committee")
    
    def get_slack_channels(self, contact_type: str) -> List[str]:
        """Get Slack channels based on contact type"""
        base_channels = ["#general", "#welcome", f"#{self.project_context.project_slug}"]
        
        type_channels = {
            "primary": ["#board", "#announcements", "#strategic-planning"],
            "marketing": ["#marketing", "#events", "#content-strategy", "#brand"],
            "technical": ["#tech-discussion", "#architecture", "#dev-updates"]
        }
        
        return base_channels + type_channels.get(contact_type, [])
    
    def is_onboarding_successful(self, results: Dict) -> bool:
        """Determine if onboarding was successful"""
        committee_success = results.get('committee', {}).get('status') in ['success', 'already_member']
        slack_success = results.get('slack', {}).get('status') == 'success'
        email_success = results.get('email', {}).get('status') == 'success'
        
        # At least committee and one communication channel should succeed
        return committee_success and (slack_success or email_success)
    
    def calculate_failure_rate(self, results: List[Dict]) -> float:
        """Calculate the failure rate of processed contacts"""
        if not results:
            return 0.0
        
        failures = sum(1 for r in results if r.get('status') in ['error', 'partial_failure'])
        return failures / len(results)
    
    async def handle_high_failure_rate(self, results: List[Dict]):
        """Handle high failure rate scenario"""
        analysis = self.analyze_failures(results)
        logger.critical(f"High failure rate alert for {self.project_context.organization_name}: {analysis}")
        
        # In production, this would trigger alerts
        # Could implement automatic recovery strategies
    
    def analyze_failures(self, results: List[Dict]) -> Dict:
        """Analyze failure patterns"""
        failures = [r for r in results if r.get('status') in ['error', 'partial_failure']]
        
        analysis = {
            "organization": self.project_context.organization_name,
            "project": self.project_context.project_slug,
            "total_failures": len(failures),
            "failure_rate": len(failures) / len(results) if results else 0,
            "committee_failures": sum(1 for f in failures if f.get('committee', {}).get('status') == 'failed'),
            "slack_failures": sum(1 for f in failures if f.get('slack', {}).get('status') == 'failed'),
            "email_failures": sum(1 for f in failures if f.get('email', {}).get('status') == 'failed'),
            "timestamp": datetime.now().isoformat()
        }
        
        return analysis
    
    async def delegate_to_agent(self, agent: Agent, task: str, context: Dict = None) -> Any:
        """Delegate a task to a specific agent"""
        # Include context in the task message for better agent understanding
        if context:
            task_with_context = f"{task}\n\nContext: {json.dumps(context, indent=2)}"
        else:
            task_with_context = task
            
        message = Message(
            role="user",
            content=task_with_context,
            context=context or {}
        )
        
        response = await agent.arun(message)
        # Extract the actual content from the response
        if hasattr(response, 'content'):
            # Try to parse JSON response if it's a string
            content = response.content
            if isinstance(content, str):
                # Check if content is wrapped in markdown code blocks
                if content.strip().startswith('```'):
                    # Extract content between ``` markers
                    lines = content.strip().split('\n')
                    json_lines = []
                    in_json = False
                    for line in lines:
                        if line.startswith('```json'):
                            in_json = True
                            continue
                        elif line.startswith('```'):
                            in_json = False
                            continue
                        elif in_json:
                            json_lines.append(line)
                    content = '\n'.join(json_lines)
                
                try:
                    # First try to parse as JSON
                    parsed = json.loads(content)
                    # If it has a 'response' field that's a string, parse that too
                    if isinstance(parsed, dict) and 'response' in parsed and isinstance(parsed['response'], str):
                        response_str = parsed['response']
                        # Check if the response contains a JSON object at the beginning
                        if response_str.strip().startswith('{'):
                            # Find the end of the JSON object
                            brace_count = 0
                            json_end = 0
                            for i, char in enumerate(response_str):
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_end = i + 1
                                        break
                            if json_end > 0:
                                json_part = response_str[:json_end]
                                try:
                                    import ast
                                    return ast.literal_eval(json_part)
                                except:
                                    try:
                                        return json.loads(json_part.replace("'", '"'))
                                    except:
                                        pass
                    return parsed
                except json.JSONDecodeError:
                    # Try to parse as Python dict string
                    try:
                        import ast
                        # First check if the content starts with a dict
                        if content.strip().startswith('{'):
                            # Find the end of the dict
                            brace_count = 0
                            dict_end = 0
                            for i, char in enumerate(content):
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        dict_end = i + 1
                                        break
                            if dict_end > 0:
                                dict_part = content[:dict_end]
                                return ast.literal_eval(dict_part)
                        return ast.literal_eval(content)
                    except:
                        return {"status": "success", "response": content}
            return content
        return response

# Main execution function
async def run_contact_onboarding(organization_name: str, project_slug: str, 
                                mcp_server_type: str = "sqlite"):
    """Main entry point for the autonomous agent system"""
    # Create project context
    project_context = ProjectContext(
        organization_name=organization_name,
        project_slug=project_slug
    )
    
    # Create orchestrator with MCP server type
    orchestrator = OrchestratorAgent(project_context, mcp_server_type)
    
    # Start the autonomous process
    result = await orchestrator.process_contacts()
    
    return result

# Configuration for production deployment
class AgentSystemConfig:
    """Configuration for the agent system"""
    
    # MCP Database configuration
    MCP_SERVER_TYPE = "sqlite"  # or "postgres"
    # MCP servers handle connection details internally
    
    # API Endpoints
    MEMBER_SERVICE_URL = "https://api.lfx.linuxfoundation.org/v1/member-service"
    PROJECT_SERVICE_URL = "https://api.lfx.linuxfoundation.org/v1/project-service"
    SLACK_API_URL = "https://slack.com/api"
    
    # Authentication (would be loaded from environment/secrets)
    LFX_API_KEY = "your-lfx-api-key"
    SLACK_BOT_TOKEN = "your-slack-bot-token"
    GITHUB_TOKEN = "your-github-token"  # For landscape updates
    
    # Email configuration
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_FROM = "onboarding@linuxfoundation.org"
    
    # Agent behavior configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    BATCH_SIZE = 10  # contacts per batch
    
    # SLA configuration
    MAX_PROCESSING_TIME = 3600  # 1 hour in seconds
    MAX_FAILURE_RATE = 0.2  # 20%

# Helper function to run with proper error handling
async def main(organization_name: str, project_slug: str):
    """Main function with error handling and monitoring"""
    try:
        # Validate inputs
        if not organization_name or not project_slug:
            raise ValueError("Both organization_name and project_slug are required")
        
        # Initialize system
        logger.debug(f"Initializing onboarding system for {organization_name} → {project_slug}")
        
        # Run the system with MCP
        result = await run_contact_onboarding(
            organization_name, 
            project_slug,
            AgentSystemConfig.MCP_SERVER_TYPE
        )
        
        # Log completion is handled by self.workflow_logger in process_contacts
        if result.get('status') == 'error':
            logger.error(f"Onboarding failed: {result.get('message')}")
        
        return result
        
    except Exception as e:
        logger.error(f"System error: {str(e)}")
        raise

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python main.py <organization_name> <project_slug>")
        print("Example: python main.py 'Acme Corp' 'kubernetes'")
        sys.exit(1)
    
    org_name = sys.argv[1]
    proj_slug = sys.argv[2]
    
    # Run the autonomous system
    asyncio.run(main(org_name, proj_slug))