"""SQLAlchemy ORM models.

Every module imports its own models from this package's submodules so
Alembic's autogenerate sees them via ``Base.metadata``.
"""

from dogeapi.models.ai import AIMessage, AIThread
from dogeapi.models.api_key import APIKey
from dogeapi.models.audit_log import AuditLog
from dogeapi.models.auth_token import AuthTokenStore
from dogeapi.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from dogeapi.models.invitation import Invitation
from dogeapi.models.membership import Membership, Role
from dogeapi.models.mvp import (
    AssetCategory,
    CollateralEvent,
    Consent,
    CustodyEvent,
    CustodyLocation,
    CustomerAcceptance,
    EvidenceFile,
    HumanAppraisal,
    Incident,
    LoanAccount,
    LoanProduct,
    Offer,
    PickupTask,
    SettlementVerification,
    StaffAssignment,
)
from dogeapi.models.oauth_account import OAuthAccount
from dogeapi.models.operations import ApplicationStatusHistory, Asset, Borrower, Branch, LoanApplication
from dogeapi.models.organization import Organization
from dogeapi.models.subscription import Subscription
from dogeapi.models.user import User

__all__ = (
    "AIMessage",
    "AIThread",
    "APIKey",
    "ApplicationStatusHistory",
    "Asset",
    "AssetCategory",
    "AuditLog",
    "AuthTokenStore",
    "Base",
    "Borrower",
    "Branch",
    "CollateralEvent",
    "Consent",
    "CustodyEvent",
    "CustodyLocation",
    "CustomerAcceptance",
    "EvidenceFile",
    "HumanAppraisal",
    "Incident",
    "Invitation",
    "LoanAccount",
    "LoanApplication",
    "LoanProduct",
    "Membership",
    "OAuthAccount",
    "Offer",
    "Organization",
    "PickupTask",
    "Role",
    "SettlementVerification",
    "StaffAssignment",
    "Subscription",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "User",
)
