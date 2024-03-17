import config as config
from helpers import normalize_txt
from src.model.song import Song


def main():
    config.init_dirs()

    #raw_file_path = config.RAW_DIR / "tabs.ultimate-guitar.com&tab&elvis-presley&jailhouse-rock-chords-79693.html"
    raw_file_path = config.RAW_DIR / "tabs.ultimate-guitar.com&tab&chris-isaak&wicked-game-chords-11066.html"
    normalized_file_path = config.NORMALIZED_DIR / f"wicked-game.txt"
    regenerated_file_path = config.NORMALIZED_DIR / f"wicked-game-regenerated.txt"

    normalize_txt(raw_file_path, normalized_file_path)

    with open(normalized_file_path, "r", encoding="utf-8") as f:
        content = f.read()
    song = Song.parse(content)

    with open(regenerated_file_path, "w", encoding="utf-8") as f:
        f.write(str(song))


if __name__ == "__main__":
    main()
