import io
import zipfile

from magazine_epub_extract import choose_issue, parse_epub


def make_epub():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""",
        )
        z.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
 <manifest>
  <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
  <item id="a1" href="article1.xhtml" media-type="application/xhtml+xml"/>
  <item id="img1" href="images/figure.jpg" media-type="image/jpeg"/>
 </manifest>
 <spine><itemref idref="a1"/></spine>
</package>""",
        )
        z.writestr(
            "OEBPS/nav.xhtml",
            """<html xmlns="http://www.w3.org/1999/xhtml"><body><nav><ol>
<li><a href="article1.xhtml">A Better Title</a></li>
</ol></nav></body></html>""",
        )
        z.writestr(
            "OEBPS/article1.xhtml",
            "<html><head><title>Fallback</title></head><body><h1>Heading</h1>"
            '<img src="images/figure.jpg" alt="Useful diagram"/><p>'
            + "Useful article body. " * 20
            + "</p></body></html>",
        )
        z.writestr("OEBPS/images/figure.jpg", b"fake-jpeg-bytes")
    return buf.getvalue()


def test_parse_epub_prefers_toc_title_and_extracts_text():
    docs = parse_epub(make_epub())
    assert len(docs) == 1
    assert docs[0]["title"] == "A Better Title"
    assert "Useful article body." in docs[0]["text"]
    assert len(docs[0]["text"]) > 120
    assert docs[0]["images"] == [{"epub_path": "OEBPS/images/figure.jpg", "alt": "Useful diagram"}]
    assert docs[0]["blocks"]
    assert docs[0]["blocks"][0]["type"] == "h1"
    assert docs[0]["blocks"][0]["text"] == "Heading"
    assert any(
        block["type"] == "p" and "Useful article body." in block["text"]
        for block in docs[0]["blocks"]
    )



def test_choose_issue_supports_exact_historical_date():
    items = [
        {"type": "dir", "name": "te_2025.05.03", "path": "root/te_2025.05.03"},
        {"type": "dir", "name": "te_2026.05.16", "path": "root/te_2026.05.16"},
    ]
    issue_date, item = choose_issue(items, "root", "2025-05-03")
    assert issue_date.isoformat() == "2025-05-03"
    assert item["path"].endswith("te_2025.05.03")


def test_choose_issue_defaults_to_latest():
    items = [
        {"type": "dir", "name": "te_2025.05.03", "path": "root/te_2025.05.03"},
        {"type": "dir", "name": "te_2026.05.16", "path": "root/te_2026.05.16"},
    ]
    issue_date, item = choose_issue(items, "root")
    assert issue_date.isoformat() == "2026-05-16"
    assert item["path"].endswith("te_2026.05.16")



def test_choose_issue_accepts_child_year_directory_items():
    items = [
        {"type": "dir", "name": "2025", "path": "01_economist/2025"},
        {"type": "dir", "name": "te_2025.05.03", "path": "01_economist/2025/te_2025.05.03"},
        {"type": "dir", "name": "te_2026.05.16", "path": "01_economist/te_2026.05.16"},
    ]
    issue_date, item = choose_issue(items, "01_economist", "2025-05-03")
    assert issue_date.isoformat() == "2025-05-03"
    assert item["path"] == "01_economist/2025/te_2025.05.03"
