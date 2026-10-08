"""Pull raw data from Slack, Linear, Notion and Granola through Scalekit, as one user.

Every call runs with the user's own Scalekit identifier, so each user only gets what
their own accounts can see. Output is one JSONL file per source under
data/raw/<user>/, one record per item, with provenance (source, author, time, url).

    python -m brain.pull --user alice@yourco.com --days 30
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from brain.scalekit_client import CONNECTIONS, call

# Live pulls go to data/raw (git-ignored) by default, and never into the committed sample/.
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / os.getenv("BRAIN_RAW_DIR", "data/raw")

# Scope: public internal channels only, minus any channel matching BRAIN_EXCLUDE_CHANNELS.
# Thread replies cost one Scalekit call per thread and hit Slack rate limits fast.
FETCH_REPLIES = os.getenv("SLACK_FETCH_REPLIES", "0") == "1"
# Channels left out of scope: Slack Connect "shared-*" plus any regex in BRAIN_EXCLUDE_CHANNELS.
EXCLUDED_CHANNEL_PATTERNS = [re.compile(r"^shared-")] + (
    [re.compile(os.environ["BRAIN_EXCLUDE_CHANNELS"], re.I)] if os.getenv("BRAIN_EXCLUDE_CHANNELS") else [])


def _write(user: str, source: str, records: list[dict]) -> Path:
    out = RAW_DIR / user / f"{source}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return out


# --- Slack -------------------------------------------------------------------------

def _slack_users(user: str) -> dict[str, str]:
    names, cursor = {}, None
    while True:
        data = call("slack", user, "slack_list_users", {"limit": 1000, "cursor": cursor})
        for m in data.get("members", []):
            p = m.get("profile", {})
            names[m["id"]] = p.get("real_name") or p.get("display_name") or m.get("name", m["id"])
        cursor = (data.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            return names


def _slack_channels(user: str) -> list[dict]:
    channels, cursor = [], None
    while True:
        data = call("slack", user, "slack_list_user_conversations",
                    {"types": "public_channel", "limit": 200, "exclude_archived": True, "cursor": cursor})
        channels += data.get("channels", [])
        cursor = (data.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            break
    keep = []
    for ch in channels:
        if ch.get("is_private") or ch.get("is_ext_shared") or ch.get("is_shared"):
            continue
        if any(p.search(ch.get("name", "")) for p in EXCLUDED_CHANNEL_PATTERNS):
            continue
        keep.append(ch)
    return keep


def _slack_channel_messages(user: str, ch: dict, oldest: float, names: dict, team_url: str) -> list[dict]:
    out, cursor = [], None
    while True:
        data = call("slack", user, "slack_fetch_conversation_history",
                    {"channel": ch["id"], "oldest": str(oldest), "limit": 200, "cursor": cursor})
        for m in data.get("messages", []):
            text = (m.get("text") or "").strip()
            if not text or m.get("subtype") in ("channel_join", "channel_leave"):
                continue
            ts = m["ts"]
            replies = []
            if m.get("reply_count") and FETCH_REPLIES:
                rdata = call("slack", user, "slack_get_conversation_replies",
                             {"channel": ch["id"], "ts": ts, "limit": 200})
                for r in rdata.get("messages", [])[1:]:
                    if (r.get("text") or "").strip():
                        replies.append({
                            "author": names.get(r.get("user"), r.get("username") or r.get("bot_profile", {}).get("name") or "?"),
                            "time": datetime.fromtimestamp(float(r["ts"]), timezone.utc).isoformat(),
                            "text": r["text"].strip(),
                        })
            out.append({
                "source": "slack",
                "id": f"{ch['id']}:{ts}",
                "channel": ch["name"],
                "author": names.get(m.get("user"), m.get("username") or m.get("bot_profile", {}).get("name") or "?"),
                "time": datetime.fromtimestamp(float(ts), timezone.utc).isoformat(),
                "url": f"{team_url}archives/{ch['id']}/p{ts.replace('.', '')}",
                "text": text,
                "replies": replies,
            })
        cursor = (data.get("response_metadata") or {}).get("next_cursor")
        if not cursor or not data.get("has_more"):
            return out


def pull_slack(user: str, since: datetime) -> list[dict]:
    team_url = call("slack", user, "slack_auth_test", {}).get("url", "https://slack.com/")
    names = _slack_users(user)
    channels = _slack_channels(user)
    print(f"  slack: {len(channels)} channels in scope")
    out = []
    for n, ch in enumerate(channels, 1):  # sequential: Scalekit rate-limits Slack history + threads
        try:
            msgs = _slack_channel_messages(user, ch, since.timestamp(), names, team_url)
        except Exception as e:  # keep going; one noisy channel should not sink the pull
            print(f"  slack: skip #{ch['name']}: {type(e).__name__}", flush=True)
            continue
        out += msgs
        print(f"  slack: [{n}/{len(channels)}] #{ch['name']}: {len(msgs)}", flush=True)
    return out


# --- Linear ------------------------------------------------------------------------

LINEAR_QUERY = """
query Issues($after: String, $since: DateTimeOrDuration) {
  issues(first: 100, after: $after, filter: { updatedAt: { gt: $since } }, orderBy: updatedAt) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id identifier title description url createdAt updatedAt priorityLabel
      state { name } team { key name } project { name }
      creator { name email } assignee { name email }
      labels { nodes { name } }
      relations { nodes { type relatedIssue { identifier } } }
      comments(first: 30) { nodes { body createdAt user { name } } }
    }
  }
}
"""


def pull_linear(user: str, since: datetime) -> list[dict]:
    out, after = [], None
    while True:
        data = call("linear", user, "linear_graphql_query",
                    {"query": LINEAR_QUERY, "variables": {"after": after, "since": since.isoformat()}})
        issues = (data.get("data") or data).get("issues", {})
        for i in issues.get("nodes", []):
            out.append({
                "source": "linear",
                "id": i["identifier"],
                "title": i["title"],
                "team": (i.get("team") or {}).get("name"),
                "project": (i.get("project") or {}).get("name"),
                "state": (i.get("state") or {}).get("name"),
                "priority": i.get("priorityLabel"),
                "author": (i.get("creator") or {}).get("name"),
                "assignee": (i.get("assignee") or {}).get("name"),
                "labels": [l["name"] for l in (i.get("labels") or {}).get("nodes", [])],
                "relations": [f"{r['type']} {r['relatedIssue']['identifier']}"
                              for r in (i.get("relations") or {}).get("nodes", []) if r.get("relatedIssue")],
                "time": i["createdAt"],
                "updated": i["updatedAt"],
                "url": i["url"],
                "text": i.get("description") or "",
                "comments": [{"author": (c.get("user") or {}).get("name", "?"), "time": c["createdAt"], "text": c["body"]}
                             for c in (i.get("comments") or {}).get("nodes", [])],
            })
        page = issues.get("pageInfo", {})
        if not page.get("hasNextPage"):
            return out
        after = page["endCursor"]


# --- Notion ------------------------------------------------------------------------

def _notion_title(page: dict) -> str:
    for prop in (page.get("properties") or {}).values():
        if prop.get("type") == "title":
            return "".join(t.get("plain_text", "") for t in prop.get("title", [])) or "Untitled"
    return "Untitled"


def pull_notion(user: str, since: datetime, max_pages: int = 300) -> list[dict]:
    pages, cursor = [], None
    while len(pages) < max_pages:
        data = call("notion", user, "notion_page_search",
                    {"page_size": 100, "sort_timestamp": "last_edited_time", "sort_direction": "descending",
                     "start_cursor": cursor})
        batch = data.get("results", [])
        recent = [p for p in batch if p.get("last_edited_time", "") >= since.isoformat()[:19]]
        pages += recent
        if len(recent) < len(batch) or not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    print(f"  notion: {len(pages)} pages edited since {since.date()}")

    def fetch(p):
        try:
            md = call("notion", user, "notion_page_markdown_get", {"page_id": p["id"]})
            text = md.get("markdown") if isinstance(md, dict) else str(md)
        except Exception as e:  # one unreadable page should not sink the pull
            print(f"  notion: skip {p['id']}: {str(e)[:80]}")
            return None
        return {
            "source": "notion",
            "id": p["id"],
            "title": _notion_title(p),
            "author": ((p.get("created_by") or {}).get("id")),
            "time": p.get("created_time"),
            "updated": p.get("last_edited_time"),
            "url": p.get("url"),
            "text": text or "",
        }

    with ThreadPoolExecutor(max_workers=6) as pool:
        return [r for r in pool.map(fetch, pages[:max_pages]) if r and r["text"].strip()]


# --- Granola -----------------------------------------------------------------------

def _granola_text(data) -> str:
    if isinstance(data, dict) and "content" in data:
        return "\n".join(c.get("text", "") for c in data["content"] if c.get("type") == "text")
    return str(data)


def pull_granola(user: str, since: datetime) -> list[dict]:
    listing = _granola_text(call("granola", user, "granolamcp_list_meetings", {"time_range": "last_30_days"}))
    meetings = re.findall(r'<meeting id="([^"]+)" title="([^"]*)" date="([^"]*)"', listing)
    print(f"  granola: {len(meetings)} meetings")
    out = []
    for i in range(0, len(meetings), 10):
        chunk = meetings[i:i + 10]
        detail = _granola_text(call("granola", user, "granolamcp_get_meetings", {"meeting_ids": [m[0] for m in chunk]}))
        # Split the combined response back into one block per meeting id.
        for mid, title, date in chunk:
            m = re.search(rf'<meeting id="{re.escape(mid)}".*?</meeting>', detail, re.S)
            body = m.group(0) if m else ""
            out.append({
                "source": "granola",
                "id": mid,
                "title": title,
                "time": date,
                "url": f"https://notes.granola.ai/d/{mid}",
                "text": body,
            })
    return out


# --- main --------------------------------------------------------------------------

PULLERS = {"slack": pull_slack, "linear": pull_linear, "notion": pull_notion, "granola": pull_granola}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", required=True, help="Scalekit identifier, also the Cognee user email")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--sources", default=",".join(PULLERS), help="comma-separated subset of " + ",".join(PULLERS))
    args = ap.parse_args()
    if RAW_DIR.resolve().is_relative_to((ROOT / "sample").resolve()):
        raise SystemExit(f"Refusing to write a live pull into {RAW_DIR}: sample/ is committed. "
                         "Set BRAIN_RAW_DIR=data/raw (git-ignored).")

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    print(f"Pulling as {args.user} since {since.date()} ({', '.join(CONNECTIONS)})")
    for source in args.sources.split(","):
        t0 = time.time()
        try:
            records = PULLERS[source](args.user, since)
        except Exception as e:
            print(f"  {source}: FAILED {type(e).__name__}: {str(e)[:200]}")
            continue
        path = _write(args.user, source, records)
        print(f"  {source}: {len(records)} records -> {path.relative_to(RAW_DIR.parent.parent)} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
