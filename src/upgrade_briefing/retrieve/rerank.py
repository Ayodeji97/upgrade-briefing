"""Second stage: rerank candidates with a cross-encoder (learning guide Stage 6).

bge (the bi-encoder) embeds the question and each chunk separately, which is fast but approximate.
bge-reranker-base reads the question and the chunk *together* and scores the pair. It is much more
precise, and much slower, so it only sees the top `depth` candidates from the first stage.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

RERANKER_NAME = "BAAI/bge-reranker-base"


@lru_cache(maxsize=1)
def get_reranker():
    load_dotenv()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from sentence_transformers import CrossEncoder

    return CrossEncoder(RERANKER_NAME, cache_folder=os.environ["MODEL_PATH"], device="cpu")


def rerank(query: str, candidates: list[dict], k: int = 10) -> list[dict]:
    if not candidates:
        return []
    scores = get_reranker().predict([(query, c["text"]) for c in candidates], batch_size=16)
    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
    # rerank_score is 0..1 (sentence-transformers applies a sigmoid). Step 4 showed it can NOT
    # separate unanswerable questions from real ones, so refusal has to happen at generation.
    return [{**c, "rerank_score": float(s)} for c, s in ranked[:k]]
