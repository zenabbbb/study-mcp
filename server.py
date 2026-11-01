import json
import os
from datetime import date, timedelta
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("Study Planner")
BASE = Path(__file__).parent


def _deadlines_path() -> Path:
    return Path(os.environ.get("DEADLINES_FILE", BASE / "deadlines.json"))

def _reminders_path() -> Path:
    return Path(os.environ.get("REMINDERS_FILE", BASE / "reminders.json"))


def get_deadlines(course: str | None = None, days_ahead: int = 14) -> list[dict]:
    """Return upcoming deadlines. Read-only: never changes anything.

    Args:
        course: optional course code, e.g. 'EECE 503P'. All courses if omitted.
        days_ahead: how many days ahead to look (must be greater than 0).

    Returns:
        A list of {id, course, title, due_date (YYYY-MM-DD)} sorted by due date.
    """
    if days_ahead <= 0:
        raise ToolError("days_ahead must be greater than 0.")

    items = json.loads(_deadlines_path().read_text())

    if course:
        wanted = course.strip().lower()
        items = [d for d in items if d["course"].lower() == wanted]
        if not items:
            raise ToolError(f"Unknown course '{course}'.")

    today = date.today()
    last_day = today + timedelta(days=days_ahead)
    upcoming = [d for d in items if today <= date.fromisoformat(d["due_date"]) <= last_day]
    return sorted(upcoming, key=lambda d: d["due_date"])

def create_reminder(title: str, remind_on: str) -> dict:
    """Save a reminder to the reminders file. This CHANGES state (writes a file).
    It does not look anything up.

    Args:
        title: what to be reminded about (must not be empty).
        remind_on: the date of the reminder, formatted YYYY-MM-DD, today or later.

    Returns:
        The saved reminder: {title, remind_on}.
    """
    title = title.strip()
    if not title:
        raise ToolError("title must not be empty.")
    try:
        when = date.fromisoformat(remind_on)
    except ValueError:
        raise ToolError(f"remind_on '{remind_on}' is not a valid YYYY-MM-DD date.")
    if when < date.today():
        raise ToolError(f"remind_on {remind_on} is in the past.")

    path = _reminders_path()
    reminders = json.loads(path.read_text()) if path.exists() else []
    record = {"title": title, "remind_on": remind_on}
    if record in reminders:
        raise ToolError(f"A reminder '{title}' on {remind_on} already exists.")
    reminders.append(record)
    path.write_text(json.dumps(reminders, indent=2))
    return record

def plan_study_session(course: str | None = None, days_ahead: int = 14) -> dict:
    """Coordinate the other two tools: fetch upcoming deadlines with get_deadlines,
    then create a reminder for each one the day before it is due (or today if that
    day has passed). Adds no new capability of its own.

    Args:
        course: optional course code. All courses if omitted.
        days_ahead: how many days ahead to plan for (must be greater than 0).

    Returns:
        {created: [...reminders saved], skipped: [...reasons], deadlines_found: int}
    """
    deadlines = get_deadlines(course, days_ahead)
    if not deadlines:
        raise ToolError(f"No deadlines in the next {days_ahead} days; nothing to plan.")

    created, skipped = [], []
    for d in deadlines:
        remind_on = max(date.today(), date.fromisoformat(d["due_date"]) - timedelta(days=1))
        title = f"{d['course']}: {d['title']} (due {d['due_date']})"
        try:
            created.append(create_reminder(title, remind_on.isoformat()))
        except ToolError as e:
            skipped.append(str(e))
    return {"created": created, "skipped": skipped, "deadlines_found": len(deadlines)}

mcp.tool(get_deadlines, annotations={"readOnlyHint": True})

mcp.tool(create_reminder, annotations={"readOnlyHint": False})

mcp.tool(plan_study_session, annotations={"readOnlyHint": False})
if __name__ == "__main__":
    mcp.run()