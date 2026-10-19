from datetime import UTC, datetime

from sqlalchemy import JSON, ForeignKey, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class Job(Base):
    """A job posting, shared across users. Deduplicated by a fingerprint of its text."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    url: Mapped[str | None] = mapped_column(String(2048))
    page_title: Mapped[str | None] = mapped_column(String(500))
    raw_text: Mapped[str] = mapped_column(Text)
    # Validated by app.schemas.jobs.JobPostingData before every write.
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow)


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    overall_score: Mapped[int]
    hard_filter_status: Mapped[str] = mapped_column(String(20))
    # Validated by app.schemas.jobs.MatchReport. Contains CV-derived quotes, so it is
    # deleted together with the candidate profile.
    report: Mapped[dict] = mapped_column(JSON)
    # Every analysis is kept (so a closed side panel can still find it); saved ones are the
    # user's picks, listed separately.
    saved: Mapped[bool] = mapped_column(default=False, server_default=false(), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow, index=True)

    job: Mapped[Job] = relationship()
