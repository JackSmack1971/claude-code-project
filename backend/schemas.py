"""
Pydantic schemas for request/response validation and serialization.
Implements type-safe data validation for the API layer.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AgentBlueprintBase(BaseModel):
    """Base schema with common agent blueprint fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    system_prompt: str = Field(..., min_length=1, description="System instructions")
    model_id: str = Field(
        ...,
        description="OpenRouter model ID (e.g., 'openrouter/anthropic/claude-3.5-sonnet')"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    has_trading_tools: bool = Field(default=False, description="Enable CCXT trading tools")
    max_retries: int = Field(default=0, ge=0, le=5, description="Retry attempts (0 for fallback)")


class AgentBlueprintCreate(AgentBlueprintBase):
    """Schema for creating a new agent blueprint."""
    pass


class AgentBlueprintUpdate(BaseModel):
    """Schema for updating an existing agent blueprint. All fields optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    system_prompt: Optional[str] = Field(None, min_length=1)
    model_id: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    has_trading_tools: Optional[bool] = None
    max_retries: Optional[int] = Field(None, ge=0, le=5)


class AgentBlueprintResponse(AgentBlueprintBase):
    """
    Schema for agent blueprint responses.
    Uses response_model to filter sensitive metadata.
    """
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AgentBlueprintList(BaseModel):
    """Schema for paginated list of agent blueprints."""
    total: int
    agents: list[AgentBlueprintResponse]


class ChatMessage(BaseModel):
    """Schema for chat messages in the agent sandbox."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """Schema for chat requests to the agent."""
    agent_id: int
    message: str = Field(..., min_length=1)
    conversation_history: list[ChatMessage] = Field(default_factory=list)


class StreamChunk(BaseModel):
    """Schema for streaming response chunks."""
    delta: str
    is_final: bool = False
