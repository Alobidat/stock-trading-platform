"""
Stock Trading Platform — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.core.database import create_tables
from app.core.logging import configure_logging
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    configure_logging()
    logger.info("Starting {name} v{version}", name=settings.app_name, version=settings.app_version)
    logger.info("Environment: {env}", env=settings.app_env.value)
    logger.info("LLM Provider: {provider}", provider=settings.llm_provider.value)

    # Create DB tables (dev only — prod uses Alembic migrations)
    if not settings.is_production:
        await create_tables()
        logger.info("Database tables ensured")

    yield

    logger.info("Shutting down...")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI Agent Stock Trading Platform — multi-agent LLM system for market analysis and automated trading",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API router
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
