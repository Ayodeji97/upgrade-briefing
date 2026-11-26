# Upgrade Briefing: a hands-on RAG learning guide

**Goal:** build a tool that reads `libs.versions.toml` and writes a cited briefing of what changed between your
pinned AndroidX versions and the latest ones. While doing that, learn how every part of RAG works by building
it, breaking it, and measuring it.

**How to use this guide:** each stage has four parts:
- **Concept:** what is happening and why.
- **Build:** the minimum code to write.
- **Experiment:** predict the result first, then run it. The gap between prediction and result is where the
  learning happens.
- **Checkpoint:** you understand the stage if you can answer this without looking.

Do the stages in order. Each one adds a single moving part.

---

## Stage 0: The mental model (read, 30 min)

RAG = **R**etrieve relevant text → **A**ugment the prompt with it → **G**enerate an answer grounded in it.

It exists because LLMs:
- don't know recent facts (Room 2.8 notes postdate their training);
- make up plausible APIs;
- can't cite sources.

RAG fixes all three by handing the model the evidence at question time.

Every RAG system has two pipelines:

```
OFFLINE (ingestion, run once / on update)
  fetch release notes → parse → chunk → attach metadata → embed → store in Weaviate

ONLINE (per briefing)
  parse libs.versions.toml → for each library:
     build query → filter by library + version range → BM25 + dense search → fuse (RRF)
     → rerank → classify (breaking / deprecated / new) → prompt LLM with chunks → cited briefing
  trace every step in Phoenix
```

**The most important idea in the course:** the quality of the answer is capped by the quality of retrieval.
If the right chunk isn't in the top-k, no prompt can save you. That's why you measure retrieval separately from
generation.

**Checkpoint:** why is "the LLM gave a wrong answer" not enough information to fix a RAG system?

---

## Stage 1: Ingestion and chunking (days 1–3)

**Concept.**
- **What a chunk is:** the unit you retrieve. Too big and it contains noise, wastes tokens and blurs the
  embedding. Too small and it loses context, for example "Fixed a crash" without knowing which version.
- **The right shape here:** AndroidX release notes already have one: library → version → section ("API
  Changes", "Behavior Changes", "Bug Fixes", "New Features", "Dependency Updates").
- **Lesson:** structure-aware chunking beats fixed-size chunking when the documents have structure.

**Build.**
- Start with 4 libraries only: Room, Navigation, Lifecycle, WorkManager. Add more later.
- Fetch each `developer.android.com/jetpack/androidx/releases/<lib>` page.
  - First check the site's terms/robots for bulk fetching.
  - Fallback source: the `mahozad/androidx-release-notes` GitHub mirror.
  - Cache raw HTML to disk so you fetch only once.
- Parse into records:
  ```python
  {
    "chunk_id": "room-2.7.0-alpha01-api-changes-0",
    "library": "room", "version": "2.7.0-alpha01",
    "version_key": 2_007_000_1_01,   # sortable integer, see below
    "channel": "alpha", "date": "2024-xx-xx",
    "section": "API Changes",
    "text": "...",                   # the bullet(s)
    "url": "https://developer.android.com/...#2.7.0-alpha01"
  }
  ```
- **The version key:** version ordering is a real problem. `2.7.0-alpha10` > `2.7.0-alpha02` but sorts
  lower as a string. Convert each version to a sortable number: major, minor, patch, then channel rank
  (alpha=1, beta=2, rc=3, stable=4), then pre-release number. Write unit tests for this function. It's the
  backbone of correct version filtering.
- **Two chunkers:**
  - A: one chunk per version + section; split long sections into groups of ~5 bullets, each prefixed with
    `"Room 2.7.0-alpha01, API Changes:"`.
  - B: naive fixed 300-token windows.

**Experiment.**
- Predict: which chunker will retrieve "When did Room add KMP support?" better? Why?
- Look at 10 random chunks from each. Which ones would *you* be able to answer from, with no surrounding
  page?

**Checkpoint:**
- Why does prefixing each chunk with its library and version help both BM25 and embeddings?
- What breaks if you don't?

---

## Stage 2: Embeddings and dense retrieval (days 3–4)

**Concept.**
- **What an embedding is:** it maps text to a vector, so texts with similar meaning are close (cosine
  similarity). `bge-base-en-v1.5` gives 768 dimensions.
- **Dense search:** "find the vectors nearest the query vector."
- **Strength:** paraphrase. "removed", "no longer supported" and "dropped" all land near each other.
- **Weakness:** exact identifiers. `RoomDatabase.Builder` vs `RoomDatabase.Callback` look almost identical
  to an embedding model.
- **Query prefix:** bge models were trained with an optional query prefix (`"Represent this sentence for
  searching relevant passages: "`). Try with and without.

**Build.**
- Create a Weaviate collection `ReleaseNote` with the fields above.
- Embed with your local bge, the same way as in M3/M4 (Flask vectorizer or client-side vectors).
- Write `dense_search(query, k)`.

**Experiment.** Run these three queries and inspect the top 5:
1. "breaking changes to database migrations"
2. "setFoo deprecated" (pick a real deprecated API name from the notes)
3. "Kotlin Multiplatform support"

Predict which one dense search gets wrong. (It's usually #2.)

**Checkpoint:** explain to a colleague, without jargon, why dense search struggles with exact API names.

---

## Stage 3: BM25 and tokenization (day 5)

**Concept.**
- **What BM25 is:** keyword scoring. Rare words that appear in a chunk score high; common words score low.
- **Strength:** exact names, error strings and version numbers.
- **Weakness:** synonyms.
- **Tokenization is the hidden lever.** Weaviate's default `word` tokenization lowercases and splits on
  non-alphanumerics, so `RoomDatabase.Builder` → `roomdatabase`, `builder`. camelCase is **not** split, so
  "database builder" won't match `RoomDatabase`.

**Build.**
- Write `bm25_search(query, k)` with Weaviate's BM25.
- Try a second text field where you pre-split camelCase (`RoomDatabase` → `room database`). Compare.

**Experiment.** Run the same 3 queries. Fill this table by hand:

| Query | Dense top-5 correct? | BM25 top-5 correct? |
|---|---|---|

You should now *feel* why hybrid exists.

**Checkpoint:** give one query where BM25 wins and one where dense wins, from *your* data.

---

## Stage 4: Hybrid search and RRF (days 6–7)

**Concept.**
- **What RRF is:** Reciprocal Rank Fusion combines ranked lists using only ranks, not scores:
  `score(d) = Σ 1 / (k + rank_i(d))`, with k ≈ 60.
- **Why ranks:** BM25 scores and cosine scores are on different scales, and ranks sidestep that.
- **Weaviate's built-in hybrid:** it has `alpha` (0 = pure BM25, 1 = pure dense) and two fusion
  methods.

**Build.**
- Implement RRF yourself in ~15 lines: run both searches with k=50, fuse, return the top 10.
- Then use Weaviate's `hybrid()` and sweep alpha over 0, 0.25, 0.5, 0.75 and 1.

**Experiment.** Predict the best alpha for your corpus before running the sweep. (It's identifier-heavy, so
expect something below 0.5. Measure it; don't trust the guess.)

**Checkpoint:**
- Why can't you just add the BM25 score and the cosine score together?
- What does the k in RRF control?

---

## Stage 5: Metadata filtering, the core of *this* project (day 8)

**Concept.**
- **Two kinds of filters:** some questions are partly structured ("between 2.6.1 and 2.8.0, library =
  room"), and filters handle that part exactly. Semantic search handles the fuzzy part.
- **Pre-filtering:** filter first, then search. Weaviate does this.
- **Avoid post-filtering:** search, then drop results. That can return nothing if the top-k were all
  filtered out.

**Build.**
```python
Filter.by_property("library").equal("room")
& Filter.by_property("version_key").greater_than(key("2.6.1"))
& Filter.by_property("version_key").less_or_equal(key("2.8.0"))
```
Add an option to include or exclude pre-releases. Users on stable usually care about the stable-to-stable
diff, but breaking changes are often announced in alpha notes.

**Experiment.**
- Run "breaking changes" for Room 2.6.1→2.8.0 with no filter vs with the filter.
- Count how many top-10 results come from the wrong library or version without it. That count is your
  **wrong-version rate**, a metric you'll report later.

**Checkpoint:** why is version filtering a *structured* problem that you shouldn't hand to the embedding
model?

---

## Stage 6: Reranking (day 9)

**Concept.**
- **Bi-encoder (bge):** embeds the query and the document *separately*. It's fast and can search millions
  of chunks, but it's approximate.
- **Cross-encoder (`bge-reranker-base`):** reads the query and the document *together* and scores the pair.
  It's far more accurate, but too slow to run on everything.
- **Standard pattern:** retrieve the top 50 cheaply, rerank to the top 10 precisely.

**Build.** Take the hybrid top 50, rerank with bge-reranker and keep the top 10. Log the reranker's latency
per query.

**Experiment.** Compare the top 10 before and after reranking for 5 queries. Did it fix near-duplicate
versions, such as alpha03 vs alpha04 notes that say similar things? Did it ever make things *worse*? (FreshStack
found reranking helps on some topics and hurts on others. Your data decides.)

**Checkpoint:** why don't we use the cross-encoder for the first-stage search?

---

## Stage 7: Routing and classification (day 10)

**Concept.**
- **Routing:** decides which path a request takes. In M5 that was FAQ vs product. Here, each retrieved
  change needs a type: **breaking / deprecated / new feature / bug fix / irrelevant**.
- **Rules before LLMs:** the cheapest correct method wins. Section headings ("Behavior Changes", "API
  Changes") already give a free, perfectly reliable signal. Use an LLM only for the ambiguous rest.
- **Offline vs online classification:** classify each chunk once at ingestion (cache the result in
  metadata) vs at every query. Offline is cheaper and faster, and lets you filter by type.

**Build.**
- Rule-based classifier from headings and keywords ("deprecated", "removed", "now requires").
- Then an LLM classifier for the leftovers, run once at ingestion, with `temperature=0` and a short prompt
  (M5's lesson on token cost).

**Experiment.**
- Hand-label 40 chunks.
- Measure the accuracy of rules only vs rules + LLM. Is the LLM worth its tokens?

**Checkpoint:** name one reason to classify at ingestion time and one reason you might still need query time.

---

## Stage 8: Generation and prompting (days 11–12)

**Concept.** The LLM's job is narrow: **summarise only the evidence given, cite each claim, and say "nothing
notable" when that's true.** Most hallucinations in RAG come from:
- missing evidence (a retrieval failure), or
- a prompt that lets the model fill gaps from memory.

**Build.** Prompt skeleton:
```
You write upgrade briefings for Android developers.
Use ONLY the release notes below. Every bullet must end with its [chunk_id].
If there is nothing breaking or deprecated, say so. Do not use outside knowledge.

Library: Room, upgrading 2.6.1 → 2.8.0
<notes>
[room-2.7.0-alpha01-api-changes-0] Room 2.7.0-alpha01, API Changes: ...
...
</notes>
Output sections: Breaking, Deprecated, New and worth knowing.
```
- Map `[chunk_id]` back to URLs after generation.
- Then validate the output: every cited ID must exist in the retrieved set. A cited ID that wasn't
  retrieved is a hallucinated citation, and you can catch it with code, no LLM needed.

**Experiment.**
- Remove "Use ONLY the release notes" and compare the outputs.
- Shuffle the chunk order: does the model favour chunks at the start or the end ("lost in the middle")?
- Measure tokens per briefing for top-5 vs top-10 vs top-20 chunks.

**Checkpoint:** which failures can you detect with plain code, and which need a judge?

---

## Stage 9: Evaluation, where most of the learning is (days 13–16)

**Concept.** Evaluate in two layers:
1. **Retrieval:** did the right chunks come back? No LLM is needed, so it's cheap and objective.
2. **Generation:** is the briefing faithful, complete and correctly cited? Needs labels and/or a judge.

**Build the golden set.**
- 30–50 real upgrades (library, from-version, to-version). For each one, *you* list the chunk IDs of the
  truly breaking and deprecated changes, read from the notes yourself.
- Your Android experience is the edge here: you know what actually matters.
- Add about 10 trap cases:
  - an upgrade with nothing breaking;
  - a library you didn't ingest;
  - a version that doesn't exist.

**Retrieval metrics** (write these yourself; each is a few lines):
- **Recall@k:** the share of labelled important chunks that appear in the top k.
- **MRR:** how high the first correct chunk ranks.
- **Wrong-version rate:** the share of retrieved chunks outside the requested range.

**Generation metrics:**
- **Citation validity** (code): every cited ID was retrieved and is in range.
- **Coverage** (code + labels): the share of labelled breaking changes mentioned in the briefing.
- **Faithfulness** (LLM judge, yes/no): "Is every bullet supported by its cited note?"
  - Use Phoenix Evals with a Groq model *different* from your generator.
  - **Validate the judge:** hand-label 30–50 bullets yourself and compare. Report how often it agrees with
    you, not just its score.
- **Cost and speed:** tokens per briefing, p50/p95 latency.

**The ablation table, the centrepiece of your README:**

| Config | Recall@10 | MRR | Wrong-version % | Coverage | Faithfulness | Tokens | p95 latency |
|---|---|---|---|---|---|---|---|
| BM25 only | | | | | | | |
| Dense only | | | | | | | |
| Hybrid (RRF) | | | | | | | |
| Hybrid + version filter | | | | | | | |
| + reranker | | | | | | | |
| + type classification | | | | | | | |

**Error analysis:**
- Read 30 traces in Phoenix where something went wrong.
- Write each failure as one line, then group them into categories ("wrong version", "missed behaviour
  change", "cited a bug fix as breaking"…).
- Fix the biggest category, then re-run the table. This loop *is* RAG engineering.

**Checkpoint:** if Recall@10 is 0.95 but Coverage is 0.6, where is the problem?

---

## Stage 10: Observability and cost (ongoing from Stage 4)

**Concept.** Phoenix traces show the *inside* of each request: which chunks came back, the prompt sent, the
tokens used and the time per step. Without traces, debugging RAG is guesswork.

**Build.**
- One span per stage: parse → filter → bm25 → dense → fuse → rerank → classify → generate → validate.
- Attach the retrieved chunk IDs and the token counts.
- Add a simple cache: same (library, from, to) → same briefing. Free-tier Groq limits make caching
  mandatory, not optional.

**Checkpoint:** a briefing took 9 seconds. Which span do you look at first, and why?

---

## Stage 11: Ship it (days 17–21)

- **CLI:** `briefing path/to/libs.versions.toml --include-prereleases`.
- **README, in this order:**
  1. a one-line outcome with a number;
  2. a demo GIF;
  3. an architecture diagram;
  4. 3–5 design decisions, each with its reason (DECISIONS.md);
  5. the ablation table;
  6. known limitations;
  7. one-command setup.
- One write-up post: "What broke when I measured my RAG pipeline."
- Optional: a thin Compose Multiplatform client calling a small FastAPI endpoint.

---

## Suggested repo layout

```
upgrade-briefing/
  ingest/       fetch.py, parse.py, versions.py (+ tests), chunk.py, index.py
  retrieve/     bm25.py, dense.py, fusion.py, filters.py, rerank.py
  classify/     rules.py, llm.py
  generate/     prompt.py, briefing.py, validate_citations.py
  eval/         golden_set.jsonl, retrieval_metrics.py, judges.py, run_ablation.py
  app/          cli.py (api.py later)
  traces/       phoenix setup
  README.md  DECISIONS.md
```

## What you'll know at the end

- Why retrieval quality caps answer quality, and how to measure each one separately.
- When BM25 beats dense search, and when the reverse is true, with *your* numbers.
- How tokenization, chunking and metadata quietly decide your results.
- Why the cross-encoder comes after the bi-encoder.
- Why rules come before LLM calls, and how to keep cost down.
- How to build a golden set, check an LLM judge, and do error analysis from traces.
- How to present all of it so an interviewer believes it.
