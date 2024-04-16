from enum import Enum

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


class ChordScheme(Enum):
    major = 0, 4, 7
    minor = 0, 3, 7


chord_scheme = {
    "": ChordScheme.major,
    "maj": ChordScheme.major,
    "major": ChordScheme.major,
    "m": ChordScheme.minor,
    "min": ChordScheme.minor,
    "minor": ChordScheme.minor,
}

chord_scheme_name = {
    ChordScheme.major: "",
    ChordScheme.minor: "m",
}


class Tone(int):
    def __new__(cls, value):
        return int.__new__(cls, value % 12)

    @staticmethod
    def parse(label):
        return Tone(tones[label])

    def __str__(self):
        return chromatic_scale[self]

    def transpose(self, interval):
        return Tone(self + interval)


class Interval(int):
    def __new__(cls, value):
        return int.__new__(cls, value)

    def __str__(self):
        interval = self
        label = ""
        if interval < 0:
            interval = -interval
            label = "-"
        if interval < len(intervals):
            label += intervals[interval]
        else:
            label += str(interval)
        return label


class Chord:
    def __init__(self, root, scheme, scheme_name):
        self.root = root
        self.scheme = scheme
        self.scheme_name = scheme_name

    def transpose(self, interval):
        return Chord(self.root.transpose(interval), self.scheme, self.scheme_name)

    @staticmethod
    def parse(label):
        split = 1
        if len(label) > 1 and label[1] in ("#", "b"):
            split = 2
        root = Tone.parse(label[0:split])
        scheme = None
        scheme_name = label[split:]
        if scheme_name in chord_scheme:
            scheme = chord_scheme[scheme_name].value
            scheme_name = chord_scheme_name[chord_scheme[scheme_name]]
        return Chord(root, scheme, scheme_name)

    def __str__(self):
        return f"{self.root}{self.scheme_name}"

    def to_json(self):
        return {
            "root": str(self.root),
            "scheme": self.scheme,
            "scheme_name": self.scheme_name,
        }
