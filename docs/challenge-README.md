> The organizers' challenge README, moved here from the repo root so the root README can describe
> our project. Content unchanged; relative links adjusted to the new location. Our project: [../README.md](../README.md).

# Build a Company Brain — AI Agents with Memory, Context and Secure Access

📍 **San Francisco · 2026-10-07 · 2:00 PM – 7:30 PM PT · part of #SFTechWeek**

🧠 **Cognee × Scalekit × Respan** 🚀

Most companies have their knowledge scattered across documents, Slack
conversations, code, tickets, CRM systems and other business apps. The
challenge is not simply giving an AI agent *access* to those tools — it is
giving the agent a **persistent understanding of the company**, while making
sure every user only sees and acts on what they are authorized to.

In this hackathon you build a **Company Brain** out of three layers:

| Layer | Tool | What it does |
|-------|------|--------------|
| **Access** | [Scalekit](https://docs.scalekit.com/agentkit/overview/) | Pulls data from each user's Google Drive, Slack, Gmail, Notion, … through managed OAuth — and **pulls and pushes code** on GitHub (read files and PRs, create branches, commits and pull requests). Your code never touches a token. |
| **Memory** | [Cognee](https://github.com/topoteretes/cognee) | Turns what Scalekit pulls into one knowledge graph the agent can `remember` into and `recall` from, per user, per dataset. |
| **LLM gateway + Evals** | [Respan](https://www.respan.ai/) | **Provides LLM credits on its gateway for the event** — one OpenAI-compatible endpoint for 1,000+ models — and traces and scores your agents' runs, so you can show the brain does the job before and after a change. |

The goal: build something that makes us think
*"this is what it would look like if a company had a brain."*

## What You Build

A Company Brain for a team workflow, wired end to end:

1. **Pull with Scalekit** — connect **at least two** systems of record
   (Drive + Slack, GitHub + Notion, Gmail + HubSpot, …) through Scalekit
   AgentKit connectors. Each user authorizes once; your agent pulls on their
   behalf using their `identifier`. Code counts as a source: the GitHub
   connector pulls repositories, files, issues and PRs — and pushes back
   (branches, commits, pull requests) when the agent has something to ship.
2. **Remember with Cognee** — send what you pulled into Cognee with
   `cognee.remember(...)`, tagged by source and scoped to the user who is
   allowed to see it. Cognee extracts entities and relationships into one
   graph across sources, so "the doc, the thread and the PR about the launch"
   become one connected thing.
3. **Wire agents for tasks** — build the agent(s) that use the brain to
   **retrieve knowledge, coordinate work, or take action**: a pre-meeting
   brief, an expert finder, a ticket triager, an onboarding guide, a "who
   decided this and why" assistant. Agents `recall` from Cognee and, when
   they need to act, write back through Scalekit (post to Slack, draft an
   email, open an issue, push a commit and open a PR). Route the agents'
   LLM calls through the Respan gateway — the event credits live there.
4. **Evaluate with Respan** — trace the agent runs and score them against a
   scenario set with Respan evaluators. Change the brain or the agent, re-run,
   and show the **before/after** scores.

Move beyond single-app demos. Projects should reflect how teams actually
work: across documents, collaboration tools, engineering systems and business
apps, with more than one person and more than one permission level.

## Architecture — Pull → Remember → Act → Evaluate

```text
   Google Drive   Slack   Gmail   GitHub   Notion   HubSpot   ...
        │          │        │       ▲│       │        │
        └──────────┴────────┴───┬───┘┴───────┴────────┘
                                │  OAuth per user, tokens stored + refreshed
                                ▼  (GitHub: pull code + PRs in, push commits + PRs out)
                  ┌───────────────────────────────┐
                  │  Scalekit AgentKit             │   ACCESS
                  │  execute_tool(identifier=...)  │   who may read / act on what
                  └──────────────┬────────────────┘
                                 │  documents, threads, issues, emails, code
                                 ▼
                  ┌───────────────────────────────┐
                  │  Cognee                        │   MEMORY
                  │  remember(data, node_set=[…],  │   one graph across sources,
                  │           dataset_name=…,      │   one dataset per user / team,
                  │           user=…)              │   permissions enforced on recall
                  │  recall(question, user=…)      │
                  └──────────────┬────────────────┘
                                 │  grounded context
                                 ▼
                  ┌───────────────────────────────┐
                  │  Your agent(s)                 │   TASKS
                  │  brief · triage · find-expert  │   LLM calls via the Respan
                  │  LLM → Respan gateway          │   gateway (event credits);
                  │  …traced + scored by Respan    │   act via Scalekit: post,
                  └──────────────┬────────────────┘   draft, open issue, push PR
                                 ▼
                           [ your team ]
```

Three things judges look for in that diagram:

- **Access shapes the experience.** The same question asked by two users with
  different Scalekit connections / Cognee permissions should get different
  answers — and the demo should show it.
- **Memory is cross-source.** A good answer stitches a Drive doc, a Slack
  thread and a GitHub issue together. A single-connector brain is a RAG demo.
- **Evaluation is part of the build.** A scenario set scored in Respan, run
  before and after a change, beats a hand-picked screenshot.

## Prizes

Prizes are announced at kickoff. Expect an afternoon of building, feedback,
demos and prizes from the partners.

## Demo Format

You will have **3 minutes** to stand out:

- Present your Company Brain idea and the team workflow it solves.
- Run a live demo: pull → remember → agent task → eval scores.
- Show the access story: what changes when a different user asks.

## Schedule

All times **Pacific Time (PT)**. Final timings are confirmed at kickoff.

| Time | What |
|------|------|
| 2:00 PM | Doors open + networking |
| 2:30 PM | Opening remarks + partner walkthroughs |
| 3:00 PM | Hacking begins |
| 6:00 PM | Project submission deadline — finalists selected |
| 6:15 PM | Finalist demos & judging |
| 7:00 PM | Awards |
| 7:30 PM | Event wrap-up & doors close |

## Reference App — Scalekit + Cognee, end to end

Want to see the Access and Memory layers wired together before you write a
line? Scalekit's
[`cognee-scalekit-example`](https://github.com/scalekit-developers/cognee-scalekit-example)
is a small local web app (a comic-book shop's "Book Issue Desk", two
customers) that does exactly what steps 3–5 below describe:

- each customer's notes land in **their own Cognee dataset**, and questions
  are answered only from that dataset — the per-user isolation this
  hackathon asks for;
- customers **sign in through Scalekit**, which tells the app who is at the
  browser and can **post to Slack on their behalf** — the Slack token never
  reaches the app or Cognee;
- it works against **local Cognee or Cognee Cloud** unchanged;
- it indexes **its own source code** into Cognee's code graph and answers
  structural questions with no LLM call.

It ships with a kickoff skill for coding agents
(`.agents/skills/cognee-hackathon-kickoff/SKILL.md`) that is the 15-minute
version of its README plus project ideas. Fork it as a starting point, or
read it as the reference for how the pieces fit.

## Setup

> **Bring a laptop and a GitHub account.** LLM access is **provided at
> kickoff as Respan gateway credits**: one `RESPAN_API_KEY` that reaches
> OpenAI, Anthropic, Gemini and 1,000+ other models through a single
> OpenAI-compatible endpoint. Scalekit has a free tier that is enough for the
> event; creating that account ahead of time saves you ten minutes, but is
> not required.

### Prerequisites

- Python 3.10 – 3.14
- `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A Scalekit account — free tier is enough: <https://app.scalekit.com>
- A Respan API key with event credits — **provided by us at kickoff** (or
  bring your own LLM key from any
  [supported provider](https://docs.cognee.ai/setup-configuration/llm-providers))

### 0. Let your coding agent keep cognee feedback for us

Please use the **`cognee-hackathon-feedback`** skill during the hack. Your
agent (Claude Code, Codex, Cursor, …) keeps a private record of how cognee
behaved for you — errors, slow steps, confusion, workarounds, and how
frustrating each was — in `./cognee-feedback.md`. It records sentiment, never
quotes; no keys, `.env`, data, or names ever go in the file, and the agent
never sends or commits it. It is the single most useful thing you can hand us
after the event.

- **Building inside this folder?** It is already installed: `.claude/skills/`,
  `.agents/skills/`, the checkpoint hook in `.claude/settings.json` /
  `.codex/hooks.json`, and the standing instruction in `AGENTS.md` /
  `CLAUDE.md`. Codex asks you to trust the project once — say yes so the
  checkpoint runs.
- **Bringing your own repo?** One command, from its root:
  ```bash
  curl -fsSL https://raw.githubusercontent.com/topoteretes/cognee-hackathons/main/agent-skills/cognee-hackathon-feedback/install.sh \
    | sh -s -- --event "Build a Company Brain — SF Tech Week 2026-10-07"
  ```
- **Before you submit:** run `/cognee-hackathon-feedback` in your agent so
  it writes the wrap-up, then attach `cognee-feedback.md` where the
  submission form says (see [`templates/SUBMISSION.md`](../templates/SUBMISSION.md)).

How it works and what it does not do:
[`agent-skills/README.md`](https://github.com/topoteretes/cognee-hackathons/tree/main/agent-skills/README.md).

### 1. Install

```bash
uv venv && source .venv/bin/activate
uv pip install "cognee>=1.6.3" scalekit-sdk-python python-dotenv
```

### 2. Configure the LLM — Respan gateway credits

Respan is providing LLM credits on its gateway for the event. The gateway is
OpenAI-compatible, so Cognee's `custom` provider talks to it directly — point
Cognee at `https://api.respan.ai/api` with your Respan key and pick any model
slug:

```bash
export LLM_PROVIDER="custom"
export LLM_ENDPOINT="https://api.respan.ai/api"
export LLM_API_KEY="<respan-key-we-give-you-at-the-event>"
export LLM_MODEL="openai/gpt-5-mini"          # any slug the gateway routes; swap freely

# Embeddings through the same gateway and key
export EMBEDDING_PROVIDER="custom"
export EMBEDDING_ENDPOINT="https://api.respan.ai/api"
export EMBEDDING_API_KEY="<same-respan-key>"
export EMBEDDING_MODEL="openai/text-embedding-3-large"
export EMBEDDING_DIMENSIONS=3072
```

Your own agent code uses the same two values with any OpenAI SDK:

```python
from openai import OpenAI

llm = OpenAI(base_url="https://api.respan.ai/api", api_key=os.environ["RESPAN_API_KEY"])
llm.chat.completions.create(model="gpt-5-mini", messages=[...])
```

Every call through the gateway is logged in Respan with model, tokens, cost
and latency — which is also the trace your evals score against (step 6).
Keep the `openai/` prefix on the slugs: it tells Cognee's LiteLLM layer to
speak the OpenAI-compatible format to `LLM_ENDPOINT`. `EMBEDDING_DIMENSIONS`
must match the embedding model you pick (3072 for `text-embedding-3-large`,
1536 for `-small`). If an embedding slug is not routed by the gateway, point
only the `EMBEDDING_*` vars at a direct provider key and keep the LLM on
Respan.
Or copy [`.env.example`](../.env.example) to `.env` and fill it in; Cognee
reads `.env` from the working directory. Prefer your own key? Set
`LLM_PROVIDER` / `LLM_MODEL` per the
[provider docs](https://docs.cognee.ai/setup-configuration/llm-providers).

### 3. Scalekit — connect the data sources

Scalekit AgentKit gives your agent per-user, OAuth-managed connections to
400+ apps and prebuilt tools on each (`gmail_fetch_mails`,
`slack_fetch_conversation_history`, `googledrive_export_file`, …). You pass a
stable `identifier` for the user; Scalekit adds their token, calls the API and
returns JSON.

1. In the Scalekit dashboard, copy **Developers → API Credentials** into your
   `.env`:
   ```text
   SCALEKIT_ENVIRONMENT_URL=https://<env>.scalekit.dev
   SCALEKIT_CLIENT_ID=skc_...
   SCALEKIT_CLIENT_SECRET=...
   ```
2. Under **AgentKit → Connections**, create one connection per source you
   want (e.g. `slack`, `googledrive`, `gmail`). The name you give a connection
   is the `connection_name` your code passes. Some connectors (Slack, for
   one) can use Scalekit's own OAuth app; Google Drive needs your own Google
   OAuth client. Each connector page says which and walks you through it.
3. Authorize each **user** once per connection, then pull:

```python
import os
from scalekit import ScalekitClient

sk = ScalekitClient(
    env_url=os.environ["SCALEKIT_ENVIRONMENT_URL"],
    client_id=os.environ["SCALEKIT_CLIENT_ID"],
    client_secret=os.environ["SCALEKIT_CLIENT_SECRET"],
)
actions = sk.actions

identifier = "alice@acme.com"   # stable, hard-to-guess id for THIS user

# One-time consent per user per connection (no-op once the account is ACTIVE)
account = actions.get_or_create_connected_account(connection_name="slack", identifier=identifier)
if account.connected_account.status != "ACTIVE":
    link = actions.get_authorization_link(connection_name="slack", identifier=identifier)
    print("Authorize Slack:", link.link)
    input("Press Enter after authorizing...")

# Every call afterwards: Scalekit adds the user's token for you
history = actions.execute_tool(
    tool_name="slack_fetch_conversation_history",
    tool_input={"channel": "#launch", "limit": 200},
    connection_name="slack",
    identifier=identifier,
)
messages = history.data["messages"]
```

Useful read tools to start from:

| Source | Tool | Returns |
|--------|------|---------|
| Slack | `slack_fetch_conversation_history` | messages in one channel/DM, paginated by `cursor` |
| Slack | `slack_search_messages` | text search across the workspace |
| Google Drive | `googledrive_search_files` / `googledrive_list_folder_contents` | file ids + metadata |
| Google Drive | `googledrive_export_file` | a Doc/Sheet/Slide exported to a MIME type (`text/plain`, `text/csv`) |
| Gmail | `gmail_fetch_mails` | messages matching a Gmail `query` |
| GitHub | `github_file_contents_get` / `github_git_tree_get` | a file (base64) or a whole tree — pull code into the brain |
| GitHub | `github_pull_requests_list` / `github_pull_request_files_list` / `github_issues_list` | PRs, their diffs, and issues |

**Scalekit pushes code too.** The GitHub connector has 217 tools, 76 of them
writes, so an agent that has something to ship does it as the user:
`github_branch_create` → `github_file_create_update` (one or more files) →
`github_pull_request_create`, or the lower-level `github_git_blob_create` /
`github_git_tree_create` / `github_git_commit_create` / `github_git_ref_update`
for a multi-file commit. The PR lands under the authorizing user's account,
not a bot's. Pair it with Cognee's code graph: `remember("https://github.com/org/repo")`
builds the symbol/import graph, the agent reasons over it, then pushes the
change back through Scalekit.

Every connector page lists its tools and their inputs:
[Slack](https://docs.scalekit.com/agentkit/connectors/slack) ·
[Google Drive](https://docs.scalekit.com/agentkit/connectors/googledrive/) ·
[GitHub](https://docs.scalekit.com/agentkit/connectors/github) ·
[all connectors](https://docs.scalekit.com/agentkit/connectors/).
`actions.list_tools(connection_name="slack")` returns the same schemas from
code — handy for handing them straight to an LLM as tool definitions.
Building with a coding agent? `npx @scalekit-inc/cli setup` installs
Scalekit's skills into Claude Code / Cursor / Codex.

### 4. Cognee — remember what you pulled

Cognee's memory API is four calls: `remember`, `recall`, `improve`, `forget`.
Turn each pulled item into text and `remember` it, tagging the source with
`node_set` so the graph keeps provenance and the demo can show *where* an
answer came from:

```python
import asyncio
import cognee


async def main():
    # 1. Remember — runs add + cognify (+ improve) and builds the graph.
    #    One document per channel keeps the conversation context together.
    transcript = "\n".join(
        f"[slack #launch · {m['user']} · {m['ts']}] {m['text']}" for m in reversed(messages)
    )
    await cognee.remember(
        transcript,
        dataset_name="acme-brain",
        node_set=["source:slack", "channel:launch"],
    )

    doc = actions.execute_tool(
        tool_name="googledrive_export_file",
        tool_input={"file_id": "<file_id>", "mime_type": "text/plain"},
        connection_name="googledrive",
        identifier=identifier,
    )
    await cognee.remember(
        str(doc.data),                 # exported Doc text — inspect .data for the exact shape
        dataset_name="acme-brain",
        node_set=["source:googledrive", "doc:launch-plan"],
    )

    # 2. Recall — auto-routes to the best search strategy
    results = await cognee.recall(
        "What did we decide about the launch date, and who owns the announcement?",
        datasets=["acme-brain"],
    )
    for r in results:
        print(r.source, "→", r.text)

    # 3. Session memory for the agent's scratchpad (fast tier, bridged to the graph)
    await cognee.remember("Alice asked about the launch date", session_id="alice-chat-1")
    await cognee.recall("what did Alice ask?", session_id="alice-chat-1")


asyncio.run(main())
```

Other things worth knowing:

- `remember()` accepts text, file paths and URLs; a folder or a GitHub repo URL
  becomes a code graph (`content_type="code"` for repos pulled from GitHub).
- `recall()` picks a search strategy for you. Pin one with
  `query_type=SearchType.GRAPH_COMPLETION` (graph-heavy questions),
  `SearchType.CHUNKS` (raw passages, no LLM) or `SearchType.TEMPORAL`
  ("what happened in September?").
- `cognee-cli -ui` starts the local server + graph explorer at
  <http://localhost:3000>. Open it during the demo — the graph is the pitch.
- `improve(dataset="acme-brain")` runs the enrichment stages; `forget(...)`
  removes a document, a dataset, or everything.
- Prefer a managed instance? `await cognee.serve(url=..., api_key=...)` points
  every call at Cognee Cloud. Ask at the Cognee table for a key.

A complete starter — authorize, pull Slack + Drive, remember per user, recall
across both — is [`examples/scalekit_to_cognee.py`](../examples/scalekit_to_cognee.py).

### 5. Access — one Scalekit identifier, one Cognee user

The brief asks you to *"show how secure user-level access and authorization
shape the experience."* Scalekit gives you the first half (what a user may
pull); Cognee gives you the second (what a user may recall). Line them up: the
Scalekit `identifier` **is** the Cognee user's email.

```python
import os
os.environ["ENABLE_BACKEND_ACCESS_CONTROL"] = "true"   # set BEFORE the first cognee call

import cognee
from cognee.modules.users.methods import create_user, get_user_by_email
from cognee.modules.data.methods import get_authorized_existing_datasets
from cognee.modules.users.permissions.methods import authorized_give_permission_on_datasets


async def get_or_create_user(email: str):
    return await get_user_by_email(email) or await create_user(email, "hackathon-pw")


alice = await get_or_create_user("alice@acme.com")
bob = await get_or_create_user("bob@acme.com")

# Each user's pulls land in a dataset only they can read
await cognee.remember(alice_slack_text, dataset_name="alice-brain", user=alice)
await cognee.remember(bob_drive_text, dataset_name="bob-brain", user=bob)

# Bob's readable set is only his own brain — Alice's is invisible to him.
# (Passing datasets=["alice-brain"] with user=bob raises DatasetNotFoundError:
#  names resolve only among datasets the user owns.)
readable = await get_authorized_existing_datasets(None, "read", bob)
print([d.name for d in readable])                                   # -> ['bob-brain']

# ... until Alice shares it
(ds,) = await get_authorized_existing_datasets(["alice-brain"], "share", alice)
await authorized_give_permission_on_datasets(bob.id, [ds.id], "read", alice.id)

# Shared datasets are reached by id, not by name
readable = await get_authorized_existing_datasets(None, "read", bob)
print([d.name for d in readable])                                   # -> ['bob-brain', 'alice-brain']
print(await cognee.recall("launch date?", dataset_ids=[d.id for d in readable], user=bob))
```

With access control on, every user+dataset gets its own isolated graph and
vector store (default Ladybug + LanceDB). Two worked examples: Scalekit's
[`cognee-scalekit-example`](https://github.com/scalekit-developers/cognee-scalekit-example)
(Scalekit login decides the user, one Cognee dataset per customer, Slack
post-back as that user) and the previous hackathon's
[`multiuser.py`](https://github.com/topoteretes/cognee-hackathons/tree/main/cognee-gtm-brain-hackathon-2026-06-26/src/gtm_brain/multiuser.py)
(two users, isolation, then a grant).

### 6. Respan — gateway credits, traces, evals

Respan is providing **LLM credits on its gateway** for the event (step 2):
every call your agents and Cognee make through `https://api.respan.ai/api`
runs on those credits and is logged with model, tokens, cost and latency. The
same platform traces an agent run (LLM calls, tool runs, retrievals) as one
span tree, and scores runs with evaluators (LLM judge, deterministic Python
check, or human review) over a testset. Instrument with the `respan-ai`
Python SDK (`Respan()` once at startup, a decorator on the function that
handles a request), build a testset from your scenario questions, and run the
same evaluator before and after you change the brain.

The Respan team walks through setup and hands out keys at kickoff. Docs:
[gateway](https://www.respan.ai/ai-gateway) ·
[tracing](https://www.respan.ai/ai-tracing) ·
[evals](https://www.respan.ai/ai-evals) ·
[SDK on GitHub](https://github.com/respanai/respan).

## Judging

Full rubric in [`challenge/COMPANY_BRAIN.md`](../challenge/COMPANY_BRAIN.md).
In short (100 points):

```text
30 - Company Brain quality      cross-source answers, real team workflow, actions taken
20 - Secure access story        Scalekit per-user connections ↔ Cognee per-user memory, demonstrated
20 - Evaluation                 scenario set, independent scorer, traced runs, before/after
15 - Memory design              what goes in the graph, how it's tagged, how it improves
10 - Reproducibility            we can run it from the README with our own keys
 5 - Demo                       3 minutes, live, shows all three layers
```

## Submission

Each team submits:

- a short writeup of the Company Brain and the team workflow it solves
- the implementation: Scalekit pull, Cognee ingestion, the agent(s), the eval
- the eval results: scenario set, before/after scores, link to the traces
- the access story: which users, which connections, what each can see
- a 3-minute demo

Use [`templates/SUBMISSION.md`](../templates/SUBMISSION.md) — copy it into your
team repo (or the PR description) and fill it in. Submit by opening a PR to
this repo that adds `submissions/<team-name>/SUBMISSION.md` under this folder,
or hand the link to an organizer before the deadline.

## Ideas to Build

- **Pre-meeting brief** — for each calendar event in the next 24 h, pull the
  attendees' recent Slack threads, shared Drive docs and open GitHub issues,
  remember them, and have the agent write the brief and post it to the
  owner's DM. Eval: does the brief mention the open decision from the last
  thread?
- **Who knows about X** — an expert finder over Slack + GitHub + Drive
  authorship. Eval: top-1 person for 10 held-out questions.
- **Decision archaeology** — "why did we pick Postgres?" answered from the RFC
  doc, the thread where it was argued, and the PR that did it, with citations.
  Eval: every answer cites at least two sources.
- **Onboarding buddy** — a new hire's brain only sees what their role is
  granted; the agent explains the team's systems from that view and files
  "I couldn't find X" gaps as Notion/Linear tasks.
- **Support triage** — Gmail + HubSpot + GitHub: route an incoming customer
  email to the right owner with the account's history attached. Eval: correct
  owner, correct linked issue.
- **Docs that fix themselves** — pull the repo and the Slack `#support`
  channel; when the brain sees the same question answered three times in
  Slack and nowhere in the docs, the agent drafts the doc change and pushes
  it as a PR through Scalekit under the answerer's account. Eval: PR touches
  the right file, cites the thread.

## Resources

- Scalekit: [`cognee-scalekit-example`](https://github.com/scalekit-developers/cognee-scalekit-example) (reference app: Scalekit login + Slack, Cognee memory per user) ·
  [AgentKit overview](https://docs.scalekit.com/agentkit/overview/) ·
  [Python SDK](https://docs.scalekit.com/agentkit/sdks/python/) ·
  [connectors](https://docs.scalekit.com/agentkit/connectors/) ·
  [meeting-prep agent walkthrough](https://www.scalekit.com/blog/meeting-prep-ai-agent-development)
- Cognee: [docs](https://docs.cognee.ai/) ·
  [repo](https://github.com/topoteretes/cognee) ·
  [company brain cookbooks](https://github.com/topoteretes/cognee/tree/main/examples/cookbooks/company_brain) ·
  [Discord](https://discord.gg/NQPKmU5CCg)
- Respan: [gateway](https://www.respan.ai/ai-gateway) ·
  [tracing](https://www.respan.ai/ai-tracing) ·
  [evals](https://www.respan.ai/ai-evals) ·
  [SDK](https://github.com/respanai/respan)
- Previous company-brain hackathons in this repo:
  [`cognee-companybrain-hackathon-2026-06-16`](https://github.com/topoteretes/cognee-hackathons/tree/main/cognee-companybrain-hackathon-2026-06-16),
  [`cognee-cloud-hackathon-2026-06-19`](https://github.com/topoteretes/cognee-hackathons/tree/main/cognee-cloud-hackathon-2026-06-19),
  [`cognee-gtm-brain-hackathon-2026-06-26`](https://github.com/topoteretes/cognee-hackathons/tree/main/cognee-gtm-brain-hackathon-2026-06-26)
- Event page: [Partiful](https://partiful.com/e/0x6c9gSKGDZi9mYMESyl)
- Capture friction for the Cognee team as you go:
  [`agent-skills/cognee-hackathon-feedback`](https://github.com/topoteretes/cognee-hackathons/tree/main/agent-skills/cognee-hackathon-feedback)
