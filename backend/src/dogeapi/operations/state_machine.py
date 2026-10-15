"""Explicit workflow rules for PrivGadai applications and collateral."""

from __future__ import annotations

APPLICATION_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"submitted", "cancelled"},
    "submitted": {"under_review", "cancelled"},
    "under_review": {"appraisal", "rejected", "cancelled"},
    "appraisal": {"offered", "rejected", "cancelled"},
    "offered": {"accepted", "rejected", "cancelled"},
    "accepted": set(),
    "rejected": set(),
    "cancelled": set(),
}

COLLATERAL_TRANSITIONS: dict[str, set[str]] = {
    "with_customer": {"pickup_assigned"},
    "pickup_assigned": {"in_transit", "incident_hold"},
    "in_transit": {"received", "incident_hold"},
    "received": {"stored", "incident_hold"},
    "stored": {"release_authorized", "incident_hold"},
    "incident_hold": {"stored"},
    "release_authorized": {"returned"},
    "returned": set(),
}

LOAN_TRANSITIONS: dict[str, set[str]] = {
    "awaiting_disbursement": {"active", "cancelled"},
    "active": {"settled", "defaulted"},
    "defaulted": {"settled"},
    "settled": set(),
    "cancelled": set(),
}


def can_transition(graph: dict[str, set[str]], current: str, target: str) -> bool:
    return target in graph.get(current, set())
