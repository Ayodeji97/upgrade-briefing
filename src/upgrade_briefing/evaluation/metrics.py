"""Retrieval metrics (learning guide Stage 9). Pure functions, no DB or model needed.

The golden set labels *releases* (entry_ids), but search returns *chunks*. Several chunks can come
from one release, so we first collapse the ranked chunk list into a ranked list of unique entry_ids.
"""

from __future__ import annotations


def ranked_entries(results: list[dict]) -> list[str]:
    """Chunk results (best first) -> unique entry_ids in first-seen order."""
    seen: list[str] = []
    for r in results:
        if r["entry_id"] not in seen:
            seen.append(r["entry_id"])
    return seen


def recall_at_k(entries: list[str], relevant: list[str], k: int) -> float:
    """Share of the relevant releases that appear in the top k."""
    return len(set(entries[:k]) & set(relevant)) / len(relevant)


def reciprocal_rank(entries: list[str], relevant: list[str]) -> float:
    """1 / rank of the first relevant release (0 if none was found). MRR = mean of this."""
    for rank, entry_id in enumerate(entries, start=1):
        if entry_id in relevant:
            return 1.0 / rank
    return 0.0


def wrong_version_rate(results: list[dict], k: int, library: str, after_key=None, upto_key=None) -> float:
    """Share of the top-k releases from the wrong library or outside the asked version range."""
    top: dict[str, dict] = {}
    for r in results:
        top.setdefault(r["entry_id"], r)
        if len(top) == k:
            break
    if not top:
        return 0.0

    def wrong(r: dict) -> bool:
        if r["library"] != library:
            return True
        if after_key is not None and r["version_key"] <= after_key:
            return True
        return upto_key is not None and r["version_key"] > upto_key

    return sum(wrong(r) for r in top.values()) / len(top)
