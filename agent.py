"""OpenAI Agents SDK host/client connected to the FastMCP server over stdio.
The model is Gemini, reached through its OpenAI-compatible endpoint.

Usage (PowerShell):
    $env:GEMINI_API_KEY = "your-key"
    python agent.py "What is due in the next 10 days for EECE 503P?"
"""
import asyncio
import os
import sys
from pathlib import Path

from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from agents.mcp import MCPServerStdio

set_tracing_disabled(True)  # tracing needs an OpenAI key; not needed here

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
MODEL = OpenAIChatCompletionsModel(model="gemini-3.5-flash", openai_client=client)

SERVER = str(Path(__file__).parent / "server.py")


async def main(prompt: str) -> None:
    async with MCPServerStdio(
        name="Study Planner",
        params={"command": sys.executable, "args": [SERVER]},
        cache_tools_list=True,
    ) as server:
        agent = Agent(
            name="Study Assistant",
            model=MODEL,
            instructions=(
                "You help a student stay on top of deadlines. Use get_deadlines to look "
                "things up, create_reminder to save one specific reminder, and "
                "plan_study_session when asked to plan/remind for several deadlines at "
                "once. If a tool returns an error, explain it plainly and suggest a fix."
            ),
            mcp_servers=[server],
        )
        result = await Runner.run(agent, prompt)
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "What is due in the next 14 days?"))