from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, OwnerId, get_job_parser, get_match_evaluator
from app.api.routes.matches import to_match_out
from app.models import CandidateProfile, Job, JobPreferences, MatchResult
from app.schemas.jobs import AnalyzeJobRequest, JobPostingData, MatchOut
from app.schemas.preferences import JobPreferencesData
from app.schemas.profile import CandidateProfileData
from app.services.job_parser import (
    MIN_JOB_TEXT_CHARS,
    JobParser,
    fingerprint,
    prepare_job_text,
)
from app.services.llm import LLMError
from app.services.match_evaluator import MatchEvaluator
from app.services.matching import build_report

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/analyze", response_model=MatchOut)
def analyze_job(
    request: AnalyzeJobRequest,
    db: DbSession,
    owner_id: OwnerId,
    job_parser: Annotated[JobParser, Depends(get_job_parser)],
    evaluator: Annotated[MatchEvaluator, Depends(get_match_evaluator)],
) -> MatchOut:
    profile = db.scalar(select(CandidateProfile).where(CandidateProfile.owner_id == owner_id))
    if profile is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Upload a resume before analyzing jobs.")
    prefs_record = db.scalar(select(JobPreferences).where(JobPreferences.owner_id == owner_id))
    prefs = JobPreferencesData(**prefs_record.data) if prefs_record else JobPreferencesData()

    job_text, truncated = prepare_job_text(request.text)
    if len(job_text) < MIN_JOB_TEXT_CHARS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Not enough text on the page to analyze."
        )

    job = _get_or_create_job(db, job_parser, job_text, request)
    job_data = JobPostingData(**job.data)
    profile_data = CandidateProfileData(**profile.data)

    try:
        evaluation = evaluator.evaluate(profile_data, prefs, job_data, job_text)
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
    return to_match_out(match)


def _get_or_create_job(
    db: DbSession, job_parser: JobParser, job_text: str, request: AnalyzeJobRequest
) -> Job:
    key = fingerprint(job_text)
    job = db.scalar(select(Job).where(Job.fingerprint == key))
    if job is not None:
        return job  # Same posting seen before: reuse the extraction, skip an LLM call.

    try:
        data = job_parser.parse(job_text)
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Job parsing failed: {exc}") from exc
    if not data.is_job_posting:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "This page doesn't look like a job posting."
        )

    job = Job(
        fingerprint=key,
        url=request.url,
        page_title=request.page_title,
        raw_text=job_text,
        data=data.model_dump(mode="json"),
    )
    db.add(job)
    db.flush()
    return job
