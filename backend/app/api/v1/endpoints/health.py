"""Health check endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.llm_provider import get_llm_info
from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str
    llm_provider: str
    llm_model: str


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check — confirms API is running."""
    llm_info = get_llm_info()
    return HealthResponse(
        status="ok",
        environment=settings.app_env.value,
        version=settings.app_version,
        llm_provider=llm_info["provider"],
        llm_model=llm_info["model"],
    )
