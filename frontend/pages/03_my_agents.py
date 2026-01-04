"""
My Agents Page
View, manage, and organize agent blueprints.
"""
import streamlit as st
import asyncio
from utils import get_agents, get_agent, update_agent, delete_agent, initialize_session_state

# Page config
st.title("📚 My Agents")
st.markdown("Manage your AI agent blueprints")

# Initialize session state
initialize_session_state()

# Fetch agents
try:
    with st.spinner("Loading agents..."):
        agents = asyncio.run(get_agents(active_only=True))

    if not agents:
        st.info("No agents found. Create your first agent in **Agent Builder**!")
    else:
        st.success(f"Found {len(agents)} active agent(s)")

        # Filters and sorting
        col1, col2, col3 = st.columns(3)
        with col1:
            search_query = st.text_input("🔍 Search", placeholder="Filter by name...")
        with col2:
            sort_by = st.selectbox("Sort by", ["Created (Newest)", "Created (Oldest)", "Name (A-Z)", "Name (Z-A)"])
        with col3:
            show_trading = st.checkbox("Trading Tools Only", value=False)

        # Apply filters
        filtered_agents = agents

        if search_query:
            filtered_agents = [
                a for a in filtered_agents
                if search_query.lower() in a['name'].lower()
            ]

        if show_trading:
            filtered_agents = [a for a in filtered_agents if a['has_trading_tools']]

        # Apply sorting
        if sort_by == "Created (Newest)":
            filtered_agents = sorted(filtered_agents, key=lambda x: x['created_at'], reverse=True)
        elif sort_by == "Created (Oldest)":
            filtered_agents = sorted(filtered_agents, key=lambda x: x['created_at'])
        elif sort_by == "Name (A-Z)":
            filtered_agents = sorted(filtered_agents, key=lambda x: x['name'])
        elif sort_by == "Name (Z-A)":
            filtered_agents = sorted(filtered_agents, key=lambda x: x['name'], reverse=True)

        st.markdown("---")

        # Display agents in cards
        for agent in filtered_agents:
            with st.container():
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.subheader(f"🤖 {agent['name']}")

                    # Agent details
                    detail_col1, detail_col2, detail_col3 = st.columns(3)
                    with detail_col1:
                        st.caption(f"**Model:** {agent['model_id'].split('/')[-1]}")
                    with detail_col2:
                        st.caption(f"**Temperature:** {agent['temperature']}")
                    with detail_col3:
                        st.caption(f"**Trading:** {'✅' if agent['has_trading_tools'] else '❌'}")

                    # System prompt preview
                    with st.expander("View System Prompt"):
                        st.code(agent['system_prompt'], language=None)

                    st.caption(f"Created: {agent['created_at'][:10]} | ID: {agent['id']}")

                with col2:
                    # Action buttons
                    if st.button("💬 Chat", key=f"chat_{agent['id']}", use_container_width=True):
                        st.session_state.selected_agent_id = agent['id']
                        st.session_state.chat_history = []
                        st.switch_page("pages/02_agent_sandbox.py")

                    if st.button("✏️ Edit", key=f"edit_{agent['id']}", use_container_width=True):
                        st.session_state[f"editing_{agent['id']}"] = True
                        st.rerun()

                    # Delete with confirmation dialog
                    @st.dialog("Confirm Deletion")
                    def confirm_delete(agent_id: int, agent_name: str):
                        st.write(f"Are you sure you want to delete **{agent_name}**?")
                        st.warning("This action cannot be undone!")

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Confirm", use_container_width=True):
                                try:
                                    asyncio.run(delete_agent(agent_id, hard_delete=False))
                                    st.success(f"Agent '{agent_name}' deleted!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                        with col2:
                            if st.button("❌ Cancel", use_container_width=True):
                                st.rerun()

                    if st.button("🗑️ Delete", key=f"delete_{agent['id']}", use_container_width=True):
                        confirm_delete(agent['id'], agent['name'])

                # Edit form (if editing)
                if st.session_state.get(f"editing_{agent['id']}", False):
                    with st.form(f"edit_form_{agent['id']}"):
                        st.subheader("Edit Agent")

                        new_name = st.text_input("Name", value=agent['name'])
                        new_system_prompt = st.text_area(
                            "System Prompt",
                            value=agent['system_prompt'],
                            height=150
                        )
                        new_temperature = st.slider(
                            "Temperature",
                            0.0, 2.0,
                            float(agent['temperature']),
                            0.1
                        )

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save", use_container_width=True):
                                try:
                                    asyncio.run(update_agent(
                                        agent['id'],
                                        name=new_name,
                                        system_prompt=new_system_prompt,
                                        temperature=new_temperature
                                    ))
                                    st.success("Agent updated!")
                                    st.session_state[f"editing_{agent['id']}"] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")

                        with col2:
                            if st.form_submit_button("❌ Cancel", use_container_width=True):
                                st.session_state[f"editing_{agent['id']}"] = False
                                st.rerun()

                st.markdown("---")

        # Summary
        st.caption(f"Showing {len(filtered_agents)} of {len(agents)} agents")

except Exception as e:
    st.error(f"Error loading agents: {str(e)}")

# Quick stats sidebar
with st.sidebar:
    st.subheader("📊 Quick Stats")

    try:
        agents = asyncio.run(get_agents(active_only=True))
        total = len(agents)
        with_trading = len([a for a in agents if a['has_trading_tools']])
        models_used = len(set(a['model_id'] for a in agents))

        st.metric("Total Agents", total)
        st.metric("With Trading Tools", with_trading)
        st.metric("Unique Models", models_used)

    except Exception:
        st.warning("Unable to load stats")
