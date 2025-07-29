"""Project data models"""
from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class ProjectContext:
    """Project context for onboarding workflow"""
    organization_name: str
    project_slug: str
    member_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    committees: Optional[Dict[str, str]] = None  # contact_type -> committee_id mapping
    
    def is_initialized(self) -> bool:
        """Check if context has required IDs"""
        return self.member_id is not None and self.project_id is not None


@dataclass
class Committee:
    """Represents a project committee"""
    id: str
    name: str
    type: str  # governance, marketing, technical
    project_id: str
    description: Optional[str] = None
    
    @property
    def contact_type(self) -> str:
        """Map committee type to contact type"""
        type_map = {
            "governance": "primary",
            "marketing": "marketing",
            "technical": "technical"
        }
        return type_map.get(self.type, "unknown")