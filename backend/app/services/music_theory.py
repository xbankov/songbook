from enum import Enum

from pydantic import BaseModel

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

chromatic_scale = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


class ChordQuality(str, Enum):
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
    q: names[0] for q, names in chord_quality_names.items()
}

chord_name_quality: dict[str, ChordQuality] = {
    name.lower(): quality
    for quality, names in chord_quality_names.items()
    for name in names
}


class Tone(BaseModel):
    value: int

    @classmethod
    def parse(cls, label: str) -> "Tone":
        return Tone(value=tones[label])

    def __str__(self) -> str:
        return chromatic_scale[self.value]

    def transpose(self, interval: int) -> "Tone":
        return Tone(value=(self.value + interval) % 12)


class Chord(BaseModel):
    root: Tone
    quality: ChordQuality | str
    bass: Tone | None = None

    @classmethod
    def parse(cls, label: str) -> "Chord":
        bass = None
        slash_splits = label.rsplit("/", 1)
        if len(slash_splits) > 1 and slash_splits[1] in tones:
            label = slash_splits[0]
            bass = Tone.parse(slash_splits[1])
        split = 1
        if len(label) > 1 and label[1] in ("#", "b"):
            split = 2
        root = Tone.parse(label[0:split])
        quality_str = label[split:]
        quality = chord_name_quality.get(quality_str.lower(), quality_str)
        return Chord(root=root, quality=quality, bass=bass)

    def transpose(self, interval: int) -> "Chord":
        return Chord(
            root=self.root.transpose(interval),
            quality=self.quality,
            bass=self.bass.transpose(interval) if self.bass is not None else None,
        )

    def __str__(self) -> str:
        quality = chord_quality_canonical_name.get(self.quality, str(self.quality))
        bass = f"/{self.bass}" if self.bass is not None else ""
        return f"{self.root}{quality}{bass}"


class Line(BaseModel):
    parts: list[str | Chord]

    def __str__(self) -> str:
        string_parts = [
            f"[{part}]" if isinstance(part, Chord) else str(part) for part in self.parts
        ]
        return "".join(string_parts)

    @staticmethod
    def from_chordpro(text: str) -> "Line":
        splits = text.split("[")
        parts = []
        first_split = splits.pop(0)
        if first_split:
            parts.append(first_split)
        for split in splits:
            sub_splits = split.split("]", 1)
            parts.append(Chord.parse(sub_splits[0]))
            if sub_splits[1]:
                parts.append(sub_splits[1])
        return Line(parts=parts)

    def transpose(self, interval: int) -> "Line":
        parts = [
            part.transpose(interval) if isinstance(part, Chord) else part
            for part in self.parts
        ]
        return Line(parts=parts)


class Section(BaseModel):
    lines: list[Line]
    label: str | None = None
    title: str | None = None

    def __str__(self) -> str:
        lines = []
        if self.label is not None:
            tag = f"start_of_{self.label}"
            if self.title is not None:
                tag += f": {self.title}"
            lines.append(f"{{{tag}}}")
        for line in self.lines:
            lines.append(str(line))
        if self.label is not None:
            lines.append(f"{{end_of_{self.label}}}")
        return "\n".join(lines)

    @staticmethod
    def from_chordpro(text: str) -> "Section":
        text_lines = text.split("\n")
        label = None
        title = None
        parsed_lines = []
        for i, line in enumerate(text_lines):
            if not line.strip():
                continue
            stripped = line.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                splits = stripped[1:-1].split(":", 1)
                tag = splits[0].strip()
                content = splits[1].strip() if len(splits) == 2 else None
                if tag.startswith("start_of_"):
                    label = tag[9:]
                    title = content
                elif tag.startswith("end_of_"):
                    pass
            elif line:
                parsed_lines.append(Line.from_chordpro(line))
        return Section(lines=parsed_lines, label=label, title=title)

    def transpose(self, interval: int) -> "Section":
        return Section(
            lines=[line.transpose(interval) for line in self.lines],
            label=self.label,
            title=self.title,
        )


class SongModel(BaseModel):
    sections: list[Section]
    title: str
    artist: str
    capo: int = 0
    key: str | None = None

    def __str__(self) -> str:
        lines = [f"{{title: {self.title}}}", f"{{artist: {self.artist}}}"]
        if self.capo:
            lines.append(f"{{capo: {self.capo}}}")
        if self.key:
            lines.append(f"{{key: {self.key}}}")
        for section in self.sections:
            lines.append(str(section))
        return "\n\n".join(lines)

    @classmethod
    def from_chordpro(cls, text: str) -> "SongModel":
        title = "Unknown"
        artist = "Unknown"
        capo = 0
        key = None
        text = text.replace("\r", "")
        lines = text.split("\n")
        sections = []
        current_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                splits = stripped[1:-1].split(":", 1)
                tag = splits[0].strip()
                content = splits[1].strip() if len(splits) == 2 else None
                if tag == "title":
                    title = content or title
                elif tag == "artist":
                    artist = content or artist
                elif tag == "capo":
                    capo = int(content) if content else 0
                elif tag == "key":
                    key = content or key
                elif tag.startswith("start_of_"):
                    if current_lines:
                        sections.append(Section.from_chordpro("\n".join(current_lines)))
                        current_lines = []
                    current_lines.append(stripped)
                elif tag.startswith("end_of_"):
                    if current_lines:
                        current_lines.append(stripped)
                        sections.append(Section.from_chordpro("\n".join(current_lines)))
                        current_lines = []
                    elif stripped:
                        current_lines.append(stripped)
            elif stripped == "" and current_lines:
                sections.append(Section.from_chordpro("\n".join(current_lines)))
                current_lines = []
            elif stripped:
                current_lines.append(line)
        if current_lines:
            sections.append(Section.from_chordpro("\n".join(current_lines)))
        return cls(sections=sections, title=title, artist=artist, capo=capo, key=key)

    def transpose(self, interval: int) -> "SongModel":
        return SongModel(
            sections=[s.transpose(interval) for s in self.sections],
            title=self.title,
            artist=self.artist,
            capo=self.capo,
            key=self.key,
        )


def detect_key(song: SongModel) -> tuple[str, float] | None:
    chord_counts: dict[str, int] = {}
    for section in song.sections:
        for line in section.lines:
            for part in line.parts:
                if isinstance(part, Chord):
                    name = str(part.root)
                    chord_counts[name] = chord_counts.get(name, 0) + 1

    if not chord_counts:
        return None

    major_keys = {
        "C": ["C", "F", "G", "Am", "Dm", "Em"],
        "G": ["G", "C", "D", "Em", "Am", "Bm"],
        "D": ["D", "G", "A", "Bm", "Em", "F#m"],
        "A": ["A", "D", "E", "F#m", "Bm", "C#m"],
        "E": ["E", "A", "B", "C#m", "F#m", "G#m"],
        "F": ["F", "Bb", "C", "Dm", "Gm", "Am"],
        "Bb": ["Bb", "Eb", "F", "Gm", "Cm", "Dm"],
        "Eb": ["Eb", "Ab", "Bb", "Cm", "Fm", "Gm"],
    }
    minor_keys = {
        "Am": ["Am", "Dm", "Em", "C", "F", "G"],
        "Em": ["Em", "Am", "Bm", "G", "C", "D"],
        "Bm": ["Bm", "Em", "F#m", "D", "G", "A"],
        "F#m": ["F#m", "Bm", "C#m", "A", "D", "E"],
        "C#m": ["C#m", "F#m", "G#m", "E", "A", "B"],
        "Dm": ["Dm", "Gm", "Am", "F", "Bb", "C"],
        "Gm": ["Gm", "Cm", "Dm", "Bb", "Eb", "F"],
        "Cm": ["Cm", "Fm", "Gm", "Eb", "Ab", "Bb"],
    }

    total = sum(chord_counts.values())
    best_key = None
    best_score = 0

    for key, diatonic in {**major_keys, **minor_keys}.items():
        score = 0
        for chord_name, count in chord_counts.items():
            chord_root = chord_name
            for d in diatonic:
                if d.startswith(chord_root):
                    score += count
                    break
        if score > best_score:
            best_score = score
            best_key = key

    if best_key and total > 0:
        return (best_key, round(best_score / total * 100, 1))
    return None


def parse_ultimate_guitar_html(html: str) -> SongModel | None:
    import json

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    store = soup.find("div", {"class": "js-store"})
    if not store:
        return None
    data = json.loads(store["data-content"])
    tab = data["store"]["page"]["data"]["tab_view"]
    title = tab["versions"][0]["song_name"]
    artist = tab["versions"][0]["artist_name"]
    wiki_text = tab["wiki_tab"]["content"].replace("\r", "")

    text_lines = wiki_text.split("\n")
    sections = []
    current_block = []
    for line in text_lines:
        stripped = line.strip()
        if (
            stripped.startswith("[")
            and stripped.endswith("]")
            and "[ch]" not in stripped
            and "[tab]" not in stripped
        ):
            if current_block:
                block_text = "\n".join(current_block)
                chunk = _parse_ug_block(block_text)
                if chunk:
                    sections.append(chunk)
                current_block = []
        else:
            current_block.append(line)
    if current_block:
        block_text = "\n".join(current_block)
        chunk = _parse_ug_block(block_text)
        if chunk:
            sections.append(chunk)
    return SongModel(sections=sections, title=title, artist=artist, capo=0)


def _parse_ug_block(text: str) -> Section | None:
    import re

    lines = text.split("\n")
    parsed_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        clean = stripped.replace("[tab]", "").replace("[/tab]", "")
        chord_match = re.findall(r"\[ch\](.*?)\[\/ch\]", clean)
        if chord_match:
            chord_line = re.sub(r"\[ch]([^\]]*)\[/ch]", r"[\1]", clean)
            parsed_lines.append(Line.from_chordpro(chord_line))
        elif re.match(r"^[A-Za-z0-9]", clean) or clean.startswith("|"):
            parsed_lines.append(Line.from_chordpro(clean))
    if not parsed_lines:
        return None
    return Section(lines=parsed_lines, label="verse")
