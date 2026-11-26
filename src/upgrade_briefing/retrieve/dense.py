"""Dense (semantic) search: embed the query, return the nearest chunks by cosine distance.

Optional metadata filters narrow the search *before* ranking:
  library="room", after_key=<version_key of 2.6.1>, upto_key=<version_key of 2.7.0>
That is the version filter from learning guide Stage 5; Step 4 measures what it adds.
"""

from __future__ import annotations

from weaviate.classes.query import Filter, MetadataQuery

from upgrade_briefing.embed import embed_query
from upgrade_briefing.store import COLLECTIONS


def build_filter(
    library: str | None = None,
    after_key: int | None = None,
    upto_key: int | None = None,
    labels: list[str] | None = None,  # Step 5: keep chunks holding at least one of these labels
):
    parts = []
    if labels:
        parts.append(Filter.by_property("labels").contains_any(labels))
    if library:
        parts.append(Filter.by_property("library").equal(library))
    if after_key is not None:
        parts.append(Filter.by_property("version_key").greater_than(after_key))
    if upto_key is not None:
        parts.append(Filter.by_property("version_key").less_or_equal(upto_key))
    return Filter.all_of(parts) if parts else None


def dense_search(
    client,
    query: str,
    k: int = 5,
    chunker: str = "section",
    prefix: bool = True,
    **filters,
) -> list[dict]:
    collection = client.collections.get(COLLECTIONS[chunker])
    result = collection.query.near_vector(
        near_vector=embed_query(query, prefix=prefix),
        limit=k,
        filters=build_filter(**filters),
        return_metadata=MetadataQuery(distance=True),
    )
    return [{**o.properties, "distance": o.metadata.distance} for o in result.objects]
