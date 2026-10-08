"""The Company Brain agent: answers and a company-wide standup, as a given user.

The agent only ever sees what the asking user can read in Cognee: it recalls raw
records (each carrying its source, author, time and link) from the user's readable
datasets, then one LLM call through the Respan gateway writes the answer with
citations. Every run is traced in Respan as a workflow with recall / answer tasks.

    python -m brain.agent ask      --as bob@example.com "Is ACME-231 a duplicate of another ticket?"
    python -m brain.agent standup  --as alice@example.com
    python -m brain.agent grant    --from alice@example.com --to bob@example.com --dataset alice-brain
    python -m brain.agent revoke   --from alice@example.com --to bob@example.com --dataset alice-brain
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
from datetime import date
from pathlib import Path

from brain.memory import ROOT, get_user, readable_datasets, revoke_dataset, setup, share_dataset
from brain.split import USERS, dataset_for

import cognee  # noqa: E402
from cognee import SearchType  # noqa: E402
from openai import OpenAI  # noqa: E402
from respan import Respan, task, workflow  # noqa: E402
from respan_instrumentation_openai import OpenAIInstrumentor  # noqa: E402

import logging  # noqa: E402

logging.getLogger("respan_tracing").setLevel(logging.WARNING)
logging.getLogger("respan").setLevel(logging.WARNING)
respan = Respan(instrumentations=[OpenAIInstrumentor()])
llm = OpenAI(base_url=os.getenv("RESPAN_BASE_URL", "https://api.respan.ai/api"), api_key=os.environ["RESPAN_API_KEY"])
ANSWER_MODEL = os.getenv("ANSWER_MODEL", "gpt-4.1")
COMPANY = os.getenv("BRAIN_COMPANY", "the company")
TICKET_KEY = re.compile(r"\b[A-Z][A-Z0-9]{1,5}-\d+\b")
ALL_DATASETS = [dataset_for(u) for u in USERS]

RULES = """Rules:
- Use ONLY the records below. Each record starts with a header [source … · who · when · link].
- Cite every claim with the link from the record header, as a markdown link, e.g. ([ACME-210](https://…)).
- Prefer the most recent record when two disagree, and say that they disagree.
- If the records do not contain the answer, say so plainly. Never guess names, ticket ids or dates.
- Names: use the person names as written in the records."""


def _context(chunks) -> str:
    return "\n\n---\n\n".join(f"(dataset: {c.dataset_name})\n{c.text}" for c in chunks)


@task(name="recall")
def recall(email: str, queries: list[str], top_k: int = 12):
    async def _run():
        user = await get_user(email)
        ds = await readable_datasets(user)
        seen, chunks = set(), []
        lookups = [(q, SearchType.CHUNKS, top_k) for q in queries]
        # Vector search ranks exact identifiers (ticket keys) poorly; add a keyword lookup per id.
        for q in queries:
            lookups += [(key, SearchType.CHUNKS_LEXICAL, 5) for key in TICKET_KEY.findall(q)]
        for q, search_type, k in lookups:
            for c in await cognee.recall(q, dataset_ids=[d.id for d in ds], user=user,
                                         query_type=search_type, top_k=k):
                key = (c.dataset_name, c.text[:200])
                if key not in seen:
                    seen.add(key)
                    chunks.append(c)
        return sorted(d.name for d in ds), chunks

    return asyncio.run(_run())


@task(name="answer")
def generate(system: str, user_msg: str) -> str:
    r = llm.chat.completions.create(model=ANSWER_MODEL, temperature=0,
                                    messages=[{"role": "system", "content": system},
                                              {"role": "user", "content": user_msg}])
    return r.choices[0].message.content


def _access_note(readable: list[str]) -> str:
    hidden = [d for d in ALL_DATASETS if d not in readable]
    return (f"The asking user can read: {', '.join(readable)}. "
            + (f"They CANNOT read: {', '.join(hidden)}; if the answer seems incomplete, say that some "
               f"context may sit in datasets they have no access to." if hidden else "They can read everything."))


@workflow(name="ask_brain")
def ask(email: str, question: str) -> str:
    readable, chunks = recall(email, [question])
    system = f"You are the company brain for {COMPANY}, answering {email}.\n{_access_note(readable)}\n{RULES}"
    return generate(system, f"Question: {question}\n\nRecords:\n{_context(chunks)}")


STANDUP_QUERIES = [
    "what people worked on and shipped in the last two days",
    "what is in progress or planned today",
    "blocked, blocker, waiting on, stuck",
    "decision decided agreed approved",
    "duplicate ticket same bug related issue",
    "outdated document replaced old version contradicts",
    "release ship date version rollout",
    "meeting notes action items follow-up",
]

STANDUP_FORMAT = """Write today's company-wide standup for {company} as markdown, synthesised across
everyone in the records (not only the reader):

# Standup — {today} (as {email})
## Exec summary
3–5 bullets across the whole org.
## People
For each person with activity: ### Name — **Yesterday:** … · **Today:** … · **Blockers:** … (omit empty parts)
## Risks
Contradictions only the cross-section shows: duplicate tickets for one bug, a document that still
describes a replaced flow, a decision that affects someone who was not in the conversation.
## Opportunities
What one person's work unlocks for another: a learning to reuse, a dependency about to clear, a duplicate to merge.
## Access
One line: which datasets this standup was built from, and which it could not see."""


@workflow(name="standup")
def standup(email: str) -> str:
    readable, chunks = recall(email, STANDUP_QUERIES, top_k=10)
    today = date.today().strftime("%a %d %b %Y")
    system = (f"You are the company brain for {COMPANY}.\n{_access_note(readable)}\n{RULES}\n\n"
              + STANDUP_FORMAT.format(company=COMPANY, today=today, email=email))
    return generate(system, f"Records:\n{_context(chunks)}")


def grant(owner: str, grantee: str, dataset: str, revoke: bool = False) -> None:
    async def _run():
        await setup()
        await (revoke_dataset if revoke else share_dataset)(await get_user(owner), await get_user(grantee), dataset)
        readable = await readable_datasets(await get_user(grantee))
        verb = "revoked read on" if revoke else "granted read on"
        print(f"{owner} {verb} {dataset} for {grantee}. {grantee} now reads: {sorted(d.name for d in readable)}")

    asyncio.run(_run())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ask"); a.add_argument("--as", dest="email", required=True); a.add_argument("question")
    s = sub.add_parser("standup"); s.add_argument("--as", dest="email", required=True)
    g = sub.add_parser("grant"); g.add_argument("--from", dest="owner", required=True)
    g.add_argument("--to", dest="grantee", required=True); g.add_argument("--dataset", required=True)
    r = sub.add_parser("revoke"); r.add_argument("--from", dest="owner", required=True)
    r.add_argument("--to", dest="grantee", required=True); r.add_argument("--dataset", required=True)
    args = ap.parse_args()

    asyncio.run(setup())
    if args.cmd == "ask":
        print(ask(args.email, args.question))
    elif args.cmd == "standup":
        doc = standup(args.email)
        out = ROOT / "out" / f"standup-{date.today()}-{args.email.split('@')[0]}.md"
        out.parent.mkdir(exist_ok=True)
        out.write_text(doc)
        print(doc, f"\n\n(saved to {out.relative_to(ROOT)})")
    else:
        grant(args.owner, args.grantee, args.dataset, revoke=args.cmd == "revoke")
    respan.shutdown()


if __name__ == "__main__":
    main()
