"""Step 5 — the unit we classify: one release-note bullet ("item").

Why bullets and not chunks? A section chunk holds up to 5 bullets, and an "API Changes" chunk
often mixes a new API, a deprecation and a removal. One label per chunk would blur that.
So we label each bullet, and a chunk later gets the *set* of its bullets' labels.

Labels (one per bullet; when a bullet fits two, the first in this list wins, because
that is what an upgrade briefing must not miss):
  breaking   — your code or build may stop working or behave differently after upgrading:
               removed/renamed API, changed signature, new minSdk/Kotlin/AGP requirement,
               a default that changed. Minor bug-fix-like behaviour changes are NOT breaking.
  deprecated — still works, but marked deprecated (often "in favor of" a replacement).
  new        — a new API, feature or artifact you can start using.
  fix        — a bug fix or performance improvement; nothing to do but upgrade.
  other      — dependency bumps, docs, known issues, contributor thanks, summaries.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import asdict, dataclass

from upgrade_briefing.ingest.chunk import _useful_items, load_entries

LABELS = ("breaking", "deprecated", "new", "fix", "other")


@dataclass
class Item:
    item_id: str  # "room@2.7.0-alpha01#1.3" = section 1, bullet 3
    entry_id: str
    library: str
    version: str
    section: str
    text: str


def iter_items(entries: list[dict] | None = None) -> list[Item]:
    entries = entries if entries is not None else load_entries()
    out = []
    for e in entries:
        for s_idx, s in enumerate(e["sections"]):
            for i, text in enumerate(_useful_items(s)):
                out.append(Item(f"{e['entry_id']}#{s_idx}.{i}", e["entry_id"], e["library"],
                                e["version"], s["title"], text))
    return out


def section_group(item: "Item") -> str:
    """Coarse bucket used only to stratify the sample.

    Deprecations are spread over many section titles and are rare, so a random draw finds
    almost none. They get their own bucket ("mentions deprecat-"); that makes the keyword
    rule look good on this bucket, which we say out loud when reporting.
    """
    if "deprecat" in item.text.lower():
        return "deprecat"
    t = item.section.lower()
    for key in ("breaking", "behavior", "api", "new feature", "bug fix"):
        if key in t:
            return key
    return "rest"


# How many bullets to draw from each bucket. Rare-but-important buckets (breaking, behaviour)
# are over-sampled, otherwise a random 60 would be ~40% bug fixes and teach us little.
QUOTA = {"deprecat": 8, "bug fix": 12, "api": 16, "new feature": 8, "behavior": 8, "breaking": 6, "rest": 10}


def draw_sample(items: list[Item], seed: int = 5) -> list[Item]:
    rng = random.Random(seed)
    by_group: dict[str, list[Item]] = defaultdict(list)
    for it in items:
        by_group[section_group(it)].append(it)
    sample = []
    for group, n in QUOTA.items():
        sample += rng.sample(by_group[group], n)
    rng.shuffle(sample)
    return sample


def to_dict(item: Item) -> dict:
    return asdict(item)
