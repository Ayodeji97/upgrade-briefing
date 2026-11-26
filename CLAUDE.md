# CLAUDE.md — Upgrade Briefing

## What this is
This is a RAG portfolio project by an Android/Kotlin developer who just finished DeepLearning.AI's RAG course.
Input is `libs.versions.toml`. Output is a cited briefing for each AndroidX library: breaking changes,
deprecations and new APIs between the pinned version and the latest.

**Working agreement:** Claude writes the code. Daniel wants to *understand* it. After each step, explain
briefly what was built and which RAG concept it shows, and point to the matching stage in
`docs/learning-guide.md`. Keep the explanations plain and short.

## Status and next step
See `HANDOVER.md`. Keep it up to date at the end of every step.

## Stack (same as the course on purpose)
- Python 3.12, managed by `uv` (`uv sync`, `uv run ...`, `uv add ...`). Add a dependency only when the step that needs it starts.
- Embeddings: `BAAI/bge-base-en-v1.5` (768-dim; queries get the bge query prefix). Reranker: `BAAI/bge-reranker-base`.
  Both are already cached at `$MODEL_PATH` (the course's `.models`). Don't download them again.
- Vector DB: Weaviate, embedded, with data in `data/weaviate/` (git-ignored).
  - The course used Weaviate's embedded mode with a Flask vectorizer on port 5000; macOS AirPlay Receiver holds that port.
    Prefer computing vectors in Python and inserting them with the objects (`vectorizer: none`). Then no Flask server is needed.
  - The Mac's disk is about 97% full. Set `DISK_USE_READONLY_PERCENTAGE=99` for embedded Weaviate, or it goes read-only.
- LLM: Groq, model `qwen/qwen3.8-27b` with `reasoning_effort="none"`. Groq has retired the Llama models.
  The free tier has rate limits, so cache LLM calls during evaluation.
- Tracing: Arize Phoenix. Pin `graphql-core<3.3` when adding it (3.3 breaks Phoenix's import).

## Layout
- `src/upgrade_briefing/versions.py`: version parsing and the sortable `version_key` (alpha=1, beta=2, rc=3, stable=4).
- `src/upgrade_briefing/ingest/scrape.py`: Step 1 scraper. Run it with `uv run briefing-scrape`.
- `src/upgrade_briefing/ingest/chunk.py` + `ingest/index.py`: Step 3 chunking and indexing (`uv run briefing-index`).
- `src/upgrade_briefing/embed.py` (bge vectors) and `store.py` (embedded Weaviate connection + collections).
- `src/upgrade_briefing/retrieve/dense.py`: dense search with library/version filters.
- `src/upgrade_briefing/{classify,generate,evaluation,app}/`: later steps (empty for now).
- `data/entries.jsonl`: one release per line (committed). `data/raw/`: cached HTML (ignored).
- `eval/`: golden set and results. `traces/`: Phoenix exports (ignored). `docs/learning-guide.md`: concept guide, stages 0–11.

## Conventions
- After each step: run `uv run pytest`, commit with the metric change in the message when there is one
  (e.g. `hybrid: Recall@5 0.62 -> 0.78`), and update `HANDOVER.md`.
- Evaluate against `eval/golden.jsonl`. Never tune on the questions you report results for.
- The `android` CLI is installed (`android docs search ...`). It is the baseline to compare against in Step 8.
