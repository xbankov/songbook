"""Seed the database with public-domain songs for a quick start."""
import asyncio
import logging

from sqlalchemy import select

from app.database import async_session_factory, init_db
from app.models.song import Song, SongVersion

logger = logging.getLogger(__name__)

SEED_SONGS = [
    {
        "title": "Knockin' on Heaven's Door",
        "artist": "Bob Dylan",
        "body": """{title: Knockin' on Heaven's Door}
{artist: Bob Dylan}
{capo: 0}
{key: G}

{start_of_verse}
[G]Mama, take this [D]badge off of [Am]me
[Am]I can't [G]use it any[D]more
[G]It's getting dark, too [D]dark to [Am]see
[Am]Feels like I'm [G]knockin' on heaven's [D]door
{end_of_verse}

{start_of_chorus}
[G]Knock, knock, [D]knockin' on [Am]heaven's door
[Am]Knock, knock, [G]knockin' on heaven's [D]door
{end_of_chorus}""",
    },
    {
        "title": "House of the Rising Sun",
        "artist": "Traditional",
        "body": """{title: House of the Rising Sun}
{artist: Traditional}
{capo: 0}
{key: Am}

{start_of_verse}
[Am]There is a [C]house in [D]New Or-[F]leans
[Am]They call the [C]Rising [E]Sun
[Am]And it's [C]been the [D]ruin of many a [F]poor boy
[Am]And [E]God I [Am]know I'm one
{end_of_verse}""",
    },
    {
        "title": "Wish You Were Here",
        "artist": "Pink Floyd",
        "body": """{title: Wish You Were Here}
{artist: Pink Floyd}
{capo: 0}
{key: Em}

{start_of_verse}
[Em]So, so you [G]think you can [Am]tell
[C]Heaven from [D]hell?
[Em]Blue skies from [G]pain?
[Am]Can you tell a [C]green field from a [D]cold steel rail?
[Em]A smile from a [G]veil?
[Am]Do you think you can [C]tell? [D]
{end_of_verse}""",
    },
    {
        "title": "Nothing Else Matters",
        "artist": "Metallica",
        "body": """{title: Nothing Else Matters}
{artist: Metallica}
{capo: 0}
{key: Em}

{start_of_verse}
[Em]So close, no [D]matter how [C]far
[Em]Couldn't be much [D]more from the [C]heart
[Em]Forever trust-[D]ing who we [C]are
[G]And nothing else [B7]matters
{end_of_verse}""",
    },
    {
        "title": "Blowin' in the Wind",
        "artist": "Bob Dylan",
        "body": """{title: Blowin' in the Wind}
{artist: Bob Dylan}
{capo: 0}
{key: G}

{start_of_verse}
[G]How many [C]roads must a [D]man walk [G]down
[G]Before you [C]call him a [D]man?
[G]How many [C]seas must a [D]white dove [G]sail
[Em]Before she [C]sleeps in the [D]sand?
{end_of_verse}""",
    },
    {
        "title": "Brown Eyed Girl",
        "artist": "Van Morrison",
        "body": """{title: Brown Eyed Girl}
{artist: Van Morrison}
{capo: 0}
{key: G}

{start_of_verse}
[G]Hey where did we [C]go?
[G]Days when the [C]rains came
[G]Down in the [C]hollow
[G]Playin' a new [D]game
{end_of_verse}

{start_of_chorus}
[G]Do you re-[C]member when
[G]We used to [C]sing
[G]Sha la la la [D]la la la la la [G]te da
{end_of_chorus}""",
    },
    {
        "title": "Let It Be",
        "artist": "The Beatles",
        "body": """{title: Let It Be}
{artist: The Beatles}
{capo: 0}
{key: C}

{start_of_verse}
[C]When I find myself in [G]times of trouble
[Am]Mother Mary [F]comes to me
[C]Speaking words of [G]wisdom, let it [F]be [C]
{end_of_verse}

{start_of_chorus}
[Am]Let it [C]be, let it [G]be, let it [F]be, let it [C]be
[C]Whisper words of [G]wisdom, let it [F]be [C]
{end_of_chorus}""",
    },
    {
        "title": "Wonderwall",
        "artist": "Oasis",
        "body": """{title: Wonderwall}
{artist: Oasis}
{capo: 2}
{key: Em}

{start_of_verse}
[Em]Today is gonna be the [G]day that they're gonna
[D]Throw it back to [A]you
[Em]By now you should've somehow
[G]Realized what you gotta [D]do [A]
{end_of_verse}

{start_of_chorus}
[Em]And after [G]all
[D]You're my [A]wonderwall
{end_of_chorus}""",
    },
    {
        "title": "Hallelujah",
        "artist": "Leonard Cohen",
        "body": """{title: Hallelujah}
{artist: Leonard Cohen}
{capo: 0}
{key: C}

{start_of_verse}
[C]Now I've heard there was a [Am]secret chord
[C]That David played and it [Am]pleased the Lord
[F]But you don't really [G]care for music, [C]do you? [G]
{end_of_verse}""",
    },
    {
        "title": "Hey Jude",
        "artist": "The Beatles",
        "body": """{title: Hey Jude}
{artist: The Beatles}
{capo: 0}
{key: F}

{start_of_verse}
[F]Hey Jude, [C]don't make it [F]bad
[F]Take a [C]sad song and [F]make it [C]better
[F]Remember to [C]let her into your [F]heart
[C]Then you can [F]start to make it [C]better [F]
{end_of_verse}""",
    },
]


async def seed():
    await init_db()
    async with async_session_factory() as session:
        result = await session.execute(select(Song).limit(1))
        if result.scalar_one_or_none():
            logger.info("Database already has songs, skipping seed.")
            return

        for data in SEED_SONGS:
            song = Song(
                title=data["title"],
                artist=data["artist"],
                body=data["body"],
                capo=data.get("capo", 0),
                key=data.get("key"),
            )
            session.add(song)
            await session.flush()
            await session.refresh(song)
            version = SongVersion(
                song_id=song.id,
                version=1,
                title=song.title,
                artist=song.artist,
                capo=song.capo,
                key=song.key,
                body=song.body,
            )
            session.add(version)

        await session.commit()
        logger.info(f"Seeded {len(SEED_SONGS)} songs.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())
