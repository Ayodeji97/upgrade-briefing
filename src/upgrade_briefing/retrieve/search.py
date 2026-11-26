"""All first-stage retrieval methods behind one function, so the evaluation can swap them.

  bm25        keyword scoring (Stage 3). field="text" or "text_split" (camelCase pre-split).
  dense       nearest vectors (Stage 2), see dense.py.
  rrf         our own Reciprocal Rank Fusion of bm25 + dense (Stage 4).
  hybrid      Weaviate's built-in hybrid, `alpha` 0 = pure BM25 ... 1 = pure dense (Stage 4).

Filters (library / version range) are applied inside Weaviate *before* ranking (Stage 5).
Each result is a dict of the chunk's properties plus a "score" (higher = better).
"""

from __future__ import annotations

from weaviate.classes.query import HybridFusion, MetadataQuery

from upgrade_briefing.embed import embed_query
from upgrade_briefing.retrieve.dense import build_filter, dense_search
from upgrade_briefing.store import COLLECTIONS
from upgrade_briefing.text import split_identifiers

RRF_K = 60  # standard constant: dampens how much the very top ranks dominate


def _bm25_query(query: str, field: str) -> str:
    return split_identifiers(query) if field == "text_split" else query


def bm25_search(client, query, k=10, chunker="section", field="text_split", **filters) -> list[dict]:
    collection = client.collections.get(COLLECTIONS[chunker])
    result = collection.query.bm25(
        query=_bm25_query(query, field),
        query_properties=[field],
        limit=k,
        filters=build_filter(**filters),
        return_metadata=MetadataQuery(score=True),
    )
    return [{**o.properties, "score": o.metadata.score} for o in result.objects]


def rrf_fuse(ranked_lists: list[list[dict]], k: int = RRF_K, key: str = "chunk_id") -> list[dict]:
    """score(d) = sum over lists of 1 / (k + rank). Uses ranks only, so BM25 scores and cosine
    distances never have to be put on the same scale."""
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}
    for results in ranked_lists:
        for rank, doc in enumerate(results, start=1):
            scores[doc[key]] = scores.get(doc[key], 0.0) + 1.0 / (k + rank)
            docs.setdefault(doc[key], doc)
    order = sorted(scores, key=scores.get, reverse=True)
    return [{**docs[d], "score": scores[d]} for d in order]


def rrf_search(client, query, k=10, chunker="section", depth=50, **filters) -> list[dict]:
    lexical = bm25_search(client, query, k=depth, chunker=chunker, **filters)
    semantic = dense_search(client, query, k=depth, chunker=chunker, **filters)
    return rrf_fuse([lexical, semantic])[:k]


def hybrid_search(
    client, query, k=10, chunker="section", alpha=0.5, field="text_split", **filters
) -> list[dict]:
    collection = client.collections.get(COLLECTIONS[chunker])
    result = collection.query.hybrid(
        query=_bm25_query(query, field),
        vector=embed_query(query),  # the vector always comes from the original wording
        alpha=alpha,
        query_properties=[field],
        fusion_type=HybridFusion.RELATIVE_SCORE,
        limit=k,
        filters=build_filter(**filters),
        return_metadata=MetadataQuery(score=True),
    )
    return [{**o.properties, "score": o.metadata.score} for o in result.objects]


def search(client, query: str, method: str, k: int = 10, **kwargs) -> list[dict]:
    if method == "dense":
        results = dense_search(client, query, k=k, **kwargs)
        return [{**r, "score": 1 - r["distance"]} for r in results]
    fn = {"bm25": bm25_search, "rrf": rrf_search, "hybrid": hybrid_search}[method]
    return fn(client, query, k=k, **kwargs)
