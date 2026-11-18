"""Open-position chord shapes for the song view (#142).

Shapes follow the web component's rule (frontend ChordDiagram.vue): on each
guitar string, play the lowest fret (0-5) that sounds a chord tone; a string
with no chord tone in that range is muted (-1). A slash chord is drawn as its
upper chord (G/B looks like G); the bass note is not fingered.
"""

from app.services.music_theory import Chord, ChordQuality, chord_quality_scheme

FRET_COUNT = 5
# Open strings, low E to high E, as semitones above C.
OPEN_STRINGS = (4, 9, 2, 7, 11, 4)


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
