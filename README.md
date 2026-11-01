# Study Planner – MCP Toolkit (FastMCP + OpenAI Agents SDK)

A student assistant that tracks course deadlines (EECE 503P, ARAB 223, CHLA 295C, EECE 501).

| Category | Tool | Purpose |
|---|---|---|
| Data | `get_deadlines` | Read-only lookup of upcoming deadlines (optional course filter) |
| Action | `create_reminder` | Saves one reminder to `reminders.json` (the only tool that writes) |
| Orchestration | `plan_study_session` | Calls `get_deadlines`, then `create_reminder` for each deadline (day before) |

## Architecture
`agent.py` (Host + MCP Client via `MCPServerStdio`, OpenAI Agents SDK) <-> stdio <-> `server.py` (FastMCP server) -> JSON files.
The agent's model is Gemini, reached through its OpenAI-compatible endpoint; the Agents SDK handles the MCP connection.

## Setup
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
$env:GEMINI_API_KEY = "your-key"
```
Edit the dates in `deadlines.json` so some fall in the next few weeks.

## Run
```
python agent.py "What is due in the next 10 days for EECE 503P?"
python agent.py "Set a reminder for 2026-11-02 to review lecture 5"
python agent.py "Plan my study session for EECE 501 over the next 30 days"
python agent.py "What is due for MATH 999?"      # failure case
```

## Tests (include failure cases)
```
pytest -q
```

## Failure handling
Each tool raises `ToolError` with a clear message: non-positive `days_ahead`, unknown course, empty title, invalid or past reminder date, duplicate reminder, and no deadlines to plan.