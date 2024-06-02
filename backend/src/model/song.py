import json
import re
from typing import Dict

from bs4 import BeautifulSoup
from model.utils import get_tag_items, is_tag, is_ug_tag
from model.composition import Chord


class Line:
    def __init__(self, parts):
        self.parts = parts

    def __str__(self):
        string_parts = [
            f"[{part}]" if isinstance(part, Chord) else str(part) for part in self.parts
        ]
        return "".join(string_parts)

    @staticmethod
    def from_chordpro(text: str):
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

        return Line(parts)

    def transpose(self, interval):
        parts = [
            part.transpose(interval) if isinstance(part, Chord) else part
            for part in self.parts
        ]
        return Line(parts)

    def json(self):
        return {
            "parts": [
                part.json() if isinstance(part, Chord) else str(part)
                for part in self.parts
            ]
        }

    @staticmethod
    def from_json(json_dict: Dict):
        parsed_parts = [
            Chord.from_json(part) if isinstance(part, dict) else part
            for part in json_dict["parts"]
        ]
        return Line(parsed_parts)


class Section:
    def __init__(self, lines: list[Line], label: str = None, title: str = None):
        self.lines = lines
        self.label = label
        self.title = title

    def __str__(self):
        string_lines = []

        if self.label is not None:
            start_tag = f"start_of_{self.label}"
            if self.title is not None:
                start_tag += f": {self.title}"
            string_lines.append(f"{{{start_tag}}}")

        for line in self.lines:
            string_lines.append(str(line))

        if self.label is not None:
            string_lines.append(f"{{end_of_{self.label}}}")

        return "\n".join(string_lines)

    @staticmethod
    def from_ug_html(text: str):
        text_lines = text.split("\n")
        parsed_lines = []
        skip_line = False
        for i, line in enumerate(text_lines):

            if skip_line:
                continue

            elif is_ug_tag(line):
                title = line.strip().strip("[]")
                label = title.lower().split(" ")[0]
                if label not in ["chorus", "verse", "bridge"]:
                    label = "verse"

            elif line:
                next_line = text_lines[i + 1]
                if line.startswith("[ch]") and line.endswith("[/ch]"):
                    chords_line = re.sub(r"\[ch]([^\]]*)\[/ch]", r"[\1]", line)
                    parsed_lines.append(Line.from_chordpro(chords_line))
                elif line.startswith("[tab]") and next_line.endswith("[/tab]"):
                    chords_line = text_lines[i].replace("[tab]", "")
                    lyrics_line = text_lines[i + 1].replace("[/tab]", "")

                    chords_line = re.sub(r"\[ch]([^\]]*)\[/ch]", r"\1", chords_line)
                    chords_position = [
                        i
                        for i, char in enumerate(chords_line)
                        if char.isalnum()
                        and (i == 0 or not chords_line[i - 1].isalnum())
                    ]
                    chords_labels = chords_line.split()

                    offset = 0
                    merged = lyrics_line
                    for pos, chord in zip(chords_position, chords_labels):
                        chord = f"[{chord}]"
                        merged = merged[: pos + offset] + chord + merged[pos + offset :]
                        offset += len(chord)
                    parsed_lines.append(Line.from_chordpro(merged))
        return Section(parsed_lines, label, title)

    @staticmethod
    def from_chordpro(text: str):
        text_lines = text.split("\n")
        label = None
        title = None
        parsed_lines = []

        for i, line in enumerate(text_lines):
            if is_tag(line):
                tag, content = get_tag_items(line)

                if i == 0 and tag.startswith("start_of_"):
                    label = tag[9:]
                    if content is not None:
                        title = content
                elif (
                    label is not None
                    and i == len(text_lines) - 1
                    and line == f"{{end_of_{label}}}"
                ):
                    pass
            elif line:
                parsed_lines.append(Line.from_chordpro(line))

        return Section(parsed_lines, label, title)

    def transpose(self, interval):
        lines = [line.transpose(interval) for line in self.lines]
        return Section(lines, self.label, self.title)

    def json(self):
        return {
            "lines": [line.json() for line in self.lines],
            "label": self.label,
            "title": self.title,
        }

    @staticmethod
    def from_json(json_dict: Dict):
        parsed_lines = [Line.from_json(line) for line in json_dict["lines"]]
        label = json_dict["label"]
        title = json_dict["title"]
        return Section(parsed_lines, label, title)


class Song:
    def __init__(
        self,
        sections: list[Section],
        title: str,
        artist: str,
        capo: str = None,
        object_id: str = None,
    ):
        # TODO VB capo should be int
        self.sections = sections
        self.title = title
        self.artist = artist
        self.capo = capo
        self.object_id = object_id

    def __str__(self):
        string_sections = [f"{{title: {self.title}}}", f"{{artist: {self.artist}}}"]

        if self.capo is not None:
            string_sections.append(f"{{capo: {self.capo}}}")

        for section in self.sections:
            string_sections.append(str(section))

        return "\n\n".join(string_sections)

    @staticmethod
    def from_ug_html(html: str):
        soup = BeautifulSoup(html, "lxml")
        json_string = soup.find("div", {"class": "js-store"})["data-content"]
        data = json.loads(json_string)
        tab_view = data["store"]["page"]["data"]["tab_view"]
        capo = None
        title = tab_view["versions"][0]["song_name"]
        artist = tab_view["versions"][0]["artist_name"]
        text = tab_view["wiki_tab"]["content"]
        text = text.replace("\r", "")
        text_lines = text.split("\n")
        parsed_sections = []

        current_section_start = 0
        first_section = True
        for i, line in enumerate(text_lines):
            if is_ug_tag(line):
                if first_section:  # First section
                    first_section = False
                    continue

                elif i == len(text_lines) - 1:  # Last section
                    current_section_end = i
                    section_lines = text_lines[
                        current_section_start:current_section_end
                    ]
                    parsed_sections.append(
                        Section.from_ug_html("\n".join(section_lines))
                    )

                else:  # Start of the section any other section
                    current_section_end = i
                    section_lines = text_lines[
                        current_section_start:current_section_end
                    ]
                    parsed_sections.append(
                        Section.from_ug_html("\n".join(section_lines))
                    )

                    # Update section start to the end of the current
                    current_section_start = i

        return Song(parsed_sections, title, artist, capo)

    @staticmethod
    def from_chordpro(text: str):
        title = None
        artist = None
        capo = None

        text = text.replace("\r", "")
        text_lines = text.split("\n")
        parsed_sections = []
        current_section_start = 0

        for i, line in enumerate(text_lines):
            line = line.strip()
            if is_tag(line):
                tag, content = get_tag_items(line)
                current_section_end = i
                next_section_start = i + 1

                if tag.startswith("start_of_"):
                    next_section_start = i
                elif tag.startswith("end_of_"):
                    current_section_end = i + 1
                elif tag == "title":
                    title = content
                elif tag == "artist":
                    artist = content
                elif tag == "capo":
                    capo = content

                if current_section_end > current_section_start:
                    section_lines = text_lines[
                        current_section_start:current_section_end
                    ]
                    parsed_sections.append(
                        Section.from_chordpro("\n".join(section_lines))
                    )
                current_section_start = next_section_start
            elif not line:
                if i > current_section_start:
                    section_lines = text_lines[current_section_start:i]
                    parsed_sections.append(
                        Section.from_chordpro("\n".join(section_lines))
                    )
                current_section_start = i + 1

        if len(text_lines) > current_section_start:
            section_lines = text_lines[current_section_start:]
            parsed_sections.append(Section.from_chordpro("\n".join(section_lines)))

        return Song(parsed_sections, title, artist, capo)

    def transpose(self, interval):
        sections = [section.transpose(interval) for section in self.sections]
        return Song(sections, self.title, self.artist, self.capo)

    def json(self):
        return {
            "sections": [section.json() for section in self.sections],
            "title": self.title,
            "artist": self.artist,
            "capo": self.capo,
            "object_id": self.object_id,
        }

    def json_meta(self):
        return {
            "title": self.title,
            "artist": self.artist,
            "capo": self.capo,
            "object_id": self.object_id,
        }

    @staticmethod
    def from_json(json_dict: Dict):
        parsed_sections = [
            Section.from_json(section) for section in json_dict["sections"]
        ]
        title = json_dict["title"]
        artist = json_dict["artist"]
        capo = json_dict["capo"]
        object_id = json_dict["_id"]

        return Song(parsed_sections, title, artist, capo, object_id)
