"""
Trader Agent

The final decision-maker in the pipeline.
Reviews the Risk Manager's approved plan and produces the final trading signal.
Only executes if the Risk Manager approved the trade.
"""

import json
from decimal import Decimal

from loguru import logger

from app.agents.base_agent import AgentContext, BaseAgent
from app.models.agent_log import AgentName


class TraderAgent(BaseAgent):
    agent_name = AgentName.TRADER

    system_prompt = """You are a professional trader at a quantitative trading firm.
You receive a risk-approved trade plan and make the final decision.
You are the last line of defense — you can still reject a trade if something feels wrong.

Output format (JSON):
{
  "action": "buy" | "sell" | "hold",
  "quantity": <shares>,
  "confidence": <0.0 to 1.0>,
  "strength": "strong" | "moderate" | "weak",
  "reasoning": "final trading rationale",
  "entry_notes": "execution notes (e.g., limit vs market, timing)"
}

If the risk manager rejected the trade, output action: "hold"."""

    async def analyze(self, context: AgentContext) -> AgentContext:
        """Make the final trading decision based on the full pipeline output."""

        risk = context.risk_assessment
        thesis = context.technical_analysis.get("research_thesis", {})
        technical = context.technical_analysis

        # If risk manager rejected, trader respects it
        if not risk.get("approved", False):
            context.final_signal = {
                "action": "hold",
                "quantity": 0,
                "confidence": 0.0,
                "strength": "weak",
                "reasoning": risk.get("risk_reasoning", "Trade rejected by risk manager."),
                "entry_notes": "No trade — risk manager veto.",
            }
            logger.info(
                "[Trader] Trade REJECTED by risk manager: {reason}",
                reason=risk.get("risk_reasoning", ""),
            )
            return context

        prompt = f"""
Make the final trading decision for {context.symbol}:

=== RISK MANAGER APPROVAL ===
Action: {risk.get('action', 'hold').upper()}
Approved Quantity: {risk.get('quantity', 0)} shares
Position Size: {risk.get('position_size_pct', 0):.1f}% of portfolio
Risk Reasoning: {risk.get('risk_reasoning', 'N/A')}
Risk Flags: {risk.get('risk_flags', [])}

=== RESEARCH THESIS ===
Conviction: {thesis.get('conviction', 'N/A')}
Rationale: {thesis.get('rationale', 'N/A')}
Bull Case: {thesis.get('bull_case', 'N/A')}
Bear Case: {thesis.get('bear_case', 'N/A')}
Suggested Stop: {thesis.get('suggested_stop', 'N/A')}
Suggested Target: {thesis.get('suggested_target', 'N/A')}

=== TECHNICAL CONTEXT ===
Price: ${context.price_data.get('latest_close', 0):.2f}
Trend: {technical.get('trend', 'N/A')}
RSI: {technical.get('rsi', 'N/A')}
MACD Histogram: {technical.get('macd_hist', 'N/A')}

=== NEWS SENTIMENT ===
{context.news_analysis.get('summary', 'N/A')}

Confirm or reject the trade. Provide your final decision in the specified JSON format.
"""

        response_text = await self.invoke_llm(prompt)

        try:
            json_str = response_text
            if "```" in response_text:
                json_str = response_text.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            signal = json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            # Safe default: hold
            signal = {
                "action": "hold",
                "quantity": 0,
                "confidence": 0.0,
                "strength": "weak",
                "reasoning": "Signal parsing failed — defaulting to hold.",
                "entry_notes": "",
            }

        # Enforce: trader cannot exceed risk-approved quantity
        if signal.get("action") != "hold":
            approved_qty = risk.get("quantity", 0)
            if signal.get("quantity", 0) > approved_qty:
                signal["quantity"] = approved_qty
                signal["entry_notes"] = (
                    f"Quantity capped at risk-approved {approved_qty} shares. "
                    + signal.get("entry_notes", "")
                )

        context.final_signal = signal

        logger.info(
            "[Trader] Final signal: {action} {qty} {symbol} | confidence={confidence}",
            action=signal.get("action"),
            qty=signal.get("quantity"),
            symbol=context.symbol,
            confidence=signal.get("confidence"),
        )

        return context
