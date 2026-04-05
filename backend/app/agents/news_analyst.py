"""
News Analyst Agent

Fetches recent news headlines for a symbol via Finnhub and uses the LLM
to score sentiment and extract key market-moving themes.
"""

import json
from datetime import UTC, datetime, timedelta

import httpx
from loguru import logger

from app.agents.base_agent import AgentContext, BaseAgent
from app.core.config import settings
from app.models.agent_log import AgentName


class NewsAnalystAgent(BaseAgent):
    agent_name = AgentName.NEWS_ANALYST

    system_prompt = """You are a financial news analyst specializing in market sentiment.
You receive recent news headlines and summaries for a stock.
Your job is to assess market sentiment and identify key themes.

Output format (JSON):
{
  "sentiment": "bullish" | "bearish" | "neutral",
  "sentiment_score": <float -1.0 to 1.0>,
  "key_themes": ["list of main themes"],
  "risk_events": ["list of risk factors mentioned"],
  "catalyst": "describe any near-term catalyst if present, else null",
  "summary": "2-3 sentence narrative"
}

Be objective. Separate facts from speculation."""

    async def analyze(self, context: AgentContext) -> AgentContext:
        """Fetch news from Finnhub, send to LLM for sentiment analysis."""

        # Fetch news headlines
        headlines = await self._fetch_news(context.symbol)

        if not headlines:
            logger.warning("[NewsAnalyst] No news found for {symbol}", symbol=context.symbol)
            context.news_analysis = {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "summary": "No recent news found.",
                "key_themes": [],
                "risk_events": [],
                "catalyst": None,
            }
            return context

        # Format headlines for LLM
        headlines_text = "\n".join(
            f"- [{h['datetime']}] {h['headline']} (Source: {h['source']})"
            for h in headlines[:20]  # Cap at 20 to stay within context window
        )

        prompt = f"""
Analyze the following recent news headlines for {context.symbol}:

{headlines_text}

Provide your sentiment analysis in the specified JSON format.
"""

        response_text = await self.invoke_llm(prompt)

        # Parse JSON response
        try:
            json_str = response_text
            if "```" in response_text:
                json_str = response_text.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            analysis = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("[NewsAnalyst] Could not parse JSON response")
            analysis = {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "raw_response": response_text,
                "key_themes": [],
                "risk_events": [],
                "catalyst": None,
                "summary": "Analysis parsing failed.",
            }

        context.news_analysis = analysis
        return context

    async def _fetch_news(self, symbol: str, days: int = 7) -> list[dict]:
        """Fetch news from Finnhub API."""
        if not settings.finnhub_api_key:
            logger.warning("[NewsAnalyst] No FINNHUB_API_KEY — returning empty news")
            return []

        end = datetime.now(UTC).date()
        start = end - timedelta(days=days)

        url = "https://finnhub.io/api/v1/company-news"
        params = {
            "symbol": symbol,
            "from": start.isoformat(),
            "to": end.isoformat(),
            "token": settings.finnhub_api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                articles = response.json()

            # Normalize fields
            return [
                {
                    "headline": a.get("headline", ""),
                    "source": a.get("source", ""),
                    "datetime": datetime.fromtimestamp(a.get("datetime", 0), tz=UTC).strftime("%Y-%m-%d"),
                    "summary": a.get("summary", "")[:200],  # Truncate
                }
                for a in articles
                if a.get("headline")
            ]

        except Exception as exc:
            logger.error("[NewsAnalyst] Finnhub API error: {error}", error=str(exc))
            return []
