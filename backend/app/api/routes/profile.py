from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, select

from app.api.deps import DbSession, OwnerId, get_resume_parser, get_settings_dep
from app.config import Settings
from app.models import CandidateProfile, MatchResult
from app.schemas.profile import ProfileOut, ProfilePatch
from app.services.llm import LLMError
from app.services.resume_parser import ResumeParser
from app.services.resume_text import (
    ResumeExtractionError,
    UnsupportedResumeType,
    extract_resume_text,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def _get_profile(db: DbSession, owner_id: str) -> CandidateProfile | None:
    return db.scalar(select(CandidateProfile).where(CandidateProfile.owner_id == owner_id))


@router.post("/resume", response_model=ProfileOut)
def upload_resume(
    db: DbSession,
    owner_id: OwnerId,
    settings: Annotated[Settings, Depends(get_settings_dep)],
    parser: Annotated[ResumeParser, Depends(get_resume_parser)],
    file: UploadFile = File(...),
) -> CandidateProfile:
    # Read one byte past the limit to detect oversize uploads without loading them fully.
    content = file.file.read(settings.max_resume_bytes + 1)
    if len(content) > settings.max_resume_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Resume file is too large.")

    try:
        text = extract_resume_text(file.filename or "", content)
    except UnsupportedResumeType as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc
    except ResumeExtractionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    try:
        data = parser.parse(text)
    except LLMError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Resume parsing failed: {exc}") from exc

    profile = _get_profile(db, owner_id)
    if profile is None:
        profile = CandidateProfile(owner_id=owner_id)
        db.add(profile)
    profile.resume_filename = file.filename or "resume"
    profile.resume_text = text
    profile.data = data.model_dump(mode="json")
    # A freshly parsed resume must be reviewed by the user before it is trusted.
    profile.confirmed = False
    db.commit()
    return profile


@router.get("", response_model=ProfileOut)
def get_profile(db: DbSession, owner_id: OwnerId) -> CandidateProfile:
    profile = _get_profile(db, owner_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile yet. Upload a resume first.")
    return profile


@router.patch("", response_model=ProfileOut)
def update_profile(db: DbSession, owner_id: OwnerId, patch: ProfilePatch) -> CandidateProfile:
    profile = _get_profile(db, owner_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No profile yet. Upload a resume first.")
    if patch.data is not None:
        profile.data = patch.data.model_dump(mode="json")
    if patch.confirmed is not None:
        profile.confirmed = patch.confirmed
    db.commit()
    return profile


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(db: DbSession, owner_id: OwnerId) -> None:
    profile = _get_profile(db, owner_id)
    if profile is not None:
        db.delete(profile)
    # Match reports quote the CV, so they go with it.
    db.execute(delete(MatchResult).where(MatchResult.owner_id == owner_id))
    db.commit()
