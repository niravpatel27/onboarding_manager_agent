"""Event and result models"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class OnboardingStatus(str, Enum):
    """Onboarding status enum"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial_failure"
    SKIPPED = "skipped"
    ALREADY_EXISTS = "already_member"


@dataclass
class OnboardingEvent:
    """Represents an onboarding event"""
    contact_id: str
    event_type: str  # committee, slack, email, landscape
    status: OnboardingStatus
    timestamp: datetime = field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ContactResult:
    """Result of processing a single contact"""
    contact_id: str
    email: str
    db_id: int
    committee: Optional[Dict[str, Any]] = None
    slack: Optional[Dict[str, Any]] = None
    email_result: Optional[Dict[str, Any]] = None
    status: OnboardingStatus = OnboardingStatus.PENDING
    events: List[OnboardingEvent] = field(default_factory=list)
    
    def add_event(self, event_type: str, status: OnboardingStatus, 
                  details: Optional[Dict] = None, error: Optional[str] = None):
        """Add an event to the contact's history"""
        event = OnboardingEvent(
            contact_id=self.contact_id,
            event_type=event_type,
            status=status,
            details=details,
            error=error
        )
        self.events.append(event)
    
    @property
    def is_successful(self) -> bool:
        """Check if onboarding was successful"""
        committee_ok = self.committee and self.committee.get('status') in ['success', 'already_member']
        slack_ok = self.slack and self.slack.get('status') == 'success'
        email_ok = self.email_result and self.email_result.get('status') == 'success'
        
        # At least committee and one communication channel should succeed
        return committee_ok and (slack_ok or email_ok)


@dataclass
class BatchResult:
    """Result of processing a batch of contacts"""
    batch_number: int
    total_contacts: int
    successful: int = 0
    failed: int = 0
    partial: int = 0
    results: List[ContactResult] = field(default_factory=list)
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate"""
        if self.total_contacts == 0:
            return 0.0
        return (self.failed + self.partial) / self.total_contacts