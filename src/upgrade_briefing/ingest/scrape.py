"""Step 1 — collect AndroidX release notes into data/entries.jsonl.

Each library has one page, e.g. https://developer.android.com/jetpack/androidx/releases/room.
On that page every release is an <h3 id="2.7.0"> heading followed by:
  - a date paragraph ("April 9, 2025")
  - section titles as <p><strong>API Changes</strong></p>
  - bullet lists (<ul><li>) under each section

We turn each release into ONE JSON line (an "entry") that keeps that structure.
Chunking happens later (Step 3); keeping the sections now lets us chunk by
structure ("Room 2.7.0 › API Changes") instead of cutting text at random lengths.

Run:  uv run briefing-scrape            (uses cached HTML in data/raw/ if present)
      uv run briefing-scrape --refresh  (re-download the pages)
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

from upgrade_briefing.versions import is_version, parse_version

BASE_URL = "https://developer.android.com/jetpack/androidx/releases/"

# v1 scope: five libraries. Add more here later.
LIBRARIES = {
    "room": "androidx.room",
    "navigation": "androidx.navigation",
    "lifecycle": "androidx.lifecycle",
    "paging": "androidx.paging",
    "work": "androidx.work",
}

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_FILE = PROJECT_ROOT / "data" / "entries.jsonl"

DEFAULT_SECTION = "Summary"  # text that appears before the first <strong> section title


@dataclass
class Section:
    title: str
    items: list[str] = field(default_factory=list)


@dataclass
class Entry:
    entry_id: str  # "room@2.7.0" (a "~2" suffix if the page repeats a version heading)
    library: str  # "room"
    group: str  # "androidx.room"
    version: str  # "2.7.0-rc03"
    version_key: int  # sortable int, see versions.py
    channel: str  # alpha | beta | rc | stable
    date: str | None  # ISO "2025-03-26"
    url: str  # deep link to this release, used as the citation
    sections: list[Section]


def fetch_page(slug: str, refresh: bool) -> str:
    """Download a release-notes page once and cache it, so re-runs don't hit the site."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cached = RAW_DIR / f"{slug}.html"
    if cached.exists() and not refresh:
        return cached.read_text(encoding="utf-8")
    resp = requests.get(
        BASE_URL + slug,
        headers={"User-Agent": "upgrade-briefing/0.1 (learning project)"},
        timeout=30,
    )
    resp.raise_for_status()
    cached.write_text(resp.text, encoding="utf-8")
    time.sleep(1)  # be polite between requests
    return resp.text


_SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,;:)])")
_SPACE_AFTER_PAREN = re.compile(r"\(\s+")


def _clean(text: str) -> str:
    """Collapse whitespace; get_text(" ") leaves "commits ." so glue punctuation back on."""
    text = " ".join(text.split())
    return _SPACE_AFTER_PAREN.sub("(", _SPACE_BEFORE_PUNCT.sub(r"\1", text))


def _normalize_title(title: str) -> str:
    """The pages mix "Bug fixes" and "Bug Fixes"; use one spelling."""
    return " ".join(w if w.isupper() else w.capitalize() for w in title.split())


def _parse_date(text: str) -> str | None:
    try:
        return datetime.strptime(_clean(text), "%B %d, %Y").date().isoformat()
    except ValueError:
        return None


def _section_title(p: Tag) -> str | None:
    """<p><strong>API Changes</strong></p> -> "API Changes" (only when the strong is the whole paragraph)."""
    strong = p.find("strong")
    if strong and _clean(strong.get_text()) == _clean(p.get_text()):
        return _normalize_title(_clean(strong.get_text()).rstrip(":"))
    return None


def parse_releases(html: str, slug: str, group: str) -> list[Entry]:
    soup = BeautifulSoup(html, "html.parser")
    entries: list[Entry] = []
    seen: dict[str, int] = {}

    for h3 in soup.find_all("h3"):
        version_id = h3.get("id", "")
        if not is_version(version_id):
            continue  # skips "gradle-plugin", "kts", etc.
        version = parse_version(version_id)

        date: str | None = None
        sections = [Section(DEFAULT_SECTION)]

        # Walk the siblings after the heading until the next release/heading.
        for el in h3.find_next_siblings():
            if el.name in ("h2", "h3"):
                break
            if el.name == "p":
                if date is None and (d := _parse_date(el.get_text())):
                    date = d
                    continue
                if title := _section_title(el):
                    sections.append(Section(title))
                    continue
                if text := _clean(el.get_text(" ")):
                    sections[-1].items.append(text)
            elif el.name in ("ul", "ol"):
                for li in el.find_all("li", recursive=False):
                    if text := _clean(li.get_text(" ")):
                        sections[-1].items.append(text)
            elif el.name == "pre":
                sections[-1].items.append(el.get_text())  # keep code formatting

        # A few pages repeat a version heading (e.g. Room 2.5.0 for two artifact sets).
        # Keep both, but give each a unique id so the golden set can point at either.
        seen[version_id] = seen.get(version_id, 0) + 1
        entry_id = f"{slug}@{version}" + (f"~{seen[version_id]}" if seen[version_id] > 1 else "")

        entries.append(
            Entry(
                entry_id=entry_id,
                library=slug,
                group=group,
                version=str(version),
                version_key=version.key,
                channel=version.channel,
                date=date,
                url=f"{BASE_URL}{slug}#{version_id}",
                sections=[s for s in sections if s.items],
            )
        )
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="re-download pages instead of using data/raw/")
    args = parser.parse_args()

    all_entries: list[Entry] = []
    for slug, group in LIBRARIES.items():
        entries = parse_releases(fetch_page(slug, args.refresh), slug, group)
        all_entries.extend(entries)
        stable = sum(e.channel == "stable" for e in entries)
        print(f"{slug:<11} {len(entries):>4} releases ({stable} stable), newest {entries[0].version if entries else '-'}")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for e in all_entries:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")
    print(f"\nWrote {len(all_entries)} entries -> {OUT_FILE.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
