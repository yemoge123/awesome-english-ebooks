#!/usr/bin/env python3
import argparse
import html
import json
import posixpath
import re
import shutil
import uuid
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

TRANSLATION_SUFFIX = ".translation.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def issue_indexes(readable_root):
    root = Path(readable_root)
    return sorted(root.glob("*/*/index.json"))


def load_selection(path):
    if not path:
        return None
    data = load_json(path)
    selected = set()
    for item in data.get("articles", []):
        publication = str(item.get("publication", "")).strip()
        issue_date = str(item.get("issue_date", "")).strip()
        seq = int(item.get("seq"))
        selected.add((publication, issue_date, seq))
    return selected


def init_workspace(readable_root, workspace, selection=None):
    workspace = Path(workspace)
    selected = load_selection(selection)
    tasks = []
    for index_path in issue_indexes(readable_root):
        index = load_json(index_path)
        issue_dir = index_path.parent
        publication = issue_dir.parent.name
        issue_date = issue_dir.name
        for item in index:
            key = (publication, issue_date, int(item["seq"]))
            if selected is not None and key not in selected:
                continue
            block_file = issue_dir / item["block_file"]
            payload = load_json(block_file)
            task_id = f"{publication}-{issue_date}-{int(item['seq']):03d}"
            out = workspace / "translations" / f"{task_id}{TRANSLATION_SUFFIX}"
            task = {
                "task_id": task_id,
                "publication": publication,
                "issue_date": issue_date,
                "seq": item["seq"],
                "title": item["title"],
                "source_text_file": str((issue_dir / item["text_file"]).as_posix()),
                "source_block_file": str(block_file.as_posix()),
                "source_issue_dir": str(issue_dir.as_posix()),
                "source_epub": item.get("source_epub"),
                "source_sha": item.get("source_sha"),
                "source_block_count": item.get("block_count", len(payload.get("blocks", []))),
                "images": item.get("images", []),
                "translation_file": str(out.as_posix()),
                "status": "translated" if out.exists() else "pending",
            }
            tasks.append(task)
    manifest = {
        "schema_version": 1,
        "translation_profile": "MAGAZINE_TRANSLATION_PROFILE.md",
        "selection_file": str(selection) if selection else None,
        "tasks": tasks,
    }
    write_json(workspace / "translation_manifest.json", manifest)
    return manifest


def ids(blocks):
    return [str(x.get("id", "")) for x in blocks]


def numeric_tokens(text):
    return re.findall(r"(?<![A-Za-z])[-+]?\d+(?:[.,]\d+)*(?:%|%|°[CF])?", text)


def validate_one(task):
    source = load_json(task["source_block_file"])
    translation_path = Path(task["translation_file"])
    errors = []
    warnings = []
    if not translation_path.exists():
        return {"task_id": task["task_id"], "status": "pending", "errors": [], "warnings": []}

    translated = load_json(translation_path)
    src_blocks = source.get("blocks", [])
    dst_blocks = translated.get("blocks", [])
    src_ids = ids(src_blocks)
    dst_ids = ids(dst_blocks)

    if len(dst_ids) != len(set(dst_ids)):
        errors.append("duplicate translation block ids")
    missing = [x for x in src_ids if x not in dst_ids]
    extra = [x for x in dst_ids if x not in src_ids]
    if missing:
        errors.append("missing blocks: " + ",".join(missing))
    if extra:
        errors.append("extra blocks: " + ",".join(extra))
    if src_ids != dst_ids:
        errors.append("block order mismatch")

    for src, dst in zip(src_blocks, dst_blocks):
        if src.get("id") != dst.get("id"):
            continue
        target_text = str(dst.get("text", "")).strip()
        if not target_text:
            errors.append(f"{src['id']}: empty translation")
            continue
        s_nums = numeric_tokens(str(src.get("text", "")))
        d_nums = numeric_tokens(target_text)
        if sorted(s_nums) != sorted(d_nums):
            warnings.append(f"{src['id']}: numeric tokens differ: {s_nums} -> {d_nums}")

    status = "pass" if not errors else "fail"
    if status == "pass" and warnings:
        status = "review"
    return {"task_id": task["task_id"], "status": status, "errors": errors, "warnings": warnings}


def validate_workspace(workspace):
    workspace = Path(workspace)
    manifest_path = workspace / "translation_manifest.json"
    manifest = load_json(manifest_path)
    results = [validate_one(t) for t in manifest["tasks"]]
    summary = {
        "pass": sum(x["status"] == "pass" for x in results),
        "review": sum(x["status"] == "review" for x in results),
        "fail": sum(x["status"] == "fail" for x in results),
        "pending": sum(x["status"] == "pending" for x in results),
    }
    report = {"summary": summary, "results": results}
    write_json(workspace / "qa_report.json", report)
    status_by_id = {x["task_id"]: x["status"] for x in results}
    for task in manifest["tasks"]:
        task["status"] = status_by_id.get(task["task_id"], task.get("status", "pending"))
    write_json(manifest_path, manifest)
    return report


def next_batch(workspace, max_articles=4, max_blocks=120, out_file=None):
    workspace = Path(workspace)
    manifest = load_json(workspace / "translation_manifest.json")
    # Refresh statuses from actual translation files before selecting work.
    validate_workspace(workspace)
    manifest = load_json(workspace / "translation_manifest.json")
    selected = []
    used_blocks = 0
    for task in manifest["tasks"]:
        if task.get("status") != "pending":
            continue
        count = int(task.get("source_block_count") or 0)
        if selected and (len(selected) >= max_articles or used_blocks + count > max_blocks):
            break
        payload = load_json(task["source_block_file"])
        selected.append({
            "task_id": task["task_id"],
            "publication": task["publication"],
            "issue_date": task["issue_date"],
            "seq": task["seq"],
            "title": task["title"],
            "translation_file": task["translation_file"],
            "blocks": payload.get("blocks", []),
        })
        used_blocks += count
        if len(selected) >= max_articles or used_blocks >= max_blocks:
            break
    batch = {
        "schema_version": 1,
        "translation_profile": manifest.get("translation_profile"),
        "article_count": len(selected),
        "block_count": used_blocks,
        "tasks": selected,
    }
    if out_file:
        write_json(out_file, batch)
    return batch


FRONT_RE = re.compile(
    r"^(?:作者|摄影(?:合成)?|插图|图|图注|图片合成|来源|译者|编辑|说明|美甲)[:：]|"
    r"^\d{4}年\d{1,2}月\d{1,2}日|"
    r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"
)


def paragraph_role(text, block_index=0):
    value = str(text or "").strip()
    if value.startswith("说明：") or value.startswith("说明:"):
        return "note"
    if FRONT_RE.search(value) and len(value) <= 80:
        return "front"
    if block_index < 2 and len(value) <= 40:
        return "front"
    return "body"


def safe_slug(text):
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-").lower()
    return value[:100] or "article"


CSS = """
:root{color-scheme:light dark}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.86;background:#f5f5f7;color:#1d1d1f}
main{max-width:760px;margin:auto;background:#fff;min-height:100vh;padding:28px 20px 56px}
a{color:inherit}
h1{font-size:1.75rem;line-height:1.28;margin:.2em 0 .35em}
h2,h3{line-height:1.38;margin:1.65em 0 .65em}
.meta{font-size:.88rem;color:#6e6e73;margin-bottom:1.55rem;overflow-wrap:anywhere;word-break:break-word}
p.body{font-size:1.08rem;text-indent:2em;margin:0 0 .72em}
p.front,p.caption,p.note,p.li{font-size:1rem;text-indent:0;margin:.35em 0 .65em}
p.front,p.caption{color:#666}
p.note{padding:.8em 1em;background:rgba(128,128,128,.08);border-radius:8px}
p.li{padding-left:1.2em}
blockquote{font-size:1.05rem;text-indent:0;border-left:3px solid #aaa;padding-left:1em;margin:1em 0}
pre{white-space:pre-wrap;overflow-wrap:anywhere}
figure{margin:1.35em 0;break-inside:avoid} img{display:block;max-width:100%;height:auto;margin:auto;border-radius:8px}
nav a{display:block;padding:.9em 0;border-bottom:1px solid #ddd;text-decoration:none}
.back{font-size:.9rem;margin-bottom:1.2rem;display:inline-block}
@media(prefers-color-scheme:dark){body{background:#000;color:#f5f5f7}main{background:#111}.meta,p.front,p.caption{color:#aaa}nav a{border-color:#333}}
"""


def build_mobile(workspace, out_dir):
    workspace = Path(workspace)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    images_out = out_dir / "images"
    images_out.mkdir(parents=True, exist_ok=True)
    manifest = load_json(workspace / "translation_manifest.json")
    qa = validate_workspace(workspace)
    status_by_id = {x["task_id"]: x["status"] for x in qa["results"]}
    links = []

    for task in manifest["tasks"]:
        if status_by_id.get(task["task_id"]) not in {"pass", "review"}:
            continue
        tr = load_json(task["translation_file"])
        title = tr.get("translated_title") or task["title"]
        slug = safe_slug(task["task_id"] + "-" + title) + ".html"
        body = []
        for block_index, block in enumerate(tr.get("blocks", [])):
            tag = block.get("type", "p")
            raw_text = str(block.get("text", "")).strip()
            if (
                block_index == 0
                and tag in {"h1", "h2"}
                and raw_text == title
            ):
                continue
            text = html.escape(raw_text).replace("\n", "<br>")
            if tag in {"h1","h2","h3","h4","h5","h6"}:
                body.append(f"<{tag}>{text}</{tag}>")
            elif tag == "blockquote":
                body.append(f"<blockquote>{text}</blockquote>")
            elif tag == "li":
                body.append(f'<p class="li">• {text}</p>')
            elif tag == "figcaption":
                body.append(f'<p class="caption">{text}</p>')
            elif tag == "pre":
                body.append(f"<pre>{text}</pre>")
            else:
                role = paragraph_role(raw_text, block_index)
                body.append(f'<p class="{role}">{text}</p>')
        figure_html = ""
        issue_dir = Path(task.get("source_issue_dir", ""))
        for image in task.get("images", [])[:1]:
            rel = image.get("image_file")
            if not rel:
                continue
            src = issue_dir / rel
            if not src.exists():
                continue
            suffix = src.suffix.lower() or ".jpg"
            asset_name = safe_slug(task["task_id"]) + suffix
            shutil.copy2(src, images_out / asset_name)
            alt = html.escape(str(image.get("alt") or ""))
            figure_html = f'<figure><img src="images/{asset_name}" alt="{alt}"></figure>'
            break
        meta = " · ".join(str(x) for x in [task["publication"], task["issue_date"]] if x)
        source = html.escape(task.get("source_epub") or task["source_block_file"])
        page = f"""<!doctype html><html lang="zh-CN"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta charset="utf-8"><title>{html.escape(title)}</title><style>{CSS}</style><main><a class="back" href="index.html">← 返回目录</a><h1>{html.escape(title)}</h1><div class="meta">{html.escape(meta)}<br>Original: {html.escape(task["title"])}<br>Source EPUB: {source}</div>{figure_html}{''.join(body)}</main></html>"""
        (out_dir / slug).write_text(page, encoding="utf-8")
        links.append((title, meta, slug))

    nav = "".join(
        f'<a href="{html.escape(slug)}"><strong>{html.escape(title)}</strong><br><span class="meta">{html.escape(meta)}</span></a>'
        for title, meta, slug in links
    )
    index = f"""<!doctype html><html lang="zh-CN"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta charset="utf-8"><title>外刊忠实翻译</title><style>{CSS}</style><main><h1>外刊忠实翻译</h1><div class="meta">手机阅读版 · {len(links)} 篇已通过构建门禁</div><nav>{nav}</nav></main></html>"""
    (out_dir / "index.html").write_text(index, encoding="utf-8")
    (out_dir / "reader.css").write_text(CSS, encoding="utf-8")
    return {"built": len(links), "output": str(out_dir)}



def build_epub(workspace, out_file):
    workspace = Path(workspace)
    out_file = Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    manifest = load_json(workspace / "translation_manifest.json")
    qa = validate_workspace(workspace)
    status_by_id = {x["task_id"]: x["status"] for x in qa["results"]}
    eligible = [
        t for t in manifest["tasks"]
        if status_by_id.get(t["task_id"]) in {"pass", "review"}
    ]
    book_id = str(uuid.uuid4())
    chapters = []
    assets = []

    for n, task in enumerate(eligible, start=1):
        tr = load_json(task["translation_file"])
        title = tr.get("translated_title") or task["title"]
        chapter_name = f"chapter-{n:03d}.xhtml"
        body = []
        for block_index, block in enumerate(tr.get("blocks", [])):
            tag = block.get("type", "p")
            raw_text = str(block.get("text", "")).strip()
            if (
                block_index == 0
                and tag in {"h1", "h2"}
                and raw_text == title
            ):
                continue
            text_value = html.escape(raw_text).replace("\n", "<br/>")
            if tag in {"h1","h2","h3","h4","h5","h6"}:
                body.append(f"<{tag}>{text_value}</{tag}>")
            elif tag == "blockquote":
                body.append(f"<blockquote>{text_value}</blockquote>")
            elif tag == "li":
                body.append(f'<p class="li">• {text_value}</p>')
            elif tag == "figcaption":
                body.append(f'<p class="caption">{text_value}</p>')
            elif tag == "pre":
                body.append(f"<pre>{text_value}</pre>")
            else:
                role = paragraph_role(raw_text, block_index)
                body.append(f'<p class="{role}">{text_value}</p>')

        figure_html = []
        issue_dir = Path(task.get("source_issue_dir", ""))
        for image_no, image in enumerate(task.get("images", [])[:1], start=1):
            rel = image.get("image_file")
            if not rel:
                continue
            src = issue_dir / rel
            if not src.exists():
                continue
            suffix = src.suffix.lower() or ".jpg"
            asset_name = f"img-{n:03d}-{image_no:02d}{suffix}"
            media_type = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".gif": "image/gif", ".webp": "image/webp",
            }.get(suffix, "application/octet-stream")
            assets.append((asset_name, src, media_type))
            alt = html.escape(str(image.get("alt") or ""))
            figure_html.append(f'<figure><img src="../images/{asset_name}" alt="{alt}"/></figure>')

        meta = " · ".join(str(x) for x in [task["publication"], task["issue_date"]] if x)
        source = html.escape(task.get("source_epub") or task["source_block_file"])
        chapter = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN">
<head><title>{html.escape(title)}</title><link rel="stylesheet" type="text/css" href="../styles/reader.css"/></head>
<body><article><h1>{html.escape(title)}</h1><div class="meta">{html.escape(meta)}<br/>Original: {html.escape(task["title"])}<br/>Source EPUB: {source}</div>{''.join(figure_html)}{''.join(body)}</article></body></html>"""
        chapters.append((chapter_name, title, chapter))

    nav_items = "".join(
        f'<li><a href="text/{name}">{html.escape(title)}</a></li>'
        for name, title, _ in chapters
    )
    nav = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN">
<head><title>目录</title></head><body><nav epub:type="toc"><h1>目录</h1><ol>{nav_items}</ol></nav></body></html>"""

    manifest_items = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="css" href="styles/reader.css" media-type="text/css"/>',
    ]
    spine = []
    for i, (name, _, _) in enumerate(chapters, start=1):
        manifest_items.append(f'<item id="c{i}" href="text/{name}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="c{i}"/>')
    for i, (name, _, media_type) in enumerate(assets, start=1):
        manifest_items.append(f'<item id="img{i}" href="images/{name}" media-type="{media_type}"/>')

    package = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">urn:uuid:{book_id}</dc:identifier>
<dc:title>外刊忠实翻译</dc:title><dc:language>zh-CN</dc:language>
</metadata><manifest>{''.join(manifest_items)}</manifest><spine>{''.join(spine)}</spine></package>"""

    epub_css = """body{font-family:serif;line-height:1.86;margin:5%;}h1{line-height:1.3}h2,h3{line-height:1.38;margin:1.6em 0 .6em}.meta{font-size:.85em;color:#666;margin-bottom:1.4em;overflow-wrap:anywhere}.body{text-indent:2em;margin:0 0 .7em}.front,.caption,.note,.li{text-indent:0}.front,.caption{color:#666}.front,.caption,.li{margin:.3em 0 .6em}.note{margin:.7em 0;padding:.7em .9em;border:1px solid #bbb}.li{padding-left:1em}blockquote{text-indent:0;margin:1em 0;padding-left:1em;border-left:2px solid #999}pre{white-space:pre-wrap}img{display:block;max-width:100%;height:auto;margin:auto}figure{margin:1.2em 0;page-break-inside:avoid}"""

    with zipfile.ZipFile(out_file, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", """<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
<rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>""")
        z.writestr("EPUB/package.opf", package)
        z.writestr("EPUB/nav.xhtml", nav)
        z.writestr("EPUB/styles/reader.css", epub_css)
        for name, _, chapter in chapters:
            z.writestr(f"EPUB/text/{name}", chapter)
        for name, src, _ in assets:
            z.write(src, f"EPUB/images/{name}")

    return {"built": len(chapters), "output": str(out_file), "images": len(assets)}


def release_check(workspace, html_dir, epub_file):
    workspace = Path(workspace)
    html_dir = Path(html_dir)
    epub_file = Path(epub_file)
    qa = validate_workspace(workspace)
    manifest = load_json(workspace / "translation_manifest.json")
    status_by_id = {x["task_id"]: x["status"] for x in qa["results"]}
    expected = sum(
        status_by_id.get(task["task_id"]) in {"pass", "review"}
        for task in manifest["tasks"]
    )
    errors = []
    warnings = []

    index_file = html_dir / "index.html"
    if not index_file.exists():
        errors.append("HTML index.html missing")
        article_files = []
    else:
        article_files = sorted(
            p for p in html_dir.glob("*.html") if p.name != "index.html"
        )
        if len(article_files) != expected:
            errors.append(
                f"HTML article count mismatch: expected {expected}, got {len(article_files)}"
            )
        for page in [index_file, *article_files]:
            text_value = page.read_text(encoding="utf-8")
            if 'name="viewport"' not in text_value:
                errors.append(f"{page.name}: viewport meta missing")
            for ref in re.findall(r'(?:href|src)="([^"]+)"', text_value):
                if ref.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                target = (page.parent / ref).resolve()
                if not target.exists():
                    errors.append(f"{page.name}: broken relative reference {ref}")

    if not epub_file.exists():
        errors.append("EPUB file missing")
    else:
        try:
            with zipfile.ZipFile(epub_file) as z:
                info = z.infolist()
                if not info or info[0].filename != "mimetype":
                    errors.append("EPUB mimetype must be first ZIP entry")
                else:
                    if info[0].compress_type != zipfile.ZIP_STORED:
                        errors.append("EPUB mimetype must be uncompressed")
                    if z.read("mimetype") != b"application/epub+zip":
                        errors.append("EPUB mimetype content invalid")
                names = set(z.namelist())
                required = {
                    "META-INF/container.xml",
                    "EPUB/package.opf",
                    "EPUB/nav.xhtml",
                }
                for name in sorted(required - names):
                    errors.append(f"EPUB required file missing: {name}")
                chapter_names = sorted(
                    name for name in names
                    if re.fullmatch(r"EPUB/text/chapter-\d+\.xhtml", name)
                )
                if len(chapter_names) != expected:
                    errors.append(
                        f"EPUB chapter count mismatch: expected {expected}, got {len(chapter_names)}"
                    )
                parse_targets = [
                    name for name in names
                    if name.endswith((".xml", ".opf", ".xhtml"))
                ]
                for name in parse_targets:
                    try:
                        root = ET.fromstring(z.read(name))
                    except Exception as exc:
                        errors.append(f"{name}: XML parse error: {exc}")
                        continue
                    base = posixpath.dirname(name)
                    for elem in root.iter():
                        ref = elem.attrib.get("src") or elem.attrib.get("href")
                        if not ref or ref.startswith(("http://", "https://", "#", "mailto:")):
                            continue
                        if ":" in ref.split("/", 1)[0]:
                            continue
                        target = posixpath.normpath(posixpath.join(base, ref.split("#", 1)[0]))
                        if target not in names:
                            errors.append(f"{name}: broken EPUB reference {ref}")
        except zipfile.BadZipFile as exc:
            errors.append(f"EPUB invalid ZIP: {exc}")

    return {
        "status": "pass" if not errors else "fail",
        "expected_articles": expected,
        "errors": errors,
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--readable-root", required=True)
    p.add_argument("--workspace", required=True)
    p.add_argument("--selection")
    p = sub.add_parser("validate")
    p.add_argument("--workspace", required=True)
    p = sub.add_parser("next-batch")
    p.add_argument("--workspace", required=True)
    p.add_argument("--max-articles", type=int, default=4)
    p.add_argument("--max-blocks", type=int, default=120)
    p.add_argument("--out")
    p = sub.add_parser("build-mobile")
    p.add_argument("--workspace", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("build-epub")
    p.add_argument("--workspace", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("release-check")
    p.add_argument("--workspace", required=True)
    p.add_argument("--html", required=True)
    p.add_argument("--epub", required=True)
    args = ap.parse_args()

    if args.cmd == "init":
        result = init_workspace(args.readable_root, args.workspace, args.selection)
        print(json.dumps({"tasks": len(result["tasks"])}, ensure_ascii=False))
    elif args.cmd == "validate":
        print(json.dumps(validate_workspace(args.workspace), ensure_ascii=False, indent=2))
    elif args.cmd == "next-batch":
        print(json.dumps(
            next_batch(args.workspace, args.max_articles, args.max_blocks, args.out),
            ensure_ascii=False,
            indent=2,
        ))
    elif args.cmd == "build-mobile":
        print(json.dumps(build_mobile(args.workspace, args.out), ensure_ascii=False, indent=2))
    elif args.cmd == "build-epub":
        print(json.dumps(build_epub(args.workspace, args.out), ensure_ascii=False, indent=2))
    else:
        result = release_check(args.workspace, args.html, args.epub)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if result["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
