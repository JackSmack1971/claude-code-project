"""
Dynamic agent delegation system.
Allows agents to delegate tasks to other agents at runtime.
"""
from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import AgentBlueprint
from agents import create_agent, AgentDependencies, AgentOutput
import logging

logger = logging.getLogger(__name__)


class DelegationContext(BaseModel):
    """
    Context for delegation operations.
    Tracks available agents and shared state.
    """
    db_session: Any  # AsyncSession (can't use directly due to Pydantic)
    available_agents: dict[int, str] = {}  # agent_id -> agent_name mapping
    delegation_history: list[dict[str, Any]] = []
    max_delegation_depth: int = 5  # Prevent infinite delegation loops


class DelegationResult(BaseModel):
    """Result of a delegation operation."""
    agent_id: int
    agent_name: str
    response: str
    reasoning: Optional[str] = None
    timestamp: datetime
    delegation_depth: int


async def get_available_agents(db: AsyncSession) -> dict[int, str]:
    """
    Fetch all active agents from the database.
    Returns a mapping of agent_id -> agent_name.
    """
    result = await db.execute(
        select(AgentBlueprint.id, AgentBlueprint.name)
        .where(AgentBlueprint.is_active == True)
    )
    agents = result.all()
    return {agent_id: agent_name for agent_id, agent_name in agents}


async def delegate_to_agent(
    target_agent_id: int,
    message: str,
    delegation_ctx: DelegationContext,
    shared_context: Optional[dict[str, Any]] = None
) -> DelegationResult:
    """
    Delegate a task to another agent.

    Args:
        target_agent_id: ID of the agent to delegate to
        message: Message/task for the delegated agent
        delegation_ctx: Delegation context with DB session and history
        shared_context: Optional shared state to pass to the agent

    Returns:
        DelegationResult with agent response

    Raises:
        ValueError: If delegation depth exceeded or agent not found
    """
    # Check delegation depth
    current_depth = len(delegation_ctx.delegation_history)
    if current_depth >= delegation_ctx.max_delegation_depth:
        raise ValueError(
            f"Maximum delegation depth ({delegation_ctx.max_delegation_depth}) exceeded. "
            "Possible infinite delegation loop detected."
        )

    # Verify agent exists and is active
    db = delegation_ctx.db_session
    result = await db.execute(
        select(AgentBlueprint)
        .where(
            AgentBlueprint.id == target_agent_id,
            AgentBlueprint.is_active == True
        )
    )
    agent_blueprint = result.scalar_one_or_none()

    if not agent_blueprint:
        raise ValueError(f"Agent with ID {target_agent_id} not found or inactive")

    # Create agent instance from blueprint
    agent = create_agent(
        system_prompt=agent_blueprint.system_prompt,
        model_id=agent_blueprint.model_id,
        temperature=agent_blueprint.temperature,
        max_retries=agent_blueprint.max_retries,
        has_trading_tools=agent_blueprint.has_trading_tools
    )

    # Prepare dependencies with shared context
    deps = AgentDependencies()
    if shared_context:
        deps.model_extra = {"shared_context": shared_context}

    # Execute agent
    logger.info(
        f"Delegating to agent {target_agent_id} ({agent_blueprint.name}): {message[:50]}..."
    )

    try:
        result_data = await agent.run(message, deps=deps)
        agent_output: AgentOutput = result_data.data

        # Create delegation result
        delegation_result = DelegationResult(
            agent_id=target_agent_id,
            agent_name=agent_blueprint.name,
            response=agent_output.response,
            reasoning=agent_output.reasoning,
            timestamp=datetime.utcnow(),
            delegation_depth=current_depth + 1
        )

        # Update delegation history
        delegation_ctx.delegation_history.append({
            "agent_id": target_agent_id,
            "agent_name": agent_blueprint.name,
            "message": message,
            "timestamp": delegation_result.timestamp.isoformat(),
            "depth": delegation_result.delegation_depth
        })

        logger.info(
            f"Delegation successful: {agent_blueprint.name} responded "
            f"({len(agent_output.response)} chars)"
        )

        return delegation_result

    except Exception as e:
        logger.error(f"Delegation to agent {target_agent_id} failed: {str(e)}")
        raise


def register_delegation_tool(
    agent: Agent,
    delegation_ctx: DelegationContext
) -> None:
    """
    Register the delegation tool with an agent.
    Allows the agent to delegate tasks to other agents dynamically.

    Args:
        agent: Pydantic AI agent to augment
        delegation_ctx: Delegation context with available agents
    """

    @agent.tool
    async def delegate_to_another_agent(
        ctx: RunContext[AgentDependencies],
        agent_id: int,
        task_description: str
    ) -> dict[str, Any]:
        """
        Delegate a task to another specialized agent.

        Use this when:
        - The task requires expertise outside your domain
        - Another agent is better suited for the subtask
        - You need to break down a complex task

        Args:
            agent_id: ID of the agent to delegate to (check available_agents)
            task_description: Clear description of what the agent should do

        Returns:
            Response from the delegated agent
        """
        # Validate agent ID
        if agent_id not in delegation_ctx.available_agents:
            available = ", ".join(
                f"{aid}: {name}"
                for aid, name in delegation_ctx.available_agents.items()
            )
            return {
                "error": f"Invalid agent_id {agent_id}. Available agents: {available}"
            }

        # Get shared context from current agent's dependencies
        shared_context = getattr(ctx.deps, "model_extra", {}).get("shared_context", {})

        # Perform delegation
        try:
            result = await delegate_to_agent(
                target_agent_id=agent_id,
                message=task_description,
                delegation_ctx=delegation_ctx,
                shared_context=shared_context
            )

            return {
                "delegated_to": result.agent_name,
                "response": result.response,
                "reasoning": result.reasoning,
                "delegation_depth": result.delegation_depth
            }

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Delegation tool error: {str(e)}")
            return {"error": f"Delegation failed: {str(e)}"}


def create_agent_with_delegation(
    blueprint: AgentBlueprint,
    delegation_ctx: DelegationContext
) -> Agent:
    """
    Create an agent with delegation capabilities.

    Args:
        blueprint: AgentBlueprint from database
        delegation_ctx: Delegation context

    Returns:
        Configured Agent with delegation tool
    """
    from agents import create_agent

    agent = create_agent(
        system_prompt=blueprint.system_prompt,
        model_id=blueprint.model_id,
        temperature=blueprint.temperature,
        max_retries=blueprint.max_retries,
        has_trading_tools=blueprint.has_trading_tools
    )

    # Augment system prompt with delegation instructions
    delegation_prompt = f"""

You have access to a special delegation capability. Available agents:
{chr(10).join(f'- Agent {aid}: {name}' for aid, name in delegation_ctx.available_agents.items())}

Use the `delegate_to_another_agent` tool when:
- A task requires specialized expertise
- You need to break down complex workflows
- Another agent is better suited for a subtask

Current delegation depth: {len(delegation_ctx.delegation_history)}/{delegation_ctx.max_delegation_depth}
"""

    # Update agent's system prompt
    agent._system_prompt = agent._system_prompt + delegation_prompt

    # Register delegation tool
    register_delegation_tool(agent, delegation_ctx)

    return agent
