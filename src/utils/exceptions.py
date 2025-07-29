"""Custom exceptions for the onboarding system"""


class OnboardingException(Exception):
    """Base exception for onboarding errors"""
    pass


class MemberNotFoundException(OnboardingException):
    """Raised when member organization is not found"""
    pass


class ProjectNotFoundException(OnboardingException):
    """Raised when project is not found"""
    pass


class CommitteeNotFoundException(OnboardingException):
    """Raised when committee is not found"""
    pass


class APIException(OnboardingException):
    """Raised when external API call fails"""
    def __init__(self, service: str, message: str, status_code: int = None):
        self.service = service
        self.status_code = status_code
        super().__init__(f"{service} API error: {message}")


class RateLimitException(APIException):
    """Raised when API rate limit is exceeded"""
    pass


class ValidationException(OnboardingException):
    """Raised when data validation fails"""
    pass