"""Portfolio endpoints — account summary, positions, trade history."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.market_data import market_data_service

router = APIRouter()


class AccountSummary(BaseModel):
    cash: float
    equity: float
    buying_power: float
    portfolio_value: float
    currency: str


class PositionResponse(BaseModel):
    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pl: float
    unrealized_plpc: float


@router.get("/account", response_model=AccountSummary)
async def get_account() -> AccountSummary:
    """Return Alpaca paper trading account summary."""
    try:
        account = await market_data_service.get_account()
        return AccountSummary(**account)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch account: {exc}") from exc


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions() -> list[PositionResponse]:
    """Return all open positions."""
    try:
        positions = await market_data_service.get_positions()
        return [PositionResponse(**p) for p in positions]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch positions: {exc}") from exc
