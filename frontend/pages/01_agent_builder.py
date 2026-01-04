"""
Agent Builder Page
Create and configure new AI agents with custom prompts.
"""
import streamlit as st
import asyncio
from utils import create_agent, initialize_session_state

# Page config
st.title("📝 Agent Builder")
st.markdown("Create a new AI agent with custom configuration")

# Initialize session state
initialize_session_state()

# Agent creation form
with st.form("agent_builder_form", clear_on_submit=True):
    st.subheader("Agent Configuration")

    # Basic settings
    col1, col2 = st.columns(2)

    with col1:
        agent_name = st.text_input(
            "Agent Name *",
            placeholder="e.g., Trading Assistant",
            help="A descriptive name for your agent"
        )

        model_id = st.selectbox(
            "Model *",
            options=[
                "openrouter/anthropic/claude-3.5-sonnet",
                "openrouter/anthropic/claude-3-opus",
                "openrouter/anthropic/claude-3-haiku",
                "openrouter/openai/gpt-4-turbo",
                "openrouter/openai/gpt-4",
                "openrouter/openai/gpt-3.5-turbo",
                "openrouter/google/gemini-pro",
                "openrouter/meta-llama/llama-3-70b-instruct"
            ],
            help="Select the LLM model from OpenRouter"
        )

    with col2:
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=0.7,
            step=0.1,
            help="Controls randomness: 0 = focused, 2 = creative"
        )

        has_trading_tools = st.checkbox(
            "Enable Trading Tools (CCXT)",
            value=False,
            help="Add CCXT tools for market data and order execution"
        )

    # System prompt
    st.markdown("---")
    system_prompt = st.text_area(
        "System Prompt *",
        height=200,
        placeholder="You are a helpful AI assistant...",
        help="Instructions that define your agent's behavior and personality"
    )

    # Example prompts
    with st.expander("📋 Example System Prompts"):
        st.markdown("""
        **General Assistant:**
        ```
        You are a helpful AI assistant. Provide clear, accurate, and concise responses.
        Always be polite and professional.
        ```

        **Trading Analyst:**
        ```
        You are an expert cryptocurrency trading analyst. Use the provided tools to fetch
        market data and analyze trends. Provide data-driven recommendations but always
        remind users that trading carries risks.
        ```

        **Code Reviewer:**
        ```
        You are a senior software engineer specializing in code review. Analyze code for
        bugs, security issues, and best practices. Provide constructive feedback with
        specific examples.
        ```

        **Creative Writer:**
        ```
        You are a creative writing assistant. Help users brainstorm ideas, develop
        characters, and craft compelling narratives. Be imaginative and supportive.
        ```
        """)

    # Submit button
    st.markdown("---")
    submitted = st.form_submit_button("🚀 Create Agent", use_container_width=True)

    if submitted:
        # Validation
        if not agent_name or not system_prompt:
            st.error("❌ Please fill in all required fields (marked with *)")
        elif len(agent_name) < 3:
            st.error("❌ Agent name must be at least 3 characters")
        elif len(system_prompt) < 10:
            st.error("❌ System prompt must be at least 10 characters")
        else:
            # Create agent
            with st.spinner("Creating agent..."):
                try:
                    result = asyncio.run(create_agent(
                        name=agent_name,
                        system_prompt=system_prompt,
                        model_id=model_id,
                        temperature=temperature,
                        has_trading_tools=has_trading_tools
                    ))

                    st.success(f"✅ Agent '{agent_name}' created successfully!")
                    st.balloons()

                    # Display created agent details
                    with st.expander("Agent Details", expanded=True):
                        st.json(result)

                    # Set as selected agent
                    st.session_state.selected_agent_id = result["id"]
                    st.info(f"💡 Agent selected! Navigate to **Agent Sandbox** to chat.")

                except Exception as e:
                    st.error(f"❌ Error creating agent: {str(e)}")

# Tips section
st.markdown("---")
st.subheader("💡 Tips for Effective Agents")
st.markdown("""
1. **Be Specific**: Clearly define the agent's role and capabilities
2. **Set Boundaries**: Specify what the agent should and shouldn't do
3. **Provide Context**: Include relevant domain knowledge in the system prompt
4. **Test Iteratively**: Start simple and refine based on performance
5. **Use Examples**: Include example interactions if needed
6. **Temperature Tuning**:
   - Low (0.0-0.3): Deterministic, focused responses
   - Medium (0.4-0.8): Balanced creativity and consistency
   - High (0.9-2.0): Maximum creativity and randomness
""")
