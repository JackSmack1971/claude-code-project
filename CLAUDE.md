# Project Context & Agentic Workflow

## 1. The Prime Directive (Standard Operating Procedure)
You are an expert software engineer. To prevent "Context Rot" and ensure precision, you MUST follow this **Agentic Loop** for any task involving more than one file:

1.  **PLAN**: Invoke the `Planner` agent to break down the user request into atomic steps.
    - *Source:* `.claude/agents/planner.md`
2.  **RESEARCH**: If the plan requires knowledge of existing code, invoke the `Researcher` agent.
    - *Constraint:* Do not assume file contents; verify with `grep` or `read`.
    - *Source:* `.claude/agents/researcher.md`
3.  **BUILD**: Invoke the `Builder` agent to execute **one atomic step** of the plan at a time.
    - *Source:* `.claude/agents/builder.md`
4.  **VERIFY**: Invoke the `Critic` agent to run tests/linters after edits.
    - *Source:* `.claude/agents/critic.md`

## 2. Project Knowledge (The "What")
- **Tech Stack**: [Insert Stack, e.g., TypeScript / Node / React / Postgres]
- **Architecture Style**: [e.g., Modular Monolith, Microservices]
- **Key Directories**:
    - `/src`: Application source code
    - `/.claude`: Agent definitions and project memory
    - `/tests`: Unit and integration tests

## 3. Operational Constraints (The "How")
- **Edit Safety**: NEVER edit a file without reading it first.
- **Token Efficiency**: When searching, prefer `grep -n` over `cat` or `read` to save context.
- **Commit Strategy**: Use the "Atomic Commit" skill (`.claude/skills/git-commit.md`) after every successful `Builder` cycle.

## 4. Commands (Universal)
- **Build**: `[e.g., npm run build]`
- **Test**: `[e.g., npm test]`
- **Lint**: `[e.g., npm run lint]`
- **Start Local**: `[e.g., npm run dev]`

## 5. Memory & Learning
- If you encounter a recurring error or architectural quirk, propose adding it to `.claude/docs/troubleshooting.md` using the `Researcher`.
- Ignored Files: Do not read `package-lock.json` or binary files unless explicitly requested.
