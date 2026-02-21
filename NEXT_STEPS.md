# Census Query Agent — Next Steps Work Plan

## Current State Summary

| Area | Status | Notes |
|---|---|---|
| BigQuery toolset integration | ✅ Done | Read-only, parameterized queries |
| System prompt & rules | ✅ Done | Covers edge cases, examples, output format |
| Terraform infrastructure | ✅ Done | Service account provisioned |
| Visualization tool | ⚠️ Incomplete | `visualization.py` exists but not wired to agent |
| Multi-agent architecture | ❌ Not started | Single flat agent |
| MCP server | ❌ Not started | |
| Session memory | ❌ Not started | No cross-turn context |
| Agent evaluation | ❌ Not started | No test suite |

---

## Step 1 — Wire Up the Visualization Tool (Quick Win)

**Goal:** Connect the existing `visualization.py` to the agent as a proper ADK `FunctionTool`.

**Why:** The `VisualizationTool` class is already written but is dead code. This step teaches how to define and register custom tools in ADK with minimal new code.

**Tasks:**
- [ ] Wrap `VisualizationTool.plot_from_rows()` in a plain Python function with type hints
- [ ] Create a `FunctionTool` instance from that function
- [ ] Add the tool to `root_agent` alongside `bq_toolset`
- [ ] Update the system prompt to tell the agent when to use the chart tool
- [ ] Test with a question like "Show top 10 suburbs by postgraduate degree as a bar chart"

**Key code pattern:**
```python
from google.adk.tools import FunctionTool
from census_query_agent.visualization import VisualizationTool

viz = VisualizationTool()

def create_chart(rows: list[dict], x: str, y: str, kind: str = "bar", title: str = "") -> dict:
    """Creates a bar/line/scatter chart from query result rows. Returns base64 PNG."""
    return viz.plot_from_rows(rows, x=x, y=y, kind=kind, title=title)

viz_tool = FunctionTool(func=create_chart)

root_agent = Agent(..., tools=[bq_toolset, viz_tool])
```

---

## Step 2 — Build an MCP Server for Census Tools

**Goal:** Expose census query capabilities as an MCP server so the tools are usable from Claude Desktop, VS Code Copilot Chat, Cursor, or any MCP-compatible client.

**Why:** MCP is becoming the standard protocol for connecting AI assistants to data sources. Building a server here gives you broad reach with minimal new code, and it's an excellent practical introduction to MCP concepts.

**Tasks:**
- [ ] Install the MCP Python SDK: `pip install mcp`
- [ ] Create `adk_project/mcp_server.py` using `FastMCP`
- [ ] Expose at least 4 census tools: income by suburb, ancestry by postcode, education by suburb, occupation by suburb
- [ ] Run the MCP server locally and connect it to Claude Desktop or VS Code
- [ ] Test that census queries work from the MCP client without touching `agent.py`
- [ ] (Optional) Add the MCP server as a tool source back into the ADK agent using `MCPToolset`

**Key code pattern:**
```python
# mcp_server.py
from mcp.server.fastmcp import FastMCP
from google.cloud import bigquery

mcp = FastMCP("NSW Census 2021")

@mcp.tool()
def query_income_by_suburb(suburb: str) -> str:
    """Query household weekly income distribution for a NSW suburb."""
    # BQ query logic here
    ...

@mcp.tool()
def query_ancestry_by_postcode(postcode: str) -> str:
    """Get ancestry breakdown for a NSW postcode."""
    ...

if __name__ == "__main__":
    mcp.run()
```

**MCP client config (Claude Desktop `~/.config/claude/claude_desktop_config.json`):**
```json
{
  "mcpServers": {
    "nsw-census": {
      "command": "python",
      "args": ["/path/to/adk_project/mcp_server.py"]
    }
  }
}
```

---

## Step 3 — Multi-Agent Architecture

**Goal:** Refactor the single flat agent into specialized sub-agents coordinated by a root orchestrator.

**Why:** This is the core ADK architectural pattern. Splitting by domain improves accuracy (each sub-agent has a tighter prompt), teaches you `AgentTool` and agent delegation, and scales better as new datasets are added.

**Target architecture:**
```
root_agent (orchestrator)
├── income_agent       → g17_personal_income, g32_family_income_weekly, g33_household_income_weekly
├── demographics_agent → g04_age, g05_marital_status
├── education_agent    → g49_education
└── occupation_agent   → g56_occupation
```

**Tasks:**
- [ ] Create one sub-agent per domain in separate files (e.g., `income_agent.py`)
- [ ] Give each sub-agent a focused system prompt covering only its tables
- [ ] Register sub-agents as `AgentTool` instances on the root orchestrator
- [ ] Update the root agent prompt to describe when to delegate to which sub-agent
- [ ] Test cross-domain queries (e.g., "Compare education and income levels in Bondi") that require multiple sub-agents

**Key code pattern:**
```python
from google.adk.agents import Agent
from google.adk.tools import AgentTool

income_agent = Agent(name="income_agent", model="gemini-2.5-flash", ...)
demographics_agent = Agent(name="demographics_agent", model="gemini-2.5-flash", ...)

root_agent = Agent(
    name="census_orchestrator",
    tools=[AgentTool(agent=income_agent), AgentTool(agent=demographics_agent)],
    ...
)
```

---

## Step 4 — Session Memory & Multi-Turn Context

**Goal:** Give the agent short-term memory so it can reference earlier parts of the conversation (e.g., "what about their education?" after asking about incomes in Bondi).

**Why:** Currently every turn is stateless. Session state is a key ADK feature and makes conversations significantly more natural.

**Tasks:**
- [ ] Enable ADK session service and pass `session_id` when invoking the agent
- [ ] Store the last queried suburb/postcode in session state after each successful query
- [ ] Update the system prompt to reference `{state.last_suburb}` in follow-up queries
- [ ] Test a multi-turn conversation that references prior context

**Key code pattern:**
```python
from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()
session = session_service.create_session(app_name="census_agent", user_id="user_1")

# Pass session when running the agent
runner.run(user_message="...", session_id=session.id)
```

---

## Step 5 — Agent Evaluation

**Goal:** Build a test suite using ADK's evaluation framework to systematically measure agent quality.

**Why:** Without evaluation you're guessing whether the agent is improving. A small test set (10–20 cases) provides a baseline metric and catches regressions when you change the prompt or tools.

**Tasks:**
- [ ] Create `adk_project/eval/` directory
- [ ] Write 10–20 test cases as JSON: input question → expected SQL pattern or key facts in response
- [ ] Use `google.adk.evaluation` to run the test suite
- [ ] Record baseline scores before any further changes
- [ ] Re-run evals after each step above to measure impact

**Test case format:**
```json
[
  {
    "input": "What is the top ancestry in postcode 2134?",
    "expected_sql_contains": ["g08_ancestry", "2134"],
    "expected_output_contains": ["Chinese", "English"]
  },
  {
    "input": "Show education levels in Bondi",
    "expected_sql_contains": ["g49_education", "Bondi"]
  }
]
```

---

## Recommended Order

```
Step 1 (Visualization) → Step 2 (MCP Server) → Step 3 (Multi-Agent) → Step 4 (Session Memory) → Step 5 (Evaluation)
```

- **Step 1** is a quick win — fixes dead code and teaches custom ADK tools
- **Step 2** maximizes reach — your census data becomes available in any MCP client
- **Step 3** is the key ADK architecture lesson — learn delegation and orchestration
- **Step 4** improves UX significantly with relatively little code
- **Step 5** gives you the discipline layer to develop confidently from here on

---

## Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [ADK Tools Guide](https://google.github.io/adk-docs/tools/)
- [ADK Multi-Agent Guide](https://google.github.io/adk-docs/agents/multi-agents/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://modelcontextprotocol.io/docs)
- [ADK + MCP Integration](https://google.github.io/adk-docs/tools/mcp-tools/)
