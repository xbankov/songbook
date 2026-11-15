from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def render_songbook(songs: list[dict]) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    return env.get_template("songbook_pdf.html").render(
        songbook_title="Book",
        songbook_description="",
        songs=songs,
        font="DejaVu Sans Mono",
        font_size=9,
        display_mode="above",
    )


def test_songbook_pdf_has_a_toc_and_per_song_columns():
    html = render_songbook(
        [
            {
                "title": "First",
                "artist": "Artist",
                "meta": "",
                "sections": [],
                "double_column": True,
            },
            {
                "title": "Second",
                "artist": "Artist",
                "meta": "",
                "sections": [],
                "double_column": False,
            },
        ]
    )
    assert "Contents" in html
    assert 'href="#song-1"' in html
    assert 'href="#song-2"' in html
    assert 'id="song-1"' in html
    assert "song-body double-column" in html
    assert "target-counter" in html
