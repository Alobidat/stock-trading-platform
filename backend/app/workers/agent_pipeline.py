"""
Agent pipeline orchestrator.

Runs the full multi-agent analysis sequence for a given symbol:
  1. Technical Analyst — price indicators
  2. News Analyst — sentiment
  3. Researcher — synthesize findings
  4. Risk Manager — validate risk limits
  5. Trader — final signal + optional execution

Each agent writes to the shared AgentContext object.
"""

import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import AgentContext
from app.core.database import AsyncSessionLocal


async def run_analysis_pipeline(
    symbol: str,
    execute_trade: bool = False,
) -> dict:
    """
    Run the full agent pipeline for a symbol.

    This function is designed to run in:
    - FastAPI BackgroundTasks (immediate)
    - Celery task queue (scheduled/repeated)

    Returns the final signal dict.
    """
    run_id = str(uuid.uuid4())
    logger.info(
        "=== Agent Pipeline START | run_id={run_id} symbol={symbol} ===",
        run_id=run_id,
        symbol=symbol,
    )

    context = AgentContext(symbol=symbol, run_id=run_id)

    async with AsyncSessionLocal() as db:
        try:
            # Import agents here — lazy loading keeps startup fast
            from app.agents.technical_analyst import TechnicalAnalystAgent
            from app.agents.news_analyst import NewsAnalystAgent
            from app.agents.researcher import ResearcherAgent
            from app.agents.risk_manager import RiskManagerAgent
            from app.agents.trader import TraderAgent

            # Sequential pipeline — each agent enriches the context
            agents = [
                TechnicalAnalystAgent(),
                NewsAnalystAgent(),
                ResearcherAgent(),
                RiskManagerAgent(),
                TraderAgent(),
            ]

            for agent in agents:
                context = await agent.run(context, db)

            await db.commit()

            logger.info(
                "=== Agent Pipeline COMPLETE | run_id={run_id} signal={signal} ===",
                run_id=run_id,
                signal=context.final_signal,
            )

            # Optionally execute the trade
            if execute_trade and context.final_signal.get("action") in ("buy", "sell"):
                await _execute_signal(context, db)

            return context.final_signal

        except Exception as exc:
            await db.rollback()
            logger.error(
                "=== Agent Pipeline FAILED | run_id={run_id} error={error} ===",
                run_id=run_id,
                error=str(exc),
            )
            raise


async def _execute_signal(context: AgentContext, db: AsyncSession) -> None:
    """Submit a trade order based on the final agent signal."""
    from app.services.market_data import market_data_service
    from app.models.trade import Trade, TradeSide, TradeStatus
    from app.models.signal import Signal, SignalAction, SignalStrength
    from decimal import Decimal

    signal_data = context.final_signal
    action = signal_data.get("action", "hold")

    if action == "hold":
        logger.info("Signal is HOLD — no trade submitted")
        return

    # Save signal to DB
    signal = Signal(
        symbol=context.symbol,
        action=SignalAction(action),
        strength=SignalStrength(signal_data.get("strength", "moderate")),
        confidence=Decimal(str(signal_data.get("confidence", 0.5))),
        reasoning=signal_data.get("reasoning", ""),
        agent_analysis=context.to_dict(),
    )
    db.add(signal)
    await db.flush()

    # Submit order
    qty = signal_data.get("quantity", 1)
    order = await market_data_service.submit_market_order(
        symbol=context.symbol,
        qty=qty,
        side=action,
        reasoning=signal_data.get("reasoning", ""),
    )

    # Record trade
    trade = Trade(
        symbol=context.symbol,
        side=TradeSide(action),
        quantity=Decimal(str(qty)),
        status=TradeStatus.SUBMITTED,
        broker_order_id=order["order_id"],
        signal_id=signal.id,
        reasoning=signal_data.get("reasoning", ""),
    )
    db.add(trade)
    signal.executed = True
    await db.flush()

    logger.info(
        "Trade submitted: {side} {qty} {symbol} | order_id={order_id}",
        side=action,
        qty=qty,
        symbol=context.symbol,
        order_id=order["order_id"],
    )
