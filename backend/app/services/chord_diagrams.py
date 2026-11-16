"""Chord diagrams for a songbook's chord chart (#89).

Shapes follow the same rule as the web view (frontend ChordDiagram.vue): on
each guitar string, play the lowest fret (0-5) that sounds a chord tone;
a string with no chord tone in that range is muted (-1). A slash chord is
drawn as its upper chord (G/B looks like G); the bass note is not fingered.

The web page renders the shapes this module computes (GET
/api/songbooks/{id}/chords), so the page and the PDF always agree.
"""

from app.services.music_theory import (
    Chord,
    ChordQuality,
    SongModel,
    chord_quality_scheme,
)

FRET_COUNT = 5
# Open strings, low E to high E, as semitones above C.
OPEN_STRINGS = (4, 9, 2, 7, 11, 4)
BASIC_QUALITIES = (ChordQuality.major, ChordQuality.minor)


def chord_shape(chord: Chord) -> list[int] | None:
    """Fret per string (low E first, -1 = muted), or None for unknown qualities."""
    if not isinstance(chord.quality, ChordQuality):
        return None
    intervals = chord_quality_scheme.get(chord.quality)
    if not intervals:
        return None
    notes = {(chord.root.value + interval) % 12 for interval in intervals}
    shape = []
    for open_note in OPEN_STRINGS:
        fret = min((note - open_note) % 12 for note in notes)
        shape.append(fret if fret <= FRET_COUNT else -1)
    return shape


def is_basic_chord(chord: Chord) -> bool:
    """Plain major or minor triads, which `uncommon` hides."""
    return chord.quality in BASIC_QUALITIES and chord.bass is None


def song_chords(song: SongModel) -> list[Chord]:
    return [
        part
        for section in song.sections
        for line in section.lines
        for part in line.parts
        if isinstance(part, Chord)
    ]


def chord_chart(songs: list[SongModel], mode: str) -> list[dict]:
    """Diagrams for the distinct chords in ``songs``, sorted by name."""
    if mode not in ("uncommon", "all"):
        return []
    chart: dict[str, dict] = {}
    for song in songs:
        for chord in song_chords(song):
            name = str(chord)
            if name in chart or (mode == "uncommon" and is_basic_chord(chord)):
                continue
            shape = chord_shape(chord)
            if shape is not None:
                chart[name] = {"name": name, "frets": shape}
    return [chart[name] for name in sorted(chart)]
