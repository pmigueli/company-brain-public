"""Thin wrapper over Scalekit AgentKit: one client, connection names in one place.

Every call passes the acting user's identifier; Scalekit injects that user's token.
No tokens ever reach this code.
"""

from __future__ import annotations

import os
import random
import time
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from scalekit import ScalekitClient  # noqa: E402

# Logical source -> Scalekit connection name (as created in AgentKit -> Connections).
CONNECTIONS = {
    "slack": os.getenv("SCALEKIT_SLACK_CONNECTION", "slack"),
    "linear": os.getenv("SCALEKIT_LINEAR_CONNECTION", "linear"),
    "notion": os.getenv("SCALEKIT_NOTION_CONNECTION", "notion"),
    "granola": os.getenv("SCALEKIT_GRANOLA_CONNECTION", "granola"),
}


@lru_cache(maxsize=1)
def actions():
    return ScalekitClient(
        env_url=os.environ["SCALEKIT_ENVIRONMENT_URL"],
        client_id=os.environ["SCALEKIT_CLIENT_ID"],
        client_secret=os.environ["SCALEKIT_CLIENT_SECRET"],
    ).actions


def call(source: str, identifier: str, tool: str, tool_input: dict, retries: int = 8) -> dict:
    """Run one Scalekit tool as `identifier`. Drops None inputs; returns the tool's data.
    Backs off on rate limits (429), which Slack history + thread pulls hit quickly."""
    clean = {k: v for k, v in tool_input.items() if v is not None}
    for attempt in range(retries):
        try:
            return actions().execute_tool(
                tool_name=tool, tool_input=clean, connection_name=CONNECTIONS[source], identifier=identifier
            ).data
        except Exception as e:
            if "429" not in str(e) and "RateLimit" not in type(e).__name__ or attempt == retries - 1:
                raise
            time.sleep(min(30, 2 ** attempt) + random.random())


def auth_status(identifier: str) -> dict[str, str]:
    a = actions()
    return {
        source: a.get_or_create_connected_account(connection_name=conn, identifier=identifier).connected_account.status
        for source, conn in CONNECTIONS.items()
    }
