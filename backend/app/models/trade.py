"""Trade model — records every order/execution."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TradeSide(str, PyEnum):
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, PyEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    signal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("signals.id"), nullable=True)

    # Order details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    side: Mapped[TradeSide] = mapped_column(Enum(TradeSide), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    order_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)  # None = market order
    filled_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    status: Mapped[TradeStatus] = mapped_column(Enum(TradeStatus), default=TradeStatus.PENDING)

    # Broker reference
    broker_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Audit
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)  # Agent's rationale
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="trades")  # noqa: F821
    signal: Mapped["Signal | None"] = relationship("Signal", back_populates="trades")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Trade {self.side.value} {self.quantity} {self.symbol} @ {self.filled_price} [{self.status.value}]>"
