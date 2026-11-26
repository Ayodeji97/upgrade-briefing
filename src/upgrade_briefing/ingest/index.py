"""Step 3b — chunk, embed and load everything into Weaviate.

Run:  uv run briefing-index

Rebuilds both collections from data/entries.jsonl each time (a few minutes on CPU).
"""

from __future__ import annotations

import time

from weaviate.util import generate_uuid5

from upgrade_briefing.classify.items import LABELS
from upgrade_briefing.classify.run import load_labels
from upgrade_briefing.embed import embed_passages
from upgrade_briefing.ingest.chunk import build_chunks, load_entries, to_dict
from upgrade_briefing.text import split_identifiers
from upgrade_briefing.store import COLLECTIONS, connect, create_collection


def chunk_labels(item_ids: list[str], labels: dict[str, str]) -> list[str]:
    """The set of labels of a chunk's bullets, in LABELS order (e.g. ["breaking", "fix"])."""
    found = {labels[i] for i in item_ids if i in labels}
    return [lab for lab in LABELS if lab in found]


def index_chunks(client, chunker: str, entries: list[dict], labels: dict[str, str]) -> int:
    chunks = build_chunks(entries, chunker)
    t0 = time.time()
    vectors = embed_passages([c.text for c in chunks])
    print(f"  embedded {len(chunks)} {chunker} chunks in {time.time() - t0:.0f}s")

    collection = create_collection(client, COLLECTIONS[chunker])
    with collection.batch.fixed_size(batch_size=200) as batch:
        for chunk, vector in zip(chunks, vectors):
            props = to_dict(chunk)
            props["date"] = props["date"] or ""
            props["text_split"] = split_identifiers(chunk.text)
            props["labels"] = chunk_labels(chunk.item_ids, labels)
            # uuid5 from chunk_id: the same chunk always gets the same id
            batch.add_object(properties=props, vector=vector, uuid=generate_uuid5(chunk.chunk_id))
    if collection.batch.failed_objects:
        raise RuntimeError(f"{len(collection.batch.failed_objects)} objects failed to insert")
    return len(collection)


def main() -> None:
    entries = load_entries()
    labels = load_labels()  # data/labels.jsonl from `briefing-classify` (Step 5)
    if not labels:
        print("  no data/labels.jsonl yet: chunks get empty labels (run briefing-classify first)")
    with connect() as client:
        for chunker, name in COLLECTIONS.items():
            n = index_chunks(client, chunker, entries, labels)
            print(f"{name}: {n} objects")


if __name__ == "__main__":
    main()
