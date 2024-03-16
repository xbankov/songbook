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
