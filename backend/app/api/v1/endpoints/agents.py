"""Agent endpoints — trigger analysis runs and view agent logs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agent_log import AgentLog
from app.agents.llm_provider import get_llm_info

router = APIRouter()


class AgentLogResponse(BaseModel):
    id: UUID
    agent_name: str
    symbol: str | None
    status: str
    llm_provider: str | None
    llm_model: str | None
    duration_seconds: float | None
    error_message: str | None
    started_at: str
    completed_at: str | None

    model_config = {"from_attributes": True}


class AnalysisRequest(BaseModel):
    symbol: str
    execute_trade: bool = False  # If True, Trader agent will submit order


class AnalysisResponse(BaseModel):
    run_id: str
    symbol: str
    status: str
    message: str


@router.get("/logs", response_model=list[AgentLogResponse])
async def list_agent_logs(
    symbol: str | None = Query(None),
    agent_name: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[AgentLogResponse]:
    """List agent execution logs."""
    query = select(AgentLog).order_by(desc(AgentLog.started_at)).limit(limit)
    if symbol:
        query = query.where(AgentLog.symbol == symbol.upper())
    if agent_name:
        query = query.where(AgentLog.agent_name == agent_name)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        AgentLogResponse(
            id=log.id,
            agent_name=log.agent_name.value,
            symbol=log.symbol,
            status=log.status.value,
            llm_provider=log.llm_provider,
            llm_model=log.llm_model,
            duration_seconds=log.duration_seconds,
            error_message=log.error_message,
            started_at=log.started_at.isoformat(),
            completed_at=log.completed_at.isoformat() if log.completed_at else None,
        )
        for log in logs
    ]


@router.post("/analyze", response_model=AnalysisResponse)
async def trigger_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """
    Trigger a full agent pipeline analysis for a given symbol.
    Runs asynchronously — check /agents/logs for results.
    """
    symbol = request.symbol.upper()

    # Import here to avoid circular deps at module load time
    from app.workers.agent_pipeline import run_analysis_pipeline

    background_tasks.add_task(
        run_analysis_pipeline,
        symbol=symbol,
        execute_trade=request.execute_trade,
    )

    return AnalysisResponse(
        run_id="queued",
        symbol=symbol,
        status="queued",
        message=f"Analysis pipeline started for {symbol}. Check /api/v1/agents/logs for results.",
    )


@router.get("/llm-info")
async def get_llm_status() -> dict:
    """Return the currently configured LLM provider and model."""
    return get_llm_info()
