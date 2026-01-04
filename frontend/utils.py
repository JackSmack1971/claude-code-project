"""
Utility functions for Streamlit frontend.
Handles API calls to the FastAPI backend.
"""
import httpx
from typing import Optional, AsyncIterator
import streamlit as st


def get_backend_url() -> str:
    """Get backend URL from secrets or environment."""
    try:
        return st.secrets["api"]["backend_url"]
    except KeyError:
        return "http://localhost:8000"


async def create_agent(
    name: str,
    system_prompt: str,
    model_id: str,
    temperature: float,
    has_trading_tools: bool
) -> dict:
    """
    Create a new agent blueprint via API.

    Args:
        name: Agent name
        system_prompt: System instructions
        model_id: OpenRouter model ID
        temperature: Sampling temperature
        has_trading_tools: Enable trading tools

    Returns:
        Created agent blueprint

    Raises:
        httpx.HTTPError: If API request fails
    """
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{backend_url}/agents",
            json={
                "name": name,
                "system_prompt": system_prompt,
                "model_id": model_id,
                "temperature": temperature,
                "has_trading_tools": has_trading_tools,
                "max_retries": 0
            }
        )
        response.raise_for_status()
        return response.json()


async def get_agents(active_only: bool = True) -> list[dict]:
    """
    Fetch all agent blueprints.

    Args:
        active_only: Filter for active agents only

    Returns:
        List of agent blueprints
    """
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{backend_url}/agents",
            params={"active_only": active_only, "limit": 100}
        )
        response.raise_for_status()
        data = response.json()
        return data["agents"]


async def get_agent(agent_id: int) -> dict:
    """
    Fetch a specific agent blueprint.

    Args:
        agent_id: Agent blueprint ID

    Returns:
        Agent blueprint details
    """
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{backend_url}/agents/{agent_id}")
        response.raise_for_status()
        return response.json()


async def update_agent(agent_id: int, **kwargs) -> dict:
    """
    Update an existing agent blueprint.

    Args:
        agent_id: Agent blueprint ID
        **kwargs: Fields to update

    Returns:
        Updated agent blueprint
    """
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.patch(
            f"{backend_url}/agents/{agent_id}",
            json=kwargs
        )
        response.raise_for_status()
        return response.json()


async def delete_agent(agent_id: int, hard_delete: bool = False) -> None:
    """
    Delete an agent blueprint.

    Args:
        agent_id: Agent blueprint ID
        hard_delete: Permanent deletion if True, soft delete otherwise
    """
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{backend_url}/agents/{agent_id}",
            params={"hard_delete": hard_delete}
        )
        response.raise_for_status()


async def chat_with_agent_stream(
    agent_id: int,
    message: str
) -> AsyncIterator[str]:
    """
    Send a chat message to an agent and stream the response.

    Args:
        agent_id: Agent blueprint ID
        message: User message

    Yields:
        Response chunks from the agent
    """
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            f"{backend_url}/agents/{agent_id}/chat",
            json={
                "agent_id": agent_id,
                "message": message,
                "conversation_history": []
            }
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_text():
                if chunk:
                    yield chunk


def initialize_session_state() -> None:
    """Initialize Streamlit session state variables."""
    if "selected_agent_id" not in st.session_state:
        st.session_state.selected_agent_id = None

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "agents_cache" not in st.session_state:
        st.session_state.agents_cache = None

    if "selected_workflow_id" not in st.session_state:
        st.session_state.selected_workflow_id = None


# ============================================================================
# Workflow API Functions
# ============================================================================

async def create_workflow(name: str, description: Optional[str] = None) -> dict:
    """
    Create a new workflow.

    Args:
        name: Workflow name
        description: Optional description

    Returns:
        Created workflow
    """
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{backend_url}/workflows",
            json={"name": name, "description": description}
        )
        response.raise_for_status()
        return response.json()


async def get_workflows(active_only: bool = True) -> list[dict]:
    """
    Fetch all workflows.

    Args:
        active_only: Filter for active workflows only

    Returns:
        List of workflows
    """
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{backend_url}/workflows",
            params={"active_only": active_only, "limit": 100}
        )
        response.raise_for_status()
        data = response.json()
        return data["workflows"]


async def get_workflow(workflow_id: int) -> dict:
    """Fetch a specific workflow."""
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{backend_url}/workflows/{workflow_id}")
        response.raise_for_status()
        return response.json()


async def get_workflow_graph(workflow_id: int) -> dict:
    """
    Fetch workflow graph (nodes + edges).

    Returns:
        Dict with "workflow", "nodes", and "edges"
    """
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{backend_url}/workflows/{workflow_id}/graph")
        response.raise_for_status()
        return response.json()


async def delete_workflow(workflow_id: int, hard_delete: bool = False) -> None:
    """Delete a workflow."""
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{backend_url}/workflows/{workflow_id}",
            params={"hard_delete": hard_delete}
        )
        response.raise_for_status()


async def create_workflow_node(
    workflow_id: int,
    name: str,
    node_type: str,
    agent_id: Optional[int] = None,
    position: int = 0
) -> dict:
    """Create a node in a workflow."""
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{backend_url}/workflows/{workflow_id}/nodes",
            json={
                "workflow_id": workflow_id,
                "name": name,
                "node_type": node_type,
                "agent_id": agent_id,
                "position": position,
                "config": {}
            }
        )
        response.raise_for_status()
        return response.json()


async def create_workflow_edge(
    workflow_id: int,
    source_node_id: int,
    target_node_id: int,
    label: Optional[str] = None
) -> dict:
    """Create an edge (connection) in a workflow."""
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{backend_url}/workflows/{workflow_id}/edges",
            json={
                "workflow_id": workflow_id,
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "label": label,
                "condition": None
            }
        )
        response.raise_for_status()
        return response.json()


async def delete_workflow_node(workflow_id: int, node_id: int) -> None:
    """Delete a node from a workflow."""
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{backend_url}/workflows/{workflow_id}/nodes/{node_id}"
        )
        response.raise_for_status()


async def delete_workflow_edge(workflow_id: int, edge_id: int) -> None:
    """Delete an edge from a workflow."""
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{backend_url}/workflows/{workflow_id}/edges/{edge_id}"
        )
        response.raise_for_status()


async def execute_workflow(workflow_id: int, initial_input: dict) -> dict:
    """
    Execute a workflow asynchronously.

    Args:
        workflow_id: Workflow to execute
        initial_input: Initial data/message

    Returns:
        Execution record with ID
    """
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{backend_url}/workflows/{workflow_id}/execute",
            json={"initial_input": initial_input}
        )
        response.raise_for_status()
        return response.json()


async def get_execution_status(execution_id: int) -> dict:
    """Get workflow execution status."""
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{backend_url}/executions/{execution_id}")
        response.raise_for_status()
        return response.json()


async def get_execution_logs(execution_id: int) -> dict:
    """
    Get detailed execution logs.

    Returns:
        Dict with "execution" and "logs"
    """
    backend_url = get_backend_url()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{backend_url}/executions/{execution_id}/logs")
        response.raise_for_status()
        return response.json()
