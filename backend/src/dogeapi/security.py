"""Scope-based access control helpers.

These compose with the basic ``deps.get_token_payload`` to enforce both:

1. The caller's JWT contains a required *scope* (RBAC).
2. The caller's JWT was issued for the *organization* whose slug is in
   the URL (tenant context match).
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from authx import TokenPayload
from authx._internal._scopes import has_required_scopes
from authx.exceptions import InsufficientScopeError
from fastapi import Depends, HTTPException, Path, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.db import get_session
from dogeapi.deps import (
    _token_extra,
    get_app_settings,
    get_token_payload,
)
from dogeapi.models import AuthSession, Organization
from dogeapi.organizations import service


def require_scope(
    *scopes: str,
    all_required: bool = True,
) -> Callable[..., Coroutine[Any, Any, TokenPayload]]:
    """Build a FastAPI dependency that enforces JWT scopes.

    Wildcards work via authx (``"org:*"`` matches everything beneath
    ``org:``). Pass ``all_required=False`` for OR semantics.
    """
    required = list(scopes)

    async def _check(
        payload: Annotated[TokenPayload, Depends(get_token_payload)],
    ) -> TokenPayload:
        if not has_required_scopes(required, payload.scopes, all_required=all_required):
            raise InsufficientScopeError(required=required, provided=payload.scopes)
        return payload

    return _check


async def require_org_match(
    slug: Annotated[str, Path(min_length=2)],
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    payload: Annotated[TokenPayload, Depends(get_token_payload)],
) -> Organization:
    """Resolve the URL's org and verify the JWT is scoped to it."""
    org = await service.get_organization_by_slug(session, slug)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")

    token_org_id = _token_extra(payload, "org_id")
    if token_org_id is None or UUID(str(token_org_id)) != org.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Switch to this organization first",
        )
    request.state.audit_org_id = str(org.id)
    return org


OrgMatch = Annotated[Organization, Depends(require_org_match)]


async def require_step_up(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Any, Depends(get_app_settings)],
    payload: Annotated[TokenPayload, Depends(get_token_payload)],
) -> TokenPayload:
    """Require a recent password+MFA confirmation for sensitive commands.

    Development and test remain usable without forced enrollment; production
    settings cannot disable this gate.
    """
    if not settings.PRIVILEGED_MFA_ENFORCED:
        return payload
    sid = _token_extra(payload, "sid")
    if sid is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Step-up authentication required")
    try:
        session_id = UUID(str(sid))
    except ValueError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Step-up authentication required") from exc
    auth_session = await session.scalar(
        select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.step_up_until > datetime.now(UTC),
        )
    )
    if auth_session is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Step-up authentication required")
    return payload


__all__ = (
    "OrgMatch",
    "require_org_match",
    "require_scope",
    "require_step_up",
)
