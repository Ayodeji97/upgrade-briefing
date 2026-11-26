from upgrade_briefing.evaluation.metrics import (
    ranked_entries,
    recall_at_k,
    reciprocal_rank,
    wrong_version_rate,
)
from upgrade_briefing.retrieve.search import rrf_fuse
from upgrade_briefing.text import split_identifiers


def r(entry_id, chunk_id=None, library="room", version_key=0):
    return {"entry_id": entry_id, "chunk_id": chunk_id or entry_id, "library": library, "version_key": version_key}


def test_chunks_collapse_to_unique_entries_in_order():
    results = [r("room@2.7.0", "a"), r("room@2.7.0", "b"), r("room@2.6.0", "c")]
    assert ranked_entries(results) == ["room@2.7.0", "room@2.6.0"]


def test_recall_and_reciprocal_rank():
    entries = ["x", "room@2.7.0", "y", "room@2.7.0-alpha01"]
    relevant = ["room@2.7.0-alpha01", "room@2.7.0"]
    assert recall_at_k(entries, relevant, 2) == 0.5
    assert recall_at_k(entries, relevant, 4) == 1.0
    assert reciprocal_rank(entries, relevant) == 0.5
    assert reciprocal_rank(["x"], relevant) == 0.0


def test_wrong_version_rate_counts_library_and_range():
    results = [
        r("room@2.7.0", version_key=20),  # in range
        r("room@2.5.0", version_key=5),  # too old
        r("work@2.7.0", library="work", version_key=20),  # wrong library
        r("room@2.6.5", version_key=15),  # in range
    ]
    assert wrong_version_rate(results, 4, "room", after_key=10, upto_key=20) == 0.5


def test_rrf_rewards_documents_ranked_well_in_both_lists():
    bm25 = [r("a"), r("b"), r("c")]
    dense = [r("c"), r("a"), r("d")]
    assert [d["chunk_id"] for d in rrf_fuse([bm25, dense])][:2] == ["a", "c"]


def test_split_identifiers():
    assert split_identifiers("RoomDatabase.Builder getRefreshKey()") == "Room Database Builder get Refresh Key()"
    assert split_identifiers("LiveDataReactiveStreams") == "Live Data Reactive Streams"
