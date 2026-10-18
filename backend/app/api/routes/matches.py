from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import DbSession, OwnerId
from app.models import MatchResult
from app.schemas.jobs import JobOut, MatchOut, MatchReport, MatchSummary

router = APIRouter(prefix="/matches", tags=["matches"])


def to_match_out(match: MatchResult) -> MatchOut:
    return MatchOut(
        id=match.id,
        job=JobOut.model_validate(match.job),
        report=MatchReport(**match.report),
        created_at=match.created_at,
    )


@router.get("", response_model=list[MatchSummary])
def list_matches(
    db: DbSession, owner_id: OwnerId, limit: int = Query(default=20, ge=1, le=100)
) -> list[MatchSummary]:
    matches = db.scalars(
        select(MatchResult)
        .where(MatchResult.owner_id == owner_id)
        .order_by(MatchResult.created_at.desc(), MatchResult.id.desc())
        .limit(limit)
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
            created_at=m.created_at,
        )
        for m in matches
    ]


@router.get("/{match_id}", response_model=MatchOut)
def get_match(match_id: int, db: DbSession, owner_id: OwnerId) -> MatchOut:
    match = db.get(MatchResult, match_id)
    # Same 404 for "missing" and "someone else's", so ids can't be probed.
    if match is None or match.owner_id != owner_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found.")
    return to_match_out(match)
