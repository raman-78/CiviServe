"""Service-centre persistence (maps/locator prompt).

One table covers every physical centre (CSC / e-Sevai / Seva Kendra / tehsil /
post office / bank) plus the provenance fields the UI needs to separate map and
location detail from official info:

- ``source`` / ``source_url`` / ``last_verified_at`` — attribution for
  "official source + last updated".
- ``verified`` — drives the trusted badge and the disclaimer that not every
  centre handles every scheme.
- ``lat``/``lng`` — WGS84 doubles. Production runs the nearby query through a
  PostGIS ``geom(Point,4326)`` + GiST ``ST_DWithin`` (docs/database/04 §6,
  docs/database/06 §Geo). This module keeps portable doubles so SQLite tests
  exercise the same surface; the service computes haversine distance in Python.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import json_type

#: Center-type mirror of ``CenterType`` (shared/src/domain/centers.ts).
CENTER_TYPES = ("csc", "esevai", "seva-kendra", "tehsil", "post_office", "bank")

#: How a centre record is produced (docs/database/04 §Ingestion).
CENTER_SOURCES = ("manual", "import", "api")


class ServiceCentre(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A physical service centre in the nation-wide catalog."""

    __tablename__ = "service_centres"
    __table_args__ = (
        CheckConstraint(
            "centre_type IN ('csc','esevai','seva-kendra','tehsil','post_office','bank')",
            name="ck_service_centres_centre_type",
        ),
        CheckConstraint(
            "source IN ('manual','import','api')",
            name="ck_service_centres_source",
        ),
        Index("ix_service_centres_state_district", "state_code", "district"),
        Index("ix_service_centres_type", "centre_type"),
    )

    centre_type: Mapped[str] = mapped_column(String(24), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    state_code: Mapped[str] = mapped_column(String(20), nullable=False)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(12), nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    services: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    timings: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    languages: Mapped[list] = mapped_column(json_type(), nullable=False, default=list)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(12), nullable=False, default="manual")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


__all__ = ["CENTER_SOURCES", "CENTER_TYPES", "ServiceCentre"]
