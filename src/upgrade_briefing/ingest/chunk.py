"""Step 3a — turn release entries into chunks (the unit we retrieve).

Two chunkers, so Step 4 can compare them (learning guide, Stage 1):

A. `section_chunks` (structure-aware, the one we use):
   one chunk per release section ("Room 2.7.0-alpha01 › API Changes"). Long sections are split
   into groups of MAX_ITEMS bullets. Every chunk starts with a header line naming the library,
   version and section, so the chunk still makes sense when it is read on its own.

B. `fixed_chunks` (naive baseline):
   the release's text cut into fixed windows of WINDOW_WORDS words, with no header.
   A window can start mid-sentence and mix sections.

Both keep the metadata (library, version_key, entry_id ...) so we can filter by version and
score retrieval against eval/golden.jsonl, which labels answers by entry_id.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENTRIES_FILE = PROJECT_ROOT / "data" / "entries.jsonl"

MAX_ITEMS = 5  # bullets per section chunk
WINDOW_WORDS = 200  # ~300 bge tokens per fixed window

DISPLAY_NAMES = {
    "room": "Room",
    "navigation": "Navigation",
    "lifecycle": "Lifecycle",
    "paging": "Paging",
    "work": "WorkManager",
}

# "androidx.room:room-*:2.7.0 is released. Version 2.7.0 contains these commits." carries no
# information, so Summary lines like that are dropped. Other Summary lines are kept.
_BOILERPLATE = re.compile(r"\bis released\b|contains these commits", re.I)


@dataclass
class Chunk:
    chunk_id: str  # "room@2.7.0-alpha01#api-changes-0"
    entry_id: str  # "room@2.7.0-alpha01" — what the golden set labels
    library: str
    version: str
    version_key: int
    channel: str
    date: str | None
    section: str  # "API Changes" ("" for fixed windows)
    text: str  # what gets embedded and searched
    url: str
    chunker: str  # "section" | "fixed"
    # Bullets in this chunk, as classify.items ids ("room@2.7.0#1.3"). Section chunks only:
    # a fixed window cuts through bullets, so it has none. Step 5 turns these into `labels`.
    item_ids: list[str] = field(default_factory=list)


def load_entries(path: Path = ENTRIES_FILE) -> list[dict]:
    with path.open() as f:
        return [json.loads(line) for line in f]


def header(entry: dict, section: str) -> str:
    """'Room 2.7.0-alpha01 (alpha, 2024-05-01) — API Changes'"""
    name = DISPLAY_NAMES.get(entry["library"], entry["library"])
    when = f", {entry['date']}" if entry.get("date") else ""
    return f"{name} {entry['version']} ({entry['channel']}{when}) — {section}"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _meta(entry: dict) -> dict:
    return {
        "entry_id": entry["entry_id"],
        "library": entry["library"],
        "version": entry["version"],
        "version_key": entry["version_key"],
        "channel": entry["channel"],
        "date": entry.get("date"),
        "url": entry["url"],
    }


def _useful_items(section: dict) -> list[str]:
    items = section["items"]
    if section["title"] == "Summary":
        items = [it for it in items if not _BOILERPLATE.search(it)]
    return [it for it in items if it.strip()]


def section_chunks(entry: dict, max_items: int = MAX_ITEMS) -> list[Chunk]:
    chunks: list[Chunk] = []
    for s_idx, section in enumerate(entry["sections"]):
        items = _useful_items(section)
        for part, start in enumerate(range(0, len(items), max_items)):
            group = items[start : start + max_items]
            text = header(entry, section["title"]) + ":\n" + "\n".join(f"- {it}" for it in group)
            chunks.append(
                Chunk(
                    # s_idx keeps ids unique when a page repeats a section title
                    chunk_id=f"{entry['entry_id']}#{s_idx}-{_slug(section['title'])}-{part}",
                    section=section["title"],
                    text=text,
                    chunker="section",
                    item_ids=[f"{entry['entry_id']}#{s_idx}.{i}" for i in range(start, start + len(group))],
                    **_meta(entry),
                )
            )
    return chunks


def fixed_chunks(entry: dict, window: int = WINDOW_WORDS) -> list[Chunk]:
    words = " ".join(it for s in entry["sections"] for it in _useful_items(s)).split()
    return [
        Chunk(
            chunk_id=f"{entry['entry_id']}#w{i // window}",
            section="",
            text=" ".join(words[i : i + window]),
            chunker="fixed",
            **_meta(entry),
        )
        for i in range(0, len(words), window)
    ]


def build_chunks(entries: list[dict], chunker: str = "section") -> list[Chunk]:
    fn = {"section": section_chunks, "fixed": fixed_chunks}[chunker]
    return [c for e in entries for c in fn(e)]


def to_dict(chunk: Chunk) -> dict:
    return asdict(chunk)
