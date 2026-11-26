"""Step 5b — LLM classifier (Groq), with a per-bullet disk cache.

Design choices (learning guide, Stage 7 + the course's lesson on token cost):
- temperature=0 and JSON output, so the same input gives the same label.
- Batches of BATCH bullets per call: the label definitions (the long part of the prompt)
  are sent once per batch instead of once per bullet. ~2,300 bullets -> ~120 calls.
- Cache per bullet, keyed on model + prompt version + bullet. Changing the prompt bumps
  PROMPT_VERSION, which invalidates the cache. Re-running the eval costs nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from upgrade_briefing.classify.items import LABELS, Item

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CACHE_DIR = PROJECT_ROOT / "data" / "cache" / "classify"
BATCH = 20
PROMPT_VERSION = "v2"  # v2: sharper breaking-vs-fix boundary for behaviour changes (dev errors)

SYSTEM = """You label AndroidX release-note bullets for an upgrade briefing.
Give each bullet exactly one label. If two fit, pick the one that comes first in this list:

breaking   - after upgrading, code or the build may stop working or the app may behave differently:
             removed or renamed API, changed signature or type, new minSdk/Kotlin/AGP requirement,
             a changed default the app could notice, a new annotation that makes lint fail
             (e.g. @MainThread). Changes between two alphas count too.
deprecated - an API is newly marked deprecated (it still works).
new        - a new API, feature, artifact, platform or lint check you can start using.
fix        - a bug fix or performance improvement, or a minor behaviour change that needs no action.
other      - dependency version bumps (even when the bump brings in fixes), docs, known issues, internal or @RestrictTo changes,
             notes that change nothing for Android apps, release summaries.

Breaking vs fix for behaviour changes: if correct, working app code could now see a different
result ("now always", "now verify", "now serialized", "now treated as", "now throws"), it is breaking.
It is fix only when the old behaviour was clearly a bug, or a restriction was lifted.

Judge by what the bullet says, not by its section title: a bullet under "Bug Fixes" can be a
deprecation, and one under "Breaking Changes" can just add an API. Mentioning a deprecated API
in a bug fix does not make it a deprecation.

Answer with JSON only: {"labels": {"<number>": "<label>", ...}} with one entry per bullet."""


def _key(model: str, item: Item) -> str:
    raw = f"{model}|{PROMPT_VERSION}|{item.library}|{item.section}|{item.text}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _user_prompt(batch: list[Item]) -> str:
    lines = [
        f"{i}. [{it.library} {it.version} | section: {it.section}] {it.text}"
        for i, it in enumerate(batch, 1)
    ]
    return "Bullets:\n" + "\n".join(lines)


def _call(client, model: str, batch: list[Item], attempts: int = 10) -> dict[str, str]:
    for attempt in range(attempts):
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": _user_prompt(batch)}],
                temperature=0,
                reasoning_effort="none",
                response_format={"type": "json_object"},
            )
            labels = json.loads(r.choices[0].message.content)["labels"]
            return {str(k): str(v).strip().lower() for k, v in labels.items()}
        except Exception as e:  # rate limit (429) or a malformed answer: wait and retry
            # Groq's free tier allows ~8k tokens/minute; a 429 says how long to wait.
            headers = getattr(getattr(e, "response", None), "headers", {}) or {}
            wait = float(headers.get("retry-after") or min(2 ** attempt * 5, 120))
            print(f"  groq error ({type(e).__name__}: {str(e)[:200]}), retry {attempt + 1}/{attempts} in {wait:.0f}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"Groq failed {attempts} times in a row (cached answers are kept; re-run to resume)")


def classify_items(items: list[Item], model: str | None = None) -> dict[str, str]:
    """item_id -> label. Cached bullets cost nothing; the rest go to Groq in batches."""
    load_dotenv(PROJECT_ROOT / ".env")
    model = model or os.environ["GROQ_MODEL"]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    out: dict[str, str] = {}
    todo: list[Item] = []
    for it in items:
        f = CACHE_DIR / f"{_key(model, it)}.json"
        if f.exists():
            out[it.item_id] = json.loads(f.read_text())["label"]
        else:
            todo.append(it)

    if todo:
        from groq import Groq

        client = Groq()
        print(f"LLM: {len(items) - len(todo)} cached, {len(todo)} to classify")
        for start in range(0, len(todo), BATCH):
            batch = todo[start : start + BATCH]
            answer = _call(client, model, batch)
            for i, it in enumerate(batch, 1):
                label = answer.get(str(i), "other")
                if label not in LABELS:  # the model invented a label: don't trust it
                    label = "other"
                out[it.item_id] = label
                (CACHE_DIR / f"{_key(model, it)}.json").write_text(
                    json.dumps({"item_id": it.item_id, "label": label})
                )
    return out
