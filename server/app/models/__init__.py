"""SQLAlchemy models. Import the aggregate modules so ``Base.metadata`` is filled."""

from app.models.admin import (
    AdminAuditLog,
    Feedback,
    ImportJob,
    SchemeReview,
    SchemeVersion,
    SystemHealthCheck,
)
from app.models.center import ServiceCentre
from app.models.chat import ChatMessage, ChatSession
from app.models.document import DocumentReview, DocumentType, UserDocument
from app.models.reference import Language, State
from app.models.scheme import (
    Scheme,
    UserSavedScheme,
    UserSavedSearch,
    UserSchemeView,
    UserSearchHistory,
)
from app.models.user import User, UserProfile

__all__ = [
    "AdminAuditLog",
    "ChatMessage",
    "ChatSession",
    "DocumentReview",
    "DocumentType",
    "Feedback",
    "ImportJob",
    "Language",
    "Scheme",
    "SchemeReview",
    "SchemeVersion",
    "ServiceCentre",
    "State",
    "SystemHealthCheck",
    "User",
    "UserDocument",
    "UserProfile",
    "UserSavedScheme",
    "UserSavedSearch",
    "UserSearchHistory",
    "UserSchemeView",
]
