import re
import pdfkit
import config as config
from helpers import load_text
from jinja2 import Environment, FileSystemLoader


def main():

    print("#####################################################")
    print("######### CONVERT CHORDPRO TO HTML ##################")
    print("#####################################################")
    chordpro2html(config.MANUAL_NORMALIZED_DIR, config.HTML_DIR)

    print("#####################################################")
    print("######### CONVERT HTML TO PDF #######################")
    print("#####################################################")
    html2pdf(config.HTML_DIR, config.PDF_DIR)

    print("#####################################################")
    print("######### COMPILE PDF INTO BOOK  ####################")
    print("#####################################################")
    pdfs2book(config.PDF_DIR)


def chordpro2html(norm_dir, html_dir):
    for norm_file_path in norm_dir.iterdir():
        norm_text = load_text(norm_file_path)
        html_file_path = html_dir / f"{norm_file_path.stem}.html"

        env = Environment(loader=FileSystemLoader("."))
        song_template = env.get_template(config.TEMPLATE_HTML)

        title=None
        title_match = re.search(r"\{title: (.+)\}", norm_text)
        if title_match:
            title = title_match.group(1)
            norm_text = re.sub(r"\{title: (.+?)\}", "", norm_text)

        capo_match = re.search(r"\{capo: (.+)\}", norm_text)
        capo = None
        if capo_match:
            capo = capo_match.group(1)
            norm_text = re.sub(r"\{capo: (.+?)\}", "", norm_text)
            

        song_lines = [d.strip() for d in norm_text.split("\n") if len(d) != 0]
        song_rendered = song_template.render(title=title, capo=capo, content=song_lines)
        with open(html_file_path, "w") as output_file:
            output_file.write(song_rendered)


def html2pdf(html_dir, pdf_dir):
    config = pdfkit.configuration(wkhtmltopdf="/usr/bin/wkhtmltopdf")
    options = {"--enable-local-file-access": ""}
    css = "src/static/styles.css"
    for html_file_path in html_dir.iterdir():
        pdf_file_path =  pdf_dir / f"{html_file_path.stem}.pdf"
        pdfkit.from_file(
            str(html_file_path), str(pdf_file_path), css=css, configuration=config, options=options
        )



def pdfs2book(pdf_dir):
    pass


if __name__ == "__main__":
    main()
