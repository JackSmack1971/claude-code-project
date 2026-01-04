"""
Agent Sandbox Page
Interactive chat interface with real-time streaming.
Uses @st.fragment to isolate chat window reruns.
"""
import streamlit as st
import asyncio
from utils import get_agents, get_agent, chat_with_agent_stream, initialize_session_state

# Page config
st.title("💬 Agent Sandbox")
st.markdown("Chat with your AI agents in real-time")

# Initialize session state
initialize_session_state()

# Agent selection sidebar
with st.sidebar:
    st.subheader("Select Agent")

    # Fetch agents
    try:
        agents = asyncio.run(get_agents(active_only=True))

        if not agents:
            st.warning("No agents found. Create one in Agent Builder!")
            agent_options = {}
        else:
            agent_options = {f"{a['name']} (ID: {a['id']})": a['id'] for a in agents}

            selected_agent_name = st.selectbox(
                "Choose an agent",
                options=list(agent_options.keys()),
                index=0
            )

            if selected_agent_name:
                selected_agent_id = agent_options[selected_agent_name]

                # Update session state
                if st.button("Load Agent", use_container_width=True):
                    st.session_state.selected_agent_id = selected_agent_id
                    st.session_state.chat_history = []
                    st.rerun()

    except Exception as e:
        st.error(f"Error fetching agents: {str(e)}")
        agent_options = {}

# Main chat interface
if st.session_state.selected_agent_id:
    # Fetch agent details
    try:
        agent = asyncio.run(get_agent(st.session_state.selected_agent_id))

        # Display agent info
        with st.expander("🤖 Agent Configuration", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Name:** {agent['name']}")
                st.write(f"**Model:** {agent['model_id']}")
                st.write(f"**Temperature:** {agent['temperature']}")
            with col2:
                st.write(f"**Trading Tools:** {'✅' if agent['has_trading_tools'] else '❌'}")
                st.write(f"**Created:** {agent['created_at'][:10]}")

            with st.expander("System Prompt"):
                st.code(agent['system_prompt'], language=None)

        st.markdown("---")

        # Chat interface using fragment for performance
        @st.fragment
        def chat_interface():
            """
            Isolated chat interface using @st.fragment.
            Prevents sidebar/config panels from resetting during conversation.
            """
            # Display chat history
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

            # Chat input
            user_message = st.chat_input("Type your message here...")

            if user_message:
                # Add user message to history
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_message
                })

                # Display user message
                with st.chat_message("user"):
                    st.write(user_message)

                # Stream agent response
                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    full_response = ""

                    try:
                        async def stream_response():
                            nonlocal full_response
                            async for chunk in chat_with_agent_stream(
                                agent_id=st.session_state.selected_agent_id,
                                message=user_message
                            ):
                                full_response += chunk
                                response_placeholder.markdown(full_response + "▌")

                            # Final update without cursor
                            response_placeholder.markdown(full_response)

                        asyncio.run(stream_response())

                        # Add assistant response to history
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": full_response
                        })

                    except Exception as e:
                        error_msg = f"Error: {str(e)}"
                        response_placeholder.error(error_msg)
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": error_msg
                        })

        # Render chat interface
        chat_interface()

        # Clear chat button
        st.markdown("---")
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

    except Exception as e:
        st.error(f"Error loading agent: {str(e)}")

else:
    # No agent selected
    st.info("👈 Select an agent from the sidebar to start chatting")

    st.markdown("---")
    st.subheader("Getting Started")
    st.markdown("""
    1. **Select an Agent**: Use the sidebar to choose an agent
    2. **Start Chatting**: Type your message in the chat input
    3. **Real-time Streaming**: See responses appear as they're generated
    4. **Context Aware**: The agent remembers your conversation history

    ### Features
    - ✨ Real-time streaming responses
    - 💾 Conversation history
    - 🔄 Isolated chat reruns (sidebar won't reset)
    - 🛠️ Access to agent tools (if enabled)
    """)
