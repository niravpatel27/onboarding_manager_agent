"""Enhanced logging module for clear onboarding progress tracking"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from functools import wraps

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

class OnboardingLogger:
    """Enhanced logger for tracking onboarding workflow progress"""
    
    def __init__(self, name: str = "OnboardingWorkflow"):
        self.logger = logging.getLogger(name)
        self.current_stage = None
        self.start_time = datetime.now()
        self.stage_timings = {}
        
        # Configure handler with custom formatter
        handler = logging.StreamHandler()
        handler.setFormatter(OnboardingFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        # Disable propagation to avoid duplicate logs
        self.logger.propagate = False
    
    def workflow_start(self, org_name: str, project_slug: str):
        """Mark the start of the workflow"""
        self.start_time = datetime.now()
        print(f"\n{Colors.HEADER}{'═'*70}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}🚀 ONBOARDING WORKFLOW{Colors.ENDC}")
        print(f"{Colors.HEADER}{'═'*70}{Colors.ENDC}")
        print(f"\n📍 Organization: {Colors.CYAN}{Colors.BOLD}{org_name}{Colors.ENDC}")
        print(f"📍 Project: {Colors.CYAN}{Colors.BOLD}{project_slug}{Colors.ENDC}")
    
    def stage_start(self, stage: str, icon: str = "🔍"):
        """Mark the start of a new workflow stage"""
        if self.current_stage:
            # Record timing for previous stage
            self.stage_timings[self.current_stage] = (datetime.now() - self.stage_start_time).total_seconds()
        
        self.current_stage = stage
        self.stage_start_time = datetime.now()
        
        print(f"\n{Colors.BLUE}{Colors.BOLD}{icon} {stage.upper()}{Colors.ENDC}")
        print(f"{Colors.DIM}{'─'*60}{Colors.ENDC}")
    
    def info(self, message: str, icon: str = "  "):
        """Log info message with optional icon"""
        print(f"{icon} {message}")
    
    def success(self, message: str, elapsed: Optional[float] = None):
        """Log success message"""
        elapsed_str = f" {Colors.DIM}({elapsed:.2f}s){Colors.ENDC}" if elapsed else ""
        print(f"     {Colors.GREEN}✓{Colors.ENDC} {message}{elapsed_str}")
    
    def warning(self, message: str):
        """Log warning message"""
        print(f"     {Colors.YELLOW}⚠{Colors.ENDC} {message}")
    
    def error(self, message: str):
        """Log error message"""
        print(f"     {Colors.RED}✗{Colors.ENDC} {message}")
    
    def contact_info(self, contacts: List[Dict[str, Any]]):
        """Display contact information"""
        print(f"     {Colors.GREEN}✓{Colors.ENDC} Retrieved {len(contacts)} contacts:")
        for c in contacts:
            print(f"        • {c.get('first_name', '')} {c.get('last_name', '')} ({c.get('email', '')}) - {c.get('title', '')}")
    
    def batch_progress(self, current_batch: int, total_batches: int):
        """Show batch processing progress"""
        self.info(f"Processing batch {current_batch} of {total_batches}", "📦")
    
    def contact_progress(self, contact: Dict[str, Any], action: str, status: str = "processing"):
        """Show individual contact processing"""
        email = contact.get('email', 'Unknown')
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}"
        
        if status == "processing":
            icon = "🔄"
            color = Colors.YELLOW
        elif status == "success":
            icon = "✅"
            color = Colors.GREEN
        else:
            icon = "❌"
            color = Colors.RED
        
        print(f"  {icon} {color}{name}{Colors.ENDC} ({email}) - {action}")
    
    def committee_assignment(self, email: str, committee: str):
        """Log committee assignment"""
        print(f"  ➕ {Colors.YELLOW}{email}{Colors.ENDC} → {Colors.CYAN}{committee}{Colors.ENDC}")
    
    def slack_invitation(self, email: str):
        """Log Slack invitation"""
        print(f"  📨 {Colors.YELLOW}{email}{Colors.ENDC}")
    
    def email_sent(self, email: str):
        """Log email sent"""
        print(f"  ✉️  {Colors.YELLOW}{email}{Colors.ENDC}")
    
    def landscape_update(self, org: str, project: str, status: str):
        """Log landscape update"""
        if status == "checking":
            print(f"  🔍 Checking {Colors.CYAN}{org}{Colors.ENDC} in {Colors.CYAN}{project}{Colors.ENDC} landscape")
        elif status == "updating":
            print(f"  🖼️  Creating PR to update {Colors.CYAN}{org}{Colors.ENDC} logo")
        elif status == "success":
            print(f"     {Colors.GREEN}✓{Colors.ENDC} Landscape update complete")
    
    def workflow_complete(self, stats: Dict[str, Any]):
        """Mark workflow completion with summary"""
        if self.current_stage:
            self.stage_timings[self.current_stage] = (datetime.now() - self.stage_start_time).total_seconds()
        
        total_elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n{Colors.HEADER}{'═'*70}{Colors.ENDC}")
        print(f"{Colors.GREEN}{Colors.BOLD}✅ WORKFLOW COMPLETED{Colors.ENDC}")
        print(f"{Colors.HEADER}{'═'*70}{Colors.ENDC}")
        
        print(f"\n📊 Results:")
        print(f"   • Total contacts: {stats.get('total_contacts', 0)}")
        print(f"   • Successfully onboarded: {Colors.GREEN}{stats.get('successful_contacts', 0)}{Colors.ENDC}")
        print(f"   • Failed: {Colors.RED}{stats.get('failed_contacts', 0)}{Colors.ENDC}")
        print(f"   • Duration: {Colors.CYAN}{total_elapsed:.2f} seconds{Colors.ENDC}")
        
        if stats.get('landscape_pr'):
            print(f"\n🌍 Landscape PR: {Colors.CYAN}{stats['landscape_pr']}{Colors.ENDC}")
        
        print(f"\n💾 Session data saved to database (ID: {stats.get('session_id', 'N/A')})")
        print("")

class OnboardingFormatter(logging.Formatter):
    """Custom formatter that strips standard logging prefix for cleaner output"""
    
    def format(self, record):
        # For our custom logger, just return the message
        return record.getMessage()

# Singleton instance
onboarding_logger = OnboardingLogger()