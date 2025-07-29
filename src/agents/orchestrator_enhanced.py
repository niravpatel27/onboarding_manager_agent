"""Enhanced Orchestrator Agent with natural language progress tracking"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from agno.agent import Agent, Message

from ..models.project import ProjectContext
from ..models.events import ContactResult, BatchResult, OnboardingStatus
from ..tools.mcp.database import OnboardingDatabase
from ..utils.progress_logger import progress_logger

# Import specialized agents
from .specialized.member_contact import MemberContactFetcherAgent
from .specialized.project_committee import ProjectCommitteeAgent
from .specialized.slack_onboarding import SlackOnboardingAgent
from .specialized.email_communication import EmailCommunicationAgent
from .specialized.landscape_update import LandscapeUpdateAgent
from .specialized.database import DatabaseAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(Agent):
    """Master agent that coordinates all other agents with enhanced logging"""
    
    def __init__(self, project_context: ProjectContext, db: OnboardingDatabase):
        super().__init__(
            name="Orchestrator",
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
               - Update project landscape
               - Generate completion report
            
            Decision rules:
            - If contact missing required data: Log and skip
            - If committee doesn't exist: Alert and use default committee
            - If Slack invitation fails 3 times: Mark as failed
            - If >20% failure rate: Pause, analyze, and alert
            """
        )
        
        self.project_context = project_context
        self.db = db
        self.session_id = None
        
        # Initialize sub-agents
        self.contact_fetcher = MemberContactFetcherAgent()
        self.committee_manager = ProjectCommitteeAgent()
        self.slack_onboarder = SlackOnboardingAgent()
        self.email_communicator = EmailCommunicationAgent()
        self.landscape_updater = LandscapeUpdateAgent()
        self.db_manager = DatabaseAgent(db)
        
        logger.debug(f"Initialized Orchestrator for {project_context.organization_name} → {project_context.project_slug}")
    
    async def run(self, task: str, context: Dict = None) -> Any:
        """Main entry point for orchestrator"""
        if "start" in task.lower() or "begin" in task.lower():
            return await self.process_contacts()
        return {"status": "error", "message": "Unknown orchestrator task"}
    
    async def process_contacts(self):
        """Main workflow orchestration method with enhanced logging"""
        try:
            # Start workflow with visual header
            progress_logger.start_workflow(
                self.project_context.organization_name,
                self.project_context.project_slug
            )
            
            # Step 1: Initialize database
            progress_logger.start_stage(
                "Database Setup",
                "Preparing database for onboarding session"
            )
            progress_logger.log_task("Initializing database schema", "DatabaseAgent")
            await self.delegate_to_agent(self.db_manager, "Initialize database schema")
            progress_logger.log_result("Database ready")
            progress_logger.complete_stage()
            
            # Step 2: Get member and project info
            progress_logger.start_stage(
                "Discovery Phase",
                "Finding organization and project details"
            )
            member_data = await self.get_member_and_project_info()
            if not member_data:
                progress_logger.log_error("Failed to find member or project")
                return {"status": "error", "message": "Failed to find member or project"}
            progress_logger.complete_stage()
            
            # Step 3: Create onboarding session
            progress_logger.start_stage(
                "Session Creation",
                "Setting up tracking for this onboarding"
            )
            progress_logger.log_task("Creating onboarding session", "DatabaseAgent")
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
            progress_logger.log_result(f"Session created", {"Session ID": self.session_id})
            progress_logger.complete_stage()
            
            # Step 4: Fetch contacts
            progress_logger.start_stage(
                "Contact Discovery",
                "Retrieving member organization contacts"
            )
            progress_logger.log_task("Fetching member contacts", "MemberContactFetcher")
            contacts_result = await self.delegate_to_agent(
                self.contact_fetcher,
                f"Fetch all contacts for organization '{self.project_context.organization_name}'",
                {"member_id": self.project_context.member_id}
            )
            
            contacts = contacts_result.get('contacts', [])
            progress_logger.log_result(
                f"Found {len(contacts)} contacts",
                {
                    "Primary": sum(1 for c in contacts if c.get('contact_type') == 'primary'),
                    "Marketing": sum(1 for c in contacts if c.get('contact_type') == 'marketing'),
                    "Technical": sum(1 for c in contacts if c.get('contact_type') == 'technical')
                }
            )
            
            # Add contacts to database
            contact_db_mapping = {}
            for contact in contacts:
                add_result = await self.delegate_to_agent(
                    self.db_manager,
                    "Add contact to onboarding session",
                    {"session_id": self.session_id, "contact": contact}
                )
                contact_db_mapping[contact['contact_id']] = add_result.get('contact_onboarding_id')
            progress_logger.complete_stage()
            
            # Step 5: Setup committees
            progress_logger.start_stage(
                "Committee Setup",
                "Identifying project committees for assignments"
            )
            committee_setup = await self.setup_committees()
            if not committee_setup.get('success'):
                progress_logger.log_error(
                    "Committee setup incomplete",
                    "Proceeding with available committees"
                )
            progress_logger.complete_stage()
            
            # Step 6: Process contacts in batches
            batch_size = 10
            all_results = []
            total_batches = (len(contacts) - 1) // batch_size + 1
            
            progress_logger.start_stage(
                "Contact Processing",
                f"Onboarding {len(contacts)} contacts in {total_batches} batch(es)"
            )
            
            for i in range(0, len(contacts), batch_size):
                batch = contacts[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                batch_results = await self.process_contact_batch(
                    batch, 
                    contact_db_mapping,
                    batch_num,
                    total_batches
                )
                all_results.extend(batch_results)
                
                # Update session stats
                await self.delegate_to_agent(
                    self.db_manager,
                    "Update session statistics",
                    {"session_id": self.session_id}
                )
                
                # Check failure rate
                failure_rate = self.calculate_failure_rate(all_results)
                if failure_rate > 0.2:
                    progress_logger.log_error(
                        f"High failure rate: {failure_rate:.0%}",
                        "Analyzing issues and continuing with caution"
                    )
                    await self.handle_high_failure_rate(all_results)
            
            progress_logger.complete_stage()
            
            # Step 7: Update landscape
            progress_logger.start_stage(
                "Landscape Update",
                "Adding organization to project landscape"
            )
            progress_logger.log_task("Updating project landscape", "LandscapeUpdater")
            landscape_result = await self.delegate_to_agent(
                self.landscape_updater,
                f"Update {self.project_context.organization_name} entry in {self.project_context.project_slug} landscape"
            )
            
            if landscape_result.get('status') == 'success':
                pr_url = landscape_result.get('pr_created', 'N/A')
                progress_logger.log_result(
                    "Landscape updated",
                    {"Pull Request": pr_url}
                )
            progress_logger.complete_stage()
            
            # Step 8: Generate final report
            progress_logger.start_stage(
                "Final Report",
                "Generating completion summary"
            )
            report_result = await self.delegate_to_agent(
                self.db_manager,
                "Generate session report",
                {"session_id": self.session_id}
            )
            
            # Update final stats
            await self.delegate_to_agent(
                self.db_manager,
                "Update session statistics",
                {"session_id": self.session_id, "completed": True}
            )
            
            progress_logger.complete_stage()
            
            # Show completion summary
            session = report_result.get('session', {})
            stats = {
                'total_contacts': session.get('total_contacts', 0),
                'successful_contacts': session.get('successful_contacts', 0),
                'failed_contacts': session.get('failed_contacts', 0),
                'success_rate': (session.get('successful_contacts', 0) / 
                               max(session.get('total_contacts', 1), 1)) * 100,
                'landscape_pr': landscape_result.get('pr_created')
            }
            
            progress_logger.complete_workflow(stats)
            
            return report_result
            
        except Exception as e:
            progress_logger.log_error(f"System error: {str(e)}")
            logger.error(f"Orchestrator error: {str(e)}", exc_info=True)
            raise
    
    async def get_member_and_project_info(self):
        """Fetch member and project information with natural logging"""
        # Get member info
        progress_logger.log_task(
            f"Looking up '{self.project_context.organization_name}'",
            "MemberContactFetcher"
        )
        member_result = await self.delegate_to_agent(
            self.contact_fetcher,
            f"Get member ID for organization '{self.project_context.organization_name}'",
            {"organization_name": self.project_context.organization_name}
        )
        
        if member_result.get('status') == 'success':
            self.project_context.member_id = member_result['member_id']
            progress_logger.log_result(
                "Organization found",
                {"Member ID": member_result['member_id']}
            )
        else:
            return None
            
        # Get project info
        progress_logger.log_task(
            f"Looking up project '{self.project_context.project_slug}'",
            "ProjectCommitteeManager"
        )
        project_result = await self.delegate_to_agent(
            self.committee_manager,
            f"Get project details for slug '{self.project_context.project_slug}'",
            {"project_slug": self.project_context.project_slug}
        )
        
        if project_result.get('status') == 'success':
            self.project_context.project_id = project_result['project_id']
            self.project_context.project_info = project_result['project_info']
            progress_logger.log_result(
                "Project found",
                {
                    "Project ID": project_result['project_id'],
                    "Name": project_result['project_info'].get('name')
                }
            )
        else:
            return None
            
        return {"member": member_result, "project": project_result}
    
    async def setup_committees(self):
        """Setup committees with progress tracking"""
        progress_logger.log_task("Fetching project committees", "ProjectCommitteeManager")
        
        committees_result = await self.delegate_to_agent(
            self.committee_manager,
            f"Get all committees for project {self.project_context.project_id}",
            {"project_id": self.project_context.project_id}
        )
        
        committees = committees_result.get('committees', [])
        self.project_context.committees = {c['type']: c for c in committees}
        
        progress_logger.log_result(
            f"Found {len(committees)} committees",
            {c['name']: c['type'] for c in committees}
        )
        
        return {"success": len(committees) >= 2}
    
    async def process_contact_batch(self, batch: List[Dict], contact_db_mapping: Dict,
                                  batch_num: int, total_batches: int):
        """Process a batch of contacts with enhanced progress tracking"""
        results = []
        
        for contact in batch:
            progress_logger.log_contact_processing(contact, batch_num, total_batches)
            
            result = ContactResult(
                contact_id=contact['contact_id'],
                email=contact['email'],
                db_id=contact_db_mapping.get(contact['contact_id'], 0)
            )
            
            # Committee assignment
            progress_logger.log_task("Assigning to committee", status="working")
            committee_result = await self.assign_to_committee(contact)
            if committee_result.get('status') == 'success':
                result.committee = committee_result
                result.add_event('committee', OnboardingStatus.SUCCESS, committee_result)
                progress_logger.log_result("Added to committee", 
                                         {"Committee": committee_result.get('committee_name')})
            else:
                result.add_event('committee', OnboardingStatus.FAILED, 
                               error=committee_result.get('message'))
                progress_logger.log_error("Committee assignment failed", 
                                        committee_result.get('message'))
            
            # Update database
            db_id = contact_db_mapping.get(contact['contact_id'])
            if db_id:
                committee_status = 'success' if result.committee else 'failed'
                await self.delegate_to_agent(
                    self.db_manager,
                    "Update contact status",
                    {
                        "contact_onboarding_id": db_id,
                        "committee_status": committee_status,
                        "committee_id": result.committee.get('committee_id') if result.committee else None
                    }
                )
            
            # Slack onboarding (in parallel with email)
            progress_logger.log_task("Sending Slack invitation", status="working")
            committee_id = result.committee.get('committee_id') if result.committee else None
            slack_task = self.onboard_to_slack(contact, committee_id)
            
            # Email welcome (in parallel with Slack)
            progress_logger.log_task("Sending welcome email", status="working")
            email_task = self.send_welcome_email(contact, committee_id)
            
            # Wait for both to complete
            slack_result, email_result = await asyncio.gather(slack_task, email_task)
            
            # Process Slack result
            if slack_result.get('status') == 'success':
                result.slack = slack_result
                result.add_event('slack', OnboardingStatus.SUCCESS, slack_result)
                progress_logger.log_result("Slack invitation sent",
                                         {"Channels": len(slack_result.get('channels_joined', []))})
            else:
                result.add_event('slack', OnboardingStatus.FAILED)
                progress_logger.log_error("Slack invitation failed")
            
            # Process email result
            if email_result.get('status') == 'success':
                result.email_result = email_result
                result.add_event('email', OnboardingStatus.SUCCESS, email_result)
                progress_logger.log_result("Welcome email sent")
            else:
                result.add_event('email', OnboardingStatus.FAILED)
                progress_logger.log_error("Email send failed")
            
            # Update final status
            if db_id:
                await self.delegate_to_agent(
                    self.db_manager,
                    "Update contact status",
                    {
                        "contact_onboarding_id": db_id,
                        "slack_status": 'success' if result.slack else 'failed',
                        "slack_user_id": result.slack.get('slack_user_id') if result.slack else None,
                        "email_status": 'success' if result.email_result else 'failed',
                        "overall_status": self.determine_overall_status(result)
                    }
                )
            
            results.append(result)
            
        return results
    
    async def assign_to_committee(self, contact: Dict) -> Dict:
        """Assign contact to appropriate committee"""
        contact_type = contact.get('contact_type', 'unknown')
        committee_map = {
            'primary': 'governance',
            'marketing': 'marketing',
            'technical': 'technical'
        }
        
        committee_type = committee_map.get(contact_type)
        if not committee_type:
            return {"status": "error", "message": f"Unknown contact type: {contact_type}"}
        
        committee = self.project_context.committees.get(committee_type)
        if not committee:
            return {"status": "error", "message": f"No {committee_type} committee found"}
        
        # Check if already member
        check_result = await self.delegate_to_agent(
            self.committee_manager,
            f"Check if {contact['email']} is already in committee {committee['id']}",
            {
                "project_id": self.project_context.project_id,
                "committee_id": committee['id'],
                "email": contact['email']
            }
        )
        
        if check_result.get('is_member'):
            return {
                "status": "success",
                "committee_id": committee['id'],
                "committee_name": committee['name'],
                "already_member": True
            }
        
        # Add to committee
        add_result = await self.delegate_to_agent(
            self.committee_manager,
            f"Add {contact['email']} to committee {committee['id']}",
            {
                "project_id": self.project_context.project_id,
                "committee_id": committee['id'],
                "member_data": {
                    "email": contact['email'],
                    "first_name": contact.get('first_name'),
                    "last_name": contact.get('last_name'),
                    "organization": self.project_context.organization_name,
                    "role": contact.get('title')
                }
            }
        )
        
        if add_result.get('status') == 'success':
            return {
                "status": "success",
                "committee_id": committee['id'],
                "committee_name": committee['name']
            }
        
        return add_result
    
    async def onboard_to_slack(self, contact: Dict, committee_id: str) -> Dict:
        """Onboard contact to Slack workspace"""
        committee = next((c for c in self.project_context.committees.values() 
                         if c['id'] == committee_id), None)
        
        return await self.delegate_to_agent(
            self.slack_onboarder,
            f"Complete Slack onboarding for {contact['email']} with committee-specific channels",
            {
                "contact": contact,
                "organization": self.project_context.organization_name,
                "project_slug": self.project_context.project_slug,
                "committee": committee['name'] if committee else 'General'
            }
        )
    
    async def send_welcome_email(self, contact: Dict, committee_id: str) -> Dict:
        """Send welcome email to contact"""
        committee = next((c for c in self.project_context.committees.values() 
                         if c['id'] == committee_id), None)
        
        return await self.delegate_to_agent(
            self.email_communicator,
            f"Send committee-specific welcome email to {contact['email']}",
            {
                "contact": contact,
                "project_info": self.project_context.project_info,
                "committee": committee['name'] if committee else 'General'
            }
        )
    
    async def delegate_to_agent(self, agent: Agent, task: str, context: Dict = None) -> Any:
        """Delegate task to another agent with enhanced logging"""
        agent_name = agent.name
        
        # Log delegation if not already logged
        if hasattr(agent, 'name'):
            logger.debug(f"Delegating to {agent_name}: {task[:50]}...")
        
        try:
            result = await agent.run(task, context or {})
            logger.debug(f"{agent_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{agent_name} failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def calculate_failure_rate(self, results: List[ContactResult]) -> float:
        """Calculate the failure rate from results"""
        if not results:
            return 0.0
        
        failed = sum(1 for r in results if self.determine_overall_status(r) == 'failed')
        return failed / len(results)
    
    def determine_overall_status(self, result: ContactResult) -> str:
        """Determine overall status based on individual statuses"""
        if result.is_successful:
            return 'completed'
        elif result.committee and (result.slack or result.email_result):
            return 'partial'
        else:
            return 'failed'
    
    async def handle_high_failure_rate(self, results: List[ContactResult]):
        """Handle high failure rate scenario"""
        # Analyze failure patterns
        committee_failures = sum(1 for r in results if r.committee_status == 'failed')
        slack_failures = sum(1 for r in results if r.slack_status == 'failed')
        email_failures = sum(1 for r in results if r.email_status == 'failed')
        
        logger.warning(f"Failure analysis - Committee: {committee_failures}, "
                      f"Slack: {slack_failures}, Email: {email_failures}")
        
        # Could implement retry logic or alerting here
        await asyncio.sleep(1)  # Brief pause before continuing