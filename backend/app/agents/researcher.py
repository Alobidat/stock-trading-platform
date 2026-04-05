"""
Researcher Agent

Synthesizes outputs from the Technical Analyst and News Analyst into
a coherent investment thesis. This is the "senior analyst" that connects
the dots before the Risk Manager and Trader make decisions.
"""

import json

from app.agents.base_agent import AgentContext, BaseAgent
from app.models.agent_log import AgentName


class ResearcherAgent(BaseAgent):
    agent_name = AgentName.RESEARCHER

    system_prompt = """You are a senior investment researcher at a quantitative trading firm.
You receive technical analysis and news sentiment data for a stock.
Your job is to synthesize all inputs into a coherent investment thesis.

Output format (JSON):
{
  "thesis": "buy" | "sell" | "hold",
  "conviction": "high" | "medium" | "low",
  "rationale": "2-4 sentence investment thesis",
  "bull_case": "key upside arguments",
  "bear_case": "key downside risks",
  "time_horizon": "short" | "medium",
  "suggested_entry": <price or null>,
  "suggested_target": <price or null>,
  "suggested_stop": <price or null>
}

Be concise and data-driven. Acknowledge uncertainty."""

    async def analyze(self, context: AgentContext) -> AgentContext:
        """Synthesize technical and news analysis into an investment thesis."""

        technical = context.technical_analysis
        news = context.news_analysis
        price = context.price_data

        prompt = f"""
Synthesize the following analysis for {context.symbol}:

=== TECHNICAL ANALYSIS ===
Trend: {technical.get('trend', 'N/A')}
Momentum: {technical.get('momentum', 'N/A')}
RSI: {technical.get('rsi', 'N/A')}
MACD Histogram: {technical.get('macd_hist', 'N/A')}
Price vs EMA20: {'ABOVE' if price.get('latest_close', 0) > technical.get('ema_20', 0) else 'BELOW'}
Price vs EMA50: {'ABOVE' if price.get('latest_close', 0) > technical.get('ema_50', 0) else 'BELOW'}
Price vs EMA200: {'ABOVE' if price.get('latest_close', 0) > technical.get('ema_200', 0) else 'BELOW'}
Key Technical Signals: {technical.get('key_signals', [])}
Technical Summary: {technical.get('summary', 'N/A')}

=== NEWS & SENTIMENT ===
Sentiment: {news.get('sentiment', 'N/A')} (Score: {news.get('sentiment_score', 0):.2f})
Key Themes: {news.get('key_themes', [])}
Risk Events: {news.get('risk_events', [])}
Catalyst: {news.get('catalyst', 'None')}
News Summary: {news.get('summary', 'N/A')}

=== PRICE CONTEXT ===
Latest Close: ${price.get('latest_close', 0):.2f}
Period High: ${price.get('period_high', 0):.2f}
Period Low: ${price.get('period_low', 0):.2f}

Provide your investment thesis in the specified JSON format.
"""

        response_text = await self.invoke_llm(prompt)

        # Parse JSON
        try:
            json_str = response_text
            if "```" in response_text:
                json_str = response_text.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            thesis = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            thesis = {
                "thesis": "hold",
                "conviction": "low",
                "rationale": "Analysis synthesis failed — defaulting to hold.",
                "bull_case": "",
                "bear_case": "",
                "time_horizon": "short",
                "suggested_entry": None,
                "suggested_target": None,
                "suggested_stop": None,
            }

        context.research_summary = thesis.get("rationale", "")
        # Store full thesis in technical_analysis dict for downstream agents
        context.technical_analysis["research_thesis"] = thesis
        return context
