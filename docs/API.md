# AgentFactory API Documentation

Base URL: `http://localhost:8000`

## Health Check

### GET /health

Check if the backend service is running.

**Response**
```json
{
  "status": "healthy",
  "service": "agentfactory-backend"
}
```

---

## Agent Blueprints

### POST /agents

Create a new agent blueprint.

**Request Body**
```json
{
  "name": "Trading Assistant",
  "system_prompt": "You are a helpful trading assistant...",
  "model_id": "openrouter/anthropic/claude-3.5-sonnet",
  "temperature": 0.7,
  "has_trading_tools": true,
  "max_retries": 0
}
```

**Response** (201 Created)
```json
{
  "id": 1,
  "name": "Trading Assistant",
  "system_prompt": "You are a helpful trading assistant...",
  "model_id": "openrouter/anthropic/claude-3.5-sonnet",
  "temperature": 0.7,
  "has_trading_tools": true,
  "max_retries": 0,
  "created_at": "2026-01-04T10:00:00",
  "updated_at": "2026-01-04T10:00:00",
  "is_active": true
}
```

---

### GET /agents

List all agent blueprints with pagination.

**Query Parameters**
- `skip` (int, default: 0): Number of records to skip
- `limit` (int, default: 100): Maximum records to return
- `active_only` (bool, default: true): Filter for active agents only

**Response**
```json
{
  "total": 5,
  "agents": [
    {
      "id": 1,
      "name": "Trading Assistant",
      "model_id": "openrouter/anthropic/claude-3.5-sonnet",
      ...
    }
  ]
}
```

---

### GET /agents/{agent_id}

Get a specific agent blueprint by ID.

**Path Parameters**
- `agent_id` (int): Agent blueprint ID

**Response**
```json
{
  "id": 1,
  "name": "Trading Assistant",
  "system_prompt": "You are a helpful trading assistant...",
  "model_id": "openrouter/anthropic/claude-3.5-sonnet",
  "temperature": 0.7,
  "has_trading_tools": true,
  "max_retries": 0,
  "created_at": "2026-01-04T10:00:00",
  "updated_at": "2026-01-04T10:00:00",
  "is_active": true
}
```

**Error Response** (404 Not Found)
```json
{
  "detail": "Agent blueprint 1 not found"
}
```

---

### PATCH /agents/{agent_id}

Update an existing agent blueprint.

**Path Parameters**
- `agent_id` (int): Agent blueprint ID

**Request Body** (all fields optional)
```json
{
  "name": "Updated Name",
  "temperature": 0.9
}
```

**Response**
```json
{
  "id": 1,
  "name": "Updated Name",
  "temperature": 0.9,
  ...
}
```

---

### DELETE /agents/{agent_id}

Delete an agent blueprint (soft delete by default).

**Path Parameters**
- `agent_id` (int): Agent blueprint ID

**Query Parameters**
- `hard_delete` (bool, default: false): Permanent deletion if true

**Response** (204 No Content)

---

## Agent Execution

### POST /agents/{agent_id}/chat

Chat with an agent using streaming responses.

**Path Parameters**
- `agent_id` (int): Agent blueprint ID

**Request Body**
```json
{
  "agent_id": 1,
  "message": "What's the current BTC price?",
  "conversation_history": []
}
```

**Response**
Streaming text/plain response with agent output.

**Example using cURL**
```bash
curl -X POST "http://localhost:8000/agents/1/chat" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": 1, "message": "Hello!", "conversation_history": []}'
```

---

## Error Responses

### Validation Error (422 Unprocessable Entity)
```json
{
  "detail": [
    {
      "loc": ["body", "temperature"],
      "msg": "ensure this value is less than or equal to 2.0",
      "type": "value_error.number.not_le"
    }
  ]
}
```

### Not Found (404)
```json
{
  "detail": "Agent blueprint 999 not found"
}
```

### Internal Server Error (500)
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

The API implements rate limiting for OpenRouter and CCXT operations:

- OpenRouter: Handled by `tenacity` with exponential backoff
- CCXT: Enabled via `enableRateLimit: true` in exchange config

---

## Authentication

Currently, the API does not require authentication. For production deployment, implement:

- API key authentication
- OAuth 2.0
- JWT tokens

---

## WebSocket Support

WebSocket support for real-time streaming is planned for a future release.

---

## API Client Examples

### Python (httpx)
```python
import httpx
import asyncio

async def create_agent():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/agents",
            json={
                "name": "My Agent",
                "system_prompt": "You are helpful.",
                "model_id": "openrouter/anthropic/claude-3.5-sonnet",
                "temperature": 0.7,
                "has_trading_tools": False
            }
        )
        print(response.json())

asyncio.run(create_agent())
```

### JavaScript (fetch)
```javascript
async function createAgent() {
  const response = await fetch('http://localhost:8000/agents', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: 'My Agent',
      system_prompt: 'You are helpful.',
      model_id: 'openrouter/anthropic/claude-3.5-sonnet',
      temperature: 0.7,
      has_trading_tools: false
    })
  });
  const data = await response.json();
  console.log(data);
}
```
