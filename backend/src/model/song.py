from __future__ import annotations
from src.helpers import get_tag_items, is_tag
from src.model.composition import Chord


class Line:
    def __init__(self, parts):
        self.parts = parts

    def __str__(self):
        string_parts = [
            f"[{part}]" if isinstance(part, Chord) else str(part)
            for part
            in self.parts
        ]
        return "".join(string_parts)

    @staticmethod
    def parse(text: str):
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
            for part
            in self.parts
        ]
        return Line(parts)


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
    def parse(text: str):
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
                elif label is not None and i == len(text_lines) - 1 and line == f"{{end_of_{label}}}":
                    pass
            elif line:
                parsed_lines.append(Line.parse(line))

        return Section(parsed_lines, label, title)

    def transpose(self, interval):
        lines = [line.transpose(interval) for line in self.lines]
        return Section(lines, self.label, self.title)


class Song:
    def __init__(self, sections: list[Section], title: str, artist: str, capo: str = None):
        # TODO VB capo should be int
        self.sections = sections
        self.title = title
        self.artist = artist
        self.capo = capo

    def __str__(self):
        string_sections = [
            f"{{title: {self.title}}}",
            f"{{artist: {self.artist}}}"
        ]

        if self.capo is not None:
            string_sections.append(f"{{capo: {self.capo}}}")

        for section in self.sections:
            string_sections.append(str(section))

        return "\n\n".join(string_sections)

    @staticmethod
    def parse(text: str):
        title = None
        artist = None
        capo = None

        text_lines = text.split("\n")
        parsed_sections = []
        current_section_start = 0

        for i, line in enumerate(text_lines):
            if is_tag(line):
                tag, content = get_tag_items(line)
                current_section_end = i
                next_section_start = i+1

                if tag.startswith("start_of_"):
                    next_section_start = i
                elif tag.startswith("end_of_"):
                    current_section_end = i+1
                elif tag == "title":
                    title = content
                elif tag == "artist":
                    artist = content
                elif tag == "capo":
                    capo = content

                if current_section_end > current_section_start:
                    section_lines = text_lines[current_section_start: current_section_end]
                    parsed_sections.append(Section.parse("\n".join(section_lines)))
                current_section_start = next_section_start
            elif not line:
                if i > current_section_start:
                    section_lines = text_lines[current_section_start: i]
                    parsed_sections.append(Section.parse("\n".join(section_lines)))
                current_section_start = i+1

        if len(text_lines) > current_section_start:
            section_lines = text_lines[current_section_start:]
            parsed_sections.append(Section.parse("\n".join(section_lines)))

        return Song(parsed_sections, title, artist, capo)

    def transpose(self, interval):
        sections = [section.transpose(interval) for section in self.sections]
        return Song(sections, self.title, self.artist, self.capo)

