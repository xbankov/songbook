import re
from typing import Any

from app.services.music_theory import Chord, Line, Section, SongModel


def chordpro_to_text(song: SongModel) -> str:
    lines = [f"{song.title} - {song.artist}"]
    if song.capo:
        lines.append(f"Capo: {song.capo}")
    if song.key:
        lines.append(f"Key: {song.key}")
    lines.append("")
    for section in song.sections:
        if section.label and section.label != "verse":
            label = section.title or section.label.capitalize()
            lines.append(f"[{label}]")
        for line in section.lines:
            text_parts = []
            chord_line_chars = {}
            for part in line.parts:
                if isinstance(part, Chord):
                    chord_line_chars[len(text_parts)] = str(part)
                else:
                    text_parts.append(part)
            if chord_line_chars:
                chord_line = ""
                for i, ch in enumerate(" ".join(text_parts)):
                    if i in chord_line_chars:
                        chord_line += chord_line_chars[i].ljust(
                            len(ch) if ch != " " else 1
                        )
                    else:
                        chord_line += " "
                lines.append(chord_line.rstrip())
            lines.append("".join(text_parts))
        lines.append("")
    return "\n".join(lines)


def chordpro_to_abc(song: SongModel) -> str:
    abc_lines = [f"X:1", f"T:{song.title}", f"C:{song.artist}"]
    if song.key:
        abc_lines.append(f"K:{song.key}")
    else:
        abc_lines.append("K:C")
    abc_lines.append("M:4/4")
    abc_lines.append("L:1/4")
    for section in song.sections:
        for line in section.lines:
            parts = []
            for part in line.parts:
                if isinstance(part, Chord):
                    parts.append(f'"{str(part)}"z')
                else:
                    parts.append("z" * len(part))
            if parts:
                abc_lines.append("|" + " ".join(parts) + "|")
    abc_lines.append("")
    return "\n".join(abc_lines)


def chordpro_to_ly(song: SongModel) -> str:
    ly_lines = [
        '\\version "2.24.0"',
        "\\header {",
        f'  title = "{song.title}"',
        f'  composer = "{song.artist}"',
        "}",
        "",
        "\\score {",
        "  <<",
        "    \\new ChordNames {",
        "      \\chordmode {",
    ]
    for section in song.sections:
        for line in section.lines:
            chord_strs = []
            for part in line.parts:
                if isinstance(part, Chord):
                    c = str(part.root).lower()
                    q = str(part.quality)
                    if q in ("m", "min", "minor"):
                        chord_strs.append(f"{c}:m")
                    elif q in ("dim", "diminished"):
                        chord_strs.append(f"{c}:dim")
                    elif q in ("aug", "augmented"):
                        chord_strs.append(f"{c}:aug")
                    elif q in ("7", "dom7"):
                        chord_strs.append(f"{c}:7")
                    elif q in ("maj7", "Maj7"):
                        chord_strs.append(f"{c}:maj7")
                    elif q in ("m7", "min7"):
                        chord_strs.append(f"{c}:m7")
                    elif q in ("sus4",):
                        chord_strs.append(f"{c}:sus4")
                    elif q in ("sus2",):
                        chord_strs.append(f"{c}:sus2")
                    else:
                        chord_strs.append(c)
            if chord_strs:
                ly_lines.append("        " + " ".join(chord_strs))
    ly_lines += [
        "      }",
        "    }",
        "  >>",
        "  \\layout {}",
        "  \\midi {}",
        "}",
        "",
    ]
    return "\n".join(ly_lines)


def transpose_key(key: str | None, interval: int) -> str | None:
    """Transpose a key name such as ``G`` or ``Am``; keep it if unparseable."""
    if not key or not interval:
        return key
    try:
        return str(Chord.parse(key).transpose(interval))
    except Exception:
        return key


def transpose_chordpro_body(body: str, interval: int) -> str:
    """Transpose bracketed chords and the key directive without dropping tags."""
    if not interval:
        return body

    def replace_chord(match: re.Match) -> str:
        try:
            chord = Chord.parse(match.group(1).strip())
            return f"[{chord.transpose(interval)}]"
        except Exception:
            return match.group(0)

    def replace_key(match: re.Match) -> str:
        return f"{{key: {transpose_key(match.group(1).strip(), interval)}}}"

    body = re.sub(r"\{key:\s*([^}]+)\}", replace_key, body, flags=re.IGNORECASE)
    return re.sub(r"\[([^\]]+)\]", replace_chord, body)


METADATA_TAGS = ("title", "artist", "capo", "key")
_METADATA_LINE = re.compile(
    r"^\s*\{\s*(title|artist|capo|key)\s*:(.*)\}\s*$", re.IGNORECASE
)


def split_chordpro_metadata(body: str) -> tuple[str, dict[str, str]]:
    """Remove ``{title}``, ``{artist}``, ``{capo}`` and ``{key}`` lines.

    Returns the body without those lines and the first value found for each
    tag. Title, artist, capo and key live in the song's own fields (#37); the
    tags are only added back when a song is exported as ChordPro.
    """
    values: dict[str, str] = {}
    kept: list[str] = []
    for line in body.replace("\r", "").split("\n"):
        match = _METADATA_LINE.match(line)
        if match:
            values.setdefault(match.group(1).lower(), match.group(2).strip())
        else:
            kept.append(line)
    while kept and not kept[0].strip():
        kept.pop(0)
    return "\n".join(kept), values


def parse_capo(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def is_unset_field(tag: str, value: Any) -> bool:
    """True when a metadata field has no real value yet.

    Blank title/artist/key and the ``Unknown`` title/artist placeholder are
    unset. Capo 0 means "no capo", so only a missing capo is unset.
    """
    if value is None:
        return True
    if tag == "capo":
        return False
    text = str(value).strip()
    return not text or (tag in ("title", "artist") and text == "Unknown")


def absorb_chordpro_metadata(
    body: str, fields: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """Strip metadata tags from an incoming ``body`` and fill unset fields.

    Used when a song is saved: a pasted body may carry ``{title}`` etc.
    ``fields`` maps tag names to the values the caller already has. A tag only
    fills a field that is unset (see ``is_unset_field``); real values win.
    """
    clean, tags = split_chordpro_metadata(body)
    resolved = dict(fields)
    for tag in METADATA_TAGS:
        if tag not in resolved or not is_unset_field(tag, resolved[tag]):
            continue
        value = parse_capo(tags.get(tag)) if tag == "capo" else tags.get(tag)
        if value:
            resolved[tag] = value
    return clean, resolved


def song_model_from_fields(
    body: str,
    title: str,
    artist: str,
    capo: int | None = 0,
    key: str | None = None,
) -> SongModel:
    """Parse ``body`` but take title/artist/capo/key from the song's fields."""
    return SongModel.from_chordpro(body).model_copy(
        update={"title": title, "artist": artist, "capo": capo or 0, "key": key or None}
    )


def song_model_from_row(song: Any) -> SongModel:
    """Build a ``SongModel`` from a ``Song`` (or ``SongVersion``) row."""
    return song_model_from_fields(
        song.body, song.title, song.artist, song.capo, song.key
    )


def chordpro_body(model: SongModel) -> str:
    """Serialize a model's sections as a stored body, without metadata tags."""
    return "\n\n".join(str(section) for section in model.sections)


def ensure_chordpro_metadata(
    body: str,
    title: str,
    artist: str,
    capo: int = 0,
    key: str | None = None,
) -> str:
    lines = split_chordpro_metadata(body)[0].split("\n")
    prefix = [f"{{title: {title}}}", f"{{artist: {artist}}}"]
    if capo:
        prefix.append(f"{{capo: {capo}}}")
    if key:
        prefix.append(f"{{key: {key}}}")
    return "\n".join(prefix + lines)


def export_songs_as_chordpro(songs: list[SongModel]) -> str:
    parts = []
    for song in songs:
        parts.append(str(song))
    return "\n\n---\n\n".join(parts)


def parse_bulk_chordpro(text: str) -> list[SongModel]:
    raw_songs = re.split(r"\n---+\n", text)
    songs = []
    for raw in raw_songs:
        raw = raw.strip()
        if raw:
            try:
                songs.append(SongModel.from_chordpro(raw))
            except Exception:
                pass
    return songs
