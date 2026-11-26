from upgrade_briefing.ingest.chunk import build_chunks, fixed_chunks, section_chunks

ENTRY = {
    "entry_id": "room@2.7.0-alpha01",
    "library": "room",
    "group": "androidx.room",
    "version": "2.7.0-alpha01",
    "version_key": 2_007_000_101,
    "channel": "alpha",
    "date": "2024-05-01",
    "url": "https://developer.android.com/jetpack/androidx/releases/room#2.7.0-alpha01",
    "sections": [
        {"title": "Summary", "items": ["androidx.room:room-*:2.7.0-alpha01 is released. Version 2.7.0-alpha01 contains these commits."]},
        {"title": "API Changes", "items": [f"Change {i}" for i in range(7)]},
        {"title": "Bug Fixes", "items": ["Fixed a crash."]},
    ],
}


def test_one_chunk_per_section_split_into_groups_of_five():
    chunks = section_chunks(ENTRY)
    # Summary is boilerplate only -> dropped. 7 API changes -> 5 + 2. 1 bug fix.
    assert [(c.section, c.text.count("\n- ")) for c in chunks] == [
        ("API Changes", 5),
        ("API Changes", 2),
        ("Bug Fixes", 1),
    ]


def test_every_chunk_starts_with_library_version_and_section():
    chunk = section_chunks(ENTRY)[-1]
    assert chunk.text.startswith("Room 2.7.0-alpha01 (alpha, 2024-05-01) — Bug Fixes:\n")
    assert chunk.entry_id == "room@2.7.0-alpha01"
    assert chunk.version_key == 2_007_000_101


def test_chunk_ids_are_unique():
    entry = {**ENTRY, "sections": ENTRY["sections"] + [{"title": "Bug Fixes", "items": ["Again."]}]}
    ids = [c.chunk_id for c in build_chunks([entry])]
    assert len(ids) == len(set(ids))


def test_fixed_windows_ignore_structure():
    chunks = fixed_chunks(ENTRY, window=4)
    assert chunks[0].text == "Change 0 Change 1"
    assert all(c.section == "" and c.chunker == "fixed" for c in chunks)
