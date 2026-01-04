"""
SQLAlchemy models for Multi-Agent Orchestration.
Defines workflow DAGs, execution tracking, and delegation logs.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, Text, DateTime, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
import enum


class WorkflowStatus(str, enum.Enum):
    """Workflow execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeType(str, enum.Enum):
    """Types of nodes in a workflow."""
    AGENT = "agent"  # Execute a specific agent
    CONDITION = "condition"  # Branch based on condition
    START = "start"  # Entry point
    END = "end"  # Terminal node


class Workflow(Base):
    """
    Workflow definition - a DAG of agent executions.

    Attributes:
        id: Primary key
        name: Human-readable workflow name
        description: Purpose and behavior description
        is_active: Soft delete flag
        created_at: Timestamp of creation
        updated_at: Timestamp of last modification
        nodes: Related workflow nodes
        edges: Related workflow edges
        executions: Historical executions of this workflow
    """
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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

    # Relationships
    nodes: Mapped[list["WorkflowNode"]] = relationship(
        "WorkflowNode",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    edges: Mapped[list["WorkflowEdge"]] = relationship(
        "WorkflowEdge",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    executions: Mapped[list["WorkflowExecution"]] = relationship(
        "WorkflowExecution",
        back_populates="workflow"
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, name='{self.name}')>"


class WorkflowNode(Base):
    """
    A node in the workflow DAG.
    Can be an agent execution, conditional branch, or start/end marker.

    Attributes:
        id: Primary key
        workflow_id: Foreign key to parent workflow
        node_type: Type of node (agent, condition, start, end)
        agent_id: Foreign key to AgentBlueprint (if node_type == AGENT)
        name: Display name for this node
        config: JSON configuration (conditions, parameters)
        position: Execution order hint (for UI and topological sort)
    """
    __tablename__ = "workflow_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    node_type: Mapped[NodeType] = mapped_column(
        Enum(NodeType, native_enum=False, length=20),
        nullable=False
    )
    agent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("agent_blueprints.id", ondelete="SET NULL"),
        nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="nodes")
    agent: Mapped[Optional["AgentBlueprint"]] = relationship("AgentBlueprint")
    outgoing_edges: Mapped[list["WorkflowEdge"]] = relationship(
        "WorkflowEdge",
        foreign_keys="WorkflowEdge.source_node_id",
        back_populates="source_node"
    )
    incoming_edges: Mapped[list["WorkflowEdge"]] = relationship(
        "WorkflowEdge",
        foreign_keys="WorkflowEdge.target_node_id",
        back_populates="target_node"
    )

    def __repr__(self) -> str:
        return f"<WorkflowNode(id={self.id}, name='{self.name}', type={self.node_type})>"


class WorkflowEdge(Base):
    """
    An edge connecting two nodes in the workflow DAG.
    Represents execution flow and can include conditional logic.

    Attributes:
        id: Primary key
        workflow_id: Foreign key to parent workflow
        source_node_id: Starting node
        target_node_id: Destination node
        condition: Optional JSON path condition (e.g., "$.sentiment == 'positive'")
        label: Human-readable edge label
    """
    __tablename__ = "workflow_edges"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_node_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_nodes.id", ondelete="CASCADE"),
        nullable=False
    )
    target_node_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_nodes.id", ondelete="CASCADE"),
        nullable=False
    )
    condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="edges")
    source_node: Mapped["WorkflowNode"] = relationship(
        "WorkflowNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_edges"
    )
    target_node: Mapped["WorkflowNode"] = relationship(
        "WorkflowNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_edges"
    )

    def __repr__(self) -> str:
        return f"<WorkflowEdge(id={self.id}, {self.source_node_id} → {self.target_node_id})>"


class WorkflowExecution(Base):
    """
    A single execution instance of a workflow.
    Tracks status, timing, and final output.

    Attributes:
        id: Primary key (also serves as execution_id for API)
        workflow_id: Foreign key to workflow definition
        status: Current execution status
        initial_input: User's starting message/data (JSON)
        final_output: Workflow result (JSON)
        error_message: Error details if status == FAILED
        started_at: Execution start timestamp
        completed_at: Execution end timestamp
        logs: Related execution logs (per-node outputs)
    """
    __tablename__ = "workflow_executions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, native_enum=False, length=20),
        default=WorkflowStatus.PENDING,
        nullable=False,
        index=True
    )
    initial_input: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    final_output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="executions")
    logs: Mapped[list["WorkflowExecutionLog"]] = relationship(
        "WorkflowExecutionLog",
        back_populates="execution",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<WorkflowExecution(id={self.id}, workflow={self.workflow_id}, status={self.status})>"


class WorkflowExecutionLog(Base):
    """
    Granular log entry for each node execution within a workflow run.
    Stores agent responses, delegation events, and timing.

    Attributes:
        id: Primary key
        execution_id: Foreign key to parent execution
        node_id: Which node was executed
        agent_id: Which agent was used (may differ from node.agent_id if delegated)
        input_data: Input received by this node (JSON)
        output_data: Output produced by this node (JSON)
        error_message: Error details if node failed
        is_delegation: Whether this was a dynamic delegation call
        timestamp: When this node completed
    """
    __tablename__ = "workflow_execution_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    node_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("workflow_nodes.id", ondelete="SET NULL"),
        nullable=True
    )
    agent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("agent_blueprints.id", ondelete="SET NULL"),
        nullable=True
    )
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_delegation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    execution: Mapped["WorkflowExecution"] = relationship(
        "WorkflowExecution",
        back_populates="logs"
    )
    node: Mapped[Optional["WorkflowNode"]] = relationship("WorkflowNode")
    agent: Mapped[Optional["AgentBlueprint"]] = relationship("AgentBlueprint")

    def __repr__(self) -> str:
        return f"<WorkflowExecutionLog(id={self.id}, node={self.node_id}, agent={self.agent_id})>"
