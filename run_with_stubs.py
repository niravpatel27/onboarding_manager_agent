#!/usr/bin/env python3
"""Run the onboarding system with stub services (no OpenAI required)"""

import asyncio
import json
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# Import stub services
from stub_services import (
    get_stub_member_service,
    get_stub_project_service,
    get_stub_slack_service,
    get_stub_email_service,
    get_stub_landscape_service,
    get_stub_database_service
)

# Import real MCP database tools
from src.tools.mcp_database_abstraction import OnboardingDatabaseTools

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Contact:
    first_name: str
    last_name: str
    title: str
    email: str
    contact_type: str
    organization: str
    contact_id: str

@dataclass
class ProjectContext:
    organization_name: str
    project_slug: str
    member_id: Optional[str] = None
    project_id: Optional[str] = None
    committees: Optional[Dict[str, str]] = None

class StubOrchestrator:
    """Orchestrator that uses stub services directly"""
    
    def __init__(self, project_context: ProjectContext):
        self.project_context = project_context
        self.session_id = None
        
        # Initialize stub services
        self.member_service = get_stub_member_service()
        self.project_service = get_stub_project_service()
        self.slack_service = get_stub_slack_service()
        self.email_service = get_stub_email_service()
        self.landscape_service = get_stub_landscape_service()
        # Use real MCP database instead of stub
        self.db_service = OnboardingDatabaseTools()
        
        logger.info("Initialized stub services with real MCP database")
    
    async def process_contacts(self):
        """Main workflow orchestration"""
        try:
            logger.info("="*60)
            logger.info(f"STARTING ONBOARDING WORKFLOW (STUB MODE)")
            logger.info(f"Organization: {self.project_context.organization_name}")
            logger.info(f"Project: {self.project_context.project_slug}")
            logger.info("="*60)
            
            # Step 1: Get member info
            logger.info("\n--- Step 1: Getting Member Information ---")
            member_result = await self.member_service.get_member_by_organization(
                self.project_context.organization_name
            )
            if member_result['status'] != 'success':
                return {"status": "error", "message": "Member not found"}
            
            self.project_context.member_id = member_result['member_id']
            logger.info(f"✓ Found member: {member_result['member_info']['name']} (ID: {self.project_context.member_id})")
            
            # Step 2: Get project info
            logger.info("\n--- Step 2: Getting Project Information ---")
            project_result = await self.project_service.get_project_by_slug(
                self.project_context.project_slug
            )
            if project_result['status'] != 'success':
                return {"status": "error", "message": "Project not found"}
            
            self.project_context.project_id = project_result['project_id']
            logger.info(f"✓ Found project: {project_result['project_info']['name']} (ID: {self.project_context.project_id})")
            
            # Step 3: Initialize database and create session
            logger.info("\n--- Step 3: Creating Database Session ---")
            # Initialize database schema
            await self.db_service.initialize()
            
            # Create onboarding session
            session_result = await self.db_service.create_onboarding_session(
                self.project_context.organization_name,
                self.project_context.project_slug,
                self.project_context.member_id,
                self.project_context.project_id
            )
            self.session_id = session_result['session_id']
            logger.info(f"✓ Created session ID: {self.session_id}")
            
            # Step 4: Get contacts
            logger.info("\n--- Step 4: Fetching Contacts ---")
            contacts_result = await self.member_service.get_member_contacts(
                self.project_context.member_id
            )
            contacts = contacts_result['contacts']
            logger.info(f"✓ Found {len(contacts)} contacts")
            
            # Step 5: Get committees
            logger.info("\n--- Step 5: Setting Up Committees ---")
            committees_result = await self.project_service.get_project_committees(
                self.project_context.project_id
            )
            committees = committees_result['committees']
            logger.info(f"✓ Found {len(committees)} committees")
            
            # Map committees by type
            committee_map = {}
            for committee in committees:
                name_lower = committee['name'].lower()
                if 'governing' in name_lower or 'board' in name_lower:
                    committee_map['primary'] = committee['id']
                elif 'marketing' in name_lower:
                    committee_map['marketing'] = committee['id']
                elif 'technical' in name_lower or 'tech' in name_lower:
                    committee_map['technical'] = committee['id']
            
            self.project_context.committees = committee_map
            
            # Step 6: Process each contact
            logger.info("\n--- Step 6: Processing Individual Contacts ---")
            results = []
            
            for i, contact in enumerate(contacts, 1):
                logger.info(f"\nProcessing contact {i}/{len(contacts)}: {contact['first_name']} {contact['last_name']}")
                
                # Add to database
                db_result = await self.db_service.add_contact_to_session(self.session_id, contact)
                contact_db_id = db_result['contact_onboarding_id']
                
                # Process committee assignment
                committee_id = committee_map.get(contact['contact_type'])
                if committee_id:
                    committee_result = await self.project_service.add_committee_member(
                        self.project_context.project_id,
                        committee_id,
                        {
                            "name": f"{contact['first_name']} {contact['last_name']}",
                            "email": contact['email'],
                            "organization": self.project_context.organization_name,
                            "title": contact['title'],
                            "role": contact['contact_type']
                        }
                    )
                    logger.info(f"  ✓ Added to committee: {committee_result['status']}")
                
                # Process Slack invitation
                slack_result = await self.slack_service.invite_to_workspace(
                    contact['email'],
                    ["#general", "#welcome"],
                    self.project_context.organization_name
                )
                logger.info(f"  ✓ Slack invitation: {slack_result['status']}")
                
                # Send welcome email
                email_result = await self.email_service.send_welcome_email(
                    contact,
                    {"name": self.project_context.project_slug}
                )
                logger.info(f"  ✓ Welcome email: {email_result['status']}")
                
                # Update contact statuses
                await self.db_service.update_contact_committee_status(
                    contact_db_id, 
                    "success" if committee_result['status'] == 'success' else "failed",
                    committee_result.get('member_id')
                )
                await self.db_service.update_contact_slack_status(
                    contact_db_id,
                    "success" if slack_result['status'] == 'success' else "failed",
                    slack_result.get('slack_user_id')
                )
                await self.db_service.update_contact_email_status(
                    contact_db_id,
                    "success" if email_result['status'] == 'success' else "failed"
                )
                await self.db_service.update_overall_status(contact_db_id)
                
                results.append({
                    "contact": contact,
                    "committee": committee_result,
                    "slack": slack_result,
                    "email": email_result
                })
            
            # Step 7: Update landscape
            logger.info("\n--- Step 7: Updating Project Landscape ---")
            landscape_result = await self.landscape_service.update_member_logo(
                self.project_context.project_slug,
                self.project_context.organization_name,
                ""
            )
            logger.info(f"✓ Landscape update: Created PR {landscape_result['pr_url']}")
            
            # Step 8: Update session statistics and generate report
            logger.info("\n--- Step 8: Generating Final Report ---")
            # Update session statistics
            await self.db_service.update_session_statistics(self.session_id)
            # Generate report
            report = await self.db_service.get_session_report(self.session_id)
            
            logger.info("\n" + "="*60)
            logger.info("ONBOARDING WORKFLOW COMPLETED")
            logger.info("="*60)
            
            return {
                "status": "success",
                "session_id": self.session_id,
                "contacts_processed": len(contacts),
                "results": results,
                "landscape_pr": landscape_result['pr_url'],
                "report": report
            }
            
        except Exception as e:
            logger.error(f"Error in orchestration: {str(e)}")
            return {"status": "error", "message": str(e)}

async def main(organization_name: str, project_slug: str):
    """Main entry point"""
    try:
        # Create project context
        project_context = ProjectContext(
            organization_name=organization_name,
            project_slug=project_slug
        )
        
        # Create and run orchestrator
        orchestrator = StubOrchestrator(project_context)
        result = await orchestrator.process_contacts()
        
        # Save results
        output_file = f"stub_result_{organization_name.lower().replace(' ', '_')}_{project_slug}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        logger.info(f"\nResults saved to: {output_file}")
        
        # Print summary
        if result['status'] == 'success':
            logger.info(f"\n✅ Successfully processed {result['contacts_processed']} contacts")
        else:
            logger.error(f"\n❌ Failed: {result.get('message', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"System error: {str(e)}")
        raise

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python run_with_stubs.py <organization_name> <project_slug>")
        print("Example: python run_with_stubs.py 'Acme Corp' 'cncf'")
        sys.exit(1)
    
    org_name = sys.argv[1]
    proj_slug = sys.argv[2]
    
    # Run the system
    asyncio.run(main(org_name, proj_slug))