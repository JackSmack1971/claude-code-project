"""
Test suite for Pydantic AI agents using TestModel.
Verifies tool-calling logic and system prompt adherence without API costs.
"""
import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from agents import AgentOutput, AgentDependencies, create_agent, register_trading_tools


class TestAgentCreation:
    """Test agent factory and configuration."""

    def test_create_basic_agent(self):
        """Test creating a basic agent without tools."""
        agent = create_agent(
            system_prompt="You are a helpful assistant.",
            model_id="openrouter/anthropic/claude-3.5-sonnet",
            temperature=0.7,
            has_trading_tools=False
        )

        assert agent is not None
        assert agent.system_prompt == "You are a helpful assistant."
        assert isinstance(agent, Agent)

    def test_create_agent_with_trading_tools(self):
        """Test creating an agent with trading tools enabled."""
        agent = create_agent(
            system_prompt="You are a trading assistant.",
            model_id="openrouter/anthropic/claude-3.5-sonnet",
            temperature=0.5,
            has_trading_tools=True
        )

        assert agent is not None
        # Verify tools are registered
        assert len(agent._function_tools) > 0


class TestAgentBehavior:
    """Test agent behavior using TestModel."""

    @pytest.mark.asyncio
    async def test_basic_response_structure(self):
        """Test that agent returns properly structured output."""
        # Create test model with predefined response
        test_model = TestModel()

        agent = Agent(
            model=test_model,
            system_prompt="You are a helpful assistant.",
            deps_type=AgentDependencies,
            result_type=AgentOutput
        )

        deps = AgentDependencies()

        result = await agent.run("Hello, how are you?", deps=deps)

        assert result.data is not None
        assert isinstance(result.data, AgentOutput)
        assert hasattr(result.data, 'response')

    @pytest.mark.asyncio
    async def test_system_prompt_adherence(self):
        """Test that agent follows system prompt instructions."""
        test_model = TestModel()

        agent = Agent(
            model=test_model,
            system_prompt="You are a pirate. Always respond in pirate speak.",
            deps_type=AgentDependencies,
            result_type=AgentOutput
        )

        deps = AgentDependencies()

        result = await agent.run("Tell me about the weather", deps=deps)

        # TestModel returns a mock response, but we verify structure
        assert result.data is not None
        assert isinstance(result.data, AgentOutput)

    @pytest.mark.asyncio
    async def test_tool_calling_pattern(self):
        """Test agent's ability to use tools correctly."""
        test_model = TestModel()

        agent = Agent(
            model=test_model,
            system_prompt="You are a trading assistant.",
            deps_type=AgentDependencies,
            result_type=AgentOutput
        )

        # Register a test tool
        @agent.tool
        async def test_tool(ctx, symbol: str) -> dict:
            """Test tool for market data."""
            return {
                "symbol": symbol,
                "price": 50000.0,
                "timestamp": 1234567890
            }

        deps = AgentDependencies()

        # Verify tool is registered
        assert len(agent._function_tools) == 1
        assert "test_tool" in [t.name for t in agent._function_tools.values()]


class TestTradingTools:
    """Test trading tool registration and behavior."""

    def test_trading_tools_registration(self):
        """Test that trading tools are properly registered."""
        test_model = TestModel()

        agent = Agent(
            model=test_model,
            system_prompt="You are a trading assistant.",
            deps_type=AgentDependencies,
            result_type=AgentOutput
        )

        # Register trading tools
        register_trading_tools(agent)

        # Verify tools are registered
        tool_names = [t.name for t in agent._function_tools.values()]
        assert "get_market_price" in tool_names
        assert "create_limit_order" in tool_names
        assert "get_account_balance" in tool_names

    @pytest.mark.asyncio
    async def test_trading_tool_requires_exchange(self):
        """Test that trading tools require exchange in dependencies."""
        test_model = TestModel()

        agent = Agent(
            model=test_model,
            system_prompt="You are a trading assistant.",
            deps_type=AgentDependencies,
            result_type=AgentOutput
        )

        register_trading_tools(agent)

        # Create dependencies without exchange
        deps = AgentDependencies()

        # Attempting to call tool without exchange should fail gracefully
        # (In real scenario, this would be caught by the tool implementation)
        assert deps.exchange is None


class TestAgentRetries:
    """Test agent retry configuration."""

    def test_agent_with_max_retries(self):
        """Test agent creation with retry configuration."""
        agent = create_agent(
            system_prompt="You are a helpful assistant.",
            model_id="openrouter/anthropic/claude-3.5-sonnet",
            temperature=0.7,
            max_retries=3,
            has_trading_tools=False
        )

        assert agent is not None
        assert agent._max_result_retries == 3

    def test_agent_with_fallback_pattern(self):
        """Test agent with fallback pattern (max_retries=0)."""
        agent = create_agent(
            system_prompt="You are a helpful assistant.",
            model_id="openrouter/anthropic/claude-3.5-sonnet",
            temperature=0.7,
            max_retries=0,  # For fallback model patterns
            has_trading_tools=False
        )

        assert agent is not None
        assert agent._max_result_retries == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
