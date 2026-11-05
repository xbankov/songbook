import io
from pathlib import Path

from app.models.settings import Settings
from app.services.music_theory import SongModel
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _build_line_data(line_parts: list) -> dict:
    text_chars = []
    chord_positions = []
    pos = 0
    for part in line_parts:
        if isinstance(part, str):
            text_chars.append(part)
            pos += len(part)
        else:
            chord_positions.append((pos, str(part)))

    text = "".join(text_chars)
    chord_line_chars = []
    inline_parts = []
    last_end = 0
    for cp in chord_positions:
        p, chord_str = cp
        while len(chord_line_chars) < p:
            chord_line_chars.append("\xa0")
        for c in chord_str:
            chord_line_chars.append(c)
        if p > last_end:
            inline_parts.append(text[last_end:p])
        inline_parts.append(f"[{chord_str}]")
        last_end = p
    if last_end < len(text):
        inline_parts.append(text[last_end:])

    chord_line = "".join(chord_line_chars) if chord_positions else ""
    inline_text = "".join(inline_parts) if chord_positions else text

    return {
        "text": text,
        "chord_line": chord_line,
        "inline": inline_text,
    }


def _build_section_data(section) -> dict:
    label = section.label if section.label and section.label != "verse" else None
    lines = [_build_line_data(line.parts) for line in section.lines]
    return {
        "label": label,
        "title": section.title,
        "lines": lines,
    }


def _build_song_data(song: SongModel) -> dict:
    meta_parts = []
    if song.capo:
        meta_parts.append(f"Capo: {song.capo}")
    if song.key:
        meta_parts.append(f"Key: {song.key}")
    return {
        "title": song.title,
        "artist": song.artist,
        "meta": " | ".join(meta_parts),
        "sections": [_build_section_data(s) for s in song.sections],
    }


def _render_song_fpdf(pdf, song: SongModel, settings: Settings):
    if settings.transpose:
        song = song.transpose(settings.transpose)

    pdf.set_font("DejaVu", "B", 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, song.title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(85, 85, 85)
    pdf.cell(0, 6, song.artist, new_x="LMARGIN", new_y="NEXT")

    meta_parts = []
    if song.capo:
        meta_parts.append(f"Capo: {song.capo}")
    if song.key:
        meta_parts.append(f"Key: {song.key}")
    if meta_parts:
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(136, 136, 136)
        pdf.cell(0, 5, " | ".join(meta_parts), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)

    font_name = (
        settings.font
        if settings.font in ("DejaVuMono", "DejaVuSans", "DejaVu")
        else "DejaVuMono"
    )
    display_mode = settings.display_mode
    font_size = settings.font_size

    for section in song.sections:
        if section.label and section.label != "verse":
            label_text = section.title or section.label.capitalize()
            pdf.set_font("DejaVu", "B", 10)
            pdf.set_text_color(139, 69, 19)
            pdf.cell(0, 6, label_text, new_x="LMARGIN", new_y="NEXT")

        for line in section.lines:
            if display_mode == "above":
                chord_chars = {}
                text_chars = []
                for part in line.parts:
                    if isinstance(part, str):
                        text_chars.append(part)
                    else:
                        chord_chars[len("".join(text_chars))] = str(part)

                if chord_chars:
                    pdf.set_font(font_name, "B", font_size)
                    pdf.set_text_color(44, 82, 130)
                    text_line = "".join(text_chars)
                    chord_line = ""
                    for i in range(len(text_line)):
                        chord_line += chord_chars.get(i, " ")
                    pdf.cell(0, 5, chord_line, new_x="LMARGIN", new_y="NEXT")

                pdf.set_font(font_name, "", font_size)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 5, "".join(text_chars), new_x="LMARGIN", new_y="NEXT")
            else:
                pdf.set_font(font_name, "", font_size)
                pdf.set_text_color(0, 0, 0)
                text_parts = []
                for part in line.parts:
                    if isinstance(part, str):
                        text_parts.append(part)
                    else:
                        text_parts.append(f"[{part}]")
                pdf.cell(0, 5, "".join(text_parts), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)


def generate_song_pdf(song: SongModel, settings: Settings) -> io.BytesIO:
    try:
        from weasyprint import HTML

        if settings.transpose:
            song = song.transpose(settings.transpose)
        env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
        template = env.get_template("song_pdf.html")
        data = _build_song_data(song)
        html = template.render(
            title=data["title"],
            artist=data["artist"],
            meta=data["meta"],
            sections=data["sections"],
            double_column=settings.double_column,
            font=settings.font,
            font_size=settings.font_size,
            display_mode=settings.display_mode,
        )
        pdf_bytes = HTML(string=html).write_pdf()
        return io.BytesIO(pdf_bytes)
    except ImportError:
        from fpdf import FPDF

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_font(
            "DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True
        )
        pdf.add_font(
            "DejaVu",
            "B",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            uni=True,
        )
        pdf.add_font(
            "DejaVuMono",
            "",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            uni=True,
        )
        pdf.add_font(
            "DejaVuMono",
            "B",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            uni=True,
        )
        pdf.add_font(
            "DejaVuSans",
            "",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            uni=True,
        )
        pdf.add_font(
            "DejaVuSans",
            "B",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            uni=True,
        )
        pdf.alias_nb_pages()
        pdf.add_page()
        _render_song_fpdf(pdf, song, settings)
        return io.BytesIO(pdf.output())


def generate_songbook_pdf(
    songs: list[SongModel],
    settings: Settings,
    title: str = "Songbook",
    description: str = "",
) -> io.BytesIO:
    try:
        from weasyprint import HTML

        if settings.transpose:
            songs = [s.transpose(settings.transpose) for s in songs]
        env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
        template = env.get_template("songbook_pdf.html")
        songs_data = [_build_song_data(s) for s in songs]
        html = template.render(
            songbook_title=title,
            songbook_description=description,
            songs=songs_data,
            double_column=settings.double_column,
            font=settings.font,
            font_size=settings.font_size,
            display_mode=settings.display_mode,
        )
        pdf_bytes = HTML(string=html).write_pdf()
        return io.BytesIO(pdf_bytes)
    except ImportError:
        from fpdf import FPDF

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_font(
            "DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True
        )
        pdf.add_font(
            "DejaVu",
            "B",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            uni=True,
        )
        pdf.add_font(
            "DejaVuMono",
            "",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            uni=True,
        )
        pdf.add_font(
            "DejaVuMono",
            "B",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            uni=True,
        )
        pdf.add_font(
            "DejaVuSans",
            "",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            uni=True,
        )
        pdf.add_font(
            "DejaVuSans",
            "B",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            uni=True,
        )
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_font("DejaVu", "B", 24)
        pdf.ln(120)
        pdf.cell(0, 12, title, align="C", new_x="LMARGIN", new_y="NEXT")
        if description:
            pdf.set_font("DejaVu", "", 12)
            pdf.set_text_color(85, 85, 85)
            pdf.cell(0, 8, description, align="C", new_x="LMARGIN", new_y="NEXT")
        for song_model in songs:
            pdf.add_page()
            _render_song_fpdf(pdf, song_model, settings)
        return io.BytesIO(pdf.output())
