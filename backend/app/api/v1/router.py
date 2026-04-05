"""API v1 router — aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, portfolio, signals, agents

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(signals.router, prefix="/signals", tags=["signals"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
