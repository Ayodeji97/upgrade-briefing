"""Embeddings with BAAI/bge-base-en-v1.5 (768 dims), computed here in Python.

Why compute vectors ourselves instead of letting Weaviate do it? The course used a Flask
vectorizer on port 5000, which macOS AirPlay Receiver blocks. Computing vectors in Python and
inserting them with the objects (vectorizer "none") needs no extra server.

bge was trained so that *queries* (not passages) get a short instruction prefix. Passages are
embedded as-is. Vectors are L2-normalised, so cosine similarity = dot product.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

MODEL_NAME = "BAAI/bge-base-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def get_model():
    load_dotenv()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")  # models are cached: never download again
    from sentence_transformers import SentenceTransformer  # slow import, so do it lazily

    return SentenceTransformer(MODEL_NAME, cache_folder=os.environ["MODEL_PATH"], device="cpu")


def embed_passages(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    vectors = get_model().encode(
        texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=len(texts) > 100
    )
    return vectors.tolist()


def embed_query(query: str, prefix: bool = True) -> list[float]:
    text = QUERY_PREFIX + query if prefix else query
    return get_model().encode(text, normalize_embeddings=True).tolist()
