"""Base API client for all services"""
from typing import Dict, Any, Optional
import os
from abc import ABC, abstractmethod


class BaseAPIClient(ABC):
    """Abstract base class for API clients"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = self._build_headers()
    
    def _build_headers(self) -> Dict[str, str]:
        """Build common headers"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'OnboardingAgent/1.0'
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate API connection"""
        pass
    
    def get_endpoint(self, path: str) -> str:
        """Build full endpoint URL"""
        return f"{self.base_url}/{path.lstrip('/')}"