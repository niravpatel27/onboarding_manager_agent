"""Contact data models"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Contact:
    """Represents a member organization contact"""
    first_name: str
    last_name: str
    title: str
    email: str
    contact_type: str  # primary, marketing, or technical
    organization: str
    contact_id: str
    member_id: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'title': self.title,
            'email': self.email,
            'contact_type': self.contact_type,
            'organization': self.organization,
            'contact_id': self.contact_id,
            'member_id': self.member_id
        }
    
    @property
    def full_name(self) -> str:
        """Get full name of contact"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def committee_type(self) -> str:
        """Map contact type to committee name"""
        committee_map = {
            "primary": "Governing Board",
            "marketing": "Marketing Committee",
            "technical": "Technical Committee"
        }
        return committee_map.get(self.contact_type, "Project Committee")