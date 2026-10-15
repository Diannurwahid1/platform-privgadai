"""Short-lived auth token store in PostgreSQL."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dogeapi.models.base import Base


class AuthTokenStore(Base):
    __tablename__ = "auth_token_store"

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
