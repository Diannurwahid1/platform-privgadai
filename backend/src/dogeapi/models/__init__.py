"""SQLAlchemy ORM models.

Every module imports its own models from this package's submodules so
Alembic's autogenerate sees them via ``Base.metadata``.
"""

from dogeapi.models.ai import AIMessage, AIThread
from dogeapi.models.api_key import APIKey
from dogeapi.models.approval import ApprovalDelegation, ApprovalEvent, ApprovalRequest
from dogeapi.models.audit_log import AuditLog
from dogeapi.models.auth_token import AuthTokenStore
from dogeapi.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from dogeapi.models.complaint import ComplaintCase, ComplaintEvent
from dogeapi.models.configuration import ConfigurationEvent, ConfigurationVersion
from dogeapi.models.erp import (
    AccountingPeriod,
    Cashbox,
    CashTransaction,
    CollectionCase,
    CollectionNote,
    CollectionPromise,
    DebtorProfile,
    GLAccount,
    InventoryCheck,
    InventoryCheckItem,
    JournalEntry,
    JournalLine,
    LoanLedgerEntry,
    PawnAgreement,
    RegulatoryReportRun,
    RegulatoryReportTemplate,
    TellerSession,
)
from dogeapi.models.invitation import Invitation
from dogeapi.models.kyc import KycDocument, KycEvent, KycProviderCheck, KycVerification
from dogeapi.models.membership import Membership, Role
from dogeapi.models.mvp import (
    AssetCategory,
    CollateralEvent,
    Consent,
    CustodyEvent,
    CustodyLocation,
    CustodyMovement,
    CustomerAcceptance,
    EvidenceEvent,
    EvidenceFile,
    HumanAppraisal,
    Incident,
    IncidentEvent,
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
from dogeapi.models.payments import PaymentAdjustment, PaymentReceipt, ReconciliationRun
from dogeapi.models.security import AuthSession, SecurityEvent, UserSecurityProfile
from dogeapi.models.subscription import Subscription
from dogeapi.models.user import User

__all__ = (
    "AIMessage",
    "AIThread",
    "APIKey",
    "AccountingPeriod",
    "ApplicationStatusHistory",
    "ApprovalDelegation",
    "ApprovalEvent",
    "ApprovalRequest",
    "Asset",
    "AssetCategory",
    "AuditLog",
    "AuthSession",
    "AuthTokenStore",
    "Base",
    "Borrower",
    "Branch",
    "CashTransaction",
    "Cashbox",
    "CollateralEvent",
    "CollectionCase",
    "CollectionNote",
    "CollectionPromise",
    "ComplaintCase",
    "ComplaintEvent",
    "ConfigurationEvent",
    "ConfigurationVersion",
    "Consent",
    "CustodyEvent",
    "CustodyLocation",
    "CustodyMovement",
    "CustomerAcceptance",
    "DebtorProfile",
    "EvidenceEvent",
    "EvidenceFile",
    "GLAccount",
    "HumanAppraisal",
    "Incident",
    "IncidentEvent",
    "InventoryCheck",
    "InventoryCheckItem",
    "Invitation",
    "JournalEntry",
    "JournalLine",
    "KycDocument",
    "KycEvent",
    "KycProviderCheck",
    "KycVerification",
    "LoanAccount",
    "LoanApplication",
    "LoanLedgerEntry",
    "LoanProduct",
    "Membership",
    "OAuthAccount",
    "Offer",
    "Organization",
    "PawnAgreement",
    "PaymentAdjustment",
    "PaymentReceipt",
    "PickupTask",
    "ReconciliationRun",
    "RegulatoryReportRun",
    "RegulatoryReportTemplate",
    "Role",
    "SecurityEvent",
    "SettlementVerification",
    "StaffAssignment",
    "Subscription",
    "TellerSession",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "User",
    "UserSecurityProfile",
)
