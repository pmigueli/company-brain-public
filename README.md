# Company Brain

A company brain that writes **the standup nobody has to attend** and answers questions **with a source
link on every claim**. It reads each person's Slack, Linear, Notion and Granola through Scalekit,
acting as that person. It remembers what they can see in their own Cognee brain and answers from
whatever the asking user may read. LLM calls, traces and the eval run through Respan.

Built by Team Causa Prima at *Build a Company Brain* (Cognee × Scalekit × Respan), San Francisco,
2026-10-07. The organizers' challenge README is in [`docs/challenge-README.md`](docs/challenge-README.md),
and our submission write-up is [`SUBMISSION.md`](SUBMISSION.md).

This is the public copy of the project: the code plus a synthetic sample company, *Acme Robotics*,
with two users, Alice and Bob. No real company data, scenarios or results are included. Out of the
box, every command runs on the sample.

## What it does

| Command | Output |
|---|---|
| `brain.agent standup --as <email>` | A company-wide standup built from everyone's activity, not just the reader's: exec summary, then Yesterday / Today / Blockers per person, then risks that only show up when you look across sources (two tickets for one bug, a doc that still describes a replaced flow, a decision that affects someone who was not in the room), then opportunities, then an access line. Saved to `out/standup-<date>-<user>.md`. |
| `brain.agent ask --as <email> "<question>"` | An answer that cites every claim with the source link (Slack message, Linear issue, Notion page, Granola note). If the answer may sit in a brain the user cannot read, it says so. |
| `brain.agent grant --from <owner> --to <grantee> --dataset <name>-brain` | The owner shares read access to their brain. The grantee's next answer draws on both brains. `revoke` (same flags) undoes it. |

## How it works

```text
Pull       brain/pull.py      Scalekit execute_tool(..., identifier=<user email>)
           │                  Slack · Linear · Notion · Granola, as each user
           ▼                  -> data/raw/<email>/<source>.jsonl   (sample/raw/ for the synthetic sample)
Remember   brain/split.py     scope + time window, one dataset per user: "<name>-brain"
           brain/ingest.py    "[source · who · when · link] text" records, ~8k-char documents
           │                  cognee.remember(texts, dataset_name, user, node_set=[source:*, channel:*|team:*, owner:*])
           ▼                  ENABLE_BACKEND_ACCESS_CONTROL=true: only the owner can read it
Act        brain/agent.py     cognee.recall(SearchType.CHUNKS) over the user's readable datasets only,
           │                  plus a CHUNKS_LEXICAL keyword lookup for ticket keys in the question
           ▼                  -> one cited gpt-4.1 call through the Respan gateway
                              traced in Respan: workflow -> recall -> answer
Evaluate   eval/run.py        sample/scenarios.json -> fact-check scorer (independent of the agent)
                              --mode baseline (Cognee's default answer) vs --mode agent
```

- **One Scalekit identifier is one Cognee user.** We follow section 5 of the challenge README. The
  user's email is both the Scalekit `identifier` and the Cognee user, and everything pulled as that
  user goes into their own `<name>-brain` dataset. Nobody else can recall it.
- **No shared team dataset. A team view comes from grants.** Cognee permissions are per dataset, and
  each dataset is its own graph. So we keep everything one person can see in one graph, where it
  stays connected across sources. Material two people both see (a shared channel, a shared ticket, a
  meeting they both attended) is extracted into each of their brains. A grant gives another user read
  access to a whole brain, and the agent merges what it recalls from several brains when it answers.
- **Provenance is kept twice.** The `node_set` tags carry source, channel or team, and owner. Every
  record's text header carries source, author, time and link, and the answer has to cite that link.

## Setup

Python 3.13. From the repo root:

```bash
python3.13 -m venv .venv
```

```bash
.venv/bin/pip install "cognee>=1.6.3" scalekit-sdk-python python-dotenv "respan-ai>=4" respan-instrumentation-openai openai
```

```bash
cp .env.example .env
```

Then put your Respan key in `.env` (`LLM_API_KEY`, `EMBEDDING_API_KEY`, `RESPAN_API_KEY`). The code
loads `.env` itself (`brain/memory.py`, `brain/split.py`, `brain/scalekit_client.py`). The `BRAIN_*`
values in `.env.example` already point at the sample.

| Variable | Needed for | Value |
|---|---|---|
| `LLM_PROVIDER`, `LLM_ENDPOINT`, `LLM_API_KEY`, `LLM_MODEL` | ingest (Cognee extraction) | `custom`, `https://api.respan.ai/api`, your Respan key, `openai/gpt-4.1-mini`. `openai/gpt-5-mini` also works but was about 3.4x slower per extraction call. |
| `EMBEDDING_PROVIDER`, `EMBEDDING_ENDPOINT`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` | ingest, recall | `custom`, `https://api.respan.ai/api`, the same Respan key, `openai/text-embedding-3-large`, `3072` |
| `RESPAN_API_KEY` | `brain.agent` (all commands), `eval.run --mode agent` | your Respan key: the answer model and tracing both use it |
| `BRAIN_NOW` | the sample | `2026-10-08T00:00:00+00:00`. Pins "today" so the dated sample records fall inside the 3-day and 14-day windows. Remove it for live data. |
| `ENABLE_BACKEND_ACCESS_CONTROL` | everything | `true` (`brain/memory.py` also forces it before Cognee is imported) |
| `SCALEKIT_ENVIRONMENT_URL`, `SCALEKIT_CLIENT_ID`, `SCALEKIT_CLIENT_SECRET` | live pulls only (run B) | Scalekit dashboard → Developers → API Credentials |

Optional overrides (all have defaults in the code):

| Variable | Default | Effect |
|---|---|---|
| `BRAIN_RAW_DIR` | `sample/raw` | where the raw JSONL is read from. Live pulls write to `data/raw` and refuse to write into `sample/`. |
| `BRAIN_USERS` | `alice=alice@example.com,bob=bob@example.com` | comma-separated `name=email` pairs. Each user gets a dataset `<name>-brain`. |
| `BRAIN_COMPANY` | `the company` | company name used in the agent's prompts (`Acme Robotics` in `.env.example`) |
| `BRAIN_LOCAL_PASSWORD` | `change-me-local-only` | password Cognee stores for each local user; only used to log in to the local Cognee UI |
| `BRAIN_LINEAR_TEAMS` | `Product & Engineering,Operations` | Linear teams kept in scope |
| `BRAIN_PINNED_TICKETS`, `BRAIN_PINNED_TEXT` | none | Linear keys (comma list) and a text regex for older items to keep despite the time window |
| `BRAIN_EXCLUDE_CHANNELS` | none | regex of Slack channel names the pull skips |
| `ANSWER_MODEL` | `gpt-4.1` | model for the agent's answer call |
| `RESPAN_BASE_URL` | `https://api.respan.ai/api` | gateway URL for the agent's OpenAI client |
| `SCALEKIT_SLACK_CONNECTION`, `SCALEKIT_LINEAR_CONNECTION`, `SCALEKIT_NOTION_CONNECTION`, `SCALEKIT_GRANOLA_CONNECTION` | `slack`, `linear`, `notion`, `granola` | your Scalekit connection names |
| `SLACK_FETCH_REPLIES` | `0` | `1` also pulls thread replies. That costs one call per thread and hits Slack rate limits quickly. |

## Run A — the synthetic sample (no Scalekit accounts needed)

`sample/raw/` holds synthetic data for *Acme Robotics*: two users, Alice and Bob, each with Slack,
Linear, Notion and Granola files plus a `slack_channels.json`, in exactly the record shapes
`brain/pull.py` writes. `sample/scenarios.json` holds 8 scenarios over that data, the access pair
included. You need only the `LLM_*`, `EMBEDDING_*` and `RESPAN_API_KEY` variables, plus `BRAIN_NOW`.

If you did not copy `.env.example`, set the date for this shell session (everything else defaults to
the sample):

```bash
export BRAIN_NOW=2026-10-08T00:00:00+00:00
```

Check what will be remembered. This needs no Cognee and no LLM:

```bash
.venv/bin/python -m brain.split
```

Remember: build `alice-brain` and `bob-brain` (Cognee extraction through the Respan gateway):

```bash
.venv/bin/python -m brain.ingest
```

Evaluate. Run these before the grant below, because the access scenario expects Bob not to see
Alice's brain yet:

```bash
.venv/bin/python -m eval.run --mode baseline --label sample-baseline
```

```bash
.venv/bin/python -m eval.run --mode agent --label sample-agent
```

Each run prints one line per scenario (score, whether it cited a source, missing facts, leaks), then
the mean. It writes `eval/results/<label>.json`.

Access story: ask the same question as each user, grant, then ask again. The answer exists only in
Alice's private Granola call.

```bash
.venv/bin/python -m brain.agent ask --as alice@example.com "What is the codename of the second warehouse site, and which city is it in?"
```

```bash
.venv/bin/python -m brain.agent ask --as bob@example.com "What is the codename of the second warehouse site, and which city is it in?"
```

```bash
.venv/bin/python -m brain.agent grant --from alice@example.com --to bob@example.com --dataset alice-brain
```

```bash
.venv/bin/python -m brain.agent ask --as bob@example.com "What is the codename of the second warehouse site, and which city is it in?"
```

Before the grant, Bob's answer lacks Alice's fact and says that some context may sit in datasets he
cannot read. After the grant, `bob` reads `['alice-brain', 'bob-brain']` and gets Alice's answer, with
the same citation. To rehearse again, undo the grant:

```bash
.venv/bin/python -m brain.agent revoke --from alice@example.com --to bob@example.com --dataset alice-brain
```

Isolation check: every user addressing another user's brain by name must be refused unless it was
granted. Exits 1 on a leak:

```bash
.venv/bin/python -m brain.verify
```

The company-wide standup, as either user:

```bash
.venv/bin/python -m brain.agent standup --as bob@example.com
```

Grants persist. To start over, delete `.cognee_system/` and `.cognee_data/` and ingest again.

## Run B — live, with your own Scalekit connections

1. In Scalekit, open AgentKit → Connections and create Slack, Linear, Notion and Granola connections.
   Set the `SCALEKIT_*_CONNECTION` variables if your names differ from the defaults.
2. Point the brain at your own users and at `data/raw` (git-ignored), and remove `BRAIN_NOW`. In
   `.env`, or for this shell:

```bash
export BRAIN_RAW_DIR=data/raw BRAIN_USERS="ana=ana@yourco.com,ben=ben@yourco.com" BRAIN_COMPANY="Your Co"
```

```bash
unset BRAIN_NOW
```

3. Each user authorizes each connection once. This prints one authorization link per connection:

```bash
.venv/bin/python -c "from brain.scalekit_client import actions, CONNECTIONS; [print(s, actions().get_authorization_link(connection_name=c, identifier='ana@yourco.com').link) for s, c in CONNECTIONS.items()]"
```

Check that every connection shows `ACTIVE`:

```bash
.venv/bin/python -c "from brain.scalekit_client import auth_status; print(auth_status('ana@yourco.com'))"
```

4. Pull as each user. This writes `data/raw/<email>/<source>.jsonl`:

```bash
.venv/bin/python -m brain.pull --user ana@yourco.com --days 30
```

```bash
.venv/bin/python -m brain.pull --user ben@yourco.com --days 30
```

`--sources slack,linear` limits a pull to some sources. Slack takes public internal channels only and
skips channels shared with other organisations.

5. Check what will be remembered:

```bash
.venv/bin/python -m brain.split
```

The content scope lives at the top of `brain/split.py`: `LINEAR_TEAMS` (`BRAIN_LINEAR_TEAMS`),
`NOTION_EXCLUDE`, and the optional pins (`BRAIN_PINNED_TICKETS`, `BRAIN_PINNED_TEXT`). Activity sources
keep the last `--days` days (ingest default 3). Notion keeps pages edited in the last 14 days.

6. Remember, then use:

```bash
.venv/bin/python -m brain.ingest
```

`--datasets ana-brain` and `--sources granola` limit a run. `--days 7` widens the activity window.

```bash
.venv/bin/python -m brain.agent standup --as ana@yourco.com
```

```bash
.venv/bin/python -m brain.agent ask --as ben@yourco.com "Is anyone working on the same bug twice?"
```

```bash
.venv/bin/python -m brain.agent grant --from ana@yourco.com --to ben@yourco.com --dataset ana-brain
```

To score your own workspace, write a scenario file in the same shape as `sample/scenarios.json` and
pass it with `--scenarios`. Keep it out of the repo if it describes real data (`eval/scenarios.json`
is git-ignored for that reason).

## Look inside

The graph explorer (local Cognee server and UI at <http://localhost:3000>):

```bash
.venv/bin/cognee-cli -ui
```

Log in as one of the users (for the sample, `alice@example.com` or `bob@example.com`) with
`BRAIN_LOCAL_PASSWORD`. The login form prefills `default_user@example.com`; overwrite it. The UI holds
a lock on the graph files it has opened, so stop it before running the CLI agent on the same brain
(otherwise the agent fails with `Could not set lock on file`).

Respan traces: each `ask` or `standup` is one workflow (`ask_brain` or `standup`) with `recall` and
`answer` spans. Every LLM and embedding call through the gateway is logged with model, tokens, cost
and latency. Browse them at <https://platform.respan.ai>, or from the terminal:

```bash
export RESPAN_API_KEY=<your-respan-key>
```

```bash
npx -y @respan/cli traces list
```

## The eval

`eval/run.py` loops over a scenario file (default `sample/scenarios.json`). A scenario has these
fields: `question`, `as_user`, `must_mention`, `must_not_mention`, `expected_sources`. The scorer is a
plain Python fact check and does not depend on the agent. An answer scores the share of
`must_mention` facts it contains (case insensitive). It scores 0 if it contains any
`must_not_mention` fact, which is how the access scenarios catch a leak. The scorer also records
whether the answer cites a link, and the latency.

- `--mode baseline`: `cognee.recall()` with its default search and answer, over the same readable
  datasets.
- `--mode agent`: `brain.agent.ask`. It recalls the raw provenance records, then makes one cited
  answer call through Respan. These runs are traced.
- `--only id1,id2` runs a subset of scenarios. `--label` names the results file. `--scenarios` picks
  another scenario file.

Results:

- Real company run, per-user brains (numbers only; the data and its scenarios stay private):
  baseline mean 0.64 with 0% cited, agent mean 1.00 with 100% cited, n = 11.
- Synthetic sample (`sample/scenarios.json`): agent mean 1.00, n = 8.

## Known rough edges

- Run `brain.memory.setup()` before any user lookup on a fresh install. Otherwise Cognee fails with
  `no such table: principals`. Every entry point already does this.
- `brain/memory.py` creates `.cognee_system/databases` up front. SQLite fails with `unable to open
  database file` when that folder is missing.
- You may see a Hugging Face tokenizer 401 warning for `openai/text-embedding-3-large`. It is noise:
  the embeddings still go through the gateway.
- The Cognee database is file-based, so don't run two ingests or evals at the same time, and stop the
  Cognee UI before using the CLI on the same brain.

## Data posture

This repository contains only code and synthetic data. When you run it on your own workspace, real
data stays on your machine: `data/`, `out/`, `eval/results/`, `eval/scenarios.json`,
`.cognee_system/`, `.cognee_data/` and `.env` are git-ignored, anything under `sample/raw/` other
than the two sample users is git-ignored, and `brain.pull` refuses to write into `sample/`. Scalekit
holds every OAuth token, and none ever reaches this code or `.env`. Every pull runs as a named user's
identifier, never through a shared bot token.
