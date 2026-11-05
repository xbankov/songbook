import pytest
from app.services.music_theory import (
    Chord,
    ChordQuality,
    Line,
    Section,
    SongModel,
    Tone,
    chord_quality_names,
    parse_ultimate_guitar_html,
)


class TestTone:
    def test_parse(self):
        assert Tone.parse("C").value == 0
        assert Tone.parse("B").value == 11
        assert Tone.parse("C#").value == 1

    def test_transpose(self):
        c = Tone.parse("C")
        assert c.transpose(2).value == 2
        assert c.transpose(-1).value == 11

    def test_str(self):
        assert str(Tone(value=0)) == "C"
        assert str(Tone(value=11)) == "B"


class TestChord:
    def test_parse_major(self):
        c = Chord.parse("C")
        assert c.root.value == 0
        assert c.quality == ChordQuality.major
        assert c.bass is None

    def test_parse_minor(self):
        c = Chord.parse("Am")
        assert c.root.value == 9
        assert c.quality == ChordQuality.minor

    def test_parse_seventh(self):
        c = Chord.parse("G7")
        assert c.root.value == 7
        assert c.quality == ChordQuality.dom7

    def test_parse_with_bass(self):
        c = Chord.parse("C/G")
        assert c.root.value == 0
        assert c.bass is not None
        assert c.bass.value == 7

    def test_transpose(self):
        c = Chord.parse("C")
        t = c.transpose(2)
        assert str(t) == "D"

    def test_transpose_minor(self):
        c = Chord.parse("Am")
        t = c.transpose(3)
        assert str(t) == "Cm"

    def test_str(self):
        assert str(Chord.parse("F#m7")) == "F#m7"
        assert str(Chord.parse("Bb")) == "A#"  # canonical form uses sharps


class TestLine:
    def test_from_chordpro(self):
        line = Line.from_chordpro("[Am]Hello [C]world")
        assert len(line.parts) == 4
        assert isinstance(line.parts[0], Chord)
        assert line.parts[0].root.value == 9  # A
        assert isinstance(line.parts[1], str)
        assert line.parts[1] == "Hello "
        assert isinstance(line.parts[2], Chord)
        assert line.parts[2].root.value == 0  # C
        assert isinstance(line.parts[3], str)
        assert line.parts[3] == "world"

    def test_transpose(self):
        line = Line.from_chordpro("[C]Hello [G]world")
        t = line.transpose(2)
        assert isinstance(t.parts[0], Chord)
        assert str(t.parts[0]) == "D"
        assert isinstance(t.parts[2], Chord)
        assert str(t.parts[2]) == "A"

    def test_str(self):
        line = Line.from_chordpro("[Am]Hello")
        s = str(line)
        assert "[Am]" in s
        assert "Hello" in s


class TestSongModel:
    def test_from_chordpro_simple(self):
        text = "{title: Test Song}\n{artist: Test Artist}\n[Am]Hello [C]world"
        song = SongModel.from_chordpro(text)
        assert song.title == "Test Song"
        assert song.artist == "Test Artist"
        assert len(song.sections) >= 1

    def test_from_chordpro_with_sections(self):
        text = """{title: My Song}
{artist: Me}
{capo: 2}
{key: G}
{start_of_verse}
[G]Hello [D]world
{end_of_verse}
{start_of_chorus: Chorus}
[C]This is the [G]chorus
{end_of_chorus}"""
        song = SongModel.from_chordpro(text)
        assert song.title == "My Song"
        assert song.capo == 2
        assert song.key == "G"
        assert len(song.sections) >= 2

    def test_transpose(self):
        text = "{title: Test}\n{artist: T}\n[C]Hello [G]world"
        song = SongModel.from_chordpro(text)
        transposed = song.transpose(2)
        s = str(transposed)
        assert "[D]" in s
        assert "[A]" in s

    def test_str_roundtrip(self):
        text = "{title: Test}\n{artist: Me}\n\n[Am]Hello [G]world"
        song = SongModel.from_chordpro(text)
        result = str(song)
        assert "title: Test" in result
        assert "artist: Me" in result

    def test_empty_body(self):
        song = SongModel.from_chordpro("")
        assert song.title == "Unknown"
        assert song.artist == "Unknown"
        assert song.sections == []


class TestChordQuality:
    def test_all_qualities_parse(self):
        tests = [
            ("C", ChordQuality.major),
            ("Cm", ChordQuality.minor),
            ("C7", ChordQuality.dom7),
            ("Cmaj7", ChordQuality.maj7),
            ("Cm7", ChordQuality.min7),
            ("Cdim", ChordQuality.dim),
            ("Caug", ChordQuality.aug),
            ("Cdim7", ChordQuality.dim7),
            ("Csus2", ChordQuality.sus2),
            ("Csus4", ChordQuality.sus4),
            ("C5", ChordQuality.power),
        ]
        for label, expected in tests:
            c = Chord.parse(label)
            assert c.quality == expected, f"Failed for {label}: got {c.quality}"

    def test_alt_names(self):
        assert Chord.parse("Cmaj").quality == ChordQuality.major
        assert Chord.parse("Cmin").quality == ChordQuality.minor
        assert Chord.parse("Cmin7").quality == ChordQuality.min7
