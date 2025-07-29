#!/usr/bin/env python3
"""Natural workflow trace that groups operations logically"""
import asyncio
import os
import sys
from datetime import datetime
from functools import wraps
import inspect
import re

# Set to local mode
os.environ['RUN_MODE'] = 'local'

# Workflow stages tracking
current_stage = None
stage_operations = []

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

def extract_email(data):
    """Extract email from various data formats"""
    if isinstance(data, str):
        match = re.search(r"'email': '([^']+)'", data)
        return match.group(1) if match else 'Unknown'
    elif isinstance(data, dict):
        return data.get('email', 'Unknown')
    return 'Unknown'

def trace_method(class_name):
    """Decorator to trace methods and group by workflow stage"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            global current_stage
            method_name = func.__name__
            
            # Get arguments
            arg_names = list(inspect.signature(func).parameters.keys())
            arg_values = {}
            for i, arg_name in enumerate(arg_names):
                if i < len(args) and arg_name != 'self':
                    arg_values[arg_name] = args[i]
                elif arg_name in kwargs:
                    arg_values[arg_name] = kwargs[arg_name]
            
            # Determine workflow stage
            if class_name in ['StubMemberService', 'StubProjectService'] and method_name in ['get_member_by_organization', 'get_project_by_slug']:
                if current_stage != 'initialization':
                    current_stage = 'initialization'
                    print(f"\n{Colors.BLUE}{Colors.BOLD}🔍 INITIALIZATION PHASE{Colors.ENDC}")
                    print(f"{Colors.DIM}{'─'*60}{Colors.ENDC}")
            
            elif method_name == 'get_member_contacts':
                if current_stage != 'contact_fetch':
                    current_stage = 'contact_fetch'
                    print(f"\n{Colors.BLUE}{Colors.BOLD}👥 FETCHING CONTACTS{Colors.ENDC}")
                    print(f"{Colors.DIM}{'─'*60}{Colors.ENDC}")
            
            elif method_name in ['check_committee_membership', 'add_committee_member']:
                if current_stage != 'committee':
                    current_stage = 'committee'
                    print(f"\n{Colors.BLUE}{Colors.BOLD}🏛️  COMMITTEE ASSIGNMENTS{Colors.ENDC}")
                    print(f"{Colors.DIM}{'─'*60}{Colors.ENDC}")
            
            elif class_name == 'StubSlackService':
                if current_stage != 'slack':
                    current_stage = 'slack'
                    print(f"\n{Colors.BLUE}{Colors.BOLD}💬 SLACK INVITATIONS{Colors.ENDC}")
                    print(f"{Colors.DIM}{'─'*60}{Colors.ENDC}")
            
            elif class_name == 'StubEmailService':
                if current_stage != 'email':
                    current_stage = 'email'
                    print(f"\n{Colors.BLUE}{Colors.BOLD}📧 WELCOME EMAILS{Colors.ENDC}")
                    print(f"{Colors.DIM}{'─'*60}{Colors.ENDC}")
            
            elif class_name == 'StubLandscapeService':
                if current_stage != 'landscape':
                    current_stage = 'landscape'
                    print(f"\n{Colors.BLUE}{Colors.BOLD}🌍 LANDSCAPE UPDATE{Colors.ENDC}")
                    print(f"{Colors.DIM}{'─'*60}{Colors.ENDC}")
            
            # Execute and display based on method
            start_time = datetime.now()
            
            try:
                # Pre-execution display
                if method_name == 'get_member_by_organization':
                    print(f"  🔎 Looking up: {Colors.CYAN}{arg_values.get('org_name', 'Unknown')}{Colors.ENDC}")
                
                elif method_name == 'get_project_by_slug':
                    print(f"  🎯 Finding project: {Colors.CYAN}{arg_values.get('project_slug', 'Unknown')}{Colors.ENDC}")
                
                elif method_name == 'get_member_contacts':
                    print(f"  📋 Retrieving contact list...")
                
                elif method_name == 'check_committee_membership':
                    email = arg_values.get('email', 'Unknown')
                    committee_map = {'comm-001': 'Governing Board', 'comm-002': 'Marketing', 'comm-003': 'Technical'}
                    committee = committee_map.get(arg_values.get('committee_id', ''), 'Unknown')
                    # Don't print individual checks, we'll summarize after
                
                elif method_name == 'add_committee_member':
                    member_data = arg_values.get('member_data', {})
                    email = extract_email(member_data)
                    committee_map = {'comm-001': 'Governing Board', 'comm-002': 'Marketing', 'comm-003': 'Technical'}
                    committee = committee_map.get(arg_values.get('committee_id', ''), 'Unknown')
                    print(f"  ➕ {Colors.YELLOW}{email}{Colors.ENDC} → {Colors.CYAN}{committee}{Colors.ENDC}")
                
                elif method_name == 'invite_to_workspace':
                    email = arg_values.get('email', 'Unknown')
                    print(f"  📨 {Colors.YELLOW}{email}{Colors.ENDC}")
                
                elif method_name == 'send_welcome_email':
                    contact = arg_values.get('contact', {})
                    email = extract_email(contact)
                    print(f"  ✉️  {Colors.YELLOW}{email}{Colors.ENDC}")
                
                elif method_name == 'check_landscape_entry':
                    org = arg_values.get('organization', 'Unknown')
                    proj = arg_values.get('project', 'Unknown')
                    print(f"  🔍 Checking {Colors.CYAN}{org}{Colors.ENDC} in {Colors.CYAN}{proj}{Colors.ENDC} landscape")
                
                elif method_name == 'update_member_logo':
                    org = arg_values.get('organization', 'Unknown')
                    print(f"  🖼️  Creating PR to update {Colors.CYAN}{org}{Colors.ENDC} logo")
                
                # Execute the method
                result = await func(*args, **kwargs)
                elapsed = (datetime.now() - start_time).total_seconds()
                
                # Post-execution display
                if isinstance(result, dict) and result.get('status') == 'success':
                    if method_name == 'get_member_by_organization':
                        member_info = result.get('member_info', {})
                        print(f"     {Colors.GREEN}✓{Colors.ENDC} Found: {member_info.get('name')} (ID: {result.get('member_id')})")
                    
                    elif method_name == 'get_project_by_slug':
                        project_info = result.get('project_info', {})
                        print(f"     {Colors.GREEN}✓{Colors.ENDC} Found: {project_info.get('name')} - {project_info.get('description')}")
                    
                    elif method_name == 'get_member_contacts':
                        contacts = result.get('contacts', [])
                        print(f"     {Colors.GREEN}✓{Colors.ENDC} Retrieved {len(contacts)} contacts:")
                        for c in contacts:
                            print(f"        • {c['first_name']} {c['last_name']} ({c['email']}) - {c['title']}")
                    
                    elif method_name in ['add_committee_member', 'invite_to_workspace', 'send_welcome_email']:
                        print(f"     {Colors.GREEN}✓ Done{Colors.ENDC} {Colors.DIM}({elapsed:.2f}s){Colors.ENDC}")
                    
                    elif method_name == 'check_landscape_entry':
                        exists = result.get('exists', False)
                        print(f"     {Colors.GREEN}✓{Colors.ENDC} Entry {'exists' if exists else 'does not exist'}")
                    
                    elif method_name == 'update_member_logo':
                        pr_url = result.get('pr_url', 'Unknown')
                        print(f"     {Colors.GREEN}✓{Colors.ENDC} PR created: {Colors.CYAN}{pr_url}{Colors.ENDC}")
                
                elif isinstance(result, dict) and result.get('status') == 'error':
                    print(f"     {Colors.RED}✗ Failed: {result.get('message', 'Unknown error')}{Colors.ENDC}")
                
                return result
                
            except Exception as e:
                print(f"     {Colors.RED}✗ Error: {str(e)}{Colors.ENDC}")
                raise
        
        return wrapper
    return decorator

# Patch the stub services
from stub_services import (
    StubMemberService, StubProjectService, StubSlackService,
    StubEmailService, StubLandscapeService
)

# Apply tracing
StubMemberService.get_member_by_organization = trace_method('StubMemberService')(StubMemberService.get_member_by_organization)
StubMemberService.get_member_contacts = trace_method('StubMemberService')(StubMemberService.get_member_contacts)
StubProjectService.get_project_by_slug = trace_method('StubProjectService')(StubProjectService.get_project_by_slug)
StubProjectService.check_committee_membership = trace_method('StubProjectService')(StubProjectService.check_committee_membership)
StubProjectService.add_committee_member = trace_method('StubProjectService')(StubProjectService.add_committee_member)
StubSlackService.invite_to_workspace = trace_method('StubSlackService')(StubSlackService.invite_to_workspace)
StubEmailService.send_welcome_email = trace_method('StubEmailService')(StubEmailService.send_welcome_email)
StubLandscapeService.check_landscape_entry = trace_method('StubLandscapeService')(StubLandscapeService.check_landscape_entry)
StubLandscapeService.update_member_logo = trace_method('StubLandscapeService')(StubLandscapeService.update_member_logo)

# Import main after patching
from main_agents_with_stubs import run_contact_onboarding

async def run_with_trace(org_name: str, project_slug: str):
    """Run the workflow with natural tracing"""
    print(f"\n{Colors.HEADER}{'═'*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}🚀 ONBOARDING WORKFLOW{Colors.ENDC}")
    print(f"{Colors.HEADER}{'═'*70}{Colors.ENDC}")
    print(f"\n📍 Organization: {Colors.CYAN}{Colors.BOLD}{org_name}{Colors.ENDC}")
    print(f"📍 Project: {Colors.CYAN}{Colors.BOLD}{project_slug}{Colors.ENDC}")
    
    start_time = datetime.now()
    
    # Run the onboarding
    result = await run_contact_onboarding(org_name, project_slug)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Summary
    print(f"\n{Colors.HEADER}{'═'*70}{Colors.ENDC}")
    print(f"{Colors.GREEN}{Colors.BOLD}✅ WORKFLOW COMPLETED{Colors.ENDC}")
    print(f"{Colors.HEADER}{'═'*70}{Colors.ENDC}")
    
    if result and 'session' in result:
        session = result['session']
        print(f"\n📊 Results:")
        print(f"   • Total contacts: {session.get('total_contacts', 0)}")
        print(f"   • Successfully onboarded: {Colors.GREEN}{session.get('successful_contacts', 0)}{Colors.ENDC}")
        print(f"   • Failed: {Colors.RED}{session.get('failed_contacts', 0)}{Colors.ENDC}")
        print(f"   • Duration: {Colors.CYAN}{elapsed:.2f} seconds{Colors.ENDC}")
    
    if result and 'landscape_update' in result:
        landscape = result['landscape_update']
        if landscape.get('pr_created'):
            print(f"\n🌍 Landscape PR: {Colors.CYAN}{landscape['pr_created']}{Colors.ENDC}")
    
    print(f"\n💾 Session data saved to local SQLite database")
    print("")
    
    return result

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python trace_workflow.py <organization_name> <project_slug>")
        print("Example: python trace_workflow.py 'Acme Corp' 'cncf'")
        sys.exit(1)
    
    # Disable agent logging for cleaner output
    import logging
    logging.basicConfig(level=logging.ERROR)
    
    org_name = sys.argv[1]
    proj_slug = sys.argv[2]
    
    asyncio.run(run_with_trace(org_name, proj_slug))