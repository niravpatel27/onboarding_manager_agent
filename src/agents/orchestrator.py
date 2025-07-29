"""Orchestrator Agent that coordinates all other agents"""
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
    """Master agent that coordinates all other agents"""
    
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
               - Update project landscape with organization data
               - Generate completion report from database
            
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
        """Main workflow orchestration method"""
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
            member_data = await self.get_member_and_project_info()
            if not member_data:
                return {"status": "error", "message": "Failed to find member or project"}
            
            # Step 3: Create onboarding session
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
            
            # Step 4: Fetch contacts
            contacts_result = await self.delegate_to_agent(
                self.contact_fetcher,
                f"Fetch all contacts for organization '{self.project_context.organization_name}'",
                {"member_id": self.project_context.member_id}
            )
            
            contacts = contacts_result.get('contacts', [])
            logger.info(f"Found {len(contacts)} contacts to process")
            
            # Add contacts to database
            contact_db_mapping = {}
            for contact in contacts:
                add_result = await self.delegate_to_agent(
                    self.db_manager,
                    "Add contact to onboarding session",
                    {"session_id": self.session_id, "contact": contact}
                )
                contact_db_mapping[contact['contact_id']] = add_result.get('contact_onboarding_id')
            
            # Step 5: Setup committees
            committee_setup = await self.setup_committees()
            if not committee_setup.get('success'):
                logger.warning("Committee setup incomplete, proceeding with available committees")
            
            # Step 6: Process contacts in batches
            batch_size = 10
            all_results = []
            
            for i in range(0, len(contacts), batch_size):
                batch = contacts[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of {(len(contacts)-1)//batch_size + 1}")
                
                batch_results = await self.process_contact_batch(batch, contact_db_mapping)
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
                    logger.warning(f"High failure rate detected: {failure_rate:.2%}")
                    await self.handle_high_failure_rate(all_results)
            
            # Step 7: Update landscape
            landscape_result = await self.delegate_to_agent(
                self.landscape_updater,
                f"Update {self.project_context.organization_name} entry in {self.project_context.project_slug} landscape"
            )
            
            # Step 8: Generate final report
            report_result = await self.delegate_to_agent(
                self.db_manager,
                "Generate session report",
                {"session_id": self.session_id}
            )
            
            report = report_result.get('report', {})
            report['landscape_update'] = landscape_result
            
            # Final session update
            await self.delegate_to_agent(
                self.db_manager,
                "Update session statistics",
                {"session_id": self.session_id}
            )
            
            logger.info("Onboarding workflow completed")
            return report
            
        except Exception as e:
            logger.error(f"Orchestration error: {str(e)}")
            return {"status": "error", "message": str(e), "context": self.project_context.__dict__}
    
    async def get_member_and_project_info(self) -> Optional[Dict]:
        """Get member ID and project details"""
        # Get member ID
        member_result = await self.delegate_to_agent(
            self.contact_fetcher,
            f"Get member ID for organization '{self.project_context.organization_name}'",
            {"organization_name": self.project_context.organization_name}
        )
        
        if not member_result.get('member_id'):
            return None
        
        self.project_context.member_id = member_result['member_id']
        
        # Get project details
        project_result = await self.delegate_to_agent(
            self.committee_manager,
            f"Get project details for slug '{self.project_context.project_slug}'",
            {"project_slug": self.project_context.project_slug}
        )
        
        if not project_result.get('project_id'):
            return None
        
        self.project_context.project_id = project_result['project_id']
        self.project_context.project_name = project_result.get('project_info', {}).get('name')
        
        return {
            "member_id": self.project_context.member_id,
            "project_id": self.project_context.project_id,
            "member_info": member_result.get('member_info', {}),
            "project_info": project_result.get('project_info', {})
        }
    
    async def setup_committees(self) -> Dict:
        """Setup committee mappings"""
        committees_result = await self.delegate_to_agent(
            self.committee_manager,
            f"Get all committees for project {self.project_context.project_id}",
            {"project_id": self.project_context.project_id}
        )
        
        committee_map = {}
        committees = committees_result.get('committees', [])
        
        for committee in committees:
            name_lower = committee.get('name', '').lower()
            if 'governing' in name_lower or 'board' in name_lower:
                committee_map['primary'] = committee['id']
            elif 'marketing' in name_lower:
                committee_map['marketing'] = committee['id']
            elif 'technical' in name_lower or 'tech' in name_lower:
                committee_map['technical'] = committee['id']
        
        self.project_context.committees = committee_map
        
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
    
    async def process_contact_batch(self, batch: List[Dict], contact_db_mapping: Dict) -> List[ContactResult]:
        """Process a batch of contacts in parallel"""
        tasks = []
        for contact in batch:
            db_id = contact_db_mapping[contact['contact_id']]
            task = self.process_single_contact(contact, db_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert to ContactResult objects
        contact_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                contact_results.append(ContactResult(
                    contact_id=batch[i]['contact_id'],
                    email=batch[i]['email'],
                    db_id=contact_db_mapping[batch[i]['contact_id']],
                    status=OnboardingStatus.FAILED,
                    error=str(result)
                ))
            else:
                contact_results.append(result)
        
        return contact_results
    
    async def process_single_contact(self, contact: Dict, db_id: int) -> ContactResult:
        """Process a single contact through all systems"""
        result = ContactResult(
            contact_id=contact['contact_id'],
            email=contact['email'],
            db_id=db_id
        )
        
        try:
            # Add to committee
            committee_id = self.project_context.committees.get(contact['contact_type'])
            if committee_id:
                result.committee = await self.add_to_committee(contact, committee_id, db_id)
            else:
                result.committee = {"status": "skipped", "reason": "committee_not_found"}
                await self.update_contact_status(db_id, "committee", "skipped")
            
            # Parallel processing for Slack and Email
            slack_task = self.process_slack_onboarding(contact, db_id)
            email_task = self.process_email_onboarding(contact, db_id)
            
            result.slack, result.email_result = await asyncio.gather(
                slack_task, email_task,
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(result.slack, Exception):
                result.slack = {"status": "failed", "error": str(result.slack)}
            if isinstance(result.email_result, Exception):
                result.email_result = {"status": "failed", "error": str(result.email_result)}
            
            # Determine final status
            if result.is_successful:
                result.status = OnboardingStatus.SUCCESS
            else:
                result.status = OnboardingStatus.PARTIAL
                
        except Exception as e:
            logger.error(f"Error processing contact {contact['contact_id']}: {str(e)}")
            result.status = OnboardingStatus.FAILED
            result.error = str(e)
        
        return result
    
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
                    await self.update_contact_status(db_id, "committee", "already_member", 
                                                   {"committee_id": committee_id})
                    return {"status": "already_member", "committee_id": committee_id}
                
                # Add to committee
                result = await self.delegate_to_agent(
                    self.committee_manager,
                    f"Add {contact['email']} to committee {committee_id}",
                    {
                        "project_id": self.project_context.project_id,
                        "committee_id": committee_id,
                        "member_data": {
                            "name": f"{contact.get('first_name', '')} {contact.get('last_name', '')}",
                            "email": contact['email'],
                            "organization": self.project_context.organization_name,
                            "title": contact.get('title', ''),
                            "role": contact['contact_type'],
                            "join_date": datetime.now().isoformat()
                        }
                    }
                )
                
                if result.get('status') == 'success':
                    await self.update_contact_status(db_id, "committee", "success", 
                                                   {"committee_id": committee_id})
                    return result
                
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    await self.update_contact_status(db_id, "committee", "failed", 
                                                   {"error": str(e)})
                    return {"status": "failed", "error": str(e)}
        
        await self.update_contact_status(db_id, "committee", "failed", 
                                       {"error": "retries_exhausted"})
        return {"status": "failed", "retries_exhausted": True}
    
    async def process_slack_onboarding(self, contact: Dict, db_id: int) -> Dict:
        """Handle Slack onboarding"""
        try:
            result = await self.delegate_to_agent(
                self.slack_onboarder,
                f"Complete Slack onboarding for {contact['email']} with committee-specific channels",
                {
                    "contact": contact,
                    "organization": self.project_context.organization_name,
                    "project_slug": self.project_context.project_slug,
                    "committee": self.get_committee_name(contact['contact_type'])
                }
            )
            
            if result.get('status') == 'success':
                await self.update_contact_status(db_id, "slack", "success", 
                                               {"slack_user_id": result.get('slack_user_id')})
            else:
                await self.update_contact_status(db_id, "slack", "failed", 
                                               {"error": result.get('error', 'Unknown error')})
            
            return result
            
        except Exception as e:
            await self.update_contact_status(db_id, "slack", "failed", {"error": str(e)})
            return {"status": "failed", "error": str(e)}
    
    async def process_email_onboarding(self, contact: Dict, db_id: int) -> Dict:
        """Handle email onboarding"""
        try:
            project_info = {
                "name": self.project_context.project_name or self.project_context.project_slug,
                "slug": self.project_context.project_slug,
                "organization": self.project_context.organization_name
            }
            
            result = await self.delegate_to_agent(
                self.email_communicator,
                f"Send committee-specific welcome email to {contact['email']}",
                {
                    "contact": contact,
                    "project_info": project_info,
                    "committee": self.get_committee_name(contact['contact_type'])
                }
            )
            
            if result.get('status') == 'success':
                await self.update_contact_status(db_id, "email", "success")
            else:
                await self.update_contact_status(db_id, "email", "failed", 
                                               {"error": result.get('error', 'Unknown error')})
            
            return result
            
        except Exception as e:
            await self.update_contact_status(db_id, "email", "failed", {"error": str(e)})
            return {"status": "failed", "error": str(e)}
    
    async def update_contact_status(self, db_id: int, status_type: str, status: str, 
                                  additional_data: Optional[Dict] = None):
        """Update contact status in database"""
        await self.delegate_to_agent(
            self.db_manager,
            "Update contact status",
            {
                "contact_onboarding_id": db_id,
                "status_type": status_type,
                "status": status,
                "additional_data": additional_data
            }
        )
    
    def get_committee_name(self, contact_type: str) -> str:
        """Get committee name based on contact type"""
        committee_names = {
            "primary": "Governing Board",
            "marketing": "Marketing Committee",
            "technical": "Technical Committee"
        }
        return committee_names.get(contact_type, "Project Committee")
    
    def calculate_failure_rate(self, results: List[ContactResult]) -> float:
        """Calculate the failure rate of processed contacts"""
        if not results:
            return 0.0
        
        failures = sum(1 for r in results if r.status in [OnboardingStatus.FAILED, OnboardingStatus.PARTIAL])
        return failures / len(results)
    
    async def handle_high_failure_rate(self, results: List[ContactResult]):
        """Handle high failure rate scenario"""
        analysis = self.analyze_failures(results)
        logger.critical(f"High failure rate alert: {analysis}")
        
        # In production, this would trigger alerts
        # Could implement automatic recovery strategies
    
    def analyze_failures(self, results: List[ContactResult]) -> Dict:
        """Analyze failure patterns"""
        failures = [r for r in results if r.status in [OnboardingStatus.FAILED, OnboardingStatus.PARTIAL]]
        
        analysis = {
            "organization": self.project_context.organization_name,
            "project": self.project_context.project_slug,
            "total_failures": len(failures),
            "failure_rate": len(failures) / len(results) if results else 0,
            "committee_failures": sum(1 for f in failures if f.committee and f.committee.get('status') == 'failed'),
            "slack_failures": sum(1 for f in failures if f.slack and f.slack.get('status') == 'failed'),
            "email_failures": sum(1 for f in failures if f.email_result and f.email_result.get('status') == 'failed'),
            "timestamp": datetime.now().isoformat()
        }
        
        return analysis
    
    async def delegate_to_agent(self, agent: Agent, task: str, context: Dict = None) -> Any:
        """Delegate a task to a specific agent"""
        logger.info(f"Delegating to {agent.name}: {task[:50]}...")
        
        result = await agent.run(task, context)
        
        if result.get('status') == 'error':
            logger.error(f"{agent.name} error: {result.get('message')}")
        else:
            logger.info(f"{agent.name} completed successfully")
        
        return result