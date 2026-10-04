import importlib.util
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "magazine_translation_pipeline",
    HERE / "magazine_translation_pipeline.py",
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def make_readable(root: Path):
    issue = root / "wired" / "2026-09-02"
    (issue / "blocks").mkdir(parents=True)
    (issue / "articles").mkdir(parents=True)
    (issue / "images").mkdir(parents=True)
    blocks = {
        "seq": 1,
        "title": "Example",
        "epub_path": "OEBPS/article.xhtml",
        "blocks": [
            {"id": "B001", "type": "h1", "text": "Example"},
            {"id": "B002", "type": "p", "text": "Revenue rose 20% in 2026."},
        ],
    }
    (issue / "blocks" / "001-example.json").write_text(
        json.dumps(blocks, ensure_ascii=False), encoding="utf-8"
    )
    (issue / "articles" / "001-example.txt").write_text(
        "Example\n\nRevenue rose 20% in 2026.", encoding="utf-8"
    )
    (issue / "images" / "001-01-figure.jpg").write_bytes(b"fake-jpeg-bytes")
    index = [{
        "seq": 1,
        "title": "Example",
        "epub_path": "OEBPS/article.xhtml",
        "text_file": "articles/001-example.txt",
        "block_file": "blocks/001-example.json",
        "char_count": 34,
        "block_count": 2,
        "images": [{
            "epub_path": "OEBPS/images/figure.jpg",
            "image_file": "images/001-01-figure.jpg",
            "alt": "Useful diagram",
            "size": 15,
        }],
    }]
    (issue / "index.json").write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8"
    )


def test_pipeline():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        readable = root / "readable"
        workspace = root / "workspace"
        mobile = root / "mobile"
        make_readable(readable)

        selection = root / "selection.json"
        selection.write_text(json.dumps({
            "articles": [
                {"publication": "wired", "issue_date": "2026-09-02", "seq": 1}
            ]
        }), encoding="utf-8")
        manifest = mod.init_workspace(readable, workspace, selection)
        assert len(manifest["tasks"]) == 1
        assert manifest["selection_file"] == str(selection)
        task = manifest["tasks"][0]

        batch = mod.next_batch(workspace, max_articles=4, max_blocks=120)
        assert batch["article_count"] == 1
        assert batch["block_count"] == 2
        assert batch["tasks"][0]["task_id"] == task["task_id"]
        assert batch["output_contract"]["translated_title"].startswith("required Simplified Chinese article title")

        translation = {
            "translated_title": "示例",
            "blocks": [
                {"id": "B001", "type": "h1", "text": "示例"},
                {"id": "B002", "type": "p", "text": "收入在2026年增长20%。"},
            ],
        }
        out = Path(task["translation_file"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(translation, ensure_ascii=False), encoding="utf-8")

        report = mod.validate_workspace(workspace)
        assert report["summary"]["pass"] == 1
        assert report["summary"]["fail"] == 0
        assert mod.paragraph_role("作者：David Owen", 2) == "front"
        assert mod.paragraph_role("摄影：某某；编辑：某某", 6) == "front"
        assert mod.paragraph_role("摄影：某某；随后正文开始并继续很长很长很长很长很长很长很长很长很长很长很长很长很长很长。", 6) == "body"
        assert mod.paragraph_role("这是普通中文正文段落。", 6) == "body"
        assert mod.paragraph_role("这是第一段短正文。", 0) == "body"
        refreshed = mod.load_json(workspace / "translation_manifest.json")
        assert refreshed["tasks"][0]["status"] == "pass"
        assert mod.next_batch(workspace)["article_count"] == 0

        built = mod.build_mobile(workspace, mobile)
        assert built["built"] == 1
        assert (mobile / "index.html").exists()
        article_pages = [p for p in mobile.glob("*.html") if p.name != "index.html"]
        assert len(article_pages) == 1
        page = article_pages[0].read_text(encoding="utf-8")
        assert "收入在2026年增长20%" in page
        assert 'name="viewport"' in page
        assert '<img src="images/' in page
        assert any((mobile / "images").iterdir())
        assert page.count("<h1>示例</h1>") == 1
        assert 'class="body"' in page
        assert 'text-indent:2em' in page
        assert 'line-height:1.64' in page
        assert (mobile / "reader.css").exists()

        epub = root / "reader.epub"
        epub_result = mod.build_epub(workspace, epub)
        assert epub_result["built"] == 1
        assert epub.exists()
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(epub) as z:
            assert z.read("mimetype") == b"application/epub+zip"
            assert "EPUB/package.opf" in z.namelist()
            assert "EPUB/nav.xhtml" in z.namelist()
            assert "EPUB/text/chapter-001.xhtml" in z.namelist()
            assert any(name.startswith("EPUB/images/") for name in z.namelist())
            ET.fromstring(z.read("EPUB/package.opf"))
            ET.fromstring(z.read("EPUB/nav.xhtml"))
            chapter = z.read("EPUB/text/chapter-001.xhtml").decode("utf-8")
            ET.fromstring(chapter)
            assert chapter.count("<h1>示例</h1>") == 1
            assert 'class="body"' in chapter
            css = z.read("EPUB/styles/reader.css").decode("utf-8")
            assert "text-indent:2em" in css
            assert "line-height:1.64" in css
            assert "padding:0 .3em" in css
            assert "padding:2rem" not in css
            assert "line-height:1.86" not in css
            assert "margin:5%" not in css

        release = mod.release_check(workspace, mobile, epub)
        assert release["status"] == "pass"
        assert release["expected_articles"] == 1
        assert release["errors"] == []


if __name__ == "__main__":
    test_pipeline()
    print("ok")
