"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.middleware.request_id import RequestContextMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    if settings.debug:
        from app.db.seeds import (
            seed_document_types,
            seed_reference_data,
            seed_schemes,
            seed_service_centres,
        )
        from app.db.session import get_session_factory, init_database

        await init_database()
        # Bootstrap the catalog so search/filter/bookmark flows work in dev/tests.
        async with get_session_factory()() as session:
            await seed_reference_data(session)
            await seed_schemes(session)
            await seed_document_types(session)
            await seed_service_centres(session)
    logger.info("startup_complete", app=settings.app_name, version=settings.version)
    yield
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="CiviServe API",
        description=(
            "Backend for the Multilingual Citizen Service Chatbot for Government "
            "Schemes (HackElite 2026)."
        ),
        version=settings.version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
