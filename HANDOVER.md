# Handover

_Last updated: 2026-11-26_

## Plan (9 steps)
| # | Step | Status |
|---|---|---|
| 0 | Repo setup (uv, git, layout, docs) | ✅ done |
| 1 | Scrape release notes for Room, Navigation, Lifecycle, Paging and WorkManager into `data/entries.jsonl` | ✅ done (591 releases) |
| 2 | Golden set: about 30 questions with the correct `entry_id`s, in `eval/golden.jsonl` | ✅ done (30 questions) |
| 3 | Chunk by section, embed, index in Weaviate with metadata | ✅ done (1133 section chunks, 652 fixed) |
| 4 ⏭ **next** | Retrieval ablation: BM25 → semantic → hybrid → version filter → rerank (Recall@5, MRR) | |
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
- `eval/golden.jsonl` has q01–q30 (10 range, 15 api, 5 negative). All three batches accepted by Daniel.
- q29: back-merged copies ("From Navigation 2.8.8: ..." in a later alpha) are NOT counted as relevant (default kept; Daniel didn't object).
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

## What Step 3 produced
- `ingest/chunk.py`: two chunkers. **section** = one chunk per release section, max 5 bullets, header line
  `Room 2.7.0-alpha01 (alpha, 2024-05-01) — API Changes:`. **fixed** = 200-word windows, no header (baseline).
  Boilerplate "X is released / contains these commits" Summary lines are dropped, so 33 no-change releases have no chunks
  (none of them is a golden answer).
- `embed.py`: bge-base, vectors computed in Python, normalised; `embed_query(prefix=True)` adds the bge query prefix.
- `store.py`: embedded Weaviate 1.40.2 (`data/weaviate/`), collections `ReleaseNote` (section) and `ReleaseNoteFixed`.
  Metadata: entry_id, library, version, version_key (INT), channel, date, section, url. Vectors are self-provided.
- `ingest/index.py`: `uv run briefing-index` rebuilds both collections (~75 s on CPU).
- `retrieve/dense.py`: `dense_search(client, query, k, chunker, prefix, library=, after_key=, upto_key=)`.
- 6 section chunks and 2 fixed chunks are over bge's 512-token limit, so their tails are cut off when embedded. Small; revisit if a golden answer is affected.

## Stage 2 experiment (first look, top 5, no filters)
- "@MapInfo deprecated": correct entry at #1 — rare identifier with a clear meaning, dense does fine.
- "breaking changes to database migrations": all top 5 are Room migration *bug fixes*. Dense finds the topic but has no idea of "breaking".
- "Kotlin Multiplatform support": mixes Lifecycle, Paging and Room. Without a library filter, dense can't tell which library you mean.
- q24 (paraphrase of launchWhenX deprecation): the answer is NOT in the top 5. Our prediction that semantic search
  would bridge "pauses instead of cancelled" -> "pausing dispatcher" was wrong for bge-base. Step 4 will show whether BM25/hybrid/rerank fix it.
- The bge query prefix changed little; Step 4 should measure it on the golden set instead of guessing.

## Next: Step 4 (retrieval ablation)
Write `evaluation/` metrics (Recall@5, MRR over entry_ids, deduplicating chunks to entries) and run on `eval/golden.jsonl`:
BM25 -> dense -> hybrid -> + version/library filter -> + rerank (bge-reranker-base), plus section vs fixed chunker and prefix on/off.
Negative questions (q20–q23 style, empty `relevant`) need a separate check (e.g. top score threshold), not Recall.
