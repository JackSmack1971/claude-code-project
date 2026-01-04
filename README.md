# AgentFactory 🤖

A modular application for rapid deployment and persistence of AI agents with FastAPI backend and Streamlit frontend.

## Features

- **Agent Builder**: Create AI agents with custom system prompts and model configurations
- **Persistent Storage**: Save and manage agent blueprints in PostgreSQL
- **Agent Sandbox**: Interactive chat interface with real-time streaming
- **Trading Tools**: Optional CCXT integration for financial operations
- **Multi-Model Support**: Access 300+ models via OpenRouter

## Tech Stack

- **Backend**: FastAPI 0.128.0 with async SQLAlchemy
- **Frontend**: Streamlit 1.52.2
- **Agent Engine**: Pydantic AI 1.39.0 + OpenRouter-Agent 0.1.3
- **Database**: PostgreSQL with asyncpg
- **Trading**: CCXT 4.4.51 (optional)

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- OpenRouter API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd claude-code-project
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

4. Install frontend dependencies:
```bash
cd ../frontend
pip install -r requirements.txt
```

### Running the Application

1. Start the backend server:
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. Start the frontend (in a new terminal):
```bash
cd frontend
streamlit run app.py
```

3. Access the application at `http://localhost:8501`

## Project Structure

```
agentfactory/
├── backend/
│   ├── main.py              # FastAPI app with lifespan management
│   ├── models.py            # SQLAlchemy models
│   ├── database.py          # Database configuration
│   ├── schemas.py           # Pydantic schemas
│   ├── agents.py            # Pydantic AI agent factory
│   ├── tools.py             # Agent tools (including CCXT)
│   └── requirements.txt
├── frontend/
│   ├── app.py               # Main Streamlit app
│   ├── pages/
│   │   ├── 01_agent_builder.py
│   │   ├── 02_agent_sandbox.py
│   │   └── 03_my_agents.py
│   ├── utils.py             # Helper functions
│   └── requirements.txt
├── tests/
│   ├── test_agents.py       # Pydantic AI tests with TestModel
│   └── test_api.py          # FastAPI endpoint tests
└── .env.example
```

## Security

- API keys managed via environment variables and `st.secrets`
- Database sessions properly managed with dependency injection
- No hardcoded credentials

## Contributing

See CLAUDE.md for development guidelines and state machine protocol.

## License

MIT
