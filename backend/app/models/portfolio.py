"""Portfolio and Position models."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Main Portfolio")
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("100000.00"))
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("100000.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="portfolios")  # noqa: F821
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")
    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="portfolio")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Portfolio id={self.id} name={self.name} value={self.total_value}>"


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    avg_entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    current_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    unrealized_pnl_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")

    def __repr__(self) -> str:
        return f"<Position symbol={self.symbol} qty={self.quantity} pnl={self.unrealized_pnl}>"
