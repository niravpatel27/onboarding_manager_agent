"""Main entry point for the onboarding agent system"""
import asyncio
import sys
import json
from typing import Optional
from .agents.orchestrator_enhanced import OrchestratorAgent
from .models.project import ProjectContext
from .tools.mcp.database import OnboardingDatabase
from .config.settings import settings
from .utils.logging import setup_logging
from .utils.metrics import metrics

# Import stub services if in local mode
if settings.is_local_mode():
    sys.path.append('..')
    from stub_services import (
        get_stub_member_service,
        get_stub_project_service,
        get_stub_slack_service,
        get_stub_email_service,
        get_stub_landscape_service
    )
    
    # Override API clients with stub versions
    from .tools.api_clients import member_service, project_service, slack, email
    
    # Monkey patch the clients to use stubs
    member_service.MemberServiceClient = get_stub_member_service
    project_service.ProjectServiceClient = get_stub_project_service
    slack.SlackClient = get_stub_slack_service
    email.EmailClient = get_stub_email_service


async def run_contact_onboarding(organization_name: str, project_slug: str):
    """Main entry point for the autonomous agent system"""
    # Setup logging with reduced verbosity for cleaner output
    logger = setup_logging('WARNING', settings.LOG_FILE)
    logger.debug(f"Starting onboarding for {organization_name} → {project_slug}")
    logger.debug(f"Running in {settings.RUN_MODE} mode")
    
    # Start metrics timer
    metrics.start_timer('total_onboarding')
    
    try:
        # Validate settings
        settings.validate()
        
        # Initialize database
        db = OnboardingDatabase(settings.DB_TYPE, settings.DB_CONNECTION)
        
        # Create project context
        project_context = ProjectContext(
            organization_name=organization_name,
            project_slug=project_slug
        )
        
        # Create orchestrator
        orchestrator = OrchestratorAgent(project_context, db)
        
        # Start the autonomous process
        result = await orchestrator.run("start onboarding workflow")
        
        # Record metrics
        duration = metrics.stop_timer('total_onboarding')
        
        if result.get('session'):
            session = result['session']
            metrics.increment('sessions_completed')
            metrics.increment('contacts_processed', session.get('total_contacts', 0))
            metrics.increment('contacts_successful', session.get('successful_contacts', 0))
            metrics.increment('contacts_failed', session.get('failed_contacts', 0))
            
            success_rate = session.get('successful_contacts', 0) / session.get('total_contacts', 1) * 100
            logger.debug(f"Onboarding completed in {duration:.2f}s. Success rate: {success_rate:.1f}%")
        
        # Log metrics summary
        logger.debug(f"Metrics: {json.dumps(metrics.get_summary(), indent=2)}")
        
        return result
        
    except Exception as e:
        logger.error(f"System error: {str(e)}", exc_info=True)
        metrics.increment('sessions_failed')
        raise


async def main(organization_name: str, project_slug: str):
    """Main function with error handling"""
    try:
        # Validate inputs
        if not organization_name or not project_slug:
            raise ValueError("Both organization_name and project_slug are required")
        
        # Run the system
        result = await run_contact_onboarding(organization_name, project_slug)
        
        # Output results (minimal, since we have the natural language summary)
        if result and 'error' not in result:
            # Success case - progress logger already showed the summary
            pass
        else:
            # Error case - show the result
            print(json.dumps(result, indent=2, default=str))
        
        return result
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m src.main <organization_name> <project_slug>")
        print("Example: python -m src.main 'Acme Corp' 'cncf'")
        sys.exit(1)
    
    org_name = sys.argv[1]
    proj_slug = sys.argv[2]
    
    # Run the autonomous system
    asyncio.run(main(org_name, proj_slug))