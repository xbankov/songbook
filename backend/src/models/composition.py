from enum import Enum

from pydantic import BaseModel, constr

tones: dict[str, int] = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "Hb": 10,
    "B": 11,
    "H": 11,
}

chromatic_scale = "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"

intervals = "P1", "m2", "M2", "m3", "M3", "P4", "TT", "P5", "m6", "M6", "m7", "M7", "P8"


class ChordQuality(str, Enum):
    """ Unique identifier for each chord type. """
    major = "major"
    minor = "minor"
    dom7 = "dom7"
    maj7 = "maj7"
    min7 = "min7"
    minmaj7 = "minmaj7"
    dim = "dim"
    aug = "aug"
    dim7 = "dim7"
    min7b5 = "min7b5"
    sus2 = "sus2"
    sus4 = "sus4"
    power = "power"
    add4 = "add4"
    minadd4 = "minadd4"
    add6 = "add6"
    minadd6 = "minadd6"
    dom7adds5 = "dom7adds5"
    maj9 = "maj9"
    dom9 = "dom9"
    dom9sus4 = "dom9sus4"
    dom11 = "dom11"


chord_quality_scheme: dict[ChordQuality, tuple] = {
    ChordQuality.major: (0, 4, 7),
    ChordQuality.minor: (0, 3, 7),
    ChordQuality.dom7: (0, 4, 7, 10),
    ChordQuality.maj7: (0, 4, 7, 11),
    ChordQuality.min7: (0, 3, 7, 10),
    ChordQuality.minmaj7: (0, 3, 7, 11),
    ChordQuality.dim: (0, 3, 6),
    ChordQuality.aug: (0, 4, 8),
    ChordQuality.dim7: (0, 3, 6, 9),
    ChordQuality.min7b5: (0, 3, 6, 10),
    ChordQuality.sus2: (0, 2, 7),
    ChordQuality.sus4: (0, 5, 7),
    ChordQuality.power: (0, 7),
    ChordQuality.add4: (0, 4, 5, 7),
    ChordQuality.minadd4: (0, 3, 5, 7),
    ChordQuality.add6: (0, 4, 7, 9),
    ChordQuality.minadd6: (0, 3, 7, 9),
    ChordQuality.dom7adds5: (0, 4, 7, 8, 10),
    ChordQuality.maj9: (0, 2, 4, 7, 11),
    ChordQuality.dom9: (0, 2, 4, 7, 10),
    ChordQuality.dom9sus4: (0, 2, 5, 7, 10),
    ChordQuality.dom11: (0, 2, 4, 5, 7, 10),
}

# The parse/display names. The first name in each list represents the canonical form we display
chord_quality_names: dict[ChordQuality, list[str]] = {
    ChordQuality.major: ["", "maj", "major"],
    ChordQuality.minor: ["m", "mi", "min", "minor"],
    ChordQuality.dom7: ["7", "dom7"],
    ChordQuality.maj7: ["Maj7", "major7"],
    ChordQuality.min7: ["m7", "min7", "minor7"],
    ChordQuality.minmaj7: ["minMaj7"],
    ChordQuality.dim: ["dim", "diminished"],
    ChordQuality.aug: ["aug", "augmented"],
    ChordQuality.dim7: ["dim7", "diminished7"],
    ChordQuality.min7b5: ["min7b5", "min7flat5", "half-diminished"],
    ChordQuality.sus2: ["sus2"],
    ChordQuality.sus4: ["sus4"],
    ChordQuality.power: ["5"],
    ChordQuality.add4: ["add4"],
    ChordQuality.minadd4: ["minAdd4", "mAdd4"],
    ChordQuality.add6: ["add6"],
    ChordQuality.minadd6: ["minAdd6", "mAdd6"],
    ChordQuality.dom7adds5: ["7add#5", "dom7add#5", "7/5+"],
    ChordQuality.maj9: ["Maj9"],
    ChordQuality.dom9: ["9", "dom9"],
    ChordQuality.dom9sus4: ["9sus4", "dom9sus4"],
    ChordQuality.dom11: ["11", "dom11"],
}

chord_quality_canonical_name: dict[ChordQuality, str] = {
    quality: chord_names[0]
    for quality, chord_names in chord_quality_names.items()}

chord_name_quality: dict[str, ChordQuality] = {
    chord_name.lower(): quality
    for quality, chord_names in chord_quality_names.items()
    for chord_name in chord_names}


class Tone(BaseModel):
    value: int

    @classmethod
    def parse(cls, label: str) -> "Tone":
        return Tone(value=tones[label])

    def __str__(self) -> str:
        return chromatic_scale[self.value]

    def transpose(self, interval: int) -> "Tone":
        return Tone(value=(self.value + interval) % 12)


class Interval(BaseModel):
    value: int

    def __str__(self) -> str:
        interval = self.value
        label = ""
        if interval < 0:
            interval = -interval
            label = "-"
        if interval < len(intervals):
            label += intervals[interval]
        else:
            label += str(interval)
        return label


class Chord(BaseModel):
    root: Tone
    quality: ChordQuality | str
    bass: Tone | None

    # TODO Add dim
    # TODO Add bass G/H
    @classmethod
    def parse(cls, label: str) -> "Chord":
        bass = None
        dash_splits = label.rsplit("/", 1)
        if len(dash_splits) > 1 and dash_splits[1] in tones:
            label = dash_splits[0]
            bass = Tone.parse(dash_splits[1])
        split = 1
        if len(label) > 1 and label[1] in ("#", "b"):
            split = 2

        root = Tone.parse(label[0:split])
        quality_str = label[split:]
        quality = chord_name_quality.get(quality_str.lower(), quality_str)
        return Chord(root=root, quality=quality, bass=bass)

    def transpose(self, interval):
        return Chord(
            root=self.root.transpose(interval),
            quality=self.quality,
            bass=self.bass.transpose(interval) if self.bass is not None else None)

    def __str__(self) -> str:
        quality = chord_quality_canonical_name.get(self.quality, self.quality)
        bass = f"/{self.bass}" if self.bass is not None else ""

        return f"{self.root}{quality}{bass}"
