"""
Test suite for FastAPI endpoints.
Tests CRUD operations and database interactions.
"""
import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app
from database import Base, get_db
from models import AgentBlueprint


# Test database URL (use in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def override_get_db():
    """Override database dependency for testing."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
async def setup_database():
    """Create test database tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(setup_database):
    """Create test client with database override."""
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestHealthCheck:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test /health endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "agentfactory-backend"


class TestAgentBlueprintCRUD:
    """Test CRUD operations for agent blueprints."""

    @pytest.mark.asyncio
    async def test_create_agent_blueprint(self, client):
        """Test creating a new agent blueprint."""
        payload = {
            "name": "Test Agent",
            "system_prompt": "You are a test assistant.",
            "model_id": "openrouter/anthropic/claude-3.5-sonnet",
            "temperature": 0.7,
            "has_trading_tools": False,
            "max_retries": 0
        }

        response = await client.post("/agents", json=payload)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "Test Agent"
        assert data["model_id"] == "openrouter/anthropic/claude-3.5-sonnet"
        assert data["temperature"] == 0.7
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_list_agent_blueprints(self, client):
        """Test listing agent blueprints."""
        # Create test agents
        for i in range(3):
            payload = {
                "name": f"Agent {i}",
                "system_prompt": f"You are agent {i}.",
                "model_id": "openrouter/anthropic/claude-3.5-sonnet",
                "temperature": 0.7,
                "has_trading_tools": False
            }
            await client.post("/agents", json=payload)

        # List agents
        response = await client.get("/agents")
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3
        assert len(data["agents"]) == 3

    @pytest.mark.asyncio
    async def test_get_agent_blueprint(self, client):
        """Test retrieving a specific agent blueprint."""
        # Create agent
        payload = {
            "name": "Specific Agent",
            "system_prompt": "You are specific.",
            "model_id": "openrouter/anthropic/claude-3.5-sonnet",
            "temperature": 0.7,
            "has_trading_tools": False
        }
        create_response = await client.post("/agents", json=payload)
        agent_id = create_response.json()["id"]

        # Get agent
        response = await client.get(f"/agents/{agent_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == agent_id
        assert data["name"] == "Specific Agent"

    @pytest.mark.asyncio
    async def test_get_nonexistent_agent(self, client):
        """Test retrieving a non-existent agent."""
        response = await client.get("/agents/9999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_agent_blueprint(self, client):
        """Test updating an agent blueprint."""
        # Create agent
        payload = {
            "name": "Original Name",
            "system_prompt": "Original prompt.",
            "model_id": "openrouter/anthropic/claude-3.5-sonnet",
            "temperature": 0.7,
            "has_trading_tools": False
        }
        create_response = await client.post("/agents", json=payload)
        agent_id = create_response.json()["id"]

        # Update agent
        update_payload = {
            "name": "Updated Name",
            "temperature": 0.9
        }
        response = await client.patch(f"/agents/{agent_id}", json=update_payload)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["temperature"] == 0.9
        assert data["system_prompt"] == "Original prompt."  # Unchanged

    @pytest.mark.asyncio
    async def test_delete_agent_blueprint_soft(self, client):
        """Test soft deleting an agent blueprint."""
        # Create agent
        payload = {
            "name": "To Delete",
            "system_prompt": "Delete me.",
            "model_id": "openrouter/anthropic/claude-3.5-sonnet",
            "temperature": 0.7,
            "has_trading_tools": False
        }
        create_response = await client.post("/agents", json=payload)
        agent_id = create_response.json()["id"]

        # Soft delete
        response = await client.delete(f"/agents/{agent_id}")
        assert response.status_code == 204

        # Verify agent is not in active list
        list_response = await client.get("/agents?active_only=true")
        data = list_response.json()
        assert all(a["id"] != agent_id for a in data["agents"])

    @pytest.mark.asyncio
    async def test_validation_errors(self, client):
        """Test validation errors for invalid input."""
        # Missing required fields
        payload = {
            "name": "Test"
            # Missing system_prompt and model_id
        }
        response = await client.post("/agents", json=payload)
        assert response.status_code == 422  # Unprocessable Entity

        # Invalid temperature
        payload = {
            "name": "Test",
            "system_prompt": "Test prompt",
            "model_id": "test-model",
            "temperature": 5.0  # Out of range
        }
        response = await client.post("/agents", json=payload)
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
