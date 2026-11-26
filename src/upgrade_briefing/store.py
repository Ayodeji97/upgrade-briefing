"""Embedded Weaviate: the vector DB runs as a child process, data lives in data/weaviate/.

Two collections, one per chunker (see ingest/chunk.py), so Step 4 can compare them:
  ReleaseNote       — section chunks (the main one)
  ReleaseNoteFixed  — fixed-size word windows (baseline)

Vectors come from embed.py (vectorizer "none"). The metadata fields are what make version
filtering possible: `library` and `version_key` let us ask for "room, 2.6.1 < version <= 2.7.0".
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import weaviate
from weaviate.classes.config import Configure, DataType, Property, Tokenization

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "weaviate"
WEAVIATE_VERSION = "1.40.2"  # already downloaded by the course: no new download

COLLECTIONS = {"section": "ReleaseNote", "fixed": "ReleaseNoteFixed"}


@contextmanager
def connect():
    client = weaviate.connect_to_embedded(
        persistence_data_path=str(DATA_PATH),
        version=WEAVIATE_VERSION,
        environment_variables={
            # The Mac's disk is ~95% full. Weaviate's default (90%) would make the DB read-only.
            "DISK_USE_READONLY_PERCENTAGE": "99",
            "DISK_USE_WARNING_PERCENTAGE": "99",
            "LOG_LEVEL": "error",
        },
    )
    try:
        yield client
    finally:
        client.close()


def _keyword(name: str) -> Property:
    """Exact-match field for filtering (no word splitting, not part of BM25)."""
    return Property(
        name=name, data_type=DataType.TEXT, tokenization=Tokenization.FIELD, index_searchable=False
    )


def create_collection(client, name: str):
    if client.collections.exists(name):
        client.collections.delete(name)
    return client.collections.create(
        name,
        vector_config=Configure.Vectors.self_provided(),  # we bring our own vectors
        properties=[
            Property(name="text", data_type=DataType.TEXT),  # searched by BM25 (Step 4)
            # same text with camelCase/dots split (text.split_identifiers), a second BM25 field
            Property(name="text_split", data_type=DataType.TEXT),
            Property(name="section", data_type=DataType.TEXT),
            _keyword("chunk_id"),
            _keyword("entry_id"),
            _keyword("library"),
            _keyword("version"),
            Property(name="version_key", data_type=DataType.INT),
            _keyword("channel"),
            _keyword("date"),
            _keyword("url"),
            _keyword("chunker"),
        ],
    )
