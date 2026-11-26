# Upgrade Briefing

> **Status: work in progress.** Step 1 of 9 is done (collecting the data).

Upgrading an AndroidX library means reading through months of release notes to find what
actually matters for *your* version range. Upgrade Briefing reads your
`gradle/libs.versions.toml` and writes a short, **cited** briefing for each library:

- **Breaking changes** and behaviour changes
- **Deprecations**
- **New APIs** worth knowing about

It covers only the releases between your pinned version and the latest one. Every claim
links to the exact release-notes entry it came from.

```bash
briefing gradle/libs.versions.toml            # planned CLI
```

## How it works (planned)

```
release-notes pages ─► entries.jsonl ─► chunks + metadata ─► Weaviate (BM25 + vectors)
                                                                   │
libs.versions.toml ─► (library, from, to) ─► hybrid search, filtered to the version range
                                              ─► rerank ─► classify ─► LLM briefing with citations
```

| Stage | Technique |
|---|---|
| Ingestion | Structure-aware parsing: one entry per release, sections kept |
| Retrieval | BM25 + `bge-base-en-v1.5` embeddings, hybrid search (RRF) in Weaviate |
| Version range | Metadata filter on a sortable integer `version_key` |
| Reranking | `bge-reranker-base` cross-encoder |
| Generation | Groq (`qwen3.8-27b`), with citations checked against retrieved chunks |
| Evaluation | Hand-labelled golden set, Recall@k / MRR, ablation table, `android docs search` as a baseline |
| Observability | Arize Phoenix traces, token cost per briefing |

## Data

v1 covers 5 libraries: Room, Navigation, Lifecycle, Paging and WorkManager. That is
591 releases, taken from developer.android.com's AndroidX release-notes pages.

Release notes © Google, used under the
[Android Developers content license](https://developer.android.com/license) (CC BY 4.0).

## Run it

```bash
uv sync
cp .env.example .env              # add your Groq key
uv run briefing-scrape            # -> data/entries.jsonl
uv run pytest
```

## Results

_The ablation table goes here once evaluation runs (Step 8)._
