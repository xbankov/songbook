import logging

import musicbrainzngs

logger = logging.getLogger(__name__)

musicbrainzngs.set_useragent("Songbook", "1.0", "https://songbook.local")


def lookup_artist(artist_name: str) -> dict | None:
    try:
        result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        if result.get("artist-list"):
            artist = result["artist-list"][0]
            return {
                "mbid": artist.get("id"),
                "name": artist.get("name"),
                "type": artist.get("type"),
                "country": artist.get("country"),
                "disambiguation": artist.get("disambiguation"),
            }
    except Exception as e:
        logger.warning(f"MusicBrainz lookup failed for artist '{artist_name}': {e}")
    return None


def lookup_recording(song_title: str, artist_name: str) -> dict | None:
    try:
        result = musicbrainzngs.search_recordings(
            query=song_title, artistname=artist_name, limit=1
        )
        if result.get("recording-list"):
            rec = result["recording-list"][0]
            return {
                "mbid": rec.get("id"),
                "title": rec.get("title"),
                "length": rec.get("length"),
                "artist": (
                    rec.get("artist-credit", [{}])[0].get("name")
                    if rec.get("artist-credit")
                    else None
                ),
            }
    except Exception as e:
        logger.warning(
            f"MusicBrainz lookup failed for '{song_title}' by '{artist_name}': {e}"
        )
    return None
