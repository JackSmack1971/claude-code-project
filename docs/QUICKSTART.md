# AgentFactory Quickstart Guide

Get up and running with AgentFactory in minutes!

## Prerequisites

- Python 3.10 or higher
- PostgreSQL 14+ (or use Docker)
- OpenRouter API key ([Get one here](https://openrouter.ai/))

## Option 1: Docker (Recommended)

The fastest way to get started:

### 1. Clone and Configure

```bash
git clone <repository-url>
cd claude-code-project
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:
```bash
OPENROUTER_API_KEY=your_key_here
```

### 2. Start Services

```bash
./scripts/start.sh
```

This will start:
- PostgreSQL database on port 5432
- FastAPI backend on http://localhost:8000
- Streamlit frontend on http://localhost:8501

### 3. Access the Application

Open your browser to http://localhost:8501

## Option 2: Local Development

For development without Docker:

### 1. Setup Environment

```bash
./scripts/dev.sh
```

### 2. Start PostgreSQL

Make sure PostgreSQL is running locally. Update `backend/.env` with your database URL:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agentfactory
```

### 3. Start Backend (Terminal 1)

```bash
cd backend
source ../venv/bin/activate
uvicorn main:app --reload
```

### 4. Start Frontend (Terminal 2)

```bash
cd frontend
source ../venv/bin/activate
streamlit run app.py
```

## Creating Your First Agent

1. Navigate to **Agent Builder** in the sidebar
2. Fill in the form:
   - **Name**: "My First Agent"
   - **Model**: Select "openrouter/anthropic/claude-3.5-sonnet"
   - **Temperature**: 0.7 (default)
   - **System Prompt**: "You are a helpful AI assistant."
3. Click **Create Agent**
4. Navigate to **Agent Sandbox** to chat with your agent!

## Enabling Trading Tools

To use CCXT trading capabilities:

1. Get API keys from your exchange (e.g., Binance)
2. Add them to `.env`:
   ```bash
   EXCHANGE_API_KEY=your_api_key
   EXCHANGE_SECRET=your_secret
   ```
3. When creating an agent, check **Enable Trading Tools**
4. The agent can now access market data and execute orders

**Warning**: Start with testnet/sandbox credentials!

## Running Tests

```bash
./scripts/test.sh
```

## Troubleshooting

### Backend won't start
- Check PostgreSQL is running: `pg_isready`
- Verify DATABASE_URL in `.env`
- Check logs: `docker-compose logs backend`

### Frontend can't connect to backend
- Ensure backend is running on port 8000
- Check `frontend/.streamlit/secrets.toml` has correct backend_url
- Verify firewall settings

### Database connection errors
- Reset database: `docker-compose down -v && docker-compose up -d`
- Check PostgreSQL logs: `docker-compose logs postgres`

## Next Steps

- Explore **My Agents** to manage your blueprints
- Experiment with different models and temperatures
- Try adding trading tools for market analysis
- Read the [API Documentation](API.md)
- Check the [Development Guide](DEVELOPMENT.md)

## Support

- Issues: https://github.com/your-repo/issues
- Discussions: https://github.com/your-repo/discussions
