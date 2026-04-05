"""
Base agent class — all specialized agents inherit from this.

Provides:
- Standardized run() interface
- Automatic logging to AgentLog table
- Error handling and timing
- LLM invocation via configured provider
"""

import time
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm_provider import get_llm, get_llm_info
from app.models.agent_log import AgentLog, AgentName, AgentRunStatus


class AgentContext:
    """
    Shared context object passed between agents in a pipeline run.
    Agents read from and write to this object.
    """

    def __init__(self, symbol: str, run_id: str | None = None):
        self.symbol = symbol
        self.run_id = run_id or str(uuid.uuid4())
        self.price_data: dict = {}
        self.technical_analysis: dict = {}
        self.news_analysis: dict = {}
        self.fundamentals: dict = {}
        self.research_summary: str = ""
        self.risk_assessment: dict = {}
        self.final_signal: dict = {}

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "run_id": self.run_id,
            "price_data": self.price_data,
            "technical_analysis": self.technical_analysis,
            "news_analysis": self.news_analysis,
            "fundamentals": self.fundamentals,
            "research_summary": self.research_summary,
            "risk_assessment": self.risk_assessment,
            "final_signal": self.final_signal,
        }


class BaseAgent(ABC):
    """
    Abstract base for all trading agents.

    Subclasses must implement:
    - agent_name: AgentName enum value
    - system_prompt: str — the agent's role/instructions
    - analyze(context): the core analysis logic
    """

    agent_name: AgentName
    system_prompt: str

    def __init__(self):
        self.llm = get_llm()
        self.llm_info = get_llm_info()

    async def run(
        self,
        context: AgentContext,
        db: AsyncSession,
    ) -> AgentContext:
        """
        Execute this agent. Handles logging, timing, and error capture.
        Returns the updated context.
        """
        log = AgentLog(
            agent_name=self.agent_name,
            symbol=context.symbol,
            status=AgentRunStatus.RUNNING,
            llm_provider=self.llm_info["provider"],
            llm_model=self.llm_info["model"],
            input_data=context.to_dict(),
        )
        db.add(log)
        await db.flush()

        start_time = time.monotonic()

        try:
            logger.info(
                "[{agent}] Starting analysis for {symbol}",
                agent=self.agent_name.value,
                symbol=context.symbol,
            )

            updated_context = await self.analyze(context)

            duration = time.monotonic() - start_time

            log.status = AgentRunStatus.SUCCESS
            log.output_data = updated_context.to_dict()
            log.duration_seconds = round(duration, 3)
            log.completed_at = datetime.now(UTC)

            logger.info(
                "[{agent}] Completed in {duration:.2f}s",
                agent=self.agent_name.value,
                duration=duration,
            )

            return updated_context

        except Exception as exc:
            duration = time.monotonic() - start_time
            log.status = AgentRunStatus.FAILED
            log.error_message = str(exc)
            log.duration_seconds = round(duration, 3)
            log.completed_at = datetime.now(UTC)

            logger.error(
                "[{agent}] Failed after {duration:.2f}s: {error}",
                agent=self.agent_name.value,
                duration=duration,
                error=str(exc),
            )
            raise

    @abstractmethod
    async def analyze(self, context: AgentContext) -> AgentContext:
        """
        Perform this agent's analysis.
        Read from context, write results back to context, return it.
        """
        ...

    async def invoke_llm(self, user_prompt: str) -> str:
        """
        Send a prompt to the configured LLM and return the text response.
        Uses this agent's system_prompt for role context.
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = await self.llm.ainvoke(messages)
        return response.content
