"""Tests for agent base logic and context object."""

import pytest
from app.agents.base_agent import AgentContext


def test_agent_context_defaults():
    """AgentContext should initialize with empty analysis fields."""
    ctx = AgentContext(symbol="AAPL")
    assert ctx.symbol == "AAPL"
    assert ctx.price_data == {}
    assert ctx.technical_analysis == {}
    assert ctx.news_analysis == {}
    assert ctx.final_signal == {}
    assert ctx.run_id is not None


def test_agent_context_to_dict():
    """to_dict should serialize all fields."""
    ctx = AgentContext(symbol="TSLA", run_id="test-run-123")
    ctx.price_data = {"latest_close": 250.0}
    d = ctx.to_dict()
    assert d["symbol"] == "TSLA"
    assert d["run_id"] == "test-run-123"
    assert d["price_data"]["latest_close"] == 250.0


def test_agent_context_unique_run_ids():
    """Each AgentContext should have a unique run_id."""
    ctx1 = AgentContext(symbol="AAPL")
    ctx2 = AgentContext(symbol="AAPL")
    assert ctx1.run_id != ctx2.run_id
