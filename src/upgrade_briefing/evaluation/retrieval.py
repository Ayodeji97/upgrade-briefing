"""Step 4 — the retrieval ablation: run every search configuration over eval/golden.jsonl.

Run:  uv run briefing-eval-retrieval

Honest-evaluation rule (CLAUDE.md): never tune on the questions you report. The golden set is
split in two: odd ids (q01, q03 ...) = DEV, used to pick settings such as hybrid `alpha`;
even ids = TEST, reported. Positive questions are scored with Recall@5/@10 and MRR over releases.
Negative questions (empty `relevant`) can't have recall, so we report what the system sees for
them instead: whether filtering leaves nothing, and the reranker's top score.

Writes eval/results/retrieval.md (the table) and eval/results/retrieval.json (every ranking).
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from upgrade_briefing.evaluation.metrics import (
    ranked_entries,
    recall_at_k,
    reciprocal_rank,
    wrong_version_rate,
)
from upgrade_briefing.retrieve.rerank import rerank
from upgrade_briefing.retrieve.search import search
from upgrade_briefing.store import connect
from upgrade_briefing.versions import parse_version

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GOLDEN = PROJECT_ROOT / "eval" / "golden.jsonl"
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"

CANDIDATES = 50  # chunks fetched per query (enough to fill 10 unique releases)
ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0]


def load_golden() -> list[dict]:
    with GOLDEN.open() as f:
        return [json.loads(line) for line in f]


def split(q: dict) -> str:
    return "dev" if int(q["id"][1:]) % 2 == 1 else "test"


def question_filters(q: dict) -> dict:
    """What the real app will know from libs.versions.toml: the library and the version range."""
    filters = {"library": q["library"]}
    if q.get("from"):
        filters["after_key"] = parse_version(q["from"]).key
    if q.get("to"):
        filters["upto_key"] = parse_version(q["to"]).key
    return filters


def configs(best_alpha: float | None = None) -> list[dict]:
    base = [
        {"name": "BM25 (raw text)", "method": "bm25", "field": "text"},
        {"name": "BM25 (camelCase split)", "method": "bm25", "field": "text_split"},
        {"name": "Dense, fixed 200-word chunks", "method": "dense", "chunker": "fixed"},
        {"name": "Dense, no query prefix", "method": "dense", "prefix": False},
        {"name": "Dense", "method": "dense"},
        {"name": "Hybrid, our RRF", "method": "rrf"},
    ]
    sweep = [{"name": f"Hybrid, Weaviate alpha={a}", "method": "hybrid", "alpha": a} for a in ALPHAS]
    if best_alpha is None:
        return base + sweep
    tuned = {"method": "hybrid", "alpha": best_alpha}
    return [
        {"name": "Dense + library/version filter", "method": "dense", "filter": True},
        {"name": "Hybrid, our RRF + filter", "method": "rrf", "filter": True},
        {"name": f"Hybrid alpha={best_alpha} + filter", **tuned, "filter": True},
        {"name": f"Hybrid alpha={best_alpha} + filter + rerank", **tuned, "filter": True, "rerank": True},
    ]


def run_config(client, cfg: dict, golden: list[dict]) -> dict:
    kwargs = {k: v for k, v in cfg.items() if k in ("field", "chunker", "prefix", "alpha")}
    rows, latencies = [], []
    for q in golden:
        filters = question_filters(q) if cfg.get("filter") else {}
        t0 = time.perf_counter()
        results = search(client, q["question"], cfg["method"], k=CANDIDATES, **kwargs, **filters)
        if cfg.get("rerank"):
            results = rerank(q["question"], results, k=CANDIDATES)
        latencies.append(time.perf_counter() - t0)

        entries = ranked_entries(results)
        row = {"id": q["id"], "type": q["type"], "split": split(q), "top10": entries[:10]}
        if q["relevant"]:
            row |= {
                "r5": recall_at_k(entries, q["relevant"], 5),
                "r10": recall_at_k(entries, q["relevant"], 10),
                "rr": reciprocal_rank(entries, q["relevant"]),
                "wrong10": wrong_version_rate(results, 10, **question_filters(q)),
            }
        else:
            row |= {
                "empty": not results,
                "top_score": results[0].get("rerank_score", results[0]["score"]) if results else None,
            }
        rows.append(row)
    return {"name": cfg["name"], "rows": rows, "p95_s": sorted(latencies)[int(0.95 * len(latencies))]}


def summarise(rows: list[dict], which: str | None = None) -> dict:
    pos = [r for r in rows if "r5" in r and (which is None or r["split"] == which)]
    mean = lambda key: statistics.mean(r[key] for r in pos)  # noqa: E731
    return {"r5": mean("r5"), "r10": mean("r10"), "mrr": mean("rr"), "wrong10": mean("wrong10"), "n": len(pos)}


def table(runs: list[dict]) -> str:
    lines = [
        "| Config | Recall@5 dev | Recall@5 test | Recall@10 all | MRR all | Wrong-version@10 | p95 s |",
        "|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        d, t, a = (summarise(run["rows"], w) for w in ("dev", "test", None))
        lines.append(
            f"| {run['name']} | {d['r5']:.2f} | {t['r5']:.2f} | {a['r10']:.2f} | {a['mrr']:.2f} "
            f"| {a['wrong10']:.0%} | {run['p95_s']:.2f} |"
        )
    return "\n".join(lines)


def negatives_table(runs: list[dict]) -> str:
    negs = [r["id"] for r in runs[0]["rows"] if "empty" in r]
    lines = ["| Config | " + " | ".join(negs) + " |", "|---|" + "---|" * len(negs)]
    for run in runs:
        cells = []
        for r in run["rows"]:
            if "empty" in r:
                cells.append("empty" if r["empty"] else f"{r['top_score']:.2f}")
        lines.append(f"| {run['name']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    golden = load_golden()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as client:
        runs = [run_config(client, cfg, golden) for cfg in configs()]
        # Pick alpha on DEV only.
        sweep = [r for r in runs if "alpha=" in r["name"]]
        best = max(sweep, key=lambda r: (summarise(r["rows"], "dev")["r5"], summarise(r["rows"], "dev")["mrr"]))
        best_alpha = float(best["name"].split("alpha=")[1])
        print(f"best alpha on dev: {best_alpha}")
        runs += [run_config(client, cfg, golden) for cfg in configs(best_alpha)]

    n_dev, n_test = (summarise(runs[0]["rows"], w)["n"] for w in ("dev", "test"))
    report = (
        f"# Retrieval ablation\n\n{len(golden)} golden questions: {n_dev} dev + {n_test} test positives, "
        f"{len(golden) - n_dev - n_test} negatives. Metrics are over releases (entry_ids). "
        f"alpha={best_alpha} was chosen on dev only.\n\n{table(runs)}\n\n"
        "## Negative questions\n\n'empty' = the filter left nothing to retrieve (correct refusal for free). "
        "Otherwise: top score (rerank logit for the rerank config, search score for others).\n\n"
        f"{negatives_table(runs)}\n"
    )
    (RESULTS_DIR / "retrieval.md").write_text(report)
    (RESULTS_DIR / "retrieval.json").write_text(json.dumps(runs, indent=1))
    print(report)


if __name__ == "__main__":
    main()
