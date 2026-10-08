"""Score the brain against a scenario file (default sample/scenarios.json). The scorer
is a plain fact check, independent of the agent: an answer scores the share of
`must_mention` facts it contains (case-insensitive), 0 if it contains any
`must_not_mention` fact.

Two modes, so a change can be shown before / after:

    python -m eval.run --mode baseline   # cognee.recall() answers on its own (default graph search)
    python -m eval.run --mode agent      # brain.agent: raw records + cited answer through Respan

    python -m eval.run --mode agent --scenarios my-scenarios.json       # another scenario set

Each run writes eval/results/<label>.json; agent runs are traced in Respan.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from brain.memory import get_user, readable_datasets, setup

import cognee  # noqa: E402

HERE = Path(__file__).resolve().parent


def score(answer: str, sc: dict) -> dict:
    low = answer.lower()
    hits = [f for f in sc.get("must_mention", []) if f.lower() in low]
    leaks = [f for f in sc.get("must_not_mention", []) if f.lower() in low]
    facts = sc.get("must_mention", [])
    s = (len(hits) / len(facts)) if facts else (1.0 if answer.strip() else 0.0)
    if leaks:
        s = 0.0
    return {"score": round(s, 2), "hits": hits, "missing": [f for f in facts if f not in hits],
            "leaks": leaks, "cited": "http" in low}


async def baseline_answer(email: str, question: str) -> str:
    user = await get_user(email)
    ds = await readable_datasets(user)
    results = await cognee.recall(question, dataset_ids=[d.id for d in ds], user=user)
    return "\n".join(getattr(r, "text", None) or str(r) for r in results)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["baseline", "agent"], required=True)
    ap.add_argument("--label", help="results file name (default: the mode)")
    ap.add_argument("--only", help="comma-separated scenario ids")
    ap.add_argument("--scenarios", type=Path, default=HERE.parent / "sample" / "scenarios.json",
                    help="scenario file (default sample/scenarios.json)")
    args = ap.parse_args()

    scenarios = json.loads(args.scenarios.read_text())
    if args.only:
        scenarios = [s for s in scenarios if s["id"] in args.only.split(",")]
    asyncio.run(setup())
    if args.mode == "agent":
        from brain.agent import ask, respan

    rows = []
    for sc in scenarios:
        t0 = time.time()
        try:
            answer = (ask(sc["as_user"], sc["question"]) if args.mode == "agent"
                      else asyncio.run(baseline_answer(sc["as_user"], sc["question"])))
        except Exception as e:
            answer = f"ERROR {type(e).__name__}: {e}"
        r = {"id": sc["id"], "as_user": sc["as_user"], "question": sc["question"],
             **score(answer, sc), "latency_s": round(time.time() - t0, 1), "answer": answer}
        if answer.startswith("ERROR "):  # a crash must never pass a negative (access) scenario
            r.update(score=0.0, cited=False, error=True)
        rows.append(r)
        print(f"{r['score']:.2f}  {'cited' if r['cited'] else '     '}  {sc['id']:20} missing={r['missing']} leaks={r['leaks']}", flush=True)

    mean = sum(r["score"] for r in rows) / len(rows)
    cited = sum(r["cited"] for r in rows) / len(rows)
    label = args.label or args.mode
    out = HERE / "results" / f"{label}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"label": label, "mode": args.mode, "mean": round(mean, 3),
                               "cited_rate": round(cited, 3), "n": len(rows), "rows": rows}, indent=2))
    print(f"\n{label}: mean score {mean:.2f}  ·  cited {cited:.0%}  ·  n={len(rows)}  →  {out.relative_to(HERE.parent)}")
    if args.mode == "agent":
        respan.shutdown()


if __name__ == "__main__":
    main()
