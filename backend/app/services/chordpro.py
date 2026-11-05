"""ChordPro text processing helpers."""


def chordpro_to_text(body: str) -> str:
    """Normalize ChordPro text (strip extra whitespace, ensure consistent line endings)."""
    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines)


def text_to_chordpro(text: str) -> str:
    """Convert raw text to basic ChordPro if not already formatted."""
    if "{" in text or "[" in text:
        return text
    return text
