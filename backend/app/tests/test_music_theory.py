import pytest
from app.services.music_theory import (
    Chord,
    ChordQuality,
    Line,
    Section,
    SongModel,
    Tone,
    analyze_key,
    chord_quality_names,
    detect_key,
)


class TestKeyAnalysis:
    def test_analysis_includes_the_chords_behind_the_suggestion(self):
        song = SongModel.from_chordpro("[C]a [C]b [F]c [G]d [Am]e")

        analysis = analyze_key(song)

        assert analysis == {
            "suggested_key": "C",
            "confidence": 100.0,
            "method": "diatonic chord match",
            "key_type": "major",
            "chord_count": 5,
            "key_chords": ["C", "F", "G", "Am", "Dm", "Em"],
            "chords": [
                {"name": "C", "count": 2, "in_key": True},
                {"name": "Am", "count": 1, "in_key": True},
                {"name": "F", "count": 1, "in_key": True},
                {"name": "G", "count": 1, "in_key": True},
            ],
        }
        assert detect_key(song) == ("C", 100.0)

    def test_analysis_marks_chords_outside_the_key(self):
        song = SongModel.from_chordpro("[C] [F] [G] [B]")

        analysis = analyze_key(song)

        assert analysis["suggested_key"] == "C"
        assert analysis["confidence"] == 75.0
        assert {"name": "C", "count": 1, "in_key": True} in analysis["chords"]
        assert {"name": "B", "count": 1, "in_key": False} in analysis["chords"]

    def test_flat_chords_match_a_flat_key(self):
        song = SongModel.from_chordpro("[F] [Bb] [C]")

        analysis = analyze_key(song)

        assert analysis["suggested_key"] == "F"
        assert analysis["confidence"] == 100.0
        assert {"name": "A#", "count": 1, "in_key": True} in analysis["chords"]

    def test_extensions_must_fit_the_key_scale(self):
        # C7 contains Bb: it is V7 in F, not a C-major chord.
        song = SongModel.from_chordpro("[C7] [F] [G]")

        analysis = analyze_key(song)

        assert analysis["suggested_key"] == "C"
        assert analysis["confidence"] == 66.7
        assert {"name": "C7", "count": 1, "in_key": False} in analysis["chords"]
        assert {"name": "F", "count": 1, "in_key": True} in analysis["chords"]

    def test_minor_key_is_not_reported_as_its_relative_major(self):
        song = SongModel.from_chordpro("[Am] [Dm] [Em]")

        analysis = analyze_key(song)

        assert analysis["suggested_key"] == "Am"
        assert analysis["key_type"] == "minor"
        assert analysis["confidence"] == 100.0
        assert {"name": "Am", "count": 1, "in_key": True} in analysis["chords"]
        assert detect_key(song) == ("Am", 100.0)

    def test_same_root_different_quality_is_not_in_key(self):
        song = SongModel.from_chordpro("[C] [Cm] [G]")

        analysis = analyze_key(song)

        assert analysis["suggested_key"] == "C"
        assert analysis["confidence"] == 66.7
        assert {"name": "C", "count": 1, "in_key": True} in analysis["chords"]
        assert {"name": "Cm", "count": 1, "in_key": False} in analysis["chords"]

    def test_no_chords_means_no_analysis(self):
        song = SongModel.from_chordpro("just words")

        assert analyze_key(song) is None
        assert detect_key(song) is None


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

    def test_chord_inside_word(self):
        line = Line.from_chordpro("bri[C]ght")
        texts = [part for part in line.parts if isinstance(part, str)]
        assert texts == ["bri", "ght"]
        assert str(line) == "bri[C]ght"

    def test_chord_inside_word_renders_at_the_right_position(self):
        from app.services.pdf import _build_line_data

        line = Line.from_chordpro("bri[C]ght")
        data = _build_line_data(line.parts)
        assert data["text"] == "bright"
        assert data["chord_line"].index("C") == 3


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
