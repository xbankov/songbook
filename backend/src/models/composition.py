from enum import Enum

from pydantic import BaseModel, constr

tones = {
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
    MAJOR = ""
    MINOR = "m"


class Tone(BaseModel):
    value: int

    @staticmethod
    def parse(label: str) -> "Tone":
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
    quality: ChordQuality
    bass: Tone | None

    # TODO Add dim
    # TODO Add bass G/H
    @classmethod
    def parse(cls, label: str) -> "Chord":
        split = 1
        if len(label) > 1 and label[1] in ("#", "b"):
            split = 2

        root = Tone.parse(label[0:split])
        quality_str = label[split:].lower()
        if quality_str in ("m", "min", "minor"):
            quality = ChordQuality.MINOR
        else:
            quality = ChordQuality.MAJOR

        return Chord(root=root, quality=quality, bass=None)

    def __str__(self) -> str:
        return f"{self.root}{self.quality.value}"
