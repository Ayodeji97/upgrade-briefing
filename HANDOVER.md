# Handover

_Last updated: 2026-11-26_

## Plan (9 steps)
| # | Step | Status |
|---|---|---|
| 0 | Repo setup (uv, git, layout, docs) | ✅ done |
| 1 | Scrape release notes for Room, Navigation, Lifecycle, Paging and WorkManager into `data/entries.jsonl` | ✅ done (591 releases) |
| 2 | Golden set: about 30 questions with the correct `entry_id`s, in `eval/golden.jsonl` | ✅ done (30 questions) |
| 3 | Chunk by section, embed, index in Weaviate with metadata | ✅ done (1133 section chunks, 652 fixed) |
| 4 | Retrieval ablation: BM25 → semantic → hybrid → version filter → rerank (Recall@5, MRR) | ✅ done |
| 5 | Classify chunks (breaking / deprecated / new / fix) | 🟡 code + eval done; full-corpus labels finishing (see below) |
| 6 ⏭ **next** | Generate the briefing with checked citations | |
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

## What Step 4 produced
- `text.py` (`split_identifiers`, camelCase split) + a second BM25 field `text_split` in both collections.
- `retrieve/search.py`: `search(client, query, method=bm25|dense|rrf|hybrid, k, field=, alpha=, library=, after_key=, upto_key=)`.
  `rrf_fuse` is our own RRF (k=60). `hybrid` = Weaviate hybrid, relativeScore fusion, BM25 on `text_split`.
- `retrieve/rerank.py`: bge-reranker-base CrossEncoder over the top 50.
- `evaluation/metrics.py` (Recall@k, reciprocal rank, wrong-version rate, all over unique entry_ids; tested).
- `evaluation/retrieval.py`: `uv run briefing-eval-retrieval` (~1 min) -> `eval/results/retrieval.md` + `.json`.
  Dev = odd question ids (used to pick alpha), test = even ids (reported).

## Step 4 results (25 positive questions; see eval/results/retrieval.md)
| Config | R@5 dev | R@5 test | R@10 all | MRR | Wrong-ver@10 |
|---|---|---|---|---|---|
| BM25 (camelCase split) | 0.68 | 0.63 | 0.73 | 0.62 | 41% |
| Dense | 0.56 | 0.68 | 0.69 | 0.64 | 39% |
| Hybrid alpha=0.5 (picked on dev) | 0.79 | 0.63 | 0.77 | 0.71 | 37% |
| Hybrid + library/version filter | 0.91 | 0.83 | 0.91 | 0.80 | 0% |
| + rerank | 0.92 | 0.89 | 0.98 | 0.84 | 0% (p95 2.7 s) |

Lessons:
- **The metadata filter is the biggest single win** (test R@5 0.63 -> 0.83). Without it ~40% of the top 10 is the wrong library/version.
- camelCase splitting helps BM25 a little (MRR 0.56 -> 0.62). Section chunks beat fixed windows clearly (dense R@10 0.69 vs 0.60).
- The bge query prefix: mixed (better on dev, slightly worse on test). Kept on.
- Hybrid without the filter: better on dev than on test. Test has only 12 questions; one question moves R@5 by ~0.08, so small gaps are noise.
- Reranking helped overall and fixed q17 (6 entries mention getRefreshKey; reranker put the right one first), but it
  **hurt q07** (MRR 0.50 -> 0.17): it prefers old launchWhenCreated bug fixes that contain the literal words.
- q24 (paraphrase, no API name) fails in every config. Known hard case; leave it, it is honest.
- **Negatives:** the filter returns *nothing* for q21 (Room 2.9.0 doesn't exist) and q23 (Hilt), a free correct refusal.
  For false-premise questions (q10, q20, q22) the reranker's top score (0.64–1.00) sits inside the positives' range
  (0.17–1.00), so a score threshold can't refuse them. Refusal must come from generation (Step 6): "does the text actually say this?"

## What Step 5 produced
- Unit = one bullet (`classify/items.py`, id `room@2.7.0#1.3` = section 1, bullet 3). A chunk's `labels`
  = the set of its bullets' labels. Labels, priority order: breaking > deprecated > new > fix > other.
- `eval/classify_labels.jsonl`: 68 hand-labelled bullets, stratified (over-samples breaking/behaviour/deprecat).
  Dev = odd ids, test = even. **Labelling rules agreed with Daniel:** minor behaviour change needing no action = fix;
  a changed default the app could notice = breaking; annotation that makes lint fail (@MainThread) = breaking;
  signature change between alphas = breaking (stable-to-stable relevance is decided later, as in the golden set).
- `classify/rules.py` (keywords, then section title), `classify/llm.py` (Groq, 20 bullets per call, per-bullet cache in
  `data/cache/classify/`, git-ignored, `PROMPT_VERSION` = v2), `evaluation/classify.py` (`uv run briefing-eval-classify`).
- `classify/run.py`: `uv run briefing-classify` labels all 2,347 bullets -> `data/labels.jsonl` (commit it).
  `briefing-index` then stores `labels` + `item_ids` per chunk; `build_filter(labels=["breaking", ...])` filters on them.

## Step 5 results (eval/results/classify.md)
| Method | Acc dev | Acc test | Breaking recall test | Breaking precision test |
|---|---|---|---|---|
| Section title only | 0.65 | 0.56 | 0.33 | 0.67 |
| Rules | 0.85 | 0.74 | 0.58 | 0.70 |
| LLM (Groq qwen3.8-27b) | 0.97 | 1.00 | 1.00 | 1.00 |
| Hybrid (rule if keyword fired, else LLM) | 0.97 | 0.91 | 0.92 | 0.85 |

Lessons:
- Section titles are a weak signal here (0.56), the opposite of what the learning guide assumed: breaking changes
  sit under "New Features", deprecations under "Bug Fixes", plain additions under "Breaking API Changes".
- The LLM beat rules clearly. The hybrid is worse than the LLM alone because "confident" keyword rules are wrong
  sometimes (e.g. "no longer experimental" matched a breaking pattern; seen on test, so deliberately NOT fixed).
- Since classification runs once at ingestion and is cached, the LLM's cost is one-off; saving calls with rules isn't worth it.
- Test is only 34 bullets, and the prompt was revised once on dev (v2: behaviour change = breaking vs fix).
- **Groq free tier: 200k tokens/day (rolling) and 8k tokens/min.** One full labelling run used nearly the whole day's budget.

## Open item when this session ended (check first!)
- If `data/labels.jsonl` does not exist: run `uv run briefing-classify` (resumes from cache; ~200 bullets were left,
  slowed by the daily token limit), then `DISK_USE_READONLY_PERCENTAGE=99 uv run briefing-index`, then check that
  `search(..., labels=["breaking"])` returns only breaking chunks, then commit `data/labels.jsonl`.
- Re-run `uv run briefing-eval-retrieval` to confirm Step 4 numbers are unchanged (chunk text did not change).

## Next: Step 6 (generate the briefing with checked citations)
Learning guide Stage 8. Retrieve with library + version filter (+ `labels` filter per briefing section), rerank,
generate per label with citations to entry_id/url, then check each citation actually supports its claim.
False-premise questions (q10, q20, q22) must be refused at this step.
