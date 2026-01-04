# Multi-Agent Orchestration System

**AgentFactory** now supports **Multi-Agent Orchestration** with dynamic delegation, enabling you to build complex AI workflows where agents collaborate and delegate tasks to each other.

---

## 🎯 Features

### 1. **DAG-Based Workflows**
- Define workflows as Directed Acyclic Graphs (DAGs)
- Automatic topological sorting for execution order
- Supports parallel execution of independent branches (future enhancement)

### 2. **Dynamic Agent Delegation**
- Agents can delegate tasks to other agents at runtime
- Delegation depth limits prevent infinite loops
- Shared context passed between agents

### 3. **Async Execution**
- Workflows run asynchronously in the background
- Real-time status tracking via execution ID
- Detailed logging of each node execution

### 4. **Form-Based Builder**
- Intuitive Streamlit UI for workflow construction
- No coding required - build workflows visually
- Support for START, AGENT, END, and CONDITION nodes

---

## 📐 Architecture

### Database Schema

```
┌─────────────────┐
│   Workflow      │  (Workflow definition)
├─────────────────┤
│ id              │
│ name            │
│ description     │
│ is_active       │
└─────────────────┘
         │
         ├── WorkflowNode  (Nodes in the DAG)
         │   ├── id
         │   ├── node_type (start/agent/end/condition)
         │   ├── agent_id  (FK to AgentBlueprint)
         │   └── position
         │
         ├── WorkflowEdge  (Connections between nodes)
         │   ├── id
         │   ├── source_node_id
         │   ├── target_node_id
         │   └── condition (optional)
         │
         └── WorkflowExecution  (Execution instances)
             ├── id
             ├── status (pending/running/completed/failed)
             ├── initial_input
             ├── final_output
             └── WorkflowExecutionLog  (Per-node logs)
                 ├── node_id
                 ├── agent_id
                 ├── input_data
                 ├── output_data
                 └── is_delegation
```

### Execution Flow

```
User initiates workflow
         ↓
Orchestrator creates WorkflowExecution record (status: PENDING)
         ↓
Background task started (status: RUNNING)
         ↓
Topological sort determines execution order
         ↓
For each node in order:
  ├── Load agent blueprint
  ├── Create agent with delegation tool
  ├── Execute agent with shared context
  ├── Log output to WorkflowExecutionLog
  └── Update shared context
         ↓
Mark execution as COMPLETED/FAILED
         ↓
User polls /executions/{id} for status
```

### Dynamic Delegation Flow

```
Agent A receives task
         ↓
Agent A determines it needs specialized help
         ↓
Agent A calls delegate_to_another_agent(agent_id=B, task="...")
         ↓
DelegationContext validates:
  ├── Agent B exists?
  ├── Delegation depth < max?
  └── Shared context available?
         ↓
Agent B is instantiated and executed
         ↓
Agent B's response returned to Agent A
         ↓
Agent A incorporates response and continues
         ↓
Delegation logged in WorkflowExecutionLog
```

---

## 🚀 Usage Guide

### Creating a Workflow

1. **Navigate to Workflows Page**
   - Go to `📚 Workflows` in Streamlit

2. **Create New Workflow**
   ```
   Name: Research → Summarize → Report
   Description: Automated research workflow
   ```

3. **Add Nodes** (in Workflow Builder)
   - Add START node (position 0)
   - Add AGENT node "Researcher" (position 1, select agent)
   - Add AGENT node "Summarizer" (position 2, select agent)
   - Add END node (position 3)

4. **Connect Nodes**
   - START → Researcher
   - Researcher → Summarizer
   - Summarizer → END

5. **Execute Workflow**
   ```
   Initial Message: "Research the latest trends in AI orchestration"
   ```

6. **Monitor Execution**
   - Workflow runs async
   - Check status with execution ID
   - View logs for each agent's output

---

## 🛠️ API Reference

### Workflow Endpoints

#### Create Workflow
```http
POST /workflows
Content-Type: application/json

{
  "name": "My Workflow",
  "description": "Description here"
}
```

#### List Workflows
```http
GET /workflows?active_only=true&limit=100
```

#### Get Workflow Graph
```http
GET /workflows/{workflow_id}/graph
```

**Response:**
```json
{
  "workflow": {...},
  "nodes": [
    {
      "id": 1,
      "name": "Start",
      "node_type": "start",
      "position": 0
    },
    ...
  ],
  "edges": [
    {
      "id": 1,
      "source_node_id": 1,
      "target_node_id": 2
    },
    ...
  ]
}
```

#### Execute Workflow
```http
POST /workflows/{workflow_id}/execute
Content-Type: application/json

{
  "initial_input": {
    "message": "Your task here"
  }
}
```

**Response (202 Accepted):**
```json
{
  "id": 42,
  "workflow_id": 1,
  "status": "pending",
  "initial_input": {...},
  "started_at": "2026-01-04T10:00:00Z"
}
```

#### Get Execution Status
```http
GET /executions/{execution_id}
```

**Response:**
```json
{
  "id": 42,
  "status": "completed",
  "final_output": {
    "final_result": {...},
    "full_context": {...}
  },
  "completed_at": "2026-01-04T10:05:00Z"
}
```

#### Get Execution Logs
```http
GET /executions/{execution_id}/logs
```

**Response:**
```json
{
  "execution": {...},
  "logs": [
    {
      "id": 1,
      "node_id": 2,
      "agent_id": 10,
      "input_data": {...},
      "output_data": {
        "response": "Agent response here",
        "delegation_history": [...]
      },
      "timestamp": "2026-01-04T10:02:00Z"
    },
    ...
  ]
}
```

---

## 🔧 Advanced Features

### Dynamic Delegation in Agents

When creating an agent blueprint that will be used in workflows, you can leverage delegation:

**Example System Prompt:**
```
You are a research coordinator. When you need specialized analysis:
- Use delegate_to_another_agent(agent_id=X, task="...")
- Available agents will be shown when workflow executes
- Delegation is tracked and logged
```

**Delegation Tool Signature:**
```python
delegate_to_another_agent(
    agent_id: int,        # ID of agent to delegate to
    task_description: str # Clear task for the agent
) -> dict
```

**Returns:**
```json
{
  "delegated_to": "Analyst Agent",
  "response": "Agent's analysis...",
  "delegation_depth": 1
}
```

### Shared Context

All nodes in a workflow share a context dictionary:

```python
{
  "initial_input": {"message": "User's original task"},
  "node_1_output": {...},
  "node_2_output": {...},
  "last_output": {...}  # Always the most recent node output
}
```

Agents can access previous outputs via the context passed in dependencies.

### Conditional Branching (Future)

V1 supports static DAGs. Future versions will support:
- JSON path conditions on edges
- Dynamic routing based on agent output
- Loop support with cycle detection

---

## 🧪 Testing

### Unit Tests
```bash
cd tests
pytest test_orchestrator.py -v
```

### Integration Tests with TestModel
```python
from pydantic_ai.models.test import TestModel

# Create agents with TestModel (no API calls)
test_model = TestModel()
agent = Agent(model=test_model, system_prompt="Test agent")

# Use in workflows for testing
# Verify execution logic without real LLM calls
```

---

## 📊 Example Workflows

### 1. Research Pipeline
```
START
  → Research Agent (gathers info)
  → Analyst Agent (analyzes data)
  → Writer Agent (creates report)
  → END
```

### 2. Trading Strategy
```
START
  → Market Data Agent (fetches prices)
  → Strategy Agent (analyzes signals)
  → Risk Manager Agent (validates trades)
  → Execution Agent (places orders)
  → END
```

### 3. Customer Support
```
START
  → Triage Agent (categorizes request)
  → [Delegation to specialists based on category]
  → Resolution Agent (formulates response)
  → END
```

---

## 🔒 Security & Limits

- **Delegation Depth Limit**: Default 5 levels (prevent infinite delegation)
- **Execution Timeout**: Workflow-level timeout (configurable)
- **API Rate Limiting**: Per-agent rate limits apply
- **Context Size**: Shared context limited by available memory

---

## 📚 Further Reading

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [DAG Algorithms](https://en.wikipedia.org/wiki/Directed_acyclic_graph)
- [OpenRouter Models](https://openrouter.ai/models)

---

## 🐛 Troubleshooting

### Workflow fails with "cycle detected"
- Check edges for circular dependencies
- Ensure workflow is a proper DAG (no loops)

### Delegation fails with "max depth exceeded"
- Check if agents are recursively delegating
- Increase `max_delegation_depth` if needed (use with caution)

### Execution stuck in "running" state
- Check backend logs for errors
- Verify all nodes have valid agents
- Check database connection

---

## 🎓 Best Practices

1. **Start Simple**: Begin with 3-node workflows (START → AGENT → END)
2. **Name Clearly**: Use descriptive names for nodes and edges
3. **Test Agents First**: Verify agents work in sandbox before adding to workflows
4. **Monitor Executions**: Use logs to debug issues
5. **Limit Delegation Depth**: Avoid deeply nested delegation chains
6. **Use Position Hints**: Order nodes logically for readability

---

**Questions?** Check the main [README.md](../README.md) or create an issue on GitHub.
