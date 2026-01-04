"""
Workflow Builder Page
Form-based interface for creating multi-agent workflow DAGs.
"""
import streamlit as st
import asyncio
from utils import (
    get_workflow,
    get_workflow_graph,
    get_agents,
    create_workflow_node,
    create_workflow_edge,
    delete_workflow_node,
    delete_workflow_edge,
    execute_workflow,
    get_execution_status,
    get_execution_logs,
    initialize_session_state
)

# Page config
st.title("🛠️ Workflow Builder")

# Initialize session state
initialize_session_state()

# Check if workflow is selected
if not st.session_state.get("selected_workflow_id"):
    st.warning("No workflow selected. Please go to **Workflows** page and select a workflow to edit.")
    if st.button("← Back to Workflows"):
        st.switch_page("pages/04_workflows.py")
    st.stop()

workflow_id = st.session_state.selected_workflow_id

# Load workflow data
try:
    with st.spinner("Loading workflow..."):
        workflow = asyncio.run(get_workflow(workflow_id))
        graph = asyncio.run(get_workflow_graph(workflow_id))
        agents_list = asyncio.run(get_agents(active_only=True))

    st.success(f"Editing: **{workflow['name']}**")
    if workflow.get('description'):
        st.caption(workflow['description'])

except Exception as e:
    st.error(f"Failed to load workflow: {str(e)}")
    st.stop()

st.divider()

# ============================================================================
# Workflow Graph Display
# ============================================================================

nodes = graph.get('nodes', [])
edges = graph.get('edges', [])

st.subheader("📊 Workflow Structure")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Nodes", len(nodes))
with col2:
    st.metric("Connections", len(edges))
with col3:
    is_valid = len(nodes) >= 2  # At least START and END
    st.metric("Status", "✅ Ready" if is_valid else "⚠️ Incomplete")

# Display current graph
if nodes:
    st.markdown("#### Current Graph")

    # Create a visual representation
    for node in sorted(nodes, key=lambda x: x['position']):
        node_type = node['node_type']
        node_name = node['name']
        node_id = node['id']

        # Icon based on type
        icon = {
            'start': '🟢',
            'agent': '🤖',
            'condition': '❓',
            'end': '🔴'
        }.get(node_type.lower(), '⚪')

        # Display node
        with st.container():
            col_a, col_b, col_c = st.columns([3, 2, 1])
            with col_a:
                st.markdown(f"{icon} **{node_name}** `({node_type})`")
                if node_type.lower() == 'agent' and node.get('agent_id'):
                    agent_name = next(
                        (a['name'] for a in agents_list if a['id'] == node['agent_id']),
                        'Unknown Agent'
                    )
                    st.caption(f"↳ Agent: {agent_name}")

            with col_b:
                st.caption(f"Position: {node['position']}")

            with col_c:
                if st.button("🗑️", key=f"del_node_{node_id}"):
                    try:
                        asyncio.run(delete_workflow_node(workflow_id, node_id))
                        st.success("Node deleted")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {str(e)}")

        # Show outgoing edges
        outgoing = [e for e in edges if e['source_node_id'] == node_id]
        for edge in outgoing:
            target_node = next((n for n in nodes if n['id'] == edge['target_node_id']), None)
            target_name = target_node['name'] if target_node else 'Unknown'
            edge_label = edge.get('label', '')

            col_x, col_y, col_z = st.columns([3, 2, 1])
            with col_x:
                st.markdown(f"  └─→ **{target_name}** {f'`({edge_label})`' if edge_label else ''}")
            with col_z:
                if st.button("🗑️", key=f"del_edge_{edge['id']}"):
                    try:
                        asyncio.run(delete_workflow_edge(workflow_id, edge['id']))
                        st.success("Edge deleted")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {str(e)}")

else:
    st.info("No nodes yet. Add your first node below!")

st.divider()

# ============================================================================
# Add Nodes
# ============================================================================

st.subheader("➕ Add Node")

with st.form("add_node_form"):
    col1, col2 = st.columns(2)

    with col1:
        node_name = st.text_input("Node Name", placeholder="e.g., Research Agent")
        node_type = st.selectbox(
            "Node Type",
            options=["start", "agent", "end", "condition"],
            format_func=lambda x: {
                "start": "🟢 START (Entry Point)",
                "agent": "🤖 AGENT (Execute Agent)",
                "end": "🔴 END (Terminal)",
                "condition": "❓ CONDITION (Branch - future)"
            }[x]
        )

    with col2:
        # Agent selection (only for AGENT node type)
        agent_id = None
        if node_type == "agent":
            if agents_list:
                agent_options = {a['id']: a['name'] for a in agents_list}
                selected_agent_id = st.selectbox(
                    "Select Agent",
                    options=list(agent_options.keys()),
                    format_func=lambda x: agent_options[x]
                )
                agent_id = selected_agent_id
            else:
                st.warning("No agents available. Create agents first!")
        else:
            st.caption("Agent selection not needed for this node type")

        position = st.number_input(
            "Position (execution order hint)",
            min_value=0,
            max_value=100,
            value=len(nodes)
        )

    submit_node = st.form_submit_button("Add Node", type="primary")

    if submit_node:
        if not node_name:
            st.error("Node name is required")
        elif node_type == "agent" and not agent_id:
            st.error("Agent must be selected for AGENT nodes")
        else:
            try:
                with st.spinner("Creating node..."):
                    new_node = asyncio.run(
                        create_workflow_node(
                            workflow_id=workflow_id,
                            name=node_name,
                            node_type=node_type,
                            agent_id=agent_id,
                            position=position
                        )
                    )
                st.success(f"✅ Added node: {new_node['name']}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create node: {str(e)}")

st.divider()

# ============================================================================
# Add Edges (Connections)
# ============================================================================

st.subheader("🔗 Add Connection")

if len(nodes) < 2:
    st.info("Add at least 2 nodes before creating connections")
else:
    with st.form("add_edge_form"):
        col1, col2, col3 = st.columns(3)

        # Create node lookup
        node_options = {n['id']: f"{n['name']} ({n['node_type']})" for n in nodes}

        with col1:
            source_id = st.selectbox(
                "From Node",
                options=list(node_options.keys()),
                format_func=lambda x: node_options[x]
            )

        with col2:
            target_id = st.selectbox(
                "To Node",
                options=list(node_options.keys()),
                format_func=lambda x: node_options[x]
            )

        with col3:
            edge_label = st.text_input(
                "Label (optional)",
                placeholder="e.g., success"
            )

        submit_edge = st.form_submit_button("Add Connection", type="primary")

        if submit_edge:
            if source_id == target_id:
                st.error("Source and target must be different nodes")
            else:
                try:
                    with st.spinner("Creating connection..."):
                        new_edge = asyncio.run(
                            create_workflow_edge(
                                workflow_id=workflow_id,
                                source_node_id=source_id,
                                target_node_id=target_id,
                                label=edge_label or None
                            )
                        )
                    st.success(f"✅ Added connection: {node_options[source_id]} → {node_options[target_id]}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create connection: {str(e)}")

st.divider()

# ============================================================================
# Execute Workflow
# ============================================================================

st.subheader("▶️ Execute Workflow")

if len(nodes) < 2:
    st.warning("Add at least a START and END node before executing")
else:
    with st.form("execute_workflow_form"):
        st.markdown("Provide initial input for the workflow:")

        initial_message = st.text_area(
            "Initial Message",
            placeholder="Enter the task or question for the workflow...",
            height=100
        )

        execute_btn = st.form_submit_button("🚀 Execute Workflow", type="primary")

        if execute_btn:
            if not initial_message:
                st.error("Initial message is required")
            else:
                try:
                    with st.spinner("Starting workflow execution..."):
                        execution = asyncio.run(
                            execute_workflow(
                                workflow_id=workflow_id,
                                initial_input={"message": initial_message}
                            )
                        )

                    execution_id = execution['id']
                    st.session_state.last_execution_id = execution_id

                    st.success(f"✅ Workflow started! Execution ID: {execution_id}")
                    st.info("Workflow is running asynchronously. Check status below.")

                except Exception as e:
                    st.error(f"Failed to execute workflow: {str(e)}")

# ============================================================================
# Monitor Execution Status
# ============================================================================

if st.session_state.get("last_execution_id"):
    st.divider()
    st.subheader("📊 Execution Status")

    execution_id = st.session_state.last_execution_id

    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔄 Refresh Status"):
            st.rerun()

    try:
        status_data = asyncio.run(get_execution_status(execution_id))

        status = status_data['status']
        status_icons = {
            'pending': '⏳',
            'running': '▶️',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '🚫'
        }
        icon = status_icons.get(status.lower(), '⚪')

        st.markdown(f"### {icon} Status: **{status.upper()}**")

        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"Started: {status_data['started_at']}")
        with col2:
            if status_data.get('completed_at'):
                st.caption(f"Completed: {status_data['completed_at']}")

        # Show final output if completed
        if status.lower() == 'completed' and status_data.get('final_output'):
            st.markdown("#### 🎯 Final Output")
            st.json(status_data['final_output'])

        # Show error if failed
        if status.lower() == 'failed' and status_data.get('error_message'):
            st.error(f"**Error:** {status_data['error_message']}")

        # Show detailed logs
        with st.expander("📜 View Detailed Logs"):
            try:
                logs_data = asyncio.run(get_execution_logs(execution_id))
                logs = logs_data.get('logs', [])

                if logs:
                    for log in logs:
                        st.markdown(f"**Node {log.get('node_id')}** @ {log['timestamp']}")
                        st.caption(f"Agent: {log.get('agent_id')}")

                        if log.get('output_data'):
                            st.json(log['output_data'])

                        if log.get('error_message'):
                            st.error(log['error_message'])

                        st.divider()
                else:
                    st.info("No logs available yet")

            except Exception as e:
                st.error(f"Failed to load logs: {str(e)}")

    except Exception as e:
        st.error(f"Failed to fetch execution status: {str(e)}")

# Back button
st.divider()
if st.button("← Back to Workflows"):
    st.switch_page("pages/04_workflows.py")
