"""Remember pulled data in Cognee: one dataset per user, provenance in node_set tags.

Reads data/raw/<user>/<source>.jsonl (written by brain.pull), turns each item into a
compact text record that keeps who / when / where / link, and remembers it into the
user's own dataset. With ENABLE_BACKEND_ACCESS_CONTROL=true nobody else can recall it
until the owner shares the dataset.

    python -m brain.ingest                       # every user's brain
    python -m brain.ingest --datasets alice-brain --sources granola
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import defaultdict

from brain.memory import get_user, setup
from brain.split import USERS, dataset_for, split

import cognee  # noqa: E402  (brain.memory loads .env and configures cognee first)

MAX_TEXT = 1500  # chars of body kept per item; the link always points to the full source
DOC_CHARS = 8000  # target size of one remembered document (several items batched together)


def _clip(text: str, n: int = MAX_TEXT) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n] + " …"


def fmt_slack(m: dict) -> str:
    lines = [f"[slack #{m['channel']} · {m['author']} · {m['time'][:16]} · {m['url']}] {_clip(m['text'], 800)}"]
    for r in m.get("replies", [])[:15]:
        lines.append(f"    ↳ reply · {r['author']} · {r['time'][:16]}: {_clip(r['text'], 400)}")
    return "\n".join(lines)


def fmt_linear(i: dict) -> str:
    head = (f"[linear {i['id']} · team {i['team']} · state {i['state']} · created by {i['author']} "
            f"· assignee {i['assignee'] or 'unassigned'} · created {i['time'][:10]} · updated {i['updated'][:10]} · {i['url']}]")
    parts = [head, f"Title: {i['title']}"]
    if i.get("project"):
        parts.append(f"Project: {i['project']}")
    if i.get("relations"):
        parts.append("Relations: " + ", ".join(i["relations"]))
    if i.get("text"):
        parts.append(_clip(i["text"], 700))
    for c in i.get("comments", [])[-3:]:
        parts.append(f"  comment · {c['author']} · {c['time'][:10]}: {_clip(c['text'], 250)}")
    return "\n".join(parts)


def fmt_notion(p: dict) -> str:
    return f"[notion page \"{p['title']}\" · last edited {str(p.get('updated'))[:10]} · {p['url']}]\n{_clip(p['text'], 3000)}"


def fmt_granola(g: dict) -> str:
    return f"[granola meeting \"{g['title']}\" · {g['time']} · {g['url']}]\n{_clip(g['text'], 3000)}"


FORMATTERS = {"slack": fmt_slack, "linear": fmt_linear, "notion": fmt_notion, "granola": fmt_granola}


def group_key(source: str, item: dict) -> str:
    """Items that share a key are remembered together, under the same node_set tags."""
    if source == "slack":
        return f"channel:{item['channel']}"
    if source == "linear":
        return f"team:{item['team']}"
    return f"{source}"


def build_documents(owner: str, items_by_source: dict[str, list[dict]]) -> list[tuple[list[str], str]]:
    """Returns (node_set, document_text) pairs, documents capped at DOC_CHARS."""
    docs = []
    for source, items in items_by_source.items():
        items = sorted(items, key=lambda x: str(x.get("updated") or x.get("time") or ""), reverse=True)
        groups: dict[str, list[str]] = defaultdict(list)
        for it in items:
            groups[group_key(source, it)].append(FORMATTERS[source](it))
        n0 = len(docs)
        for key, records in groups.items():
            tags = [f"source:{source}", key, f"owner:{owner}"]
            buf, size = [], 0
            for rec in records:
                if size + len(rec) > DOC_CHARS and buf:
                    docs.append((tags, "\n\n".join(buf)))
                    buf, size = [], 0
                buf.append(rec)
                size += len(rec)
            if buf:
                docs.append((tags, "\n\n".join(buf)))
        print(f"  {source}: {len(items)} items -> {len(docs) - n0} documents")
    return docs


async def ingest_dataset(dataset: str, owner_email: str, items_by_source: dict[str, list[dict]]) -> None:
    user = await get_user(owner_email)
    docs = build_documents(owner_email, items_by_source)
    total = sum(len(d) for _, d in docs)
    print(f"Remembering {len(docs)} documents ({total:,} chars) into {dataset} as {owner_email}")
    by_tags: dict[tuple, list[str]] = defaultdict(list)
    for tags, text in docs:
        by_tags[tuple(tags)].append(text)
    t0 = time.time()
    for tags, texts in by_tags.items():
        t = time.time()
        await cognee.remember(texts, dataset_name=dataset, user=user, node_set=list(tags))
        print(f"  ✓ {dataset:12} {tags[1]:40} {len(texts):3} docs {time.time() - t:5.0f}s", flush=True)
    print(f"{dataset} done in {time.time() - t0:.0f}s", flush=True)


async def run(datasets: list[str], sources: list[str], days: int) -> None:
    await setup()
    plan = split(days=days)
    for ds in datasets:
        owner = USERS[ds.removesuffix("-brain")]
        items = {s: v for s, v in plan[ds].items() if s in sources and v}
        await ingest_dataset(ds, owner, items)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datasets", default=",".join(dataset_for(u) for u in USERS))
    ap.add_argument("--sources", default="slack,linear,notion,granola")
    ap.add_argument("--days", type=int, default=3, help="standup window for activity sources")
    args = ap.parse_args()
    asyncio.run(run(args.datasets.split(","), args.sources.split(","), args.days))


if __name__ == "__main__":
    main()
