from upgrade_briefing.classify.items import Item, iter_items
from upgrade_briefing.classify.rules import classify
from upgrade_briefing.evaluation.classify import per_label, score
from upgrade_briefing.ingest.chunk import build_chunks
from upgrade_briefing.ingest.index import chunk_labels

from test_chunk import ENTRY


def test_item_ids_match_chunk_item_ids():
    # the join between labels (per bullet) and chunks must line up exactly
    items = {it.item_id for it in iter_items([ENTRY])}
    chunk_items = {i for c in build_chunks([ENTRY]) for i in c.item_ids}
    assert items == chunk_items


def test_rules_trust_text_over_section_title():
    assert classify("Fixed a bug where deprecated methods were not suppressed.", "Bug Fixes") == ("fix", True)
    assert classify("Deprecated setProgress() in RxWorker.", "Bug Fixes") == ("deprecated", True)
    assert classify("Update the minSDK from API 21 to API 23", "API Changes") == ("breaking", True)
    # no keyword: fall back to the section title, and say it is a guess
    assert classify("NavHost uses Crossfades between destinations.", "Behavior Changes") == ("breaking", False)


def test_chunk_labels_is_an_ordered_set():
    labels = {"a#0.0": "fix", "a#0.1": "breaking", "a#0.2": "fix"}
    assert chunk_labels(["a#0.0", "a#0.1", "a#0.2", "missing"], labels) == ["breaking", "fix"]


def test_scores():
    gold = ["breaking", "breaking", "fix", "new"]
    pred = ["breaking", "fix", "fix", "new"]
    pl = per_label(gold, pred)
    assert pl["breaking"]["recall"] == 0.5 and pl["breaking"]["precision"] == 1.0
    assert pl["fix"]["precision"] == 0.5
    s = score(gold, pred)
    assert s["accuracy"] == 0.75
    # labels absent from gold (deprecated, other) are left out of macro-F1
    assert abs(s["macro_f1"] - (2 / 3 + 2 / 3 + 1.0) / 3) < 1e-9
