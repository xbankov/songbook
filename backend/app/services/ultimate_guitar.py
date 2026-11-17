"""Ultimate Guitar search and import (#132).

One fetch path for UG: an identifying User-Agent, a timeout, and at most one
request every few seconds. Pages are parsed from the ``js-store`` JSON the
site embeds; chord lines above lyric lines are merged into inline ChordPro.
"""

import json
import logging
import re
import threading
import time
from typing import Any
from urllib.parse import quote, urlparse

import requests
from app.services.music_theory import Chord, Line, Section, SongModel
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "Songbook/1.0 (self-hosted chord sheet importer)"
TIMEOUT_SECONDS = 20
MIN_INTERVAL_SECONDS = 3.0
SEARCH_URL = "https://www.ultimate-guitar.com/search.php"
SEARCH_LIMIT = 10
# Types whose page carries the song text; Official/Pro tabs need the app.
IMPORTABLE_TYPES = {"Chords", "Tabs", "Ukulele Chords"}

_CHORD = re.compile(r"\[ch\](.*?)\[/ch\]")
# A tablature staff line such as "e|--3--|" or "G|-4-5h7-|".
_STAFF = re.compile(r"\s*[A-Ga-g][#b]?\s*\|[-\w|/\\~*.() ]*")
_HEADER = re.compile(r"\[([A-Za-z][^\[\]]*)\]")
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
        return json.loads(store["data-content"])["store"]["page"]["data"]
    except (ValueError, KeyError, TypeError) as e:
        raise UltimateGuitarError("Could not read the Ultimate Guitar page.") from e


# --- search -----------------------------------------------------------------


def parse_search_html(html: str) -> list[dict[str, Any]]:
    results = []
    for tab in _page_data(html).get("results") or []:
        url = tab.get("tab_url") or ""
        if tab.get("type") not in IMPORTABLE_TYPES or not is_ultimate_guitar_url(url):
            continue
        if urlparse(url).path.startswith("/pro"):
            continue
        results.append(
            {
                "title": tab.get("song_name") or "Unknown",
                "artist": tab.get("artist_name") or "Unknown",
                "url": url,
                "source": "ultimate-guitar",
                "type": tab["type"],
                "rating": tab.get("rating") or 0,
                "votes": tab.get("votes") or 0,
            }
        )
        if len(results) == SEARCH_LIMIT:
            break
    return results


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
    """Each chord's column in the line as displayed (markup removed)."""
    columns = []
    column = 0
    position = 0
    for match in _CHORD.finditer(line):
        column += match.start() - position
        columns.append((column, match.group(1).strip()))
        column += len(match.group(1))
        position = match.end()
    return columns


def _plain(text: str) -> str:
    """Lyric text with brackets that ChordPro would read as chords neutralised."""
    return text.replace("[", "(").replace("]", ")")


def _inline(name: str) -> str:
    # A chord we cannot parse ("N.C.") would break the song model; keep it
    # visible as text instead.
    return f"[{name}]" if _valid_chord(name) else name


def merge_chord_line(chords: str, lyrics: str) -> str:
    """Put the chords of ``chords`` into ``lyrics`` at the same columns."""
    merged = _plain(lyrics)
    for column, name in reversed(_chord_columns(chords)):
        if not _valid_chord(name):
            continue
        merged = merged.ljust(column)
        merged = f"{merged[:column]}[{name}]{merged[column:]}"
    return merged.rstrip()


def chord_only_line(line: str) -> str:
    """Convert a line in place: ``[ch]X[/ch]`` becomes ``[X]``, the rest is text."""
    parts = _CHORD.split(line)
    # re.split with one group alternates text, chord, text, ...
    return "".join(
        _inline(part.strip()) if index % 2 else _plain(part)
        for index, part in enumerate(parts)
    ).strip()


def _section_for(header: str) -> tuple[str, str | None]:
    lowered = header.lower()
    if lowered.startswith(("chorus", "refrain")):
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
    return match.group(1).strip() if match and "[ch]" not in line else None


def parse_content(content: str) -> list[Section]:
    """Turn UG ``wiki_tab`` markup into sections of inline-ChordPro lines."""
    text = content.replace("\r", "").replace("[tab]", "").replace("[/tab]", "")
    lines = [line.rstrip() for line in text.split("\n")]
    sections: list[Section] = []
    label: str | None = None
    title: str | None = None
    current: list[str] = []

    def close() -> None:
        if current:
            sections.append(
                Section(
                    lines=[Line.from_chordpro(line) for line in current],
                    label=label,
                    title=title,
                )
            )

    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip():
            continue
        header = _header(line)
        if header is not None:
            close()
            label, title = _section_for(header)
            current = []
        elif _is_chord_line(line):
            following = lines[index] if index < len(lines) else ""
            # Merge only a line of bare chords: bars or repeat marks ("x2")
            # have no place inside a lyric, so such a line stays as it is.
            if not _CHORD.sub("", line).strip() and _is_lyric(following):
                current.append(merge_chord_line(line, following))
                index += 1
            else:
                current.append(chord_only_line(line))
        else:
            # Lyrics without chords, or text with chords inline already.
            current.append(chord_only_line(line))
    close()
    return sections


def _capo(meta: dict[str, Any]) -> int:
    try:
        capo = int(meta.get("capo") or 0)
    except (TypeError, ValueError):
        return 0
    return capo if 0 <= capo <= 12 else 0


def _key(meta: dict[str, Any], tab: dict[str, Any]) -> str | None:
    key = (meta.get("tonality") or tab.get("tonality_name") or "").strip()
    return key if key and _valid_chord(key) else None


def parse_tab_html(html: str) -> SongModel:
    data = _page_data(html)
    view = data.get("tab_view") or {}
    tab = data.get("tab") or {}
    first_version = (view.get("versions") or [{}])[0]
    meta = view.get("meta") or {}
    try:
        content = view["wiki_tab"]["content"]
    except (KeyError, TypeError) as e:
        raise UltimateGuitarError("That Ultimate Guitar page has no song text.") from e
    try:
        sections = parse_content(content or "")
    except (KeyError, IndexError, ValueError) as e:
        raise UltimateGuitarError(
            "Could not read the Ultimate Guitar song text."
        ) from e
    return SongModel(
        sections=sections,
        title=tab.get("song_name") or first_version.get("song_name") or "Unknown",
        artist=tab.get("artist_name") or first_version.get("artist_name") or "Unknown",
        capo=_capo(meta),
        key=_key(meta, tab),
    )


def import_tab(url: str) -> SongModel:
    return parse_tab_html(fetch(url))
