from upgrade_briefing.ingest.scrape import parse_releases

# A trimmed copy of the real page structure.
HTML = """
<h2 id="version_27_2">Version 2.7</h2>
<h3 id="2.7.0">Version 2.7.0</h3>
<p>April 9, 2025</p>
<p><code>androidx.room:room-*:2.7.0</code> is released. Version 2.7.0 contains <a href="#">these commits</a>.</p>
<p><strong>API Changes</strong></p>
<ul><li>Removed <code>Foo</code> ( <a href="#">b/123</a> ).</li></ul>
<p><strong>Bug fixes</strong></p>
<ul><li>Fixed a crash.</li><li>Fixed another crash.</li></ul>
<h3 id="2.7.0-rc03">Version 2.7.0-rc03</h3>
<p>March 26, 2025</p>
<p><strong>Bug Fixes</strong></p>
<ul><li>Fixed a leak.</li></ul>
<h3 id="gradle-plugin">Not a release</h3>
"""


def test_parses_each_release_with_its_sections():
    entries = parse_releases(HTML, "room", "androidx.room")
    assert [e.version for e in entries] == ["2.7.0", "2.7.0-rc03"]

    stable = entries[0]
    assert stable.entry_id == "room@2.7.0"
    assert stable.date == "2025-04-09"
    assert stable.url.endswith("/room#2.7.0")
    assert [s.title for s in stable.sections] == ["Summary", "API Changes", "Bug Fixes"]
    assert stable.sections[1].items == ["Removed Foo (b/123)."]
    assert stable.sections[0].items[0].endswith("these commits.")  # no stray space before "."

    assert entries[1].channel == "rc"
    assert entries[1].version_key < stable.version_key
