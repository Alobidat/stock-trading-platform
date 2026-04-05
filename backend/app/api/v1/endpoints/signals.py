"""Signal endpoints — view and trigger AI trading signals."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.signal import Signal

router = APIRouter()


class SignalResponse(BaseModel):
    id: UUID
    symbol: str
    action: str
    strength: str
    confidence: float
    price_at_signal: float | None
    target_price: float | None
    stop_loss: float | None
    reasoning: str | None
    executed: bool
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[SignalResponse])
async def list_signals(
    symbol: str | None = Query(None, description="Filter by ticker symbol"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[SignalResponse]:
    """List recent trading signals, optionally filtered by symbol."""
    query = select(Signal).order_by(desc(Signal.created_at)).limit(limit)
    if symbol:
        query = query.where(Signal.symbol == symbol.upper())

    result = await db.execute(query)
    signals = result.scalars().all()

    return [
        SignalResponse(
            id=s.id,
            symbol=s.symbol,
            action=s.action.value,
            strength=s.strength.value,
            confidence=float(s.confidence),
            price_at_signal=float(s.price_at_signal) if s.price_at_signal else None,
            target_price=float(s.target_price) if s.target_price else None,
            stop_loss=float(s.stop_loss) if s.stop_loss else None,
            reasoning=s.reasoning,
            executed=s.executed,
            created_at=s.created_at.isoformat(),
        )
        for s in signals
    ]


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SignalResponse:
    """Get a single signal by ID."""
    result = await db.execute(select(Signal).where(Signal.id == signal_id))
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    return SignalResponse(
        id=signal.id,
        symbol=signal.symbol,
        action=signal.action.value,
        strength=signal.strength.value,
        confidence=float(signal.confidence),
        price_at_signal=float(signal.price_at_signal) if signal.price_at_signal else None,
        target_price=float(signal.target_price) if signal.target_price else None,
        stop_loss=float(signal.stop_loss) if signal.stop_loss else None,
        reasoning=signal.reasoning,
        executed=signal.executed,
        created_at=signal.created_at.isoformat(),
    )
