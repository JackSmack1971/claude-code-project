"""
AgentFactory - Main Streamlit Application
CRITICAL: st.set_page_config must be the FIRST command.
"""
import streamlit as st
from utils import initialize_session_state

# CRITICAL: This must be the first Streamlit command
st.set_page_config(
    page_title="AgentFactory",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
initialize_session_state()

# Main app content
st.title("🤖 AgentFactory")
st.markdown("""
Welcome to **AgentFactory** - Your platform for rapid AI agent deployment and management.

### Features
- **Agent Builder**: Create custom AI agents with personalized system prompts
- **Agent Sandbox**: Interactive chat interface with real-time streaming
- **My Agents**: Manage and organize your agent blueprints
- **Trading Tools**: Optional CCXT integration for financial operations

### Quick Start
1. Navigate to **Agent Builder** to create your first agent
2. Configure the model, temperature, and system prompt
3. Test your agent in the **Sandbox**
4. Manage all your agents in **My Agents**

### Navigation
Use the sidebar to navigate between pages:
- 📝 **Agent Builder**: Create new agents
- 💬 **Agent Sandbox**: Chat with your agents
- 📚 **My Agents**: View and manage agents
""")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")

    st.markdown("---")

    st.info("""
    **Current Session**

    Selected Agent: {}
    """.format(
        st.session_state.selected_agent_id if st.session_state.selected_agent_id
        else "None"
    ))

    st.markdown("---")

    # Backend health check
    with st.expander("🔧 System Status"):
        import asyncio
        import httpx
        from utils import get_backend_url

        async def check_health():
            try:
                backend_url = get_backend_url()
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{backend_url}/health")
                    if response.status_code == 200:
                        return "✅ Backend: Online"
                    else:
                        return "❌ Backend: Error"
            except Exception as e:
                return f"❌ Backend: Offline ({str(e)[:30]}...)"

        if st.button("Check Backend Status"):
            health_status = asyncio.run(check_health())
            st.write(health_status)

    st.markdown("---")
    st.caption("AgentFactory v1.0.0 | Powered by Pydantic AI & OpenRouter")
