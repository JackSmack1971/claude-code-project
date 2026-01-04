"""
FastAPI backend for AgentFactory.
Implements lifespan context manager, CRUD endpoints, and streaming chat.
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import httpx

from database import get_db, init_db, dispose_db
from models import AgentBlueprint
from schemas import (
    AgentBlueprintCreate,
    AgentBlueprintUpdate,
    AgentBlueprintResponse,
    AgentBlueprintList,
    ChatRequest,
)
from agents import create_agent, run_agent_stream, AgentDependencies
from tools import TradingContext, get_exchange

# Workflow orchestration imports
from workflow_models import Workflow, WorkflowNode, WorkflowEdge, WorkflowExecution, WorkflowExecutionLog
from workflow_schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowList,
    WorkflowNodeCreate,
    WorkflowNodeUpdate,
    WorkflowNodeResponse,
    WorkflowEdgeCreate,
    WorkflowEdgeUpdate,
    WorkflowEdgeResponse,
    WorkflowGraphResponse,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowExecutionDetailResponse,
    WorkflowExecutionLogResponse,
)
from orchestrator import WorkflowOrchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Handles startup (DB table creation) and shutdown (engine disposal).
    """
    # Startup
    print("🚀 Starting AgentFactory backend...")
    await init_db()
    print("✅ Database initialized")

    yield

    # Shutdown
    print("🛑 Shutting down AgentFactory backend...")
    await dispose_db()
    print("✅ Database engine disposed")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="AgentFactory API",
    description="Backend for AI agent deployment and management",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# CRUD Endpoints for Agent Blueprints
# ============================================================================

@app.post(
    "/agents",
    response_model=AgentBlueprintResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_agent_blueprint(
    blueprint: AgentBlueprintCreate,
    db: AsyncSession = Depends(get_db)
) -> AgentBlueprint:
    """
    Create a new agent blueprint.

    Args:
        blueprint: Agent configuration
        db: Database session

    Returns:
        Created agent blueprint with ID
    """
    db_blueprint = AgentBlueprint(**blueprint.model_dump())
    db.add(db_blueprint)
    await db.flush()
    await db.refresh(db_blueprint)
    return db_blueprint


@app.get("/agents", response_model=AgentBlueprintList)
async def list_agent_blueprints(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    List agent blueprints with pagination.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        active_only: Filter for active agents only
        db: Database session

    Returns:
        Paginated list of agent blueprints
    """
    query = select(AgentBlueprint)

    if active_only:
        query = query.where(AgentBlueprint.is_active == True)

    query = query.offset(skip).limit(limit).order_by(AgentBlueprint.created_at.desc())

    result = await db.execute(query)
    agents = result.scalars().all()

    # Count total
    count_query = select(AgentBlueprint)
    if active_only:
        count_query = count_query.where(AgentBlueprint.is_active == True)

    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return {
        "total": total,
        "agents": agents
    }


@app.get("/agents/{agent_id}", response_model=AgentBlueprintResponse)
async def get_agent_blueprint(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
) -> AgentBlueprint:
    """
    Get a specific agent blueprint by ID.

    Args:
        agent_id: Agent blueprint ID
        db: Database session

    Returns:
        Agent blueprint details

    Raises:
        HTTPException: If agent not found
    """
    query = select(AgentBlueprint).where(AgentBlueprint.id == agent_id)
    result = await db.execute(query)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent blueprint {agent_id} not found"
        )

    return agent


@app.patch("/agents/{agent_id}", response_model=AgentBlueprintResponse)
async def update_agent_blueprint(
    agent_id: int,
    blueprint_update: AgentBlueprintUpdate,
    db: AsyncSession = Depends(get_db)
) -> AgentBlueprint:
    """
    Update an existing agent blueprint.

    Args:
        agent_id: Agent blueprint ID
        blueprint_update: Fields to update
        db: Database session

    Returns:
        Updated agent blueprint

    Raises:
        HTTPException: If agent not found
    """
    # Check if agent exists
    query = select(AgentBlueprint).where(AgentBlueprint.id == agent_id)
    result = await db.execute(query)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent blueprint {agent_id} not found"
        )

    # Update fields
    update_data = blueprint_update.model_dump(exclude_unset=True)
    if update_data:
        stmt = (
            update(AgentBlueprint)
            .where(AgentBlueprint.id == agent_id)
            .values(**update_data)
        )
        await db.execute(stmt)
        await db.flush()
        await db.refresh(agent)

    return agent


@app.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_blueprint(
    agent_id: int,
    hard_delete: bool = False,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete an agent blueprint (soft delete by default).

    Args:
        agent_id: Agent blueprint ID
        hard_delete: If True, permanently delete; if False, soft delete
        db: Database session

    Raises:
        HTTPException: If agent not found
    """
    query = select(AgentBlueprint).where(AgentBlueprint.id == agent_id)
    result = await db.execute(query)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent blueprint {agent_id} not found"
        )

    if hard_delete:
        stmt = delete(AgentBlueprint).where(AgentBlueprint.id == agent_id)
        await db.execute(stmt)
    else:
        stmt = (
            update(AgentBlueprint)
            .where(AgentBlueprint.id == agent_id)
            .values(is_active=False)
        )
        await db.execute(stmt)

    await db.flush()


# ============================================================================
# Agent Execution Endpoints
# ============================================================================

@app.post("/agents/{agent_id}/chat")
async def chat_with_agent(
    agent_id: int,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """
    Chat with an agent using streaming responses.

    CRITICAL: Never pass database session to background tasks.
    Only pass agent_id and recreate resources inside.

    Args:
        agent_id: Agent blueprint ID
        chat_request: User message and conversation history
        db: Database session

    Returns:
        Streaming response with agent output

    Raises:
        HTTPException: If agent not found
    """
    # Fetch agent blueprint
    query = select(AgentBlueprint).where(AgentBlueprint.id == agent_id)
    result = await db.execute(query)
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent blueprint {agent_id} not found"
        )

    # Create agent instance
    agent = create_agent(
        system_prompt=blueprint.system_prompt,
        model_id=blueprint.model_id,
        temperature=blueprint.temperature,
        max_retries=blueprint.max_retries,
        has_trading_tools=blueprint.has_trading_tools
    )

    # Prepare dependencies
    deps = AgentDependencies(
        http_client=httpx.AsyncClient(timeout=60.0)
    )

    # Add trading context if enabled
    if blueprint.has_trading_tools:
        from database import settings
        trading_ctx = TradingContext(
            exchange_id="binance",
            api_key=settings.exchange_api_key if settings.exchange_api_key else None,
            secret=settings.exchange_secret if settings.exchange_secret else None,
            testnet=True
        )
        exchange = get_exchange(trading_ctx)
        await exchange.load_markets()  # CRITICAL: Load markets before operations

        deps.trading_ctx = trading_ctx
        deps.exchange = exchange

    # Stream response
    async def generate() -> AsyncIterator[str]:
        """Generator for streaming response chunks."""
        try:
            async for chunk in run_agent_stream(agent, chat_request.message, deps):
                yield chunk
        finally:
            # Cleanup
            if deps.http_client:
                await deps.http_client.aclose()
            if deps.exchange:
                await deps.exchange.close()

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "agentfactory-backend"}


# ============================================================================
# Workflow Orchestration Endpoints
# ============================================================================

@app.post(
    "/workflows",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_workflow(
    workflow: WorkflowCreate,
    db: AsyncSession = Depends(get_db)
) -> Workflow:
    """
    Create a new workflow.

    Args:
        workflow: Workflow configuration
        db: Database session

    Returns:
        Created workflow with ID
    """
    db_workflow = Workflow(**workflow.model_dump())
    db.add(db_workflow)
    await db.flush()
    await db.refresh(db_workflow)
    return db_workflow


@app.get("/workflows", response_model=WorkflowList)
async def list_workflows(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    List workflows with pagination.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        active_only: Filter for active workflows only
        db: Database session

    Returns:
        Paginated list of workflows
    """
    query = select(Workflow)

    if active_only:
        query = query.where(Workflow.is_active == True)

    query = query.offset(skip).limit(limit).order_by(Workflow.created_at.desc())

    result = await db.execute(query)
    workflows = result.scalars().all()

    # Count total
    count_query = select(Workflow)
    if active_only:
        count_query = count_query.where(Workflow.is_active == True)

    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return {
        "total": total,
        "workflows": workflows
    }


@app.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: int,
    db: AsyncSession = Depends(get_db)
) -> Workflow:
    """Get a specific workflow by ID."""
    query = select(Workflow).where(Workflow.id == workflow_id)
    result = await db.execute(query)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    return workflow


@app.patch("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: int,
    workflow_update: WorkflowUpdate,
    db: AsyncSession = Depends(get_db)
) -> Workflow:
    """Update an existing workflow."""
    query = select(Workflow).where(Workflow.id == workflow_id)
    result = await db.execute(query)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    # Update fields
    update_data = workflow_update.model_dump(exclude_unset=True)
    if update_data:
        stmt = (
            update(Workflow)
            .where(Workflow.id == workflow_id)
            .values(**update_data)
        )
        await db.execute(stmt)
        await db.flush()
        await db.refresh(workflow)

    return workflow


@app.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: int,
    hard_delete: bool = False,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a workflow (soft delete by default)."""
    query = select(Workflow).where(Workflow.id == workflow_id)
    result = await db.execute(query)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    if hard_delete:
        stmt = delete(Workflow).where(Workflow.id == workflow_id)
        await db.execute(stmt)
    else:
        stmt = (
            update(Workflow)
            .where(Workflow.id == workflow_id)
            .values(is_active=False)
        )
        await db.execute(stmt)

    await db.flush()


# ============================================================================
# Workflow Graph Management (Nodes & Edges)
# ============================================================================

@app.post(
    "/workflows/{workflow_id}/nodes",
    response_model=WorkflowNodeResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_workflow_node(
    workflow_id: int,
    node: WorkflowNodeCreate,
    db: AsyncSession = Depends(get_db)
) -> WorkflowNode:
    """Add a node to a workflow."""
    # Verify workflow exists
    workflow_query = select(Workflow).where(Workflow.id == workflow_id)
    workflow_result = await db.execute(workflow_query)
    if not workflow_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    # Create node
    db_node = WorkflowNode(**node.model_dump())
    db.add(db_node)
    await db.flush()
    await db.refresh(db_node)
    return db_node


@app.delete(
    "/workflows/{workflow_id}/nodes/{node_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_workflow_node(
    workflow_id: int,
    node_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove a node from a workflow."""
    query = select(WorkflowNode).where(
        WorkflowNode.id == node_id,
        WorkflowNode.workflow_id == workflow_id
    )
    result = await db.execute(query)
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found in workflow {workflow_id}"
        )

    stmt = delete(WorkflowNode).where(WorkflowNode.id == node_id)
    await db.execute(stmt)
    await db.flush()


@app.post(
    "/workflows/{workflow_id}/edges",
    response_model=WorkflowEdgeResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_workflow_edge(
    workflow_id: int,
    edge: WorkflowEdgeCreate,
    db: AsyncSession = Depends(get_db)
) -> WorkflowEdge:
    """Add an edge (connection) to a workflow."""
    # Verify workflow exists
    workflow_query = select(Workflow).where(Workflow.id == workflow_id)
    workflow_result = await db.execute(workflow_query)
    if not workflow_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    # Create edge
    db_edge = WorkflowEdge(**edge.model_dump())
    db.add(db_edge)
    await db.flush()
    await db.refresh(db_edge)
    return db_edge


@app.delete(
    "/workflows/{workflow_id}/edges/{edge_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_workflow_edge(
    workflow_id: int,
    edge_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove an edge from a workflow."""
    query = select(WorkflowEdge).where(
        WorkflowEdge.id == edge_id,
        WorkflowEdge.workflow_id == workflow_id
    )
    result = await db.execute(query)
    edge = result.scalar_one_or_none()

    if not edge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge {edge_id} not found in workflow {workflow_id}"
        )

    stmt = delete(WorkflowEdge).where(WorkflowEdge.id == edge_id)
    await db.execute(stmt)
    await db.flush()


@app.get("/workflows/{workflow_id}/graph", response_model=WorkflowGraphResponse)
async def get_workflow_graph(
    workflow_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get complete workflow structure (nodes + edges) for visualization."""
    from sqlalchemy.orm import selectinload

    # Load workflow with nodes and edges
    query = select(Workflow).options(
        selectinload(Workflow.nodes),
        selectinload(Workflow.edges)
    ).where(Workflow.id == workflow_id)

    result = await db.execute(query)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow {workflow_id} not found"
        )

    return {
        "workflow": workflow,
        "nodes": workflow.nodes,
        "edges": workflow.edges
    }


# ============================================================================
# Workflow Execution Endpoints
# ============================================================================

@app.post(
    "/workflows/{workflow_id}/execute",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def execute_workflow(
    workflow_id: int,
    execution_request: WorkflowExecutionRequest,
    db: AsyncSession = Depends(get_db)
) -> WorkflowExecution:
    """
    Start async workflow execution.

    Returns execution ID immediately. Use GET /executions/{id} to monitor status.

    Args:
        workflow_id: Workflow to execute
        execution_request: Initial input data
        db: Database session

    Returns:
        Execution record with PENDING/RUNNING status
    """
    orchestrator = WorkflowOrchestrator(db)

    try:
        execution_id = await orchestrator.execute_workflow(
            workflow_id=workflow_id,
            initial_input=execution_request.initial_input
        )

        # Fetch and return execution record
        execution = await orchestrator.get_execution_status(execution_id)
        return execution

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}"
        )


@app.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_execution_status(
    execution_id: int,
    db: AsyncSession = Depends(get_db)
) -> WorkflowExecution:
    """Get current status of a workflow execution."""
    orchestrator = WorkflowOrchestrator(db)

    try:
        execution = await orchestrator.get_execution_status(execution_id)
        return execution
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@app.get(
    "/executions/{execution_id}/logs",
    response_model=WorkflowExecutionDetailResponse
)
async def get_execution_logs(
    execution_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get detailed execution logs for debugging and monitoring."""
    orchestrator = WorkflowOrchestrator(db)

    try:
        execution = await orchestrator.get_execution_status(execution_id)
        logs = await orchestrator.get_execution_logs(execution_id)

        return {
            "execution": execution,
            "logs": logs
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
