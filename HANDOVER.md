# Handover

_Last updated: 2026-11-26_

## Plan (9 steps)
| # | Step | Status |
|---|---|---|
| 0 | Repo setup (uv, git, layout, docs) | ✅ done |
| 1 | Scrape release notes for Room, Navigation, Lifecycle, Paging and WorkManager into `data/entries.jsonl` | ✅ done (591 releases) |
| 2 | Golden set: about 30 questions with the correct `entry_id`s, in `eval/golden.jsonl` | ⏭ **next** |
| 3 | Chunk by section, embed, index in Weaviate with metadata | |
| 4 | Retrieval ablation: BM25 → semantic → hybrid → version filter → rerank (Recall@5, MRR) | |
| 5 | Classify chunks (breaking / deprecated / new / fix) | |
| 6 | Generate the briefing with checked citations | |
| 7 | CLI over `libs.versions.toml` | |
| 8 | Full evaluation, Phoenix traces, `android docs search` baseline, cost | |
| 9 | README, diagram, demo GIF, publish | |

## What Step 1 produced
- 591 entries: room 98, navigation 163, lifecycle 123, paging 93, work 114.
  Newest versions when scraped: room 2.8.5, navigation 2.10.2, lifecycle 2.12.0-alpha06, paging 3.6.0-alpha01, work 2.12.0.
- Each entry has `entry_id` (e.g. `room@2.7.0`), `library`, `group`, `version`, `version_key`, `channel`, `date`, `url` and `sections` (title plus items).
- Most common section titles: Summary, Bug Fixes, API Changes, New Features, Behavior Changes, Dependency Updates, Known Issues.
  Stable releases often have an "Important changes since X.Y.0" section, which summarises the whole alpha-to-rc cycle.

## Data quirks to remember
- The source pages repeat some version headings (room 2.5.0, navigation 1.0.0-alpha08, paging 1.0.0-rc01).
  Both copies are kept; the second gets `~2` in its `entry_id`.
- 2 very old entries have no date (room 1.1.1-rc01, paging 1.0.0-rc01). This is harmless.
- Section titles are free text, so "breaking" is not a label on the page. Step 5 (classification) exists for this reason.

## Next session: Step 2 (golden set)
Write about 30 questions *before* any retrieval code exists, so that the evaluation stays honest. Mix them like this:
- version-range questions ("room 2.6.1 → 2.7.0: what breaks?")
- specific API questions ("when was X deprecated in Lifecycle?")
- a few questions with no answer in the data (to test that the system refuses)

Planned format, one JSON object per line:
`{"id": "q01", "library": "room", "from": "2.6.1", "to": "2.7.0", "question": "...", "relevant": ["room@2.7.0", ...], "type": "range|api|negative"}`.

Daniel should help pick or check the answers: labelling them is where most of the learning happens.

## Not done yet / decisions pending
- GitHub remote: https://github.com/Ayodeji97/upgrade-briefing (`main` pushed).
- `.env` exists locally (Groq key copied from the course `.env`). It is git-ignored.
