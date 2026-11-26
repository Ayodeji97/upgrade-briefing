"""Text helpers shared by indexing and querying.

`split_identifiers` exists for BM25 (learning guide Stage 3). Weaviate's `word` tokenizer lowercases
and splits on non-alphanumerics, but it does NOT split camelCase: `RoomDatabase` becomes one token
`roomdatabase`, so a query for "room database" can't match it. We store a second copy of the text
with identifiers pre-split and let BM25 search that copy. The same function must run on the query.
"""

from __future__ import annotations

import re

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def split_identifiers(text: str) -> str:
    """'RoomDatabase.Builder getRefreshKey()' -> 'Room Database Builder get Refresh Key()'"""
    text = _CAMEL.sub(" ", text)
    return re.sub(r"[._]", " ", text)
