"""
Pydantic schemas for workflow orchestration API.
Implements request/response validation for workflow management.
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from workflow_models import WorkflowStatus, NodeType


# ============================================================================
# Workflow Schemas
# ============================================================================

class WorkflowBase(BaseModel):
    """Base schema for workflow attributes."""
    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow purpose and behavior")


class WorkflowCreate(WorkflowBase):
    """Schema for creating a new workflow."""
    pass


class WorkflowUpdate(BaseModel):
    """Schema for updating an existing workflow. All fields optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class WorkflowResponse(WorkflowBase):
    """Schema for workflow responses."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowList(BaseModel):
    """Schema for paginated list of workflows."""
    total: int
    workflows: list[WorkflowResponse]


# ============================================================================
# Workflow Node Schemas
# ============================================================================

class WorkflowNodeBase(BaseModel):
    """Base schema for workflow node attributes."""
    name: str = Field(..., min_length=1, max_length=255, description="Node display name")
    node_type: NodeType = Field(..., description="Type of node (agent, condition, start, end)")
    agent_id: Optional[int] = Field(None, description="Agent blueprint ID (required if node_type=AGENT)")
    config: Optional[dict[str, Any]] = Field(None, description="Node-specific configuration")
    position: int = Field(default=0, description="Execution order hint")


class WorkflowNodeCreate(WorkflowNodeBase):
    """Schema for creating a new workflow node."""
    workflow_id: int = Field(..., description="Parent workflow ID")


class WorkflowNodeUpdate(BaseModel):
    """Schema for updating a workflow node. All fields optional."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    agent_id: Optional[int] = None
    config: Optional[dict[str, Any]] = None
    position: Optional[int] = None


class WorkflowNodeResponse(WorkflowNodeBase):
    """Schema for workflow node responses."""
    id: int
    workflow_id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Workflow Edge Schemas
# ============================================================================

class WorkflowEdgeBase(BaseModel):
    """Base schema for workflow edge attributes."""
    source_node_id: int = Field(..., description="Source node ID")
    target_node_id: int = Field(..., description="Target node ID")
    condition: Optional[str] = Field(None, description="Optional condition (JSON path or expression)")
    label: Optional[str] = Field(None, max_length=255, description="Edge label")


class WorkflowEdgeCreate(WorkflowEdgeBase):
    """Schema for creating a new workflow edge."""
    workflow_id: int = Field(..., description="Parent workflow ID")


class WorkflowEdgeUpdate(BaseModel):
    """Schema for updating a workflow edge. All fields optional."""
    condition: Optional[str] = None
    label: Optional[str] = Field(None, max_length=255)


class WorkflowEdgeResponse(WorkflowEdgeBase):
    """Schema for workflow edge responses."""
    id: int
    workflow_id: int

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Workflow Graph Schema (Combined Nodes + Edges)
# ============================================================================

class WorkflowGraphResponse(BaseModel):
    """
    Combined workflow structure for visualization and execution.
    Contains both nodes and edges.
    """
    workflow: WorkflowResponse
    nodes: list[WorkflowNodeResponse]
    edges: list[WorkflowEdgeResponse]


# ============================================================================
# Workflow Execution Schemas
# ============================================================================

class WorkflowExecutionRequest(BaseModel):
    """Schema for starting a workflow execution."""
    initial_input: dict[str, Any] = Field(
        default_factory=dict,
        description="Initial data/message for workflow"
    )


class WorkflowExecutionResponse(BaseModel):
    """Schema for workflow execution status responses."""
    id: int
    workflow_id: int
    status: WorkflowStatus
    initial_input: Optional[dict[str, Any]]
    final_output: Optional[dict[str, Any]]
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class WorkflowExecutionLogResponse(BaseModel):
    """Schema for individual execution log entries."""
    id: int
    execution_id: int
    node_id: Optional[int]
    agent_id: Optional[int]
    input_data: Optional[dict[str, Any]]
    output_data: Optional[dict[str, Any]]
    error_message: Optional[str]
    is_delegation: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowExecutionDetailResponse(BaseModel):
    """
    Detailed execution response with all logs.
    Used for monitoring and debugging.
    """
    execution: WorkflowExecutionResponse
    logs: list[WorkflowExecutionLogResponse]


# ============================================================================
# Dynamic Delegation Schemas
# ============================================================================

class DelegationRequest(BaseModel):
    """
    Schema for dynamic agent delegation.
    Used when an agent decides to delegate to another agent.
    """
    target_agent_id: int = Field(..., description="Agent to delegate to")
    message: str = Field(..., min_length=1, description="Message for delegated agent")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Shared context to pass"
    )


class DelegationResponse(BaseModel):
    """Response from a delegated agent call."""
    agent_id: int
    response: str
    context: dict[str, Any]
    timestamp: datetime
