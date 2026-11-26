# Handover

_Last updated: 2026-11-26_

## Plan (9 steps)
| # | Step | Status |
|---|---|---|
| 0 | Repo setup (uv, git, layout, docs) | ✅ done |
| 1 | Scrape release notes for Room, Navigation, Lifecycle, Paging and WorkManager into `data/entries.jsonl` | ✅ done (591 releases) |
| 2 | Golden set: about 30 questions with the correct `entry_id`s, in `eval/golden.jsonl` | 🔶 30/30 drafted; batch 3 (q21–q30) awaiting Daniel's review |
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
- The scraper drops HTML tables. Two entries say "the table below" with no table: lifecycle@2.6.0 and navigation@2.9.0-alpha04. Fix in Step 3 if it matters.
- The paging 1.0.0-* entries are actually Paging *Compose* 1.0.0 releases (LazyPagingItems), listed on the same page.
- The source pages repeat some version headings (room 2.5.0, navigation 1.0.0-alpha08, paging 1.0.0-rc01).
  Both copies are kept; the second gets `~2` in its `entry_id`.
- 2 very old entries have no date (room 1.1.1-rc01, paging 1.0.0-rc01). This is harmless.
- Section titles are free text, so "breaking" is not a label on the page. Step 5 (classification) exists for this reason.

## Step 2 progress
- `eval/golden.jsonl` has q01–q30 (10 range, 15 api, 5 negative). Batches 1–2 accepted by Daniel; batch 3 (q21–q30) drafted, not yet reviewed.
- Open question (q29): do back-merged copies ("From Navigation 2.8.8: ..." in a later alpha) count as relevant? Currently left out.
- Each line has a `notes` field explaining the labels.
- **Labelling rules agreed with Daniel:**
  - An entry is relevant if it contains a line that answers the question.
  - Range questions (stable → stable): the stable entry counts; an alpha/beta/rc entry counts *only* if it adds something the stable "Important changes" summary leaves out.
  - API questions ("when was X deprecated"): the pre-release where it first appeared counts, plus the stable summary if it repeats it.
  - Minor behaviour changes (e.g. room 2.7.0-alpha12 destructive migration drops views) are not "breaking".
  - Related-but-different facts are left out (e.g. lifecycle-compiler deprecation is not the @OnLifecycleEvent answer).

## Step 2 (golden set): original plan
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

## Next
1. Daniel reviews batch 3 (q21–q30) and the q29 "copies" question; then mark Step 2 ✅.
2. Step 3: chunk each entry by section, embed with bge-base (vectors computed in Python), index in embedded Weaviate with `library`, `version_key`, `channel`, `section_title`, `entry_id` metadata.
