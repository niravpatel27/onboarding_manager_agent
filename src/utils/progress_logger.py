"""Enhanced progress logger for natural workflow tracking"""
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import threading
import time


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'


class ProgressLogger:
    """Natural language progress logger with visual indicators"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.current_stage = None
        self.stage_start = None
        self.spinner = None
        self.spinner_thread = None
        self.spinner_active = False
        
    def start_workflow(self, org_name: str, project_slug: str):
        """Start the workflow with a welcome message"""
        print(f"\n{Colors.HEADER}{'═' * 70}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}🚀 MEMBER ONBOARDING WORKFLOW{Colors.ENDC}")
        print(f"{Colors.HEADER}{'═' * 70}{Colors.ENDC}")
        print(f"\n📍 Organization: {Colors.CYAN}{Colors.BOLD}{org_name}{Colors.ENDC}")
        print(f"📍 Project: {Colors.CYAN}{Colors.BOLD}{project_slug}{Colors.ENDC}")
        print(f"🕐 Started: {Colors.DIM}{datetime.now().strftime('%I:%M %p')}{Colors.ENDC}")
        print("")
        
    def start_stage(self, stage_name: str, description: str):
        """Start a new workflow stage"""
        self.stop_spinner()
        self.current_stage = stage_name
        self.stage_start = datetime.now()
        
        print(f"\n{Colors.BLUE}{Colors.BOLD}▶ {stage_name.upper()}{Colors.ENDC}")
        print(f"{Colors.DIM}  {description}{Colors.ENDC}")
        print(f"{Colors.DIM}{'─' * 60}{Colors.ENDC}")
        
    def log_task(self, task: str, agent: Optional[str] = None, status: str = "working"):
        """Log a specific task with optional agent attribution"""
        self.stop_spinner()
        
        icons = {
            "working": "🔄",
            "success": "✅", 
            "failed": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        
        icon = icons.get(status, "•")
        
        if agent:
            print(f"  {icon} {task} {Colors.DIM}[{agent}]{Colors.ENDC}")
        else:
            print(f"  {icon} {task}")
            
        if status == "working":
            self.start_spinner()
            
    def log_result(self, message: str, details: Optional[Dict[str, Any]] = None, status: str = "success"):
        """Log the result of an operation"""
        self.stop_spinner()
        
        colors = {
            "success": Colors.GREEN,
            "failed": Colors.RED,
            "warning": Colors.YELLOW,
            "info": Colors.CYAN
        }
        
        color = colors.get(status, Colors.ENDC)
        
        print(f"     {color}→ {message}{Colors.ENDC}")
        
        if details:
            for key, value in details.items():
                print(f"       {Colors.DIM}• {key}: {color}{value}{Colors.ENDC}")
                
    def log_contact_processing(self, contact: Dict[str, Any], batch_num: int, total_batches: int):
        """Log contact processing with details"""
        self.stop_spinner()
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}"
        email = contact.get('email', '')
        role = contact.get('title', '')
        
        print(f"\n  {Colors.YELLOW}👤 Processing: {name}{Colors.ENDC}")
        print(f"     {Colors.DIM}Email: {email}{Colors.ENDC}")
        print(f"     {Colors.DIM}Role: {role}{Colors.ENDC}")
        print(f"     {Colors.DIM}Batch: {batch_num}/{total_batches}{Colors.ENDC}")
        
    def log_delegation(self, from_agent: str, to_agent: str, task: str):
        """Log agent delegation in natural language"""
        self.stop_spinner()
        print(f"  {Colors.CYAN}↪{Colors.ENDC} {from_agent} asking {Colors.BOLD}{to_agent}{Colors.ENDC} to: {Colors.DIM}{task}{Colors.ENDC}")
        
    def log_error(self, error: str, recovery_action: Optional[str] = None):
        """Log errors with optional recovery actions"""
        self.stop_spinner()
        print(f"  {Colors.RED}⚠️  Error: {error}{Colors.ENDC}")
        if recovery_action:
            print(f"  {Colors.YELLOW}🔧 Recovery: {recovery_action}{Colors.ENDC}")
            
    def complete_stage(self):
        """Complete the current stage with timing"""
        self.stop_spinner()
        if self.stage_start:
            duration = (datetime.now() - self.stage_start).total_seconds()
            print(f"\n  {Colors.GREEN}✓ Stage completed in {duration:.1f}s{Colors.ENDC}")
            
    def complete_workflow(self, stats: Dict[str, Any]):
        """Complete the workflow with summary statistics"""
        self.stop_spinner()
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n{Colors.HEADER}{'═' * 70}{Colors.ENDC}")
        print(f"{Colors.GREEN}{Colors.BOLD}✅ WORKFLOW COMPLETED SUCCESSFULLY{Colors.ENDC}")
        print(f"{Colors.HEADER}{'═' * 70}{Colors.ENDC}")
        
        print(f"\n📊 {Colors.BOLD}Summary:{Colors.ENDC}")
        print(f"   • Total contacts: {stats.get('total_contacts', 0)}")
        print(f"   • Successfully onboarded: {Colors.GREEN}{stats.get('successful_contacts', 0)}{Colors.ENDC}")
        print(f"   • Failed: {Colors.RED}{stats.get('failed_contacts', 0)}{Colors.ENDC}")
        
        success_rate = stats.get('success_rate', 0)
        rate_color = Colors.GREEN if success_rate >= 80 else Colors.YELLOW if success_rate >= 60 else Colors.RED
        print(f"   • Success rate: {rate_color}{success_rate:.1f}%{Colors.ENDC}")
        
        print(f"   • Duration: {Colors.CYAN}{total_duration:.1f} seconds{Colors.ENDC}")
        
        if stats.get('landscape_pr'):
            print(f"\n🌍 Landscape Update:")
            print(f"   • PR Created: {Colors.CYAN}{stats['landscape_pr']}{Colors.ENDC}")
            
        print(f"\n💾 All data saved to local database")
        print(f"🕐 Completed: {Colors.DIM}{datetime.now().strftime('%I:%M %p')}{Colors.ENDC}")
        print("")
        
    def start_spinner(self):
        """Start the loading spinner"""
        if not self.spinner_active:
            self.spinner_active = True
            self.spinner_thread = threading.Thread(target=self._spin)
            self.spinner_thread.daemon = True
            self.spinner_thread.start()
            
    def stop_spinner(self):
        """Stop the loading spinner"""
        if self.spinner_active:
            self.spinner_active = False
            if self.spinner_thread:
                self.spinner_thread.join()
            # Clear spinner line
            sys.stdout.write('\r' + ' ' * 50 + '\r')
            sys.stdout.flush()
            
    def _spin(self):
        """Spinner animation"""
        spinners = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        i = 0
        while self.spinner_active:
            sys.stdout.write(f'\r     {Colors.CYAN}{spinners[i % len(spinners)]}{Colors.ENDC} ')
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1


# Global progress logger instance
progress_logger = ProgressLogger()