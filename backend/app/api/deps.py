import secrets
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.config import Settings
from app.services.resume_parser import ResumeParser

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Single-user MVP: every valid key maps to this owner. Replace with real auth later.
LOCAL_OWNER_ID = "local"


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def get_owner_id(
    settings: Annotated[Settings, Depends(get_settings_dep)],
    api_key: Annotated[str | None, Security(_api_key_header)],
) -> str:
    expected = settings.api_key.get_secret_value()
    if api_key is None or not secrets.compare_digest(api_key, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key.")
    return LOCAL_OWNER_ID


def get_resume_parser(request: Request) -> ResumeParser:
    parser = request.app.state.resume_parser
    if parser is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "LLM is not configured.")
    return parser


DbSession = Annotated[Session, Depends(get_db)]
OwnerId = Annotated[str, Depends(get_owner_id)]
