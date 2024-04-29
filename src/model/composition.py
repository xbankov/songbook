from enum import Enum

tones = {
    "C": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10, "Hb": 10,
    "B": 11, "H": 11,
}

chromatic_scale = "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"

intervals = "P1", "m2", "M2", "m3", "M3", "P4", "TT", "P5", "m6", "M6", "m7", "M7", "P8"


class ChordScheme(Enum):
    major = 0, 4, 7
    minor = 0, 3, 7
    dom7 = 0, 4, 7, 10
    maj7 = 0, 4, 7, 11
    min7 = 0, 3, 7, 10
    minmaj7 = 0, 3, 7, 11
    dim = 0, 3, 6
    aug = 0, 4, 8
    dim7 = 0, 3, 6, 9
    min7b5 = 0, 3, 6, 10
    sus2 = 0, 2, 7
    sus4 = 0, 5, 7
    power = 0, 7
    add4 = 0, 4, 5, 7
    minadd4 = 0, 3, 5, 7
    add6 = 0, 4, 7, 9
    minadd6 = 0, 3, 7, 9
    maj9 = 0, 2, 4, 7, 11
    dom9 = 0, 2, 4, 7, 10


chord_scheme_names = {
    ChordScheme.major: ["", "maj", "major"],
    ChordScheme.minor: ["m", "min", "minor"],
    ChordScheme.dom7: ["7", "dom7"],
    ChordScheme.maj7: ["Maj7", "major7"],
    ChordScheme.min7: ["m7", "min7", "minor7"],
    ChordScheme.minmaj7: ["minMaj7"],
    ChordScheme.dim: ["dim", "diminished"],
    ChordScheme.aug: ["aug", "augmented"],
    ChordScheme.dim7: ["dim7", "diminished7"],
    ChordScheme.min7b5: ["min7b5", "min7flat5", "half-diminished"],
    ChordScheme.sus2: ["sus2"],
    ChordScheme.sus4: ["sus4"],
    ChordScheme.power: ["5"],
    ChordScheme.add4: ["add4"],
    ChordScheme.minadd4: ["minAdd4", "mAdd4"],
    ChordScheme.add6: ["add6"],
    ChordScheme.minadd6: ["minAdd6", "mAdd6"],
    ChordScheme.maj9: ["Maj9"],
    ChordScheme.dom9: ["dom9"],
}

chord_scheme_canonical_name = {scheme: chord_names[0] for scheme, chord_names in chord_scheme_names.items()}

chord_name_scheme = {chord_name.lower(): scheme
                     for scheme, chord_names in chord_scheme_names.items()
                     for chord_name in chord_names}


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
            interval = - interval
            label = "-"
        if interval < len(intervals):
            label += intervals[interval]
        else:
            label += str(interval)
        return label


class Chord:
    def __init__(self, root, scheme, scheme_name, bass=None):
        self.root = root
        self.scheme = scheme
        self.scheme_name = scheme_name
        self.bass = bass if bass is not None else root

    def transpose(self, interval):
        return Chord(self.root.transpose(interval), self.scheme, self.scheme_name, self.bass.transpose(interval))

    @staticmethod
    def parse(label):
        dash_splits = label.rsplit("/", 1)
        bass = None
        if len(dash_splits) > 1:
            label = dash_splits[0]
            bass = Tone.parse(dash_splits[1])
        split = 1
        if len(label) > 1 and label[1] in ("#", "b"):
            split = 2
        root = Tone.parse(label[0:split])
        scheme = None
        scheme_name = label[split:]
        scheme_name_lower = scheme_name.lower()
        if scheme_name_lower in chord_name_scheme:
            scheme_id = chord_name_scheme[scheme_name_lower]
            scheme = scheme_id.value
            scheme_name = chord_scheme_canonical_name[scheme_id]
        # TODO VB else warning unknown chord
        return Chord(root, scheme, scheme_name, bass)

    def __str__(self):
        bass = f"/{self.bass}" if self.bass != self.root else ""
        return f"{self.root}{self.scheme_name}{bass}"
