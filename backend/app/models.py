from datetime import UTC, datetime

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    resume_filename: Mapped[str] = mapped_column(String(255))
    # Kept so later match reports can quote CV evidence; deleted together with the profile.
    resume_text: Mapped[str] = mapped_column(Text)
    # Validated by app.schemas.profile.CandidateProfileData before every write.
    data: Mapped[dict] = mapped_column(JSON)
    confirmed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow, onupdate=_utcnow)


class JobPreferences(Base):
    """Stored separately from the CV: preferences are wishes, the profile is facts."""

    __tablename__ = "job_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Validated by app.schemas.preferences.JobPreferencesData before every write.
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow, onupdate=_utcnow)
