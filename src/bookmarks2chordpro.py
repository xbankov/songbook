import json


import config as config
from helpers import download, extract, normalize


def main():
    print("#####################################################")
    print("## DOWNLOAD & CONVERT BOOKMARKS TO CHORDPRO FORMAT ##")
    print("#####################################################")

    with open(config.FIREFOX_BOOKMARKS_FILE_PATH, "r") as fp:
        bookmarks = json.load(fp)

    toolbar = bookmarks["children"][1]
    music = [folder for folder in toolbar["children"] if folder["title"] == "Music"][0]

    print("#####################################################")
    print("######### EXTRACT CSV FROM BOOKMARKS ################")
    print("#####################################################")
    extract(music, config.CSV_FILE_PATH)

    print("#####################################################")
    print("######### DOWNLOAD HTML OF URLS #####################")
    print("#####################################################")
    download(config.CSV_FILE_PATH)

    print("#####################################################")
    print("######### NORMALIZE CHORDS TXTS #####################")
    print("#####################################################")
    normalize(config.CSV_FILE_PATH)


if __name__ == "__main__":
    main()
