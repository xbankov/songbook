"""Ultimate Guitar search and import (#132).

One fetch path for UG: an identifying User-Agent, a timeout, and at most one
request every few seconds. Pages are parsed from the ``js-store`` JSON the
site embeds; chord lines above lyric lines are merged into inline ChordPro.
"""

import json
import logging
import math
import re
import threading
import time
import unicodedata
from typing import Any
from urllib.parse import quote, urlparse

import requests
from app.services.music_theory import Chord, Line, Section, SongModel
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "Songbook/1.0 (self-hosted chord sheet importer)"
# (connect, read) seconds. The read timeout is per read, so a very slow server
# can hold the fetch lock longer; fine for a single-user instance.
TIMEOUT_SECONDS = (5, 20)
MIN_INTERVAL_SECONDS = 3.0
SEARCH_URL = "https://www.ultimate-guitar.com/search.php"
SEARCH_LIMIT = 10
# Types whose page carries the song text; Official/Pro tabs need the app.
IMPORTABLE_TYPES = {"Chords", "Tabs", "Ukulele Chords"}

_CHORD = re.compile(r"\[ch\](.*?)\[/ch\]")
# A tablature staff line such as "e|--3--|" or "G|-4-5h7-|".
_STAFF = re.compile(r"\s*[A-Ga-g][#b]?\s*\|[-\w|/\\~*.() ]*")
_HEADER = re.compile(r"\[([A-Za-z][^\[\]]*)\]")
# Page chrome at the top of a UG tab; the capo comes from the metadata.
_URL = re.compile(r"(?i)^\s*(?:https?://|www\.)\S+\s*$")
_CAPO_TEXT = re.compile(r"(?i)^\s*capo\s*(?:[:=]?\s*(?:\d{1,2}|[ivxlcdm]+))?\s*\**\s*$")
# A footnote that starts a trailing notes/alternate-chord block. Require a
# column-0 marker and whitespace so a lyric such as "*When the morning comes"
# is not mistaken for a note.
_NOTES = re.compile(r"^\*{1,3}\s+\S")
# A header artist line often carries a year or a trailing footnote.
_ARTIST_CREDIT = re.compile(r"(?i)(?:\b(?:19|20)\d{2}\b|\*+\s*$)")
# The first line of a tab header, e.g. "Song Title chords".
_TITLE_LIKE = re.compile(r"(?i)^.+\s+(?:chords?|tabs?)\s*\**\s*$")
# Markers such as "*" or "x2" that may sit after a chord; "(x2)" is a repeat
# annotation, not a marker, so it is kept.
_CHORD_MARK = re.compile(r"(?i)\*+|\b(?<!\()x\d+(?!\))\b|\b\d+x\b")
# Words that start a section header; other bracketed lines ("[x2]") are text.
_SECTION_WORDS = (
    "verse",
    "chorus",
    "refrain",
    "bridge",
    "intro",
    "outro",
    "solo",
    "instrumental",
    "interlude",
    "pre-chorus",
    "pre chorus",
    "prechorus",
    "post-chorus",
    "coda",
    "hook",
    "break",
    "ending",
    "riff",
    "tag",
    # Czech/Slovak: refrén = chorus, sloka/strofa = verse.
    "ref",
    "sloka",
    "strofa",
)
_CHORUS_WORDS = ("chorus", "refrain", "ref")
# "[R]", "[R:]", "[R2:]": the usual Czech/Slovak chorus marker.
_CHORUS_MARK = re.compile(r"(?i)r\d*:?")
# What may sit on a chord line besides chords: bars, dashes, repeat marks.
_CHORD_LINE_EXTRAS = re.compile(r"(?i)[\s|/\\\-.,()*:~]|\bx\d+\b|\b\d+x\b")

_fetch_lock = threading.Lock()
_last_request = 0.0


class UltimateGuitarError(Exception):
    """A UG page could not be fetched or read; the message is for the user."""


def is_ultimate_guitar_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "ultimate-guitar.com" or host.endswith(".ultimate-guitar.com")


def fetch(url: str) -> str:
    """GET a UG page politely: serialised, spaced out, identifying, with a timeout."""
    global _last_request
    with _fetch_lock:
        wait = _last_request + MIN_INTERVAL_SECONDS - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            response = requests.get(
                url, timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}
            )
        except requests.RequestException as e:
            logger.error(f"Ultimate Guitar request failed: {url}: {e}")
            raise UltimateGuitarError("Could not reach Ultimate Guitar.") from e
        finally:
            _last_request = time.monotonic()
    if response.status_code != 200:
        logger.error(f"Ultimate Guitar returned {response.status_code} for {url}")
        raise UltimateGuitarError(
            f"Ultimate Guitar answered with HTTP {response.status_code}."
        )
    return response.text


def _page_data(html: str) -> dict[str, Any]:
    store = BeautifulSoup(html, "lxml").find("div", {"class": "js-store"})
    if store is None or not store.get("data-content"):
        raise UltimateGuitarError("That page has no Ultimate Guitar song data.")
    try:
        data = json.loads(store["data-content"])["store"]["page"]["data"]
    except (ValueError, KeyError, TypeError) as e:
        raise UltimateGuitarError("Could not read the Ultimate Guitar page.") from e
    if not isinstance(data, dict):
        raise UltimateGuitarError("Could not read the Ultimate Guitar page.")
    return data


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(*values: Any) -> str:
    """The first non-empty string among ``values``, else "Unknown"."""
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Unknown"


# --- search -----------------------------------------------------------------


def _optional_text(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        return text or None
    return None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _number(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return value == 1


def _best_score(result: dict[str, Any]) -> float:
    """Rating weighted by votes so a 4.9 with 53 votes does not beat 4.78/1171."""
    rating = result["rating"]
    if not rating:
        return 0.0
    return rating * math.log10(max(0, result["votes"]) + 10)


def parse_search_html(html: str) -> list[dict[str, Any]]:
    """Importable search rows, best first.

    The search page carries version, rating, key and difficulty for each tab;
    keep them so the UI can tell ten rows with the same title apart (#161).
    Identical URLs are listed once, but different versions are never collapsed.
    """
    results = []
    seen_urls: set[str] = set()
    found = _page_data(html).get("results")
    for tab in found if isinstance(found, list) else []:
        if not isinstance(tab, dict):
            continue
        url = tab.get("tab_url") or ""
        if not isinstance(url, str) or url in seen_urls:
            continue
        kind = tab.get("type")
        if not isinstance(kind, str) or kind not in IMPORTABLE_TYPES:
            continue
        if not is_ultimate_guitar_url(url):
            continue
        if urlparse(url).path.startswith("/pro"):
            continue
        seen_urls.add(url)
        results.append(
            {
                "title": _text(tab.get("song_name")),
                "artist": _text(tab.get("artist_name")),
                "url": url,
                "source": "ultimate-guitar",
                "type": kind,
                "type_label": _optional_text(tab.get("typeLabel")) or kind,
                "rating": _number(tab.get("rating")),
                "votes": max(0, int(_number(tab.get("votes")))),
                "version": _optional_int(tab.get("version")),
                "version_count": _optional_int(tab.get("tp_version")),
                "version_description": _optional_text(tab.get("version_description")),
                "key": _optional_text(tab.get("tonality_name")),
                "difficulty": _optional_text(
                    tab.get("difficulty") or tab.get("ug_difficulty")
                ),
                "updated": _optional_text(tab.get("date_update") or tab.get("date")),
                "verified": _flag(tab.get("verified")),
            }
        )
    # Sort every candidate before applying the UI limit, so a better later
    # row is not discarded unseen.
    results.sort(key=_best_score, reverse=True)
    return results[:SEARCH_LIMIT]


def search(query: str) -> list[dict[str, Any]]:
    url = f"{SEARCH_URL}?search_type=title&value={quote(query)}"
    return parse_search_html(fetch(url))


# --- tab page ---------------------------------------------------------------


def _valid_chord(name: str) -> bool:
    try:
        Chord.parse(name)
    except (KeyError, IndexError, ValueError):
        return False
    return True


def _is_chord_line(line: str) -> bool:
    if not _CHORD.search(line):
        return False
    return not _CHORD_LINE_EXTRAS.sub("", _CHORD.sub("", line))


def _chord_columns(line: str) -> list[tuple[int, str]]:
    """Each chord's column in the line as displayed (markup removed, tabs expanded)."""
    columns = []
    shown = ""
    position = 0
    for match in _CHORD.finditer(line):
        shown = (shown + line[position : match.start()]).expandtabs()
        columns.append((len(shown), match.group(1).strip()))
        shown += match.group(1)
        position = match.end()
    return columns


def _plain(text: str) -> str:
    """Lyric text with brackets that ChordPro would read as chords neutralised."""
    return text.replace("[", "(").replace("]", ")")


def _inline(name: str) -> str:
    # A chord we cannot parse ("N.C.") would break the song model; keep it
    # visible as text instead.
    return f"[{name}]" if _valid_chord(name) else _plain(name)


def _strip_chord_marks(line: str) -> str:
    """Remove "*"/"x2" markers outside the chord tags of a chord line."""
    parts = _CHORD.split(line)
    return "".join(
        f"[ch]{part}[/ch]" if index % 2 else _CHORD_MARK.sub("", part)
        for index, part in enumerate(parts)
    )


def merge_chord_line(chords: str, lyrics: str) -> str:
    """Put the chords of ``chords`` into ``lyrics`` at the same columns."""
    chords = _strip_chord_marks(chords)
    merged = _plain(lyrics.expandtabs())
    for column, name in reversed(_chord_columns(chords)):
        merged = merged.ljust(column)
        merged = f"{merged[:column]}[{name}]{merged[column:]}"
    annotation = _CHORD.split(chords)[-1].strip()
    if annotation:
        merged = f"{merged.rstrip()}  {_plain(annotation)}"
    return merged.rstrip()


def _mergeable(chords: str) -> bool:
    """Bare chords, optionally followed by a mark such as "*" or "x2".

    Bars between chords have no place inside a lyric, and a chord the model
    cannot parse ("N.C.") would be lost, so such lines stay as they are.
    """
    parts = _CHORD.split(_strip_chord_marks(chords))
    texts, names = parts[0:-1:2], parts[1::2]
    return all(not text.strip() for text in texts) and all(
        _valid_chord(name.strip()) for name in names
    )


def chord_only_line(line: str, keep_indent: bool = False) -> str:
    """Convert a line in place: ``[ch]X[/ch]`` becomes ``[X]``, the rest is text."""
    parts = _CHORD.split(line)
    # re.split with one group alternates text, chord, text, ...
    converted = "".join(
        _inline(part.strip()) if index % 2 else _plain(part)
        for index, part in enumerate(parts)
    )
    return converted.rstrip() if keep_indent else converted.strip()


def _section_for(header: str) -> tuple[str, str | None]:
    lowered = header.lower()
    if lowered.startswith(_CHORUS_WORDS) or _CHORUS_MARK.fullmatch(lowered):
        label = "chorus"
    elif lowered.startswith("bridge"):
        label = "bridge"
    else:
        label = "verse"
    return label, None if lowered == label else header


def _is_lyric(line: str) -> bool:
    """A line a chord line above it can be merged into."""
    return bool(
        line.strip()
        and not _CHORD.search(line)
        and _header(line) is None
        and not _STAFF.fullmatch(line)
    )


def _header(line: str) -> str | None:
    match = _HEADER.fullmatch(line.strip())
    if not match or "[ch]" in line:
        return None
    header = match.group(1).strip()
    lowered = header.lower()
    if lowered.startswith(_SECTION_WORDS) or _CHORUS_MARK.fullmatch(lowered):
        return header
    return None


def _matches_name(line: str, name: str | None, extra_ok: bool = False) -> bool:
    """Whether a header line names the tab's title or artist."""
    if not name or name == "Unknown":
        return False
    line = " ".join(line.split()).casefold()
    wanted = " ".join(name.split()).casefold()
    if line == wanted:
        return True
    if extra_ok:
        # UG artist lines often add a year, album or footnote.
        return line.startswith(f"{wanted} ")
    return line in (
        f"{wanted} chord",
        f"{wanted} chords",
        f"{wanted} tab",
        f"{wanted} tabs",
    )


def _drop_leading_header(
    lines: list[str], title: str | None, artist: str | None
) -> list[str]:
    """Drop the title, artist, URL and textual capo before the first real line."""
    index = 0
    artist_expected = False
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            artist_expected = False
            index += 1
            continue
        if _URL.fullmatch(line) or _CAPO_TEXT.fullmatch(line):
            artist_expected = False
            index += 1
            continue
        if _matches_name(line, title) or (
            title and title != "Unknown" and _TITLE_LIKE.fullmatch(line)
        ):
            # UG's header title is not always the same as the tab metadata.
            artist_expected = True
            index += 1
            continue
        if _matches_name(line, artist, extra_ok=True):
            artist_expected = False
            index += 1
            continue
        if artist_expected and _ARTIST_CREDIT.search(line):
            following = next(
                (item.strip() for item in lines[index + 1 :] if item.strip()), ""
            )
            # Only a header artist is followed by page chrome or a section.
            # A lyric with a year ("I was born (1984)") is followed by another
            # lyric or a chord line, so it stays.
            if (
                not following
                or _URL.fullmatch(following)
                or _CAPO_TEXT.fullmatch(following)
                or _header(following) is not None
            ):
                artist_expected = False
                index += 1
                continue
        break
    return lines[index:]


def parse_content(
    content: str, title: str | None = None, artist: str | None = None
) -> list[Section]:
    """Turn UG ``wiki_tab`` markup into sections of inline-ChordPro lines."""
    text = unicodedata.normalize("NFC", content).replace("\r", "")
    text = text.replace("[tab]", "").replace("[/tab]", "")
    lines = [line.rstrip() for line in text.split("\n")]
    lines = _drop_leading_header(lines, title, artist)
    sections: list[Section] = []
    header: str | None = None
    label: str | None = None
    section_title: str | None = None
    current: list[str] = []

    def close() -> None:
        if current:
            sections.append(
                Section(
                    lines=[Line.from_chordpro(line) for line in current],
                    label=label,
                    title=section_title,
                )
            )
        elif header is not None:
            # A bare "[Chorus]" means "repeat the chorus here": keep the cue.
            sections.append(Section(lines=[Line.from_chordpro(f"({header})")]))

    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip():
            continue
        if _NOTES.match(line) and (sections or current):
            # Footnotes and the alternate-chord/tab lines that follow run
            # until the next section, or to the end of the tab.
            while index < len(lines) and _header(lines[index]) is None:
                index += 1
            continue
        next_header = _header(line)
        if next_header is not None:
            close()
            header = next_header
            label, section_title = _section_for(header)
            current = []
        elif _STAFF.fullmatch(line):
            continue
        elif _is_chord_line(line):
            following = lines[index] if index < len(lines) else ""
            if _mergeable(line) and _is_lyric(following):
                current.append(merge_chord_line(line, following))
                index += 1
            else:
                current.append(chord_only_line(line, keep_indent=True))
        else:
            # Lyrics without chords, or text with chords inline already.
            current.append(chord_only_line(line))
    close()
    return sections


def _capo(meta: dict[str, Any]) -> int:
    try:
        capo = int(meta.get("capo") or 0)
    except (TypeError, ValueError, OverflowError):
        return 0
    return capo if 0 <= capo <= 12 else 0


def _key(meta: dict[str, Any], tab: dict[str, Any]) -> str | None:
    key = meta.get("tonality") or tab.get("tonality_name") or ""
    key = key.strip() if isinstance(key, str) else ""
    return key if key and _valid_chord(key) else None


def parse_tab_html(html: str) -> SongModel:
    data = _page_data(html)
    view = _dict(data.get("tab_view"))
    tab = _dict(data.get("tab"))
    versions = view.get("versions")
    first_version = _dict(
        versions[0] if isinstance(versions, list) and versions else None
    )
    meta = _dict(view.get("meta"))
    content = _dict(view.get("wiki_tab")).get("content")
    if not isinstance(content, str):
        raise UltimateGuitarError("That Ultimate Guitar page has no song text.")
    title = _text(tab.get("song_name"), first_version.get("song_name"))
    artist = _text(tab.get("artist_name"), first_version.get("artist_name"))
    try:
        sections = parse_content(content, title=title, artist=artist)
    except (KeyError, IndexError, ValueError, TypeError, AttributeError) as e:
        raise UltimateGuitarError(
            "Could not read the Ultimate Guitar song text."
        ) from e
    return SongModel(
        sections=sections,
        title=title,
        artist=artist,
        capo=_capo(meta),
        key=_key(meta, tab),
    )


def import_tab(url: str) -> SongModel:
    return parse_tab_html(fetch(url))
