from fastapi import APIRouter, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import select

from app.api.deps import DbSession, OwnerId
from app.models import JobPreferences
from app.schemas.preferences import JobPreferencesData, JobPreferencesPatch, PreferencesOut

router = APIRouter(prefix="/preferences", tags=["preferences"])


def _get_preferences(db: DbSession, owner_id: str) -> JobPreferences | None:
    return db.scalar(select(JobPreferences).where(JobPreferences.owner_id == owner_id))


def _to_out(record: JobPreferences | None) -> PreferencesOut:
    if record is None:
        return PreferencesOut()
    return PreferencesOut(**record.data, updated_at=record.updated_at)


@router.get("", response_model=PreferencesOut)
def get_preferences(db: DbSession, owner_id: OwnerId) -> PreferencesOut:
    # Unset preferences are a valid state ("no restrictions"), so this never 404s.
    return _to_out(_get_preferences(db, owner_id))


@router.patch("", response_model=PreferencesOut)
def update_preferences(
    db: DbSession, owner_id: OwnerId, patch: JobPreferencesPatch
) -> PreferencesOut:
    record = _get_preferences(db, owner_id)
    current = record.data if record else JobPreferencesData().model_dump(mode="json")
    try:
        merged = JobPreferencesData.model_validate(
            {**current, **patch.model_dump(exclude_unset=True)}
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_url=False)) from exc

    if record is None:
        record = JobPreferences(owner_id=owner_id)
        db.add(record)
    record.data = merged.model_dump(mode="json")
    db.commit()
    return _to_out(record)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_preferences(db: DbSession, owner_id: OwnerId) -> None:
    record = _get_preferences(db, owner_id)
    if record is not None:
        db.delete(record)
        db.commit()
