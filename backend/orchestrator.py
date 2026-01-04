"""
Workflow orchestration engine.
Executes workflows as DAGs with topological sorting and state management.
"""
from typing import Any, Optional
from datetime import datetime
from collections import deque, defaultdict
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from workflow_models import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowExecutionLog,
    WorkflowStatus,
    NodeType
)
from models import AgentBlueprint
from delegation import (
    DelegationContext,
    get_available_agents,
    create_agent_with_delegation
)
from agents import create_agent, AgentDependencies

logger = logging.getLogger(__name__)


class DAGValidationError(Exception):
    """Raised when workflow DAG is invalid (cycles, missing nodes, etc.)."""
    pass


class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails."""
    pass


class WorkflowOrchestrator:
    """
    Orchestrates workflow execution with DAG validation and state management.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_workflow(
        self,
        workflow_id: int,
        initial_input: dict[str, Any]
    ) -> int:
        """
        Execute a workflow asynchronously.

        Args:
            workflow_id: ID of workflow to execute
            initial_input: Initial data/message for workflow

        Returns:
            Execution ID for tracking status

        Raises:
            DAGValidationError: If workflow structure is invalid
            WorkflowExecutionError: If execution fails
        """
        # Load workflow with nodes and edges
        workflow = await self._load_workflow(workflow_id)

        # Create execution record
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING,
            initial_input=initial_input,
            started_at=datetime.utcnow()
        )
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)

        logger.info(f"Created execution {execution.id} for workflow {workflow_id}")

        # Execute workflow in background (async task)
        asyncio.create_task(
            self._run_workflow_async(execution.id, workflow, initial_input)
        )

        return execution.id

    async def _load_workflow(self, workflow_id: int) -> Workflow:
        """Load workflow with all nodes and edges."""
        result = await self.db.execute(
            select(Workflow)
            .options(
                selectinload(Workflow.nodes).selectinload(WorkflowNode.agent),
                selectinload(Workflow.edges)
            )
            .where(
                Workflow.id == workflow_id,
                Workflow.is_active == True
            )
        )
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found or inactive")

        return workflow

    async def _run_workflow_async(
        self,
        execution_id: int,
        workflow: Workflow,
        initial_input: dict[str, Any]
    ) -> None:
        """
        Run workflow execution in background.
        Updates execution status in database.
        """
        try:
            # Update status to RUNNING
            await self._update_execution_status(execution_id, WorkflowStatus.RUNNING)

            # Validate DAG structure
            execution_order = self._topological_sort(workflow)

            # Initialize delegation context
            delegation_ctx = DelegationContext(
                db_session=self.db,
                available_agents=await get_available_agents(self.db)
            )

            # Execute nodes in topological order
            shared_context = {"initial_input": initial_input}
            final_output = None

            for node in execution_order:
                logger.info(f"Executing node {node.id} ({node.name})")

                node_output = await self._execute_node(
                    node=node,
                    context=shared_context,
                    delegation_ctx=delegation_ctx,
                    execution_id=execution_id
                )

                # Update shared context with node output
                shared_context[f"node_{node.id}_output"] = node_output
                shared_context["last_output"] = node_output

                # If this is an END node, capture final output
                if node.node_type == NodeType.END:
                    final_output = node_output

            # Mark execution as completed
            await self._update_execution_status(
                execution_id,
                WorkflowStatus.COMPLETED,
                final_output=final_output or shared_context
            )

            logger.info(f"Workflow execution {execution_id} completed successfully")

        except Exception as e:
            logger.error(f"Workflow execution {execution_id} failed: {str(e)}")
            await self._update_execution_status(
                execution_id,
                WorkflowStatus.FAILED,
                error_message=str(e)
            )

    def _topological_sort(self, workflow: Workflow) -> list[WorkflowNode]:
        """
        Perform topological sort on workflow nodes.
        Returns nodes in execution order.

        Raises:
            DAGValidationError: If graph has cycles or is invalid
        """
        # Build adjacency list and in-degree map
        adj_list = defaultdict(list)
        in_degree = defaultdict(int)
        nodes_map = {node.id: node for node in workflow.nodes}

        # Initialize all nodes with in-degree 0
        for node in workflow.nodes:
            if node.id not in in_degree:
                in_degree[node.id] = 0

        # Build graph from edges
        for edge in workflow.edges:
            adj_list[edge.source_node_id].append(edge.target_node_id)
            in_degree[edge.target_node_id] += 1

        # Find START nodes (in-degree 0 or explicitly marked as START)
        queue = deque()
        for node in workflow.nodes:
            if node.node_type == NodeType.START or in_degree[node.id] == 0:
                queue.append(node.id)

        if not queue:
            raise DAGValidationError("No START node found in workflow")

        # Kahn's algorithm for topological sort
        sorted_nodes = []
        while queue:
            node_id = queue.popleft()
            sorted_nodes.append(nodes_map[node_id])

            # Reduce in-degree for neighbors
            for neighbor_id in adj_list[node_id]:
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)

        # Check for cycles
        if len(sorted_nodes) != len(workflow.nodes):
            raise DAGValidationError(
                "Workflow contains cycles or unreachable nodes. "
                f"Expected {len(workflow.nodes)} nodes, got {len(sorted_nodes)}"
            )

        logger.info(
            f"Topological sort complete: {[n.name for n in sorted_nodes]}"
        )

        return sorted_nodes

    async def _execute_node(
        self,
        node: WorkflowNode,
        context: dict[str, Any],
        delegation_ctx: DelegationContext,
        execution_id: int
    ) -> dict[str, Any]:
        """
        Execute a single workflow node.

        Args:
            node: Node to execute
            context: Shared context from previous nodes
            delegation_ctx: Delegation context for agent calls
            execution_id: Execution ID for logging

        Returns:
            Node output (merged into shared context)
        """
        log_entry = WorkflowExecutionLog(
            execution_id=execution_id,
            node_id=node.id,
            agent_id=node.agent_id,
            input_data=context.copy(),
            timestamp=datetime.utcnow()
        )

        try:
            if node.node_type == NodeType.START:
                # START node just passes through initial input
                output = context.get("initial_input", {})

            elif node.node_type == NodeType.END:
                # END node aggregates final output
                output = {
                    "final_result": context.get("last_output"),
                    "full_context": context
                }

            elif node.node_type == NodeType.AGENT:
                # Execute agent node
                if not node.agent_id:
                    raise ValueError(f"Node {node.id} is type AGENT but has no agent_id")

                output = await self._execute_agent_node(
                    node=node,
                    context=context,
                    delegation_ctx=delegation_ctx
                )

            elif node.node_type == NodeType.CONDITION:
                # Conditional branching (future enhancement)
                # For v1, just pass through
                output = context.get("last_output", {})

            else:
                raise ValueError(f"Unknown node type: {node.node_type}")

            # Log successful execution
            log_entry.output_data = output
            self.db.add(log_entry)
            await self.db.commit()

            return output

        except Exception as e:
            # Log failure
            log_entry.error_message = str(e)
            self.db.add(log_entry)
            await self.db.commit()
            raise

    async def _execute_agent_node(
        self,
        node: WorkflowNode,
        context: dict[str, Any],
        delegation_ctx: DelegationContext
    ) -> dict[str, Any]:
        """
        Execute an agent node with delegation support.

        Args:
            node: Agent node to execute
            context: Shared context
            delegation_ctx: Delegation context

        Returns:
            Agent response as dict
        """
        # Load agent blueprint
        result = await self.db.execute(
            select(AgentBlueprint).where(AgentBlueprint.id == node.agent_id)
        )
        agent_blueprint = result.scalar_one_or_none()

        if not agent_blueprint:
            raise ValueError(f"Agent {node.agent_id} not found")

        # Create agent with delegation capabilities
        agent = create_agent_with_delegation(
            blueprint=agent_blueprint,
            delegation_ctx=delegation_ctx
        )

        # Prepare message from context
        # Use last_output or initial_input as the message
        message = context.get("last_output", {})
        if isinstance(message, dict):
            message = message.get("response", str(message))
        elif not isinstance(message, str):
            message = str(message)

        # If this is the first node after START, use initial_input
        if not message or message == "{}":
            initial = context.get("initial_input", {})
            message = initial.get("message", str(initial))

        # Create dependencies with shared context
        deps = AgentDependencies()
        deps.model_extra = {"shared_context": context}

        # Execute agent
        logger.info(f"Running agent {agent_blueprint.name}: {message[:100]}...")

        try:
            result_data = await agent.run(message, deps=deps)
            agent_output = result_data.data

            return {
                "agent_id": agent_blueprint.id,
                "agent_name": agent_blueprint.name,
                "response": agent_output.response,
                "reasoning": agent_output.reasoning,
                "tool_calls": agent_output.tool_calls,
                "delegation_history": delegation_ctx.delegation_history.copy()
            }

        except Exception as e:
            logger.error(f"Agent {agent_blueprint.name} execution failed: {str(e)}")
            raise

    async def _update_execution_status(
        self,
        execution_id: int,
        status: WorkflowStatus,
        final_output: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update execution status in database."""
        result = await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one()

        execution.status = status
        if status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
            execution.completed_at = datetime.utcnow()
        if final_output:
            execution.final_output = final_output
        if error_message:
            execution.error_message = error_message

        await self.db.commit()
        logger.info(f"Execution {execution_id} status updated to {status}")

    async def get_execution_status(self, execution_id: int) -> WorkflowExecution:
        """Get current execution status."""
        result = await self.db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        return execution

    async def get_execution_logs(self, execution_id: int) -> list[WorkflowExecutionLog]:
        """Get detailed execution logs for debugging."""
        result = await self.db.execute(
            select(WorkflowExecutionLog)
            .where(WorkflowExecutionLog.execution_id == execution_id)
            .order_by(WorkflowExecutionLog.timestamp)
        )
        return list(result.scalars().all())
