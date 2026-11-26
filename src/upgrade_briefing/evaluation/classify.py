"""Step 5 eval — how well does each classifier match the hand labels in eval/classify_labels.jsonl?

Run: uv run briefing-eval-classify   ->  eval/results/classify.md + .json

Classifiers compared (learning guide, Stage 7 experiment):
  section  — label from the section title only (the "free signal")
  rules    — keywords first, then the section title
  llm      — Groq, label definitions in the prompt
  hybrid   — rules when a keyword fired, the LLM for the rest (fewer LLM calls)

Dev = odd ids (used to write the rules and the prompt), test = even ids (reported, not tuned on).
The sample over-represents rare labels on purpose, so accuracy here is NOT the accuracy over
all 2,347 bullets; per-label recall is the more useful number.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from upgrade_briefing.classify import llm, rules
from upgrade_briefing.classify.items import LABELS, Item

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LABELS_FILE = PROJECT_ROOT / "eval" / "classify_labels.jsonl"
OUT_DIR = PROJECT_ROOT / "eval" / "results"


def load_labelled() -> list[dict]:
    return [json.loads(line) for line in LABELS_FILE.open()]


def to_item(row: dict) -> Item:
    return Item(row["item_id"], row["entry_id"], row["library"], row["version"], row["section"], row["text"])


def per_label(gold: list[str], pred: list[str]) -> dict[str, dict]:
    out = {}
    for lab in LABELS:
        tp = sum(g == p == lab for g, p in zip(gold, pred))
        n_pred = sum(p == lab for p in pred)
        n_gold = sum(g == lab for g in gold)
        prec = tp / n_pred if n_pred else 0.0
        rec = tp / n_gold if n_gold else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        out[lab] = {"precision": prec, "recall": rec, "f1": f1, "support": n_gold}
    return out


def score(gold: list[str], pred: list[str]) -> dict:
    pl = per_label(gold, pred)
    return {
        "accuracy": sum(g == p for g, p in zip(gold, pred)) / len(gold),
        # average over labels that occur in this split (a label with no examples has no F1)
        "macro_f1": sum(v["f1"] for v in pl.values() if v["support"]) / sum(1 for v in pl.values() if v["support"]),
        "per_label": pl,
    }


def predict_all(rows: list[dict]) -> dict[str, list[str]]:
    items = [to_item(r) for r in rows]
    llm_labels = llm.classify_items(items)
    rule_out = [rules.classify(r["text"], r["section"]) for r in rows]
    return {
        "section": [rules.classify("", r["section"])[0] for r in rows],
        "rules": [lab for lab, _ in rule_out],
        "llm": [llm_labels[it.item_id] for it in items],
        "hybrid": [lab if conf else llm_labels[it.item_id] for (lab, conf), it in zip(rule_out, items)],
        "_llm_share": [not conf for _, conf in rule_out],
    }


def main() -> None:
    rows = load_labelled()
    preds = predict_all(rows)
    splits = {
        "dev": [i for i, r in enumerate(rows) if int(r["id"][1:]) % 2 == 1],
        "test": [i for i, r in enumerate(rows) if int(r["id"][1:]) % 2 == 0],
    }
    methods = ["section", "rules", "llm", "hybrid"]
    results = {m: {s: score([rows[i]["label"] for i in idx], [preds[m][i] for i in idx])
                   for s, idx in splits.items()} for m in methods}
    llm_share = sum(preds["_llm_share"]) / len(rows)

    errors = {m: [{"id": r["id"], "gold": r["label"], "pred": preds[m][i], "section": r["section"],
                   "text": r["text"][:160]}
                  for i, r in enumerate(rows) if preds[m][i] != r["label"]] for m in methods}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "classify.json").write_text(json.dumps(
        {"results": results, "hybrid_llm_share": llm_share, "errors": errors}, indent=2))

    gold_counts = Counter(r["label"] for r in rows)
    lines = [
        "# Step 5: classification results",
        "",
        f"{len(rows)} hand-labelled bullets ({dict(gold_counts)}). Dev = odd ids, test = even ids.",
        "The sample over-represents rare labels, so accuracy is not the corpus-wide accuracy.",
        "",
        "| Method | Acc dev | Acc test | Macro-F1 test | Breaking recall test | Breaking precision test | Deprecated recall test |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in methods:
        d, t = results[m]["dev"], results[m]["test"]
        b, dp = t["per_label"]["breaking"], t["per_label"]["deprecated"]
        lines.append(f"| {m} | {d['accuracy']:.2f} | {t['accuracy']:.2f} | {t['macro_f1']:.2f} | "
                     f"{b['recall']:.2f} | {b['precision']:.2f} | {dp['recall']:.2f} |")
    lines += ["", f"Hybrid sends {llm_share:.0%} of bullets to the LLM (the rest are decided by a keyword rule).", ""]
    for m in ("rules", "llm", "hybrid"):
        lines += [f"## Errors: {m} ({len(errors[m])})", "", "| id | gold | pred | section | text |", "|---|---|---|---|---|"]
        lines += [f"| {e['id']} | {e['gold']} | {e['pred']} | {e['section']} | {e['text'].replace('|', '/')} |"
                  for e in errors[m]]
        lines.append("")
    (OUT_DIR / "classify.md").write_text("\n".join(lines))
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main()
