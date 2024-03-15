import config as config
from helpers import normalize_txt


def main():
    config.init_dirs()

    raw_file_path = config.RAW_DIR / "tabs.ultimate-guitar.com&tab&elvis-presley&jailhouse-rock-chords-79693.html"
    normalized_file_path = config.NORMALIZED_DIR / f"jailhouse-rock.txt"

    normalize_txt(raw_file_path, normalized_file_path)


if __name__ == "__main__":
    main()
