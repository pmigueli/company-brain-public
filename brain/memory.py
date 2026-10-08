"""Cognee setup shared by ingestion, the agent and the evals.

One Scalekit identifier == one Cognee user (same email). Each user owns one dataset,
"<name>-brain"; access control makes it invisible to everyone else until shared.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
# Must be set before cognee is imported.
# Forced, not defaulted: with it off every dataset shares one store and isolation silently disappears.
os.environ["ENABLE_BACKEND_ACCESS_CONTROL"] = "true"
# Cognee only accepts absolute storage roots; keep all state inside the repo by default.
os.environ.setdefault("SYSTEM_ROOT_DIRECTORY", str(ROOT / ".cognee_system"))
os.environ.setdefault("DATA_ROOT_DIRECTORY", str(ROOT / ".cognee_data"))
# Cognee logs every retrieval step at info; keep the terminal readable for the demo.
os.environ.setdefault("LOG_LEVEL", "ERROR")
(ROOT / ".cognee_system" / "databases").mkdir(parents=True, exist_ok=True)
(ROOT / ".cognee_data").mkdir(parents=True, exist_ok=True)

import cognee  # noqa: E402,F401

# Cognee needs a password to create a local user; it only matters for the local Cognee UI login.
LOCAL_PASSWORD = os.getenv("BRAIN_LOCAL_PASSWORD", "change-me-local-only")


def dataset_for(email: str) -> str:
    return f"{email.split('@')[0]}-brain"


async def setup() -> None:
    """Create cognee's relational tables on a fresh install (user lookups fail without it)."""
    from cognee.modules.engine.operations.setup import setup as _setup

    await _setup()


async def get_user(email: str):
    from cognee.modules.users.methods import create_user, get_user_by_email

    return await get_user_by_email(email) or await create_user(email, LOCAL_PASSWORD)


async def readable_datasets(user):
    from cognee.modules.data.methods import get_authorized_existing_datasets

    return await get_authorized_existing_datasets(None, "read", user)


async def _owned_dataset(owner, dataset_name: str):
    from cognee.modules.data.methods import get_authorized_existing_datasets

    found = await get_authorized_existing_datasets([dataset_name], "share", owner)
    if not found:
        raise SystemExit(f"{owner.email} has no dataset named {dataset_name}")
    return found[0]


async def share_dataset(owner, grantee, dataset_name: str) -> None:
    """Owner grants grantee read access to one of the owner's datasets."""
    from cognee.modules.users.permissions.methods import authorized_give_permission_on_datasets

    ds = await _owned_dataset(owner, dataset_name)
    await authorized_give_permission_on_datasets(grantee.id, [ds.id], "read", owner.id)


async def revoke_dataset(owner, grantee, dataset_name: str) -> None:
    """Undo share_dataset, so the access demo can be rehearsed."""
    from cognee.modules.users.permissions.methods import authorized_revoke_permission_on_datasets

    ds = await _owned_dataset(owner, dataset_name)
    await authorized_revoke_permission_on_datasets(grantee.id, [ds.id], "read", owner.id)
