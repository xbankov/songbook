"""Ultimate Guitar import (#132): chords merged into lyrics, sections, capo.

Fixtures are real UG pages of public-domain songs, trimmed to the fields the
importer reads. No test touches the network.
"""

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import requests
from app.database import get_db
from app.main import app
from app.models.song import Song
from app.services import ultimate_guitar
from app.services.auth import create_access_token
from app.services.scraper import SongImportError, detect_source, import_from_url
from app.services.ultimate_guitar import (
    UltimateGuitarError,
    chord_only_line,
    merge_chord_line,
    parse_content,
    parse_search_html,
    parse_tab_html,
)
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def _page(content: str, meta: dict | None = None) -> str:
    data = {
        "store": {
            "page": {
                "data": {
                    "tab": {"song_name": "Song", "artist_name": "Artist"},
                    "tab_view": {"meta": meta or {}, "wiki_tab": {"content": content}},
                }
            }
        }
    }
    payload = html.escape(json.dumps(data), quote=True)
    return f'<div class="js-store" data-content="{payload}"></div>'


def _body(content: str) -> str:
    return "\n\n".join(str(section) for section in parse_content(content))


# --- chord lines -------------------------------------------------------------


def test_chord_line_merges_into_the_lyric_at_its_columns():
    chords = " [ch]G[/ch]      [ch]G7[/ch]         [ch]C[/ch]         [ch]G[/ch]"
    lyric = "Amazing Grace, how sweet the sound"

    assert merge_chord_line(chords, lyric) == (
        "A[G]mazing [G7]Grace, how [C]sweet the [G]sound"
    )


def test_chord_past_the_end_of_the_lyric_is_kept():
    assert merge_chord_line("[ch]D[/ch]        [ch]A[/ch]", "Oh") == "[D]Oh       [A]"


def test_line_with_an_unparsable_chord_is_kept_whole():
    # Merging would lose "N.C."; keep the chord line and the lyric instead.
    assert _body("[ch]N.C.[/ch]   [ch]G[/ch]\nStop and go") == "N.C.   [G]\nStop and go"


def test_trailing_mark_on_a_chord_line_still_merges():
    body = _body("     [ch]A[/ch]   [ch]D[/ch] *\nI've seen trouble")
    assert body == "I've [A]seen[D] trouble  *"


def test_unmerged_chord_line_keeps_its_indent():
    assert _body("    [ch]G[/ch]  [ch]C[/ch] | x2") == "    [G]  [C] | x2"


def test_tabs_and_decomposed_accents_do_not_shift_chords():
    assert _body("\t[ch]G[/ch]\nHello world wide") == "Hello wo[G]rld wide"
    # "Za" + combining acute is one character after NFC normalisation.
    assert _body("       [ch]G[/ch]\nZa\u0301hrada je") == "Záhrada[G] je"


def test_brackets_in_lyrics_do_not_become_chords():
    assert merge_chord_line("[ch]G[/ch]", "Hello [whisper]") == "[G]Hello (whisper)"
    assert _body("Spoken [quietly] here") == "Spoken (quietly) here"


def test_chord_only_line_keeps_bars_and_unknown_chords_as_text():
    line = "| [ch]D[/ch]   | [ch]N.C.[/ch]   |"
    assert chord_only_line(line) == "| [D]   | N.C.   |"
    # A bracketed "chord" must not turn back into ChordPro chord syntax.
    assert chord_only_line("[ch][x][/ch] [ch]G[/ch]") == "(x) [G]"


def test_chord_line_with_a_trailing_mark_merges_but_bars_do_not():
    # A trailing mark is moved behind the lyric; bars between chords are not.
    assert _body("[ch]G[/ch]  [ch]C[/ch]  (x2)\nSing along") == (
        "[G]Sin[C]g along  (x2)"
    )
    assert _body("| [ch]D[/ch] | [ch]G[/ch] |\nSing along") == (
        "| [D] | [G] |\nSing along"
    )


def test_chord_line_before_a_blank_line_stays_a_chord_line():
    assert _body("[ch]Am[/ch]  [ch]E[/ch]\n\nWords") == "[Am]  [E]\nWords"


def test_chord_line_is_not_merged_into_a_tab_staff():
    body = _body("    [ch]G7[/ch]\ne|-----|\nB|--3--|")
    assert body == "    [G7]\ne|-----|\nB|--3--|"


# --- sections ----------------------------------------------------------------


@pytest.mark.parametrize(
    "header, label, title",
    [
        ("Chorus", "chorus", None),
        ("Refrain", "chorus", "Refrain"),
        ("Chorus 2", "chorus", "Chorus 2"),
        ("Verse", "verse", None),
        ("Verse 1", "verse", "Verse 1"),
        ("Bridge", "bridge", None),
        ("Intro", "verse", "Intro"),
        ("Pre-Chorus", "verse", "Pre-Chorus"),
        ("Refrén", "chorus", "Refrén"),
        ("R:", "chorus", "R:"),
        ("R2", "chorus", "R2"),
        ("Sloka 1", "verse", "Sloka 1"),
    ],
)
def test_section_headers_map_to_chordpro_sections(header, label, title):
    (section,) = parse_content(f"[{header}]\n[ch]G[/ch]\nla la")
    assert (section.label, section.title) == (label, title)


def test_bare_header_is_kept_as_a_repeat_cue():
    body = _body("[Verse 1]\nla\n\n[Chorus]\n\n[Verse 2]\nlo\n[Chorus]")
    assert body == (
        "{start_of_verse: Verse 1}\nla\n{end_of_verse}\n\n(Chorus)\n\n"
        "{start_of_verse: Verse 2}\nlo\n{end_of_verse}\n\n(Chorus)"
    )


def test_bracketed_line_that_is_not_a_section_is_text():
    assert _body("[Verse]\nla\n[x2]") == ("{start_of_verse}\nla\n(x2)\n{end_of_verse}")


def test_text_before_the_first_header_has_no_section():
    sections = parse_content("Capo III\n[Verse]\nla")
    assert [s.label for s in sections] == [None, "verse"]


# --- whole pages (real fixtures) ---------------------------------------------


def test_amazing_grace_page():
    song = parse_tab_html(_fixture("ug_amazing_grace_chords.html"))
    body = str(song)

    assert (song.title, song.artist, song.capo, song.key) == (
        "Amazing Grace",
        "Misc Praise Songs",
        0,
        "G",
    )
    assert "{start_of_chorus: Refrain}" in body
    assert "{start_of_verse: Verse 1}" in body
    assert "A[G]mazing [G7]Grace, how [C]sweet the [G]sound" in body
    assert "That saved a [A]wretch like [D]me!" in body
    # The chord diagram at the top stays a chord line above its tab staff.
    assert "[G7]\ne|-----|" in body


def test_capo_and_key_come_from_the_tab_metadata():
    song = parse_tab_html(_fixture("ug_constant_sorrow_capo_chords.html"))

    assert song.capo == 3
    assert song.key == "F"
    assert "[D]I Am A Man Of Constant [G]Sorrow" in str(song)
    # This chord line ends in "*": it still merges, and the mark is kept.
    assert "I've seen [A]trouble all my [D]day.  *" in str(song)


def test_intro_bars_and_parenthesised_lines_are_kept():
    # Regression: lines starting with "(" used to be dropped.
    body = str(parse_tab_html(_fixture("ug_constant_sorrow_chords.html")))

    assert "{start_of_verse: Intro}\n| [D]   | [D]   | [D]   | [D]   |" in body
    assert "(In constant [A]sorrow all through his [D]days)" in body
    assert "[D]I am a [D7]man of constant [G]sorrow" in body


@pytest.mark.parametrize("capo", [None, "", "x", -1, 40, float("inf")])
def test_missing_or_bad_capo_is_zero(capo):
    song = parse_tab_html(_page("[ch]G[/ch]\nla", {"capo": capo}))
    assert song.capo == 0


def test_page_without_store_is_an_error():
    with pytest.raises(UltimateGuitarError, match="no Ultimate Guitar song data"):
        parse_tab_html("<html><body>Not found</body></html>")


def _raw(data) -> str:
    payload = html.escape(json.dumps({"store": {"page": {"data": data}}}), quote=True)
    return f'<div class="js-store" data-content="{payload}"></div>'


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        {"tab_view": None},
        {"tab_view": {"wiki_tab": {"content": 5}}},
        {"tab_view": {"wiki_tab": None}},
    ],
)
def test_malformed_tab_page_is_a_clean_error(data):
    with pytest.raises(UltimateGuitarError):
        parse_tab_html(_raw(data))


def test_odd_metadata_values_do_not_crash():
    data = {
        "tab": {"song_name": 5, "artist_name": None, "tonality_name": 7},
        "tab_view": {
            "versions": [None],
            "meta": {"capo": "2", "tonality": ["G"]},
            "wiki_tab": {"content": "[ch]G[/ch]\nla"},
        },
    }
    song = parse_tab_html(_raw(data))
    assert (song.title, song.artist, song.capo, song.key) == (
        "Unknown",
        "Unknown",
        2,
        None,
    )


@pytest.mark.parametrize("data", [None, []])
def test_search_page_without_data_is_a_clean_error(data):
    with pytest.raises(UltimateGuitarError):
        parse_search_html(_raw(data))


@pytest.mark.parametrize(
    "results",
    [None, 5, [None, 5, {"tab_url": 3}, {"type": [], "tab_url": "x"}]],
)
def test_malformed_search_results_are_skipped(results):
    assert parse_search_html(_raw({"results": results})) == []


# Regressions for #51, moved from test_music_theory.py.


def test_tab_wrapped_lines_are_not_dropped():
    content = (
        "[tab][ch]Am[/ch]\r\n"
        "Start wearing purple, wearing purple[/tab]\r\n"
        "[tab]                            [ch]E7[/ch]\r\n"
        "Start wearing purple for me now[/tab]"
    )
    body = _body(content)
    assert "[Am]Start wearing purple, wearing purple" in body
    assert "Start wearing purple for me [E7]now" in body


def test_lyric_line_without_chords_is_kept():
    content = (
        "[tab]     [ch]Em[/ch]\r\n"
        "Ya - soldat,\r\n"
        "Ya ne spal pyat' let\r\n"
        "    [ch]Am7[/ch]                [ch]Em[/ch]\r\n"
        "i u menya pod glazami meshki[/tab]"
    )
    body = _body(content)
    assert "Ya ne spal pyat' let" in body
    assert "i u [Am7]menya pod glazami m[Em]eshki" in body


# --- search --------------------------------------------------------------------


def test_search_lists_only_importable_tabs():
    results = parse_search_html(_fixture("ug_search_amazing_grace.html"))

    assert [r["type"] for r in results] == ["Chords", "Tabs"]
    assert all("/pro/" not in r["url"] for r in results)
    assert results[0] == {
        "title": "Amazing Grace",
        "artist": "Misc Praise Songs",
        "url": "https://tabs.ultimate-guitar.com/tab/misc-praise-songs/amazing-grace-chords-66733",
        "source": "ultimate-guitar",
        "type": "Chords",
        "rating": 4.80747,
        "votes": 2379,
    }


def test_search_endpoint_uses_the_shared_fetch(monkeypatch):
    requested = []

    def fake_fetch(url):
        requested.append(url)
        return _fixture("ug_search_amazing_grace.html")

    monkeypatch.setattr(ultimate_guitar, "fetch", fake_fetch)
    response = TestClient(app).get(
        "/api/search",
        params={"q": "amazing grace"},
        headers={"Authorization": f"Bearer {create_access_token()}"},
    )

    assert response.status_code == 200
    assert len(response.json()["results"]) == 2
    assert requested == [
        "https://www.ultimate-guitar.com/search.php"
        "?search_type=title&value=amazing%20grace"
    ]


def test_search_endpoint_returns_nothing_when_ug_fails(monkeypatch):
    def fail(url):
        raise UltimateGuitarError("down")

    monkeypatch.setattr(ultimate_guitar, "fetch", fail)
    response = TestClient(app).get(
        "/api/search",
        params={"q": "amazing grace"},
        headers={"Authorization": f"Bearer {create_access_token()}"},
    )

    assert response.status_code == 200
    assert response.json()["results"] == []


# --- fetching ----------------------------------------------------------------


class _Response:
    def __init__(self, status_code=200, text="<html></html>"):
        self.status_code = status_code
        self.text = text


@pytest.fixture
def fake_clock(monkeypatch):
    """A clock that only advances when the fetcher sleeps."""
    clock = {"now": 1000.0, "slept": []}

    def sleep(seconds):
        clock["slept"].append(seconds)
        clock["now"] += seconds

    monkeypatch.setattr(ultimate_guitar.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(ultimate_guitar.time, "sleep", sleep)
    monkeypatch.setattr(ultimate_guitar, "_last_request", 0.0)
    return clock


def test_fetch_identifies_itself_with_a_timeout_and_spaces_requests(
    monkeypatch, fake_clock
):
    calls = []

    def get(url, timeout, headers):
        calls.append((url, timeout, headers))
        return _Response()

    monkeypatch.setattr(ultimate_guitar.requests, "get", get)

    ultimate_guitar.fetch("https://www.ultimate-guitar.com/a")
    ultimate_guitar.fetch("https://www.ultimate-guitar.com/b")

    assert [call[1] for call in calls] == [(5, 20), (5, 20)]
    assert all(
        call[2]["User-Agent"].startswith("Songbook/") for call in calls
    ), "identifying User-Agent"
    assert fake_clock["slept"] == [ultimate_guitar.MIN_INTERVAL_SECONDS]


def test_fetch_waits_after_a_failed_request_too(monkeypatch, fake_clock):
    def fail(url, timeout, headers):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(ultimate_guitar.requests, "get", fail)
    for _ in range(2):
        with pytest.raises(UltimateGuitarError, match="Could not reach"):
            ultimate_guitar.fetch("https://www.ultimate-guitar.com/a")

    assert fake_clock["slept"] == [ultimate_guitar.MIN_INTERVAL_SECONDS]


def test_fetch_reports_http_errors(monkeypatch, fake_clock):
    monkeypatch.setattr(
        ultimate_guitar.requests, "get", lambda url, **kwargs: _Response(404)
    )
    with pytest.raises(UltimateGuitarError, match="HTTP 404"):
        ultimate_guitar.fetch("https://www.ultimate-guitar.com/a")


@pytest.mark.parametrize(
    "url, source",
    [
        ("https://tabs.ultimate-guitar.com/tab/a/b-chords-1", "ultimate-guitar"),
        ("https://ultimate-guitar.com/tab/a", "ultimate-guitar"),
        ("http://127.0.0.1/?ultimate-guitar", "unknown"),
        ("https://ultimate-guitar.com.evil.example/tab", "unknown"),
        ("https://www.supermusic.cz/piesen.php?id=1", "supermusic"),
        ("https://supermusic.sk/piesen.php?id=1", "supermusic"),
        ("https://example.com/supermusic", "unknown"),
    ],
)
def test_source_is_detected_from_the_host_only(url, source):
    assert detect_source(url) == source


def test_import_never_fetches_a_url_that_only_mentions_ug(monkeypatch):
    monkeypatch.setattr(ultimate_guitar, "fetch", pytest.fail)
    with pytest.raises(SongImportError, match="Unsupported site"):
        import_from_url("http://127.0.0.1/?ultimate-guitar")


# --- saving ----------------------------------------------------------------


class _Session:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def refresh(self, obj):
        now = datetime.now(timezone.utc)
        for name, value in [
            ("id", uuid4()),
            ("version", 1),
            ("created_at", now),
            ("updated_at", now),
        ]:
            if getattr(obj, name, None) is None:
                setattr(obj, name, value)
        if isinstance(obj, Song):
            obj.tags = []


def test_import_saves_capo_key_sections_and_source(monkeypatch):
    url = "https://tabs.ultimate-guitar.com/tab/x/y-chords-1113648"
    monkeypatch.setattr(
        ultimate_guitar,
        "fetch",
        lambda requested: _fixture("ug_constant_sorrow_capo_chords.html"),
    )
    session = _Session()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).post(
            "/api/songs/import",
            params={"url": url},
            headers={"Authorization": f"Bearer {create_access_token()}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    song = response.json()
    assert (song["capo"], song["key"]) == (3, "F")
    assert song["metadata"] == {"imported_from": url}
    assert "{start_of_verse: Verse 1}" in song["body"]
    assert "[D]I Am A Man Of Constant [G]Sorrow" in song["body"]
