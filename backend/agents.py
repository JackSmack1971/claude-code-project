"""
Pydantic AI agent factory with OpenRouter integration.
Implements agent creation, streaming, and tool calling.
"""
from typing import Any, Optional, AsyncIterator
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openrouter import OpenRouterModel
from openrouter_agent import OpenRouterAgent
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from database import settings
import tools


class AgentDependencies(BaseModel):
    """
    Dependencies injected into agent context.
    External resources like HTTP clients or exchange connections.
    """
    http_client: Optional[httpx.AsyncClient] = None
    trading_ctx: Optional[tools.TradingContext] = None
    exchange: Optional[Any] = None  # ccxt.Exchange


class AgentOutput(BaseModel):
    """
    Structured output schema for agent responses.
    Ensures type-safe validation of agent results.
    """
    response: str
    reasoning: Optional[str] = None
    tool_calls: list[dict[str, Any]] = []


def create_agent(
    system_prompt: str,
    model_id: str,
    temperature: float = 0.7,
    max_retries: int = 0,
    has_trading_tools: bool = False
) -> Agent[AgentDependencies, AgentOutput]:
    """
    Factory function to create a configured Pydantic AI agent.

    Args:
        system_prompt: Instructions defining agent behavior
        model_id: OpenRouter model identifier
        temperature: Sampling temperature (0.0-2.0)
        max_retries: Retry attempts (0 for fallback pattern)
        has_trading_tools: Whether to enable CCXT trading tools

    Returns:
        Configured Agent instance

    Example:
        agent = create_agent(
            system_prompt="You are a helpful trading assistant",
            model_id="openrouter/anthropic/claude-3.5-sonnet",
            temperature=0.7,
            has_trading_tools=True
        )
    """
    # Initialize OpenRouter model
    model = OpenRouterModel(
        model_id=model_id,
        api_key=settings.openrouter_api_key,
        http_client=httpx.AsyncClient(timeout=60.0)
    )

    # Create agent with dependencies type
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        deps_type=AgentDependencies,
        result_type=AgentOutput,
        retries=max_retries
    )

    # Register trading tools if enabled
    if has_trading_tools:
        register_trading_tools(agent)

    return agent


def register_trading_tools(agent: Agent) -> None:
    """
    Register CCXT trading tools with the agent.

    CRITICAL: Exchange must be initialized in dependencies
    with enableRateLimit=True and markets loaded.
    """

    @agent.tool
    async def get_market_price(
        ctx: RunContext[AgentDependencies],
        symbol: str
    ) -> dict[str, Any]:
        """Get current market price for a trading pair."""
        if not ctx.deps.exchange:
            raise ValueError("Trading exchange not initialized in context")

        return await tools.get_market_price(symbol, ctx.deps.exchange)

    @agent.tool
    async def create_limit_order(
        ctx: RunContext[AgentDependencies],
        symbol: str,
        side: str,
        amount: float,
        price: float
    ) -> dict[str, Any]:
        """Create a limit buy or sell order with proper precision."""
        if not ctx.deps.exchange:
            raise ValueError("Trading exchange not initialized in context")

        return await tools.create_limit_order(
            symbol, side, amount, price, ctx.deps.exchange
        )

    @agent.tool
    async def get_account_balance(
        ctx: RunContext[AgentDependencies]
    ) -> dict[str, Any]:
        """Get account balance across all assets."""
        if not ctx.deps.exchange:
            raise ValueError("Trading exchange not initialized in context")

        return await tools.get_account_balance(ctx.deps.exchange)


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=16),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException))
)
async def run_agent(
    agent: Agent,
    message: str,
    deps: Optional[AgentDependencies] = None
) -> AgentOutput:
    """
    Run agent with a single message and dependencies.

    Implements exponential backoff for rate limit and provider errors.

    Args:
        agent: Configured Pydantic AI agent
        message: User message
        deps: Optional dependencies for context

    Returns:
        Structured agent output
    """
    if deps is None:
        deps = AgentDependencies()

    result = await agent.run(message, deps=deps)
    return result.data


async def run_agent_stream(
    agent: Agent,
    message: str,
    deps: Optional[AgentDependencies] = None
) -> AsyncIterator[str]:
    """
    Run agent with streaming output.

    Yields chunks of the response as they're generated.

    Args:
        agent: Configured Pydantic AI agent
        message: User message
        deps: Optional dependencies for context

    Yields:
        Response chunks as strings
    """
    if deps is None:
        deps = AgentDependencies()

    async with agent.run_stream(message, deps=deps) as stream:
        async for chunk in stream.stream_text():
            yield chunk
