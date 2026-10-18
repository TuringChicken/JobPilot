from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

from app.api.deps import get_owner_id
from app.api.routes import health, profile
from app.config import Settings, get_settings
from app.db import make_engine, make_session_factory
from app.services.resume_parser import AzureOpenAIResumeParser


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
    app.state.resume_parser = (
        AzureOpenAIResumeParser(
            OpenAI(
                base_url=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key.get_secret_value(),
            ),
            settings.azure_openai_chat_deployment,
        )
        if settings.llm_configured
        else None
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["X-API-Key", "Content-Type"],
        )

    app.include_router(health.router, prefix="/api")
    app.include_router(profile.router, prefix="/api", dependencies=[Depends(get_owner_id)])
    return app
