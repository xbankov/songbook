"""Crawl Google Drive + GitHub chord databases and seed the DB.

Sources:
  - SONGBOOK LITE (Google Drive) - Alvin Tostig's ChordPro ZIP (~1,166 files)
  - SONGBOOK (Google Drive)       - full collection (~1,174 files)
  - Bluegrass-Songbook (GitHub)   - 18,157 lead-sheet.pro files locally cloned
  - CHORDONOMICON (Hugging Face)  - 679k song metadata CSV (chord progressions + genres)

Usage:
    python crawler.py                           # crawl all sources
    python crawler.py --lite-only               # only SONGBOOK LITE
    python crawler.py --skip-gdrive             # skip Google Drive sources
    python crawler.py --skip-bluegrass          # skip Bluegrass-Songbook
    python crawler.py --chordonomicon           # also seed CHORDONOMICON metadata
"""
import asyncio
import io
import logging
import os
import re
import zipfile
from pathlib import Path

import requests

from app.database import async_session_factory, init_db
from app.models.song import Song, SongVersion

logger = logging.getLogger("crawler")

CHORDPRO_ZIPS = {
    "songbook-lite": "11RuX4BixJdhjWkuPinwFyoN41yqx2ywx",
    "songbook": "1wNR8iJrSbruzxWNPYCtGu889dAo2RQw-",
}

BLUEGRASS_DIR = "/tmp/bluegrass-songbook/works"
CHORDONOMICON_PATH = "/data/chordonomicon/chordonomicon_v2.csv"

SKIP_PATTERNS = [
    re.compile(r"^#"),
    re.compile(r"^TIP:"),
    re.compile(r"^\{ns\}"),
    re.compile(r"^\{define:"),
    re.compile(r"^\{composer:"),
]

SECTION_MARKER_RE = re.compile(r"\[(\w+)\]\[:\]")


def download_gdrive_file(file_id: str) -> bytes:
    """Download a file from Google Drive, handling the virus scan warning."""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })

    resp = session.get(url, timeout=120)

    for match in re.finditer(r'confirm=([^&\s"]+)', resp.text):
        confirm = match.group(1)
        dl_url = f"https://drive.google.com/uc?export=download&confirm={confirm}&id={file_id}"
        resp = session.get(dl_url, timeout=120)
        break

    return resp.content


def normalize_chordpro(text: str, filename: str = "") -> tuple[str, str, str]:
    """Normalize ChordPro text and extract title/artist.

    Returns (normalized_body, title, artist).
    Title/artist from directives first, then filename fallback.
    """
    lines = text.split("\n")
    cleaned = []
    title = ""
    artist = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if any(p.match(stripped) for p in SKIP_PATTERNS):
            continue

        if stripped.startswith("{") and stripped.endswith("}"):
            content = stripped[1:-1]
            tag_parts = content.split(":", 1)
            tag = tag_parts[0].strip()
            val = tag_parts[1].strip() if len(tag_parts) > 1 else ""

            if tag == "t":
                if not title:
                    title = val
                elif not artist and val != title:
                    artist = val
                continue
            elif tag == "artist":
                artist = val
                continue
            elif tag in ("composer", "ns", "define") or tag.startswith("define"):
                continue

            cleaned.append(stripped)
        elif stripped.startswith("TIP:"):
            continue
        elif stripped.startswith("https://"):
            continue
        elif re.match(r"^[|]", stripped) and re.match(r"^[\s|\[\]A-Za-z0-9#bmM7susadd9/]+$", stripped):
            line_no_bars = stripped.replace("[|]", "").replace("|", "")
            if line_no_bars.strip():
                cleaned.append(line_no_bars)
        else:
            line_fixed = stripped.replace("[|]", " ")
            if "[:]" in line_fixed:
                m = SECTION_MARKER_RE.match(line_fixed)
                if m:
                    section_label = m.group(1).lower()
                    cleaned.append(f"{{start_of_{section_label}}}")
                    rest = line_fixed[m.end():].strip()
                    if rest:
                        cleaned.append(rest)
                else:
                    rest = line_fixed.replace("[:]", "").strip()
                    if rest:
                        cleaned.append(rest)
            else:
                cleaned.append(line_fixed)

    if not title and filename:
        name = Path(filename).stem
        if " - " in name:
            parts = name.split(" - ", 1)
            title = parts[0].strip()
            if not artist:
                artist = parts[1].strip()
        elif name:
            title = name

    body = "\n".join(cleaned)
    return body, title, artist or "Unknown"


def parse_chordpro(body: str) -> dict | None:
    """Parse normalized ChordPro body, extracting metadata and sections.

    Returns dict with title, artist, capo, key, body or None on failure.
    """
    lines = body.split("\n")
    title = "Unknown"
    artist = "Unknown"
    capo = 0
    key = None
    sections = []
    current = []
    in_section = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            content = stripped[1:-1]
            tag_parts = content.split(":", 1)
            tag = tag_parts[0].strip().lower()
            val = tag_parts[1].strip() if len(tag_parts) > 1 else ""

            if tag == "title":
                title = val or title
            elif tag == "artist":
                artist = val or artist
            elif tag == "capo":
                try:
                    capo = int(val)
                except (ValueError, TypeError):
                    capo = 0
            elif tag == "key":
                key = val or key
            elif tag.startswith("start_of_"):
                if current:
                    sections.append("\n".join(current))
                    current = []
                in_section = True
            elif tag.startswith("end_of_"):
                if current:
                    sections.append("\n".join(current))
                    current = []
                in_section = False
            else:
                current.append(line)
        else:
            current.append(line)

    if current:
        sections.append("\n".join(current))

    # Rebuild the body from sections for clean output
    body_parts = []
    for sec in sections:
        sec_lines = sec.strip().split("\n")
        body_parts.append("\n".join(l for l in sec_lines if l.strip()))

    final_body = "\n\n".join(p for p in body_parts if p.strip())
    if not final_body.strip():
        return None

    return {
        "title": title,
        "artist": artist,
        "capo": capo,
        "key": key,
        "body": body_parts if body_parts else [],
    }


def merge_body_parts(parts: list[str]) -> str:
    """Merge body parts into a final ChordPro string."""
    merged = []
    for p in parts:
        merged.append(p.strip())
    return "\n\n".join(p for p in merged if p)


async def seed_from_zip(file_id: str, source: str) -> dict:
    """Download ChordPro ZIP from Google Drive, extract, parse, and seed DB.

    Returns stats dict.
    """
    stats = {"downloaded": 0, "imported": 0, "skipped": 0, "errors": 0, "duplicates": 0}

    logger.info("Downloading %s ZIP...", source)
    try:
        data = download_gdrive_file(file_id)
    except Exception as e:
        logger.error("Download failed for %s: %s", source, e)
        return stats

    logger.info("Downloaded %d bytes for %s", len(data), source)

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        logger.error("Bad ZIP for %s: %s", source, e)
        return stats

    pro_files = []
    for name in zf.namelist():
        lower = name.lower()
        if lower.endswith(".pro") or lower.endswith(".chordpro"):
            pro_files.append(name)

    pro_files.sort()
    stats["downloaded"] = len(pro_files)
    logger.info("Found %d ChordPro files in %s", len(pro_files), source)

    async with async_session_factory() as session:
        for i, name in enumerate(pro_files):
            try:
                raw = zf.read(name).decode("utf-8", errors="replace")
            except Exception as e:
                logger.warning("Cannot read %s in ZIP: %s", name, e)
                stats["errors"] += 1
                continue

            body, title, artist = normalize_chordpro(raw, Path(name).name)
            if not body.strip():
                stats["skipped"] += 1
                continue

            parsed = parse_chordpro(body)
            if parsed is None:
                stats["skipped"] += 1
                continue

            song = Song(
                title=parsed["title"] or title,
                artist=parsed["artist"] or artist,
                capo=parsed["capo"],
                key=parsed.get("key"),
                body=merge_body_parts(parsed["body"]),
                metadata_={
                    "imported_from": f"gdrive/{source}/{name}",
                },
            )
            session.add(song)
            await session.flush()
            await session.refresh(song)

            version = SongVersion(
                song_id=song.id, version=1,
                title=song.title, artist=song.artist,
                capo=song.capo, key=song.key, body=song.body,
            )
            session.add(version)
            stats["imported"] += 1

            if stats["imported"] % 100 == 0:
                await session.commit()
                logger.info("  Progress: %d/%d imported from %s",
                            stats["imported"], len(pro_files), source)

        await session.commit()

    logger.info("Done %s: %d/%d imported (%d skipped, %d errors)",
                source, stats["imported"], len(pro_files),
                stats["skipped"], stats["errors"])
    return stats


async def seed_from_local_files(path: str, source: str) -> dict:
    """Walk a directory of ChordPro files and seed the DB.

    Expected structure: path/<song-dir>/lead-sheet.pro
    """
    stats = {"discovered": 0, "imported": 0, "skipped": 0, "errors": 0}

    pro_files = sorted(Path(path).rglob("lead-sheet.pro"))
    if not pro_files:
        pro_files = sorted(Path(path).rglob("*.pro"))
    if not pro_files:
        pro_files = sorted(Path(path).rglob("*.chordpro"))

    stats["discovered"] = len(pro_files)
    if not pro_files:
        logger.warning("No ChordPro files found in %s", path)
        return stats

    logger.info("Found %d ChordPro files in %s", len(pro_files), source)

    async with async_session_factory() as session:
        for i, filepath in enumerate(pro_files):
            try:
                raw = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.warning("Cannot read %s: %s", filepath, e)
                stats["errors"] += 1
                continue

            body, title, artist = normalize_chordpro(raw, filepath.stem)
            if not body.strip():
                stats["skipped"] += 1
                continue

            parsed = parse_chordpro(body)
            if parsed is None:
                stats["skipped"] += 1
                continue

            song = Song(
                title=parsed["title"] or title,
                artist=parsed["artist"] or artist,
                capo=parsed["capo"],
                key=parsed.get("key"),
                body=merge_body_parts(parsed["body"]),
                metadata_={
                    "imported_from": f"local/{source}/{filepath.relative_to(path).as_posix()}",
                },
            )
            session.add(song)
            await session.flush()
            await session.refresh(song)

            version = SongVersion(
                song_id=song.id, version=1,
                title=song.title, artist=song.artist,
                capo=song.capo, key=song.key, body=song.body,
            )
            session.add(version)
            stats["imported"] += 1

            if stats["imported"] % 200 == 0:
                await session.commit()
                logger.info("  Progress: %d/%d imported from %s",
                            stats["imported"], stats["discovered"], source)

        await session.commit()

    logger.info("Done %s: %d/%d imported (%d skipped, %d errors)",
                source, stats["imported"], stats["discovered"],
                stats["skipped"], stats["errors"])
    return stats


async def main(lite_only: bool = False, skip_gdrive: bool = False,
               skip_bluegrass: bool = False):
    await init_db()
    total = {"imported": 0, "skipped": 0, "errors": 0}

    # Google Drive sources
    if not skip_gdrive:
        targets = {"songbook-lite": CHORDPRO_ZIPS["songbook-lite"]}
        if not lite_only:
            targets["songbook"] = CHORDPRO_ZIPS["songbook"]

        for source, file_id in targets.items():
            logger.info("=== Crawling %s ===", source)
            stats = await seed_from_zip(file_id, source)
            for k in total:
                total[k] += stats.get(k, 0)
    else:
        logger.info("Skipping Google Drive sources")

    # Bluegrass-Songbook local clone
    if not skip_bluegrass:
        bg_path = os.environ.get("BLUEGRASS_DIR", BLUEGRASS_DIR)
        if os.path.isdir(bg_path):
            logger.info("=== Crawling Bluegrass-Songbook ===")
            stats = await seed_from_local_files(bg_path, "bluegrass")
            for k in total:
                total[k] += stats.get(k, 0)
        else:
            logger.warning("Bluegrass-Songbook directory not found at %s", bg_path)
    else:
        logger.info("Skipping Bluegrass-Songbook")

    logger.info("=== CRAWL COMPLETE ===")
    logger.info("Total imported: %d, skipped: %d, errors: %d",
                total["imported"], total["skipped"], total["errors"])


if __name__ == "__main__":
    import sys
    lite_only = "--lite-only" in sys.argv
    skip_gdrive = "--skip-gdrive" in sys.argv
    skip_bluegrass = "--skip-bluegrass" in sys.argv
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(main(lite_only=lite_only, skip_gdrive=skip_gdrive, skip_bluegrass=skip_bluegrass))
