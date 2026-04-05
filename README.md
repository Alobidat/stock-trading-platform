# ⚡ AI Agent Stock Trading Platform

A multi-agent LLM system for market analysis and automated paper trading. Specialized AI agents collaborate to analyze markets, generate trading signals, and execute trades with built-in risk controls.

[![CI](https://github.com/Alobidat/stock-trading-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Alobidat/stock-trading-platform/actions/workflows/ci.yml)

---

## Architecture

```
Frontend (Next.js 15)  ←→  Backend (FastAPI)  ←→  Agent Pipeline (Celery)
                                    ↕                       ↕
                              PostgreSQL              Alpaca / Finnhub / LLM
                              Redis (pub/sub)
```

### Agent Pipeline

| Agent | Role |
|---|---|
| **Technical Analyst** | RSI, MACD, Bollinger Bands, EMAs |
| **News Analyst** | Sentiment scoring via Finnhub |
| **Researcher** | Synthesizes findings into an investment thesis |
| **Risk Manager** | Validates trade against risk limits (gatekeeper) |
| **Trader** | Final decision + optional paper order execution |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Alpaca Markets account (free): https://alpaca.markets
- Finnhub account (free): https://finnhub.io
- One of: Ollama (local), OpenAI API key, or Anthropic API key

### 1. Clone & Configure

```bash
git clone https://github.com/Alobidat/stock-trading-platform.git
cd stock-trading-platform
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start Services

```bash
docker compose up -d
```

### 3. Verify

```bash
curl http://localhost:8000/api/v1/health/
# → {"status": "ok", "llm_provider": "ollama", ...}
```

Frontend: http://localhost:3000  
API Docs: http://localhost:8000/docs

---

## Environment Variables

See `.env.example` for full documentation. Key variables:

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | `ollama` \| `openai` \| `anthropic` | `ollama` |
| `OLLAMA_MODEL` | Model name for Ollama | `llama3.1:8b` |
| `ALPACA_API_KEY` | Alpaca Markets API key | — |
| `FINNHUB_API_KEY` | Finnhub news API key | — |
| `MAX_POSITION_SIZE_PCT` | Max % of portfolio per trade | `5` |
| `DAILY_LOSS_LIMIT_PCT` | Kill switch daily loss threshold | `3` |

---

## Development

### Backend (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Run Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

---

## Switching LLM Providers

Edit `.env`:

```bash
# Use Ollama (local, free)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b

# Use OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Use Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

No code changes needed — the factory pattern handles the rest.

---

## Triggering an Analysis

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/agents/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "execute_trade": false}'

# Check results
curl http://localhost:8000/api/v1/agents/logs?symbol=AAPL
curl http://localhost:8000/api/v1/signals/?symbol=AAPL
```

---

## Project Structure

```
stock-trading-platform/
├── backend/
│   ├── app/
│   │   ├── agents/          # Technical, News, Researcher, Risk, Trader agents
│   │   ├── api/v1/          # FastAPI routers + endpoints
│   │   ├── core/            # Config, database, auth, logging
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── services/        # Market data (Alpaca) service
│   │   └── workers/         # Agent pipeline orchestrator
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/             # Next.js pages
│       ├── components/      # UI components
│       └── lib/             # API client
├── .env.example
├── docker-compose.yml
└── .github/workflows/ci.yml
```

---

## Roadmap

- [x] Phase 1 — Foundation (backend scaffold, agent framework, Docker)
- [ ] Phase 2 — Full agent implementation + Celery scheduling
- [ ] Phase 3 — Frontend dashboard (portfolio, signals, agent logs)
- [ ] Phase 4 — Backtesting engine
- [ ] Phase 5 — Live trading (requires explicit approval)

---

## ⚠️ Disclaimer

This platform is for **educational and research purposes only**. Paper trading mode is the default. The authors are not responsible for any financial losses. Never trade money you cannot afford to lose.

---

*Built by Nova ⚡ — AI engineering agent*
