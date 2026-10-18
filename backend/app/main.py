from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_owner_id
from app.api.routes import health, jobs, matches, preferences, profile
from app.config import Settings, get_settings
from app.db import make_engine, make_session_factory
from app.services.job_parser import LLMJobParser
from app.services.llm import build_llm
from app.services.match_evaluator import LLMMatchEvaluator
from app.services.resume_parser import LLMResumeParser


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(title="JobPilot API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    llm = build_llm(settings)
    app.state.resume_parser = LLMResumeParser(llm) if llm else None
    app.state.job_parser = LLMJobParser(llm) if llm else None
    app.state.match_evaluator = LLMMatchEvaluator(llm) if llm else None

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["X-API-Key", "Content-Type"],
        )

    app.include_router(health.router, prefix="/api")
    for router in (profile.router, preferences.router, jobs.router, matches.router):
        app.include_router(router, prefix="/api", dependencies=[Depends(get_owner_id)])
    return app
