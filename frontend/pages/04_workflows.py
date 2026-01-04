"""
Workflows Page
Manage multi-agent orchestration workflows.
"""
import streamlit as st
import asyncio
from datetime import datetime
from utils import (
    get_workflows,
    create_workflow,
    delete_workflow,
    get_workflow_graph,
    execute_workflow,
    get_execution_status,
    initialize_session_state
)

# Page config
st.title("🔗 Multi-Agent Workflows")
st.markdown("Create and manage orchestrated agent workflows with dynamic delegation")

# Initialize session state
initialize_session_state()

# Tabs for different views
tab1, tab2 = st.tabs(["📋 My Workflows", "▶️ Executions"])

# ============================================================================
# Tab 1: Workflow Management
# ============================================================================

with tab1:
    # Create new workflow
    with st.expander("➕ Create New Workflow", expanded=False):
        with st.form("new_workflow_form"):
            workflow_name = st.text_input(
                "Workflow Name",
                placeholder="e.g., Research → Summarize → Report"
            )
            workflow_description = st.text_area(
                "Description (optional)",
                placeholder="Describe what this workflow does...",
                height=100
            )

            col1, col2 = st.columns([1, 4])
            with col1:
                submit_workflow = st.form_submit_button("Create", type="primary", use_container_width=True)
            with col2:
                st.caption("After creating, go to **Workflow Builder** to add agents and connections")

            if submit_workflow:
                if not workflow_name:
                    st.error("Workflow name is required")
                else:
                    try:
                        with st.spinner("Creating workflow..."):
                            new_workflow = asyncio.run(
                                create_workflow(workflow_name, workflow_description)
                            )
                        st.success(f"✅ Created workflow: {new_workflow['name']}")
                        st.session_state.selected_workflow_id = new_workflow['id']
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create workflow: {str(e)}")

    st.divider()

    # Load and display workflows
    try:
        with st.spinner("Loading workflows..."):
            workflows = asyncio.run(get_workflows(active_only=True))

        if not workflows:
            st.info("No workflows found. Create your first workflow above!")
        else:
            st.success(f"Found {len(workflows)} workflow(s)")

            # Display workflows in cards
            for workflow in workflows:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

                    with col1:
                        st.subheader(workflow['name'])
                        if workflow.get('description'):
                            st.caption(workflow['description'])

                    with col2:
                        created_date = datetime.fromisoformat(
                            workflow['created_at'].replace('Z', '+00:00')
                        )
                        st.caption(f"Created: {created_date.strftime('%Y-%m-%d')}")

                    with col3:
                        # View/Edit workflow button
                        if st.button("📝 Edit", key=f"edit_{workflow['id']}"):
                            st.session_state.selected_workflow_id = workflow['id']
                            st.switch_page("pages/05_workflow_builder.py")

                    with col4:
                        # Delete button
                        if st.button("🗑️", key=f"delete_{workflow['id']}"):
                            try:
                                asyncio.run(delete_workflow(workflow['id']))
                                st.success(f"Deleted workflow: {workflow['name']}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to delete: {str(e)}")

                    # Show workflow graph summary
                    with st.expander("🔍 View Structure"):
                        try:
                            graph = asyncio.run(get_workflow_graph(workflow['id']))
                            nodes = graph.get('nodes', [])
                            edges = graph.get('edges', [])

                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Nodes", len(nodes))
                                if nodes:
                                    st.caption("**Nodes:**")
                                    for node in nodes:
                                        st.markdown(f"- {node['name']} ({node['node_type']})")
                            with col_b:
                                st.metric("Connections", len(edges))
                                if edges:
                                    st.caption("**Edges:**")
                                    for edge in edges:
                                        label = edge.get('label', 'unlabeled')
                                        st.markdown(f"- {edge['source_node_id']} → {edge['target_node_id']} ({label})")
                        except Exception as e:
                            st.error(f"Failed to load graph: {str(e)}")

                    st.divider()

    except Exception as e:
        st.error(f"Failed to load workflows: {str(e)}")


# ============================================================================
# Tab 2: Execution History
# ============================================================================

with tab2:
    st.info("🚧 Execution history coming soon! For now, use the Workflow Builder to execute workflows.")

    # Placeholder for execution tracking
    if st.session_state.get("last_execution_id"):
        st.subheader("Latest Execution")
        execution_id = st.session_state.last_execution_id

        if st.button("🔄 Refresh Status"):
            try:
                status = asyncio.run(get_execution_status(execution_id))
                st.json(status)
            except Exception as e:
                st.error(f"Failed to fetch execution: {str(e)}")
