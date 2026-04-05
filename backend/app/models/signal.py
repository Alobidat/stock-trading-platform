"""Signal model — AI agent trading signals before execution."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SignalAction(str, PyEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class SignalStrength(str, PyEnum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class Signal(Base):
    """
    A trading signal produced by the AI agent pipeline.
    Multiple agents contribute analysis; the final Trader agent produces the signal.
    """
    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    action: Mapped[SignalAction] = mapped_column(Enum(SignalAction), nullable=False)
    strength: Mapped[SignalStrength] = mapped_column(Enum(SignalStrength), default=SignalStrength.MODERATE)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0"))  # 0.0 - 1.0

    # Price context at signal generation time
    price_at_signal: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    # Agent analysis breakdown (JSON blob of each agent's output)
    agent_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Was this signal acted upon?
    executed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="signal")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Signal {self.action.value} {self.symbol} confidence={self.confidence}>"
