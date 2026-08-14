"""Identity + profile aggregates: ``users`` and ``user_profiles``.

Mirror ``shared/src/domain/user.ts`` and the schema in ``docs/database/01`` §1-2.
Only the columns needed by Prompt 3 (auth + profile) are declared; eligibility
filter flags are all present (they are the mirrored input set of the engine).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import json_type


class User(Base):
    """A citizen account; null firebase_uid + is_guest=True for anonymous."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "auth_method IN ('email','phone','google','guest')",
            name="ck_users_auth_method",
        ),
        CheckConstraint(
            "role IN ('citizen','admin','content_editor')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "status IN ('active','suspended','deleted')",
            name="ck_users_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    auth_method: Mapped[str] = mapped_column(String(20), nullable=False, default="guest")
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="citizen")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    preferred_language: Mapped[str] = mapped_column(
        String(8),
        ForeignKey("languages.code", ondelete="SET NULL"),
        nullable=False,
        default="en",
    )
    consent_json: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    is_guest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped[UserProfile] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserProfile(Base):
    """Citizen eligibility attributes; 1:1 with users (docs §2)."""

    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
        CheckConstraint("age BETWEEN 0 AND 130", name="ck_user_profiles_age"),
        CheckConstraint(
            "gender IN ('male','female','transgender','prefer-not-to-say')",
            name="ck_user_profiles_gender",
        ),
        CheckConstraint(
            "income_band IN ('below-poverty','low','middle','upper')",
            name="ck_user_profiles_income_band",
        ),
        CheckConstraint(
            "community IN ('general','sc','st','obc','ews')",
            name="ck_user_profiles_community",
        ),
        CheckConstraint(
            "source IN ('manual','chat','ocr','import')",
            name="ck_user_profiles_source",
        ),
        CheckConstraint(
            "marital_status IN ('unmarried','married','widowed','divorced','prefer-not-to-say')",
            name="ck_user_profiles_marital_status",
        ),
        CheckConstraint(
            "preferred_input_method IN ('text','voice','both')",
            name="ck_user_profiles_input_method",
        ),
        CheckConstraint(
            "preferred_output_method IN ('text','voice','both')",
            name="ck_user_profiles_output_method",
        ),
        CheckConstraint(
            "notification_preference IN ('all','essential','none')",
            name="ck_user_profiles_notification_pref",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    state_code: Mapped[str | None] = mapped_column(
        String(8), ForeignKey("states.code", ondelete="SET NULL"), nullable=True
    )
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    income_band: Mapped[str | None] = mapped_column(String(20), nullable=True)
    annual_income_inr: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(40), nullable=True)
    community: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_minority: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_farmer: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_student: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_senior_citizen: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_widow: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_self_employed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_disabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    disability_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    preferred_input_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    preferred_output_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notification_preference: Mapped[str | None] = mapped_column(String(20), nullable=True)
    languages: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    accessibility_json: Mapped[dict] = mapped_column(json_type(), nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="profile")
