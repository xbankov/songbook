from urllib.parse import quote


def content_disposition(filename: str, inline: bool = False) -> str:
    """Build a safe Content-Disposition value for any filename."""
    safe = "".join(char for char in filename if char not in "\r\n").strip()
    safe = safe or "download"
    ascii_name = safe.encode("ascii", "ignore").decode() or "download"
    ascii_name = ascii_name.replace('"', "'")
    disposition = "inline" if inline else "attachment"
    return f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(safe)}"
