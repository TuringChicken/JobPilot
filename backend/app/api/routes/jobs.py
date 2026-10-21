from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, OwnerId, get_job_parser, get_match_evaluator
from app.api.routes.matches import evaluate_and_store, load_candidate, to_match_out
from app.models import Job
from app.schemas.jobs import AnalyzeJobRequest, MatchOut
from app.services.job_parser import (
    MIN_JOB_TEXT_CHARS,
    JobParser,
    fingerprint,
    prepare_job_text,
)
from app.services.llm import LLMError
from app.services.match_evaluator import MatchEvaluator

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/analyze", response_model=MatchOut)
def analyze_job(
    request: AnalyzeJobRequest,
    db: DbSession,
    owner_id: OwnerId,
    job_parser: Annotated[JobParser, Depends(get_job_parser)],
    evaluator: Annotated[MatchEvaluator, Depends(get_match_evaluator)],
) -> MatchOut:
    profile, prefs = load_candidate(db, owner_id)

    job_text, truncated = prepare_job_text(request.text)
    if len(job_text) < MIN_JOB_TEXT_CHARS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Not enough text on the page to analyze."
        )

    job = _get_or_create_job(db, job_parser, job_text, request)
    match = evaluate_and_store(
        db, owner_id, evaluator, profile, prefs, job, job_text, truncated, request.language
    )
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
