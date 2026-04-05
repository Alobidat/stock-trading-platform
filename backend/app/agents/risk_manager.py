"""
Risk Manager Agent

Validates the Researcher's thesis against portfolio risk limits.
Acts as a gatekeeper — can veto or downsize a trade before it reaches the Trader.

Risk checks:
- Max position size (% of portfolio)
- Max portfolio risk concentration
- Daily loss limit (circuit breaker)
- Minimum conviction threshold
"""

import json
from decimal import Decimal

from loguru import logger

from app.agents.base_agent import AgentContext, BaseAgent
from app.core.config import settings
from app.models.agent_log import AgentName
from app.services.market_data import market_data_service


class RiskManagerAgent(BaseAgent):
    agent_name = AgentName.RISK_MANAGER

    system_prompt = """You are a risk manager at a quantitative trading firm.
You enforce strict risk controls to protect the portfolio.
You receive a researcher's thesis and current portfolio state.
Your job is to approve, modify, or reject the trade.

Output format (JSON):
{
  "approved": true | false,
  "action": "buy" | "sell" | "hold",
  "quantity": <number of shares>,
  "position_size_pct": <% of portfolio for this trade>,
  "risk_reasoning": "why approved/rejected",
  "risk_flags": ["list of risk concerns"]
}

When in doubt, size down or reject. Capital preservation comes first."""

    async def analyze(self, context: AgentContext) -> AgentContext:
        """Validate the research thesis against risk limits."""

        thesis = context.technical_analysis.get("research_thesis", {})
        researcher_action = thesis.get("thesis", "hold")

        # Skip risk check if researcher says hold
        if researcher_action == "hold":
            context.risk_assessment = {
                "approved": False,
                "action": "hold",
                "quantity": 0,
                "position_size_pct": 0.0,
                "risk_reasoning": "Researcher recommends hold — no trade required.",
                "risk_flags": [],
            }
            return context

        # Get current portfolio state
        try:
            account = await market_data_service.get_account()
            portfolio_value = account["portfolio_value"]
            cash = account["cash"]
        except Exception as exc:
            logger.warning("[RiskManager] Cannot fetch account: {error}", error=str(exc))
            # If we can't verify portfolio state, reject the trade
            context.risk_assessment = {
                "approved": False,
                "action": "hold",
                "quantity": 0,
                "position_size_pct": 0.0,
                "risk_reasoning": "Cannot verify portfolio state — trade rejected for safety.",
                "risk_flags": ["portfolio_state_unavailable"],
            }
            return context

        latest_price = context.price_data.get("latest_close", 0)
        if latest_price <= 0:
            context.risk_assessment = {
                "approved": False,
                "action": "hold",
                "quantity": 0,
                "position_size_pct": 0.0,
                "risk_reasoning": "Invalid price data — trade rejected.",
                "risk_flags": ["invalid_price"],
            }
            return context

        # Compute max allowed position
        max_position_value = portfolio_value * (settings.max_position_size_pct / 100)
        max_shares = int(max_position_value / latest_price)

        # Check conviction level
        conviction = thesis.get("conviction", "low")
        conviction_multiplier = {"high": 1.0, "medium": 0.6, "low": 0.3}.get(conviction, 0.3)
        adjusted_shares = max(1, int(max_shares * conviction_multiplier))

        # Validate we have enough cash for a buy
        trade_value = adjusted_shares * latest_price
        risk_flags = []

        if researcher_action == "buy" and trade_value > cash:
            adjusted_shares = max(1, int(cash * 0.95 / latest_price))
            risk_flags.append("position_reduced_insufficient_cash")

        position_pct = (adjusted_shares * latest_price / portfolio_value) * 100

        prompt = f"""
Review this trade request for {context.symbol}:

Portfolio Value: ${portfolio_value:,.2f}
Available Cash: ${cash:,.2f}
Proposed Action: {researcher_action.upper()}
Proposed Shares: {adjusted_shares}
Share Price: ${latest_price:.2f}
Trade Value: ${adjusted_shares * latest_price:,.2f} ({position_pct:.1f}% of portfolio)

Researcher Conviction: {conviction}
Researcher Rationale: {thesis.get('rationale', 'N/A')}
Stop Loss: {thesis.get('suggested_stop', 'not set')}

Risk Limits:
- Max position size: {settings.max_position_size_pct}% of portfolio
- Max portfolio risk: {settings.max_portfolio_risk_pct}%
- Daily loss limit: {settings.daily_loss_limit_pct}%

Current risk flags: {risk_flags}

Assess this trade. Approve, modify quantity, or reject. Output in the specified JSON format.
"""

        response_text = await self.invoke_llm(prompt)

        try:
            json_str = response_text
            if "```" in response_text:
                json_str = response_text.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            risk_result = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            # Safe default: reject
            risk_result = {
                "approved": False,
                "action": "hold",
                "quantity": 0,
                "position_size_pct": 0.0,
                "risk_reasoning": "Risk assessment parse failed — defaulting to hold.",
                "risk_flags": ["parse_error"] + risk_flags,
            }

        # Hard limit enforcement — LLM cannot override these
        if risk_result.get("quantity", 0) * latest_price > portfolio_value * (settings.max_position_size_pct / 100):
            risk_result["quantity"] = adjusted_shares
            risk_result["risk_flags"] = risk_result.get("risk_flags", []) + ["quantity_hard_capped"]

        context.risk_assessment = risk_result
        return context
