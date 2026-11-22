# /// script
# requires-python = ">=3.10"
# dependencies = ["fonttools==4.61.1", "brotli==1.2.0"]
# ///

from base64 import b64encode
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from fontTools import subset
from fontTools.ttLib import TTFont


class DocumentText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_data = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip_data = True

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip_data = False

    def handle_data(self, data):
        if not self.skip_data:
            self.parts.append(data)


def woff2_url(data):
    return "data:font/woff2;base64," + b64encode(data).decode("ascii")


def subset_font(original, text, style, license_text):
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=text)

    output = BytesIO()
    with TTFont(BytesIO(original), recalcTimestamp=False) as font:
        subsetter.subset(font)
        names = font["name"]
        postscript_name = f"MyBatisGuideSans-{style}"
        replacements = {
            1: "MyBatis Guide Sans",
            3: postscript_name,
            4: f"MyBatis Guide Sans {style}",
            6: postscript_name,
        }
        for record in names.names:
            if record.nameID in replacements:
                record.string = replacements[record.nameID]
        names.setName(license_text, 13, 3, 1, 0x409)
        font.save(output)
    return output.getvalue()


def main():
    root = Path(__file__).resolve().parents[1]
    html_path = root / "dist" / "index.html"
    fonts = root / "fonts"
    html = html_path.read_text(encoding="utf-8")

    parser = DocumentText()
    parser.feed(html)
    parser.close()
    text = "".join(parser.parts)
    # Include uppercase forms for labels styled with CSS text-transform.
    characters = "".join(sorted(set(text + text.upper())))
    license_text = (fonts / "IBM-Plex-Sans-KR-OFL.txt").read_text(encoding="utf-8")

    for suffix, style in [("regular", "Regular"), ("700", "Bold")]:
        original = (fonts / f"ibm-plex-sans-kr-v11-korean_latin-{suffix}.woff2").read_bytes()
        original_url = woff2_url(original)
        if html.count(original_url) != 1:
            raise RuntimeError(f"Expected one embedded IBM Plex Sans KR {style} font")
        reduced = subset_font(original, characters, style, license_text)
        html = html.replace(original_url, woff2_url(reduced), 1)
        print(f"MyBatis Guide Sans {style}: {len(original):,} -> {len(reduced):,} bytes")

    with TemporaryDirectory(dir=html_path.parent) as directory:
        temporary = Path(directory) / html_path.name
        temporary.write_bytes(html.encode("utf-8"))
        temporary.replace(html_path)

    print(f"dist/index.html: {html_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
