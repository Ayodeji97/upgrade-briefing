"""Step 5c — label every bullet once, at ingestion time, and save to data/labels.jsonl.

Run: uv run briefing-classify   (~120 Groq calls the first time; cached afterwards)

Why offline (at ingestion) and not at query time: each bullet is labelled once instead of on
every question, answers are instant, and the label becomes metadata we can filter on
("only breaking changes between 2.6.1 and 2.7.0"). The eval (briefing-eval-classify) picked the
LLM over rules: test accuracy 1.00 vs 0.74, breaking recall 1.00 vs 0.58.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from upgrade_briefing.classify import llm
from upgrade_briefing.classify.items import iter_items

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LABELS_OUT = PROJECT_ROOT / "data" / "labels.jsonl"


def load_labels(path: Path = LABELS_OUT) -> dict[str, str]:
    """item_id -> label ({} if briefing-classify has not been run)."""
    if not path.exists():
        return {}
    return {d["item_id"]: d["label"] for d in map(json.loads, path.open())}


def main() -> None:
    items = iter_items()
    labels = llm.classify_items(items)
    with LABELS_OUT.open("w") as f:
        for it in items:
            f.write(json.dumps({"item_id": it.item_id, "label": labels[it.item_id]}) + "\n")
    print(f"{len(items)} bullets -> {LABELS_OUT.name}: {dict(Counter(labels.values()).most_common())}")


if __name__ == "__main__":
    main()
