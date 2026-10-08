"""Decide what goes into each user's Cognee dataset.

Follows the Cognee hackathon README (section 5, "one Scalekit identifier, one Cognee
user"): every user's own Scalekit pulls go into a dataset only that user can read,
"<name>-brain". There is no shared team dataset; sharing is an explicit grant from
the owner (brain.agent grant). Shared material (a channel both users are in, the same
Linear issue) is therefore extracted into each brain that can see it, which keeps every
user's graph complete and connected across sources.

This module only applies the content scope and time windows.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")  # so `python -m brain.split` sees BRAIN_* set in .env too

# Defaults point at the synthetic sample/; set BRAIN_RAW_DIR / BRAIN_USERS for your own pulls.
RAW_DIR = ROOT / os.getenv("BRAIN_RAW_DIR", "sample/raw")

USERS = dict(pair.strip().split("=", 1) for pair in
             os.getenv("BRAIN_USERS", "alice=alice@example.com,bob=bob@example.com").split(",") if pair.strip())
SOURCES = ("slack", "linear", "notion", "granola")

# Content scope: Linear teams to keep (BRAIN_LINEAR_TEAMS, comma list) and Notion titles to drop.
LINEAR_TEAMS = {t.strip() for t in os.getenv("BRAIN_LINEAR_TEAMS", "Product & Engineering,Operations").split(",") if t.strip()}
NOTION_EXCLUDE = re.compile(r"fundrais|seed|roadshow|investor|pricing|sales|gtm|finance|payroll|reimburse|hiring|offer|salary", re.I)

# Optional pins for items older than the window that should still be remembered:
# BRAIN_PINNED_TICKETS (comma list of Linear keys) and BRAIN_PINNED_TEXT (regex over
# Slack / Notion / Granola text). Default: nothing pinned.
PINNED_LINEAR = {t.strip() for t in os.getenv("BRAIN_PINNED_TICKETS", "").split(",") if t.strip()}
PINNED_TEXT = re.compile(os.environ["BRAIN_PINNED_TEXT"], re.I) if os.getenv("BRAIN_PINNED_TEXT") else None


def dataset_for(user: str) -> str:
    return f"{user}-brain"


def _load(user: str, source: str) -> list[dict]:
    path = RAW_DIR / USERS[user] / f"{source}.jsonl"
    return [json.loads(line) for line in path.open()] if path.exists() else []


def item_date(item: dict) -> str:
    """YYYY-MM-DD for an item; Granola dates come as 'Oct 7, 2026 10:00 AM'."""
    raw = str(item.get("updated") or item.get("time") or "")
    if re.match(r"\d{4}-\d{2}-\d{2}", raw):
        return raw[:10]
    m = re.match(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", raw)
    return datetime.strptime(" ".join(m.groups()), "%b %d %Y").strftime("%Y-%m-%d") if m else ""


def _pinned(item: dict, source: str) -> bool:
    if source == "linear":  # Linear text matches are too broad; pin by ticket only
        return item["id"] in PINNED_LINEAR or any(r.split()[-1] in PINNED_LINEAR for r in item.get("relations", []))
    if PINNED_TEXT is None:
        return False
    blob = " ".join([item.get("title", ""), item.get("text", "")] + [r.get("text", "") for r in item.get("replies", [])])
    return bool(PINNED_TEXT.search(blob))


def _window(items: list[dict], source: str, since: datetime) -> list[dict]:
    cutoff = since.isoformat()[:10]
    recent = [i for i in items if item_date(i) >= cutoff]
    ids = {i["id"] for i in recent}
    return recent + [i for i in items if i["id"] not in ids and _pinned(i, source)]


def _in_scope(source: str, item: dict) -> bool:
    if source == "linear":
        return item.get("team") in LINEAR_TEAMS
    if source == "notion":
        return not NOTION_EXCLUDE.search(item.get("title", ""))
    return True  # Slack scope is applied at pull time; Granola is the user's own calls


def split(days: int = 3, doc_days: int = 14) -> dict[str, dict[str, list[dict]]]:
    """Returns {dataset: {source: [items]}}, one dataset per user, built only from
    that user's own pulls. Activity sources use `days`; Notion uses `doc_days`."""
    # BRAIN_NOW pins "today" (ISO 8601) so the dated sample/ data stays inside the windows.
    now = datetime.fromisoformat(os.environ["BRAIN_NOW"]) if os.getenv("BRAIN_NOW") else datetime.now(timezone.utc)
    out = {}
    for user in USERS:
        out[dataset_for(user)] = {
            source: [i for i in _window(_load(user, source), source,
                                        now - timedelta(days=doc_days if source == "notion" else days))
                     if _in_scope(source, i)]
            for source in SOURCES
        }
    return out


if __name__ == "__main__":
    for ds, sources in split().items():
        print(ds, {s: len(v) for s, v in sources.items()})
