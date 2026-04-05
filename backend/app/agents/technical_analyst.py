"""
Technical Analyst Agent

Computes technical indicators from price data and generates a structured
technical analysis summary for the researcher agent.

Indicators computed:
- RSI (14-period)
- MACD (12/26/9)
- Bollinger Bands (20-period, 2σ)
- EMA (20, 50, 200)
- Volume trend
"""

import json

import pandas as pd
import ta
from loguru import logger

from app.agents.base_agent import AgentContext, BaseAgent
from app.models.agent_log import AgentName
from app.services.market_data import market_data_service


class TechnicalAnalystAgent(BaseAgent):
    agent_name = AgentName.TECHNICAL_ANALYST

    system_prompt = """You are an expert technical analyst for a quantitative trading firm.
You receive OHLCV price data and computed technical indicators for a stock.
Your job is to interpret the indicators and produce a concise, structured analysis.

Output format (JSON):
{
  "trend": "bullish" | "bearish" | "neutral",
  "momentum": "strong" | "moderate" | "weak",
  "key_signals": ["list of key observations"],
  "support_level": <price>,
  "resistance_level": <price>,
  "summary": "2-3 sentence narrative"
}

Be precise. Focus on what the data actually shows, not what you hope for."""

    async def analyze(self, context: AgentContext) -> AgentContext:
        """Fetch price data, compute indicators, invoke LLM for interpretation."""

        # --- Fetch price data ---
        df = await market_data_service.get_bars(context.symbol, days=90)

        if df.empty:
            logger.warning("[TechnicalAnalyst] No price data for {symbol}", symbol=context.symbol)
            context.technical_analysis = {"error": "No price data available"}
            return context

        # --- Compute indicators using ta library ---
        indicators = self._compute_indicators(df)

        # --- Store raw price context ---
        context.price_data = {
            "symbol": context.symbol,
            "latest_close": float(df["close"].iloc[-1]),
            "period_high": float(df["high"].max()),
            "period_low": float(df["low"].min()),
            "bars_analyzed": len(df),
        }

        # --- Ask LLM to interpret indicators ---
        prompt = f"""
Analyze the following technical indicators for {context.symbol}:

Latest Price: ${indicators['latest_close']:.2f}
Period: {indicators['bars_analyzed']} trading days

RSI (14): {indicators.get('rsi', 'N/A')}
MACD: {indicators.get('macd', 'N/A')} | Signal: {indicators.get('macd_signal', 'N/A')} | Histogram: {indicators.get('macd_hist', 'N/A')}
EMA 20: {indicators.get('ema_20', 'N/A')}
EMA 50: {indicators.get('ema_50', 'N/A')}
EMA 200: {indicators.get('ema_200', 'N/A')}
Bollinger Upper: {indicators.get('bb_upper', 'N/A')}
Bollinger Middle: {indicators.get('bb_mid', 'N/A')}
Bollinger Lower: {indicators.get('bb_lower', 'N/A')}
Volume (latest vs 20d avg): {indicators.get('volume_ratio', 'N/A')}x

Price vs EMA20: {'ABOVE' if indicators['latest_close'] > indicators.get('ema_20', 0) else 'BELOW'}
Price vs EMA50: {'ABOVE' if indicators['latest_close'] > indicators.get('ema_50', 0) else 'BELOW'}
Price vs EMA200: {'ABOVE' if indicators['latest_close'] > indicators.get('ema_200', 0) else 'BELOW'}

Provide your technical analysis in the specified JSON format.
"""

        response_text = await self.invoke_llm(prompt)

        # Parse JSON response
        try:
            # Extract JSON from response (LLM may wrap it in markdown)
            json_str = response_text
            if "```" in response_text:
                json_str = response_text.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            analysis = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("[TechnicalAnalyst] Could not parse JSON response, using raw text")
            analysis = {"raw_response": response_text, "indicators": indicators}

        context.technical_analysis = {**indicators, **analysis}
        return context

    def _compute_indicators(self, df: pd.DataFrame) -> dict:
        """Compute all technical indicators from a price DataFrame."""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        result = {
            "latest_close": round(float(close.iloc[-1]), 4),
            "bars_analyzed": len(df),
        }

        # RSI
        try:
            rsi = ta.momentum.RSIIndicator(close=close, window=14)
            result["rsi"] = round(float(rsi.rsi().iloc[-1]), 2)
        except Exception:
            result["rsi"] = None

        # MACD
        try:
            macd = ta.trend.MACD(close=close)
            result["macd"] = round(float(macd.macd().iloc[-1]), 4)
            result["macd_signal"] = round(float(macd.macd_signal().iloc[-1]), 4)
            result["macd_hist"] = round(float(macd.macd_diff().iloc[-1]), 4)
        except Exception:
            result["macd"] = result["macd_signal"] = result["macd_hist"] = None

        # EMAs
        for period in [20, 50, 200]:
            try:
                ema = ta.trend.EMAIndicator(close=close, window=period)
                result[f"ema_{period}"] = round(float(ema.ema_indicator().iloc[-1]), 4)
            except Exception:
                result[f"ema_{period}"] = None

        # Bollinger Bands
        try:
            bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
            result["bb_upper"] = round(float(bb.bollinger_hband().iloc[-1]), 4)
            result["bb_mid"] = round(float(bb.bollinger_mavg().iloc[-1]), 4)
            result["bb_lower"] = round(float(bb.bollinger_lband().iloc[-1]), 4)
        except Exception:
            result["bb_upper"] = result["bb_mid"] = result["bb_lower"] = None

        # Volume ratio (latest vs 20-day average)
        try:
            avg_vol = float(volume.rolling(20).mean().iloc[-1])
            latest_vol = float(volume.iloc[-1])
            result["volume_ratio"] = round(latest_vol / avg_vol, 2) if avg_vol > 0 else None
        except Exception:
            result["volume_ratio"] = None

        return result
