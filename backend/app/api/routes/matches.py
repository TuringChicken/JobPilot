from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import DbSession, OwnerId, get_match_evaluator
from app.models import CandidateProfile, Job, JobPreferences, MatchResult
from app.schemas.jobs import (
    JobOut,
    JobPostingData,
    MatchOut,
    MatchPatch,
    MatchReport,
    MatchSummary,
    ReanalyzeRequest,
)
from app.schemas.preferences import JobPreferencesData
from app.schemas.profile import CandidateProfileData
from app.services.llm import LLMError
from app.services.match_evaluator import MatchEvaluator
from app.services.matching import build_report

router = APIRouter(prefix="/matches", tags=["matches"])


def load_candidate(db: DbSession, owner_id: str) -> tuple[CandidateProfile, JobPreferencesData]:
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.owner_id == owner_id))
    if profile is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Upload a resume before analyzing jobs.")
    prefs_record = db.scalar(select(JobPreferences).where(JobPreferences.owner_id == owner_id))
    prefs = JobPreferencesData(**prefs_record.data) if prefs_record else JobPreferencesData()
    return profile, prefs


def evaluate_and_store(
    db: DbSession,
    owner_id: str,
    evaluator: MatchEvaluator,
    profile: CandidateProfile,
    prefs: JobPreferencesData,
    job: Job,
    job_text: str,
    truncated: bool,
    language: str,
) -> MatchResult:
    """One LLM call (S/E/R), then the deterministic report; saved as a new match."""
    job_data = JobPostingData(**job.data)
    profile_data = CandidateProfileData(**profile.data)
    try:
        evaluation = evaluator.evaluate(profile_data, prefs, job_data, job_text, language)
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Match evaluation failed: {exc}") from exc

    report = build_report(
        profile_data, profile.confirmed, prefs, job_data, job_text, truncated, evaluation
    )
    match = MatchResult(
        owner_id=owner_id,
        job=job,
        overall_score=report.overall_score,
        hard_filter_status=report.hard_filter.status,
        report=report.model_dump(mode="json"),
    )
    db.add(match)
    db.commit()
    return match


def to_match_out(match: MatchResult) -> MatchOut:
    return MatchOut(
        id=match.id,
        job=JobOut.model_validate(match.job),
        report=MatchReport(**match.report),
        saved=match.saved,
        created_at=match.created_at,
    )


@router.get("", response_model=list[MatchSummary])
def list_matches(
    db: DbSession,
    owner_id: OwnerId,
    limit: int = Query(default=20, ge=1, le=100),
    saved: bool | None = Query(default=None, description="Only saved (true) or unsaved (false)"),
) -> list[MatchSummary]:
    query = select(MatchResult).where(MatchResult.owner_id == owner_id)
    if saved is not None:
        query = query.where(MatchResult.saved == saved)
    matches = db.scalars(
        query.order_by(MatchResult.created_at.desc(), MatchResult.id.desc()).limit(limit)
    )
    return [
        MatchSummary(
            id=m.id,
            job_id=m.job_id,
            title=m.job.data.get("title"),
            company=m.job.data.get("company"),
            url=m.job.url,
            overall_score=m.overall_score,
            hard_filter_status=m.hard_filter_status,
            saved=m.saved,
            created_at=m.created_at,
        )
        for m in matches
    ]


def _get_own_match(db: DbSession, owner_id: str, match_id: int) -> MatchResult:
    match = db.get(MatchResult, match_id)
    # Same 404 for "missing" and "someone else's", so ids can't be probed.
    if match is None or match.owner_id != owner_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found.")
    return match


@router.get("/{match_id}", response_model=MatchOut)
def get_match(match_id: int, db: DbSession, owner_id: OwnerId) -> MatchOut:
    return to_match_out(_get_own_match(db, owner_id, match_id))


@router.post("/{match_id}/reanalyze", response_model=MatchOut)
def reanalyze_match(
    match_id: int,
    request: ReanalyzeRequest,
    db: DbSession,
    owner_id: OwnerId,
    evaluator: Annotated[MatchEvaluator, Depends(get_match_evaluator)],
) -> MatchOut:
    """Evaluate the same job again with the current CV/preferences, without the job page.

    Reuses the stored text and extraction, so only the evaluation calls the LLM. The old
    report is kept; the new one is a separate match.
    """
    previous = _get_own_match(db, owner_id, match_id)
    profile, prefs = load_candidate(db, owner_id)
    job = previous.job
    truncated = MatchReport(**previous.report).job_text_truncated
    match = evaluate_and_store(
        db, owner_id, evaluator, profile, prefs, job, job.raw_text, truncated, request.language
    )
    return to_match_out(match)


@router.patch("/{match_id}", response_model=MatchOut)
def update_match(match_id: int, patch: MatchPatch, db: DbSession, owner_id: OwnerId) -> MatchOut:
    match = _get_own_match(db, owner_id, match_id)
    match.saved = patch.saved
    db.commit()
    return to_match_out(match)


@router.delete("/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(match_id: int, db: DbSession, owner_id: OwnerId) -> None:
    db.delete(_get_own_match(db, owner_id, match_id))
    db.commit()
