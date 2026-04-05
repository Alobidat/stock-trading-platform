"""
Market data service — wraps Alpaca API for price data and trading.

Handles:
- Historical OHLCV bars
- Latest quote/trade
- Paper order execution
- Account info
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from loguru import logger

from app.core.config import settings


class MarketDataService:
    """
    Provides market data and trade execution via Alpaca.
    Paper trading by default (configured via ALPACA_BASE_URL).
    """

    def __init__(self):
        self._data_client: StockHistoricalDataClient | None = None
        self._trading_client: TradingClient | None = None

    @property
    def data_client(self) -> StockHistoricalDataClient:
        if self._data_client is None:
            self._data_client = StockHistoricalDataClient(
                api_key=settings.alpaca_api_key or None,
                secret_key=settings.alpaca_secret_key or None,
            )
        return self._data_client

    @property
    def trading_client(self) -> TradingClient:
        if self._trading_client is None:
            if not settings.alpaca_api_key:
                raise ValueError("ALPACA_API_KEY is required for trading")
            self._trading_client = TradingClient(
                api_key=settings.alpaca_api_key,
                secret_key=settings.alpaca_secret_key,
                paper=True,  # Always paper unless explicitly changed
            )
        return self._trading_client

    async def get_bars(
        self,
        symbol: str,
        days: int = 60,
        timeframe: str = "1Day",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV bars for a symbol.

        Args:
            symbol: Ticker symbol (e.g. "AAPL")
            days: Number of calendar days of history
            timeframe: "1Min" | "5Min" | "1Hour" | "1Day"

        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        tf_map = {
            "1Min": TimeFrame(1, TimeFrameUnit.Minute),
            "5Min": TimeFrame(5, TimeFrameUnit.Minute),
            "15Min": TimeFrame(15, TimeFrameUnit.Minute),
            "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
            "1Day": TimeFrame(1, TimeFrameUnit.Day),
        }
        tf = tf_map.get(timeframe, TimeFrame(1, TimeFrameUnit.Day))

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start,
            end=end,
        )

        logger.debug("Fetching {days}d bars for {symbol}", days=days, symbol=symbol)
        bars = self.data_client.get_stock_bars(request)
        df = bars.df

        if df.empty:
            logger.warning("No bars returned for {symbol}", symbol=symbol)
            return pd.DataFrame()

        # Flatten multi-index if present
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level="symbol")

        df.index = pd.to_datetime(df.index)
        return df[["open", "high", "low", "close", "volume"]]

    async def get_latest_quote(self, symbol: str) -> dict:
        """Return the latest bid/ask quote for a symbol."""
        request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        quote = self.data_client.get_stock_latest_quote(request)
        q = quote[symbol]
        return {
            "symbol": symbol,
            "bid": float(q.bid_price),
            "ask": float(q.ask_price),
            "mid": float((q.bid_price + q.ask_price) / 2),
            "timestamp": q.timestamp.isoformat(),
        }

    async def get_account(self) -> dict:
        """Return current account info (cash, equity, buying power)."""
        account = self.trading_client.get_account()
        return {
            "cash": float(account.cash),
            "equity": float(account.equity),
            "buying_power": float(account.buying_power),
            "portfolio_value": float(account.portfolio_value),
            "currency": account.currency,
        }

    async def submit_market_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        reasoning: str = "",
    ) -> dict:
        """
        Submit a market order.

        Args:
            symbol: Ticker symbol
            qty: Number of shares
            side: "buy" or "sell"
            reasoning: Agent's rationale (stored for audit)

        Returns:
            Order details dict
        """
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )

        logger.info(
            "Submitting {side} order: {qty} shares of {symbol}",
            side=side,
            qty=qty,
            symbol=symbol,
        )

        order = self.trading_client.submit_order(request)

        return {
            "order_id": str(order.id),
            "symbol": order.symbol,
            "side": order.side.value,
            "qty": float(order.qty),
            "status": order.status.value,
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
        }

    async def get_positions(self) -> list[dict]:
        """Return all current open positions."""
        positions = self.trading_client.get_all_positions()
        return [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "avg_entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
                "unrealized_plpc": float(p.unrealized_plpc),
            }
            for p in positions
        ]


# Module-level singleton
market_data_service = MarketDataService()
