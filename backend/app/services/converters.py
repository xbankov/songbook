import re

from app.services.music_theory import SongModel, Line, Section, Chord


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
                        chord_line += chord_line_chars[i].ljust(len(ch) if ch != " " else 1)
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
        f"  title = \"{song.title}\"",
        f"  composer = \"{song.artist}\"",
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
