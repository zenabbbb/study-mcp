import json
from datetime import date, timedelta

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

import server


def _d(n):
    return (date.today() + timedelta(days=n)).isoformat()


@pytest.fixture(autouse=True)
def files(tmp_path, monkeypatch):
    deadlines = [
        {"id": 1, "course": "EECE 503P", "title": "A1", "due_date": _d(3)},
        {"id": 2, "course": "EECE 503P", "title": "A2", "due_date": _d(40)},
        {"id": 3, "course": "ARAB 223", "title": "R1", "due_date": _d(1)},
    ]
    (tmp_path / "d.json").write_text(json.dumps(deadlines))
    monkeypatch.setenv("DEADLINES_FILE", str(tmp_path / "d.json"))
    monkeypatch.setenv("REMINDERS_FILE", str(tmp_path / "r.json"))
    return tmp_path


@pytest.fixture
async def client():
    async with Client(server.mcp) as c:
        yield c


async def test_exactly_three_tools(client):
    names = {t.name for t in await client.list_tools()}
    assert names == {"get_deadlines", "create_reminder", "plan_study_session"}


async def test_data_filters_and_sorts(client):
    r = await client.call_tool("get_deadlines", {"days_ahead": 14})
    assert [d["title"] for d in r.structured_content["result"]] == ["R1", "A1"]
    r = await client.call_tool("get_deadlines", {"course": "eece 503p", "days_ahead": 14})
    assert [d["title"] for d in r.structured_content["result"]] == ["A1"]


async def test_data_failures(client):
    with pytest.raises(ToolError, match="Unknown course"):
        await client.call_tool("get_deadlines", {"course": "XYZ"})
    with pytest.raises(ToolError, match="greater than 0"):
        await client.call_tool("get_deadlines", {"days_ahead": 0})


async def test_action_creates_and_persists(client, files):
    await client.call_tool("create_reminder", {"title": "Study", "remind_on": _d(2)})
    saved = json.loads((files / "r.json").read_text())
    assert saved == [{"title": "Study", "remind_on": _d(2)}]


async def test_action_failures(client):
    with pytest.raises(ToolError, match="not a valid"):
        await client.call_tool("create_reminder", {"title": "x", "remind_on": "tomorrow"})
    with pytest.raises(ToolError, match="in the past"):
        await client.call_tool("create_reminder", {"title": "x", "remind_on": _d(-1)})
    with pytest.raises(ToolError, match="must not be empty"):
        await client.call_tool("create_reminder", {"title": " ", "remind_on": _d(1)})


async def test_orchestration_chains_tools(client, files):
    r = await client.call_tool("plan_study_session", {"days_ahead": 14})
    out = r.structured_content
    assert out["deadlines_found"] == 2 and len(out["created"]) == 2
    assert len(json.loads((files / "r.json").read_text())) == 2
    out2 = (await client.call_tool("plan_study_session", {"days_ahead": 14})).structured_content
    assert out2["created"] == [] and len(out2["skipped"]) == 2


async def test_orchestration_failure_no_deadlines(client):
    with pytest.raises(ToolError, match="nothing to plan"):
        await client.call_tool("plan_study_session", {"course": "EECE 503P", "days_ahead": 1})