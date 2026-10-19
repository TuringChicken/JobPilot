from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import DbSession, OwnerId
from app.models import MatchResult
from app.schemas.jobs import JobOut, MatchOut, MatchPatch, MatchReport, MatchSummary

router = APIRouter(prefix="/matches", tags=["matches"])


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
