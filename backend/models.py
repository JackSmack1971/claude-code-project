"""
SQLAlchemy models for AgentFactory.
Defines the agent blueprint schema with async operations support.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class AgentBlueprint(Base):
    """
    Persistent storage for AI agent configurations.

    Attributes:
        id: Primary key
        name: Human-readable agent name
        system_prompt: Instructions that define agent behavior
        model_id: OpenRouter model identifier (e.g., 'openrouter/anthropic/claude-3.5-sonnet')
        temperature: Sampling temperature (0.0-2.0)
        has_trading_tools: Whether CCXT trading tools are enabled
        max_retries: Number of retry attempts (0 for fallback patterns)
        created_at: Timestamp of blueprint creation
        updated_at: Timestamp of last modification
        is_active: Soft delete flag
    """
    __tablename__ = "agent_blueprints"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    has_trading_tools: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=0, nullable=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<AgentBlueprint(id={self.id}, name='{self.name}', model='{self.model_id}')>"
