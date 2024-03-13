import config as config
from helpers import chordpro2html


def main():
    
    print("#####################################################")
    print("######### CONVERT CHORDPRO TO HTML ##################")
    print("#####################################################")
    chordpro2html(config.MANUAL_NORMALIZED_DIR, config.HTML_DIR)

    print("#####################################################")
    print("######### CONVERT HTML TO PDF #######################")
    print("#####################################################")
    song2bookhtml(config.HTML_DIR, config.PDF_DIR)


def pdfs2book(pdf_dir):
    pass


if __name__ == "__main__":
    main()
