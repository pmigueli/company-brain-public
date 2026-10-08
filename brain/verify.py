"""Isolation check over the users in BRAIN_USERS (default: the alice / bob sample).

For every user, prints the datasets they can read, then checks that addressing any
other user's brain by name is refused unless that brain was granted to them. Cognee
reaches a shared dataset by id, so a by-name request for someone else's brain must
fail (DatasetNotFoundError). Grants nothing and revokes nothing. Exits 1 on a leak.

    python -m brain.verify
    python -m brain.verify "Is ACME-231 a duplicate of another ticket?"   # plus raw recall per user
"""

from __future__ import annotations

import asyncio
import sys

from brain.memory import get_user, readable_datasets, setup
from brain.split import USERS, dataset_for

import cognee  # noqa: E402


async def recall_as(user, question: str) -> None:
    ds = await readable_datasets(user)
    print(f"\n[{user.email}] readable: {sorted(d.name for d in ds)}\nQ: {question}")
    try:
        results = await cognee.recall(question, dataset_ids=[d.id for d in ds], user=user)
    except Exception as e:
        print(f"  ERROR {type(e).__name__}: {str(e)[:200]}")
        return
    for r in results[:3]:
        print("  ->", (getattr(r, "text", None) or str(r))[:600].replace("\n", " "))


async def main(question: str | None) -> int:
    await setup()
    users = {name: await get_user(email) for name, email in USERS.items()}
    leaks = 0
    for name, user in users.items():
        readable = sorted(d.name for d in await readable_datasets(user))
        print(f"{user.email} reads: {readable}")
        for owner in USERS:
            target = dataset_for(owner)
            if owner == name or target in readable:
                continue
            try:
                await cognee.recall("anything", datasets=[target], user=user)
                print(f"  ISOLATION FAILED: {user.email} could read {target}")
                leaks += 1
            except Exception as e:
                print(f"  isolation ok: {user.email} -> {target} refused ({type(e).__name__})")
    if question:
        for user in users.values():
            await recall_as(user, question)
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(" ".join(sys.argv[1:]) or None)))
