#!/usr/bin/env python3
import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

SOURCE_REPO = "yemoge123/awesome-english-ebooks"
POLICY_PATH = Path(__file__).resolve().parents[1] / "authorized-input" / "magazine_policy.json"
API_BASE = f"https://api.github.com/repos/{SOURCE_REPO}/contents"
PUBLICATIONS = {
    "economist": {"name": "The Economist", "root": "01_economist"},
    "new_yorker": {"name": "The New Yorker", "root": "02_new_yorker"},
    "atlantic": {"name": "The Atlantic", "root": "04_atlantic"},
    "wired": {"name": "WIRED", "root": "05_wired"},
}
DATE_RE = re.compile(r"(20\d{2})[._-](\d{2})[._-](\d{2})")


def http_get(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "personal-magazine-translation/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def github_json(url: str):
    return json.loads(http_get(url).decode("utf-8"))


def load_authorization_policy():
    if not POLICY_PATH.exists():
        raise RuntimeError(f"Authorization policy missing: {POLICY_PATH}")
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    required = {
        "status": "authorized",
        "scope": "personal_translation_and_processing",
        "source_repo": SOURCE_REPO,
    }
    for key, expected in required.items():
        if policy.get(key) != expected:
            raise RuntimeError(
                f"Authorization policy mismatch for {key}: "
                f"{policy.get(key)!r} != {expected!r}"
            )
    allowed_roots = set(policy.get("allowed_roots") or [])
    expected_roots = {cfg["root"] for cfg in PUBLICATIONS.values()}
    if not expected_roots.issubset(allowed_roots):
        raise RuntimeError("Authorization policy does not cover all configured magazine roots")
    if "epub" not in set(policy.get("formats") or []):
        raise RuntimeError("Authorization policy does not allow EPUB processing")
    return policy


def extract_date(name: str):
    m = DATE_RE.search(name)
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def choose_issue(items, root: str, requested_date: str = None):
    candidates = []
    for item in items:
        if item.get("type") != "dir":
            continue
        issue_date = extract_date(item.get("name", ""))
        if issue_date:
            candidates.append((issue_date, item))
    if not candidates:
        raise RuntimeError(f"No dated issue directory found under {root}")
    candidates.sort(key=lambda x: x[0])
    if requested_date:
        try:
            target = dt.date.fromisoformat(requested_date)
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid issue date {requested_date!r}; expected YYYY-MM-DD"
            ) from exc
        for issue_date, item in candidates:
            if issue_date == target:
                return issue_date, item
        raise RuntimeError(
            f"Issue date {requested_date} not found under {root}"
        )
    return candidates[-1]


def issue_dir(root: str, requested_date: str = None):
    items = github_json(f"{API_BASE}/{urllib.parse.quote(root)}?ref=master")
    expanded = list(items)
    for item in items:
        name = str(item.get("name", ""))
        if item.get("type") != "dir" or not re.fullmatch(r"20\\d{2}", name):
            continue
        year_path = item.get("path") or f"{root}/{name}"
        year_items = github_json(
            f"{API_BASE}/{urllib.parse.quote(year_path)}?ref=master"
        )
        expanded.extend(year_items)
    return choose_issue(expanded, root, requested_date)


class ImageRefExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = dict(attrs)
        src = None
        alt = ""
        if tag == "img":
            src = attrs.get("src")
            alt = attrs.get("alt", "")
        elif tag == "image":
            src = attrs.get("href") or attrs.get("xlink:href")
            alt = attrs.get("aria-label", "")
        if not src or src.startswith("data:"):
            return
        self.images.append({"src": src, "alt": " ".join(alt.split()).strip()})


class SemanticBlockExtractor(HTMLParser):
    """Extract reader-facing semantic blocks without treating layout wrappers as paragraphs."""

    BLOCK_TAGS = {
        "p", "h1", "h2", "h3", "h4", "h5", "h6",
        "li", "blockquote", "figcaption", "pre",
    }
    SKIP = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.skip_depth = 0
        self.active_tag = None
        self.active_depth = 0
        self.parts = []

    def _flush(self):
        if self.active_tag is None:
            return
        raw = html.unescape("".join(self.parts)).replace("\r", "")
        text = re.sub(r"[ \t\f\v]+", " ", raw)
        text = re.sub(r" *\n *", "\n", text).strip()
        if text:
            self.blocks.append({"type": self.active_tag, "text": text})
        self.active_tag = None
        self.active_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.SKIP:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if self.active_tag is not None:
            self.active_depth += 1
            if tag == "br":
                self.parts.append("\n")
            return
        if tag in self.BLOCK_TAGS:
            self.active_tag = tag
            self.active_depth = 0
            self.parts = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.SKIP:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth or self.active_tag is None:
            return
        if self.active_depth:
            self.active_depth -= 1
            return
        if tag == self.active_tag:
            self._flush()

    def handle_data(self, data):
        if not self.skip_depth and self.active_tag is not None:
            self.parts.append(data)

    def close(self):
        super().close()
        self._flush()


class TextExtractor(HTMLParser):
    BLOCK = {
        "p", "div", "section", "article", "header", "footer", "aside",
        "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote",
        "br", "hr", "tr", "td", "th", "figcaption",
    }
    SKIP = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
        self.title_parts = []
        self.heading_parts = []
        self.in_title = False
        self.heading_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.SKIP:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "title":
            self.in_title = True
        if tag in {"h1", "h2"}:
            self.heading_depth += 1
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.SKIP:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag == "title":
            self.in_title = False
        if tag in {"h1", "h2"} and self.heading_depth:
            self.heading_depth -= 1
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip_depth:
            return
        text = html.unescape(data)
        if self.in_title:
            self.title_parts.append(text)
        if self.heading_depth:
            self.heading_parts.append(text)
        self.parts.append(text)

    def result(self):
        raw = "".join(self.parts).replace("\r", "")
        lines = []
        for line in raw.split("\n"):
            line = re.sub(r"[ \t\f\v]+", " ", line).strip()
            if line:
                lines.append(line)
        text = "\n\n".join(lines)
        title = " ".join("".join(self.title_parts).split()).strip()
        heading = " ".join("".join(self.heading_parts).split()).strip()
        return title, heading, text


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def resolve_posix(base: str, href: str) -> str:
    href = urllib.parse.unquote(href.split("#", 1)[0])
    joined = PurePosixPath(base).parent.joinpath(href)
    parts = []
    for part in joined.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


def parse_epub(data: bytes):
    zf = zipfile.ZipFile(BytesIO(data))
    container = ET.fromstring(zf.read("META-INF/container.xml"))
    rootfile = None
    for elem in container.iter():
        if local_name(elem.tag) == "rootfile":
            rootfile = elem.attrib.get("full-path")
            if rootfile:
                break
    if not rootfile:
        raise RuntimeError("EPUB rootfile not found")

    opf = ET.fromstring(zf.read(rootfile))
    manifest = {}
    spine = []
    nav_href = None
    ncx_href = None
    for elem in opf.iter():
        tag = local_name(elem.tag)
        if tag == "item":
            item_id = elem.attrib.get("id")
            href = elem.attrib.get("href")
            media = elem.attrib.get("media-type", "")
            props = elem.attrib.get("properties", "")
            if item_id and href:
                manifest[item_id] = (href, media, props)
                if "nav" in props.split():
                    nav_href = href
                if media == "application/x-dtbncx+xml":
                    ncx_href = href
        elif tag == "itemref":
            idref = elem.attrib.get("idref")
            if idref:
                spine.append(idref)

    toc = {}
    base = rootfile
    if nav_href:
        nav_path = resolve_posix(base, nav_href)
        try:
            nav_root = ET.fromstring(zf.read(nav_path))
            for a in nav_root.iter():
                if local_name(a.tag) != "a":
                    continue
                href = a.attrib.get("href")
                if not href:
                    continue
                text = " ".join("".join(a.itertext()).split()).strip()
                if text:
                    toc[resolve_posix(nav_path, href)] = text
        except Exception:
            pass
    if not toc and ncx_href:
        ncx_path = resolve_posix(base, ncx_href)
        try:
            ncx_root = ET.fromstring(zf.read(ncx_path))
            for nav_point in ncx_root.iter():
                if local_name(nav_point.tag) != "navPoint":
                    continue
                label = None
                src = None
                for child in nav_point.iter():
                    lname = local_name(child.tag)
                    if lname == "text" and label is None:
                        label = " ".join("".join(child.itertext()).split()).strip()
                    elif lname == "content" and src is None:
                        src = child.attrib.get("src")
                if label and src:
                    toc[resolve_posix(ncx_path, src)] = label
        except Exception:
            pass

    docs = []
    seen_paths = set()
    for idref in spine:
        item = manifest.get(idref)
        if not item:
            continue
        href, media, _ = item
        if media not in {"application/xhtml+xml", "text/html"}:
            continue
        path = resolve_posix(base, href)
        if path in seen_paths:
            continue
        seen_paths.add(path)
        try:
            body = zf.read(path).decode("utf-8", errors="replace")
        except KeyError:
            continue
        parser = TextExtractor()
        parser.feed(body)
        html_title, heading, text = parser.result()
        block_parser = SemanticBlockExtractor()
        block_parser.feed(body)
        block_parser.close()
        blocks = block_parser.blocks
        if not blocks:
            blocks = [
                {"type": "p", "text": part.strip()}
                for part in text.split("\n\n")
                if part.strip()
            ]
        image_parser = ImageRefExtractor()
        image_parser.feed(body)
        images = []
        seen_images = set()
        for image in image_parser.images:
            image_path = resolve_posix(path, image["src"])
            if not image_path or image_path in seen_images:
                continue
            seen_images.add(image_path)
            images.append({"epub_path": image_path, "alt": image.get("alt", "")})
        title = toc.get(path) or heading or html_title or PurePosixPath(path).stem
        title = " ".join(title.split())
        if len(text) < 120:
            continue
        docs.append(
            {
                "path": path,
                "title": title,
                "text": text,
                "blocks": blocks,
                "images": images,
            }
        )
    return docs


def safe_name(text: str) -> str:
    text = text.encode("ascii", errors="ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80] or "article"


def process_publication(
    slug: str, config: dict, out_dir: Path, requested_date: str = None
):
    issue_date, issue_item = issue_dir(config["root"], requested_date)
    issue_path = issue_item["path"]
    contents = github_json(f"{API_BASE}/{urllib.parse.quote(issue_path)}?ref=master")
    epub = next(
        (
            x
            for x in contents
            if x.get("type") == "file"
            and x.get("name", "").lower().endswith(".epub")
        ),
        None,
    )
    result = {
        "publication": config["name"],
        "slug": slug,
        "issue_date": issue_date.isoformat(),
        "issue_path": issue_path,
        "selected_format": "epub" if epub else None,
        "source_repo": SOURCE_REPO,
        "status": "pending",
    }
    if not epub:
        result["status"] = "no_epub"
        result["article_count"] = 0
        return result

    result.update(
        {
            "source_file": epub["path"],
            "source_sha": epub["sha"],
            "source_size": epub["size"],
        }
    )
    data = http_get(epub["download_url"])
    docs = parse_epub(data)
    issue_out = out_dir / slug / issue_date.isoformat()
    articles_out = issue_out / "articles"
    blocks_out = issue_out / "blocks"
    images_out = issue_out / "images"
    articles_out.mkdir(parents=True, exist_ok=True)
    blocks_out.mkdir(parents=True, exist_ok=True)
    images_out.mkdir(parents=True, exist_ok=True)
    supported_image_suffixes = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    index = []
    with zipfile.ZipFile(BytesIO(data)) as asset_zip:
        for i, doc in enumerate(docs, start=1):
            filename = f"{i:03d}-{safe_name(doc['title'])}.txt"
            relpath = f"articles/{filename}"
            (articles_out / filename).write_text(doc["text"], encoding="utf-8")
            block_filename = filename.rsplit(".", 1)[0] + ".json"
            block_relpath = f"blocks/{block_filename}"
            block_payload = {
                "seq": i,
                "title": doc["title"],
                "epub_path": doc["path"],
                "blocks": [
                    {
                        "id": f"B{j:03d}",
                        "type": block["type"],
                        "text": block["text"],
                    }
                    for j, block in enumerate(doc.get("blocks") or [], start=1)
                ],
            }
            (blocks_out / block_filename).write_text(
                json.dumps(block_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            image_items = []
            for j, image in enumerate(doc.get("images") or [], start=1):
                epub_path = image["epub_path"]
                suffix = PurePosixPath(epub_path).suffix.lower()
                if suffix not in supported_image_suffixes:
                    continue
                try:
                    image_bytes = asset_zip.read(epub_path)
                except KeyError:
                    continue
                image_name = f"{i:03d}-{j:02d}-{safe_name(PurePosixPath(epub_path).stem)}{suffix}"
                image_relpath = f"images/{image_name}"
                (images_out / image_name).write_bytes(image_bytes)
                image_items.append(
                    {
                        "epub_path": epub_path,
                        "image_file": image_relpath,
                        "alt": image.get("alt", ""),
                        "size": len(image_bytes),
                    }
                )
            index.append(
                {
                    "seq": i,
                    "title": doc["title"],
                    "epub_path": doc["path"],
                    "source_epub": epub["path"],
                    "source_sha": epub["sha"],
                    "text_file": relpath,
                    "block_file": block_relpath,
                    "char_count": len(doc["text"]),
                    "block_count": len(block_payload["blocks"]),
                    "images": image_items,
                }
            )
    (issue_out / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    result["status"] = "ok"
    result["article_count"] = len(index)
    result["block_count"] = sum(item.get("block_count", 0) for item in index)
    result["image_count"] = sum(len(item.get("images") or []) for item in index)
    result["index_file"] = f"{slug}/{issue_date.isoformat()}/index.json"
    return result


def main(argv=None):
    policy = load_authorization_policy()
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="magazine-readable")
    parser.add_argument(
        "--publication", action="append", choices=sorted(PUBLICATIONS)
    )
    parser.add_argument(
        "--issue",
        action="append",
        default=[],
        metavar="PUBLICATION=YYYY-MM-DD",
        help=(
            "Extract an exact historical issue. Repeat for multiple issues, "
            "for example --issue economist=2025-05-03."
        ),
    )
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    requested = []
    for spec in args.issue:
        slug, sep, issue_date = spec.partition("=")
        if not sep or slug not in PUBLICATIONS or not issue_date:
            parser.error(
                "--issue must be PUBLICATION=YYYY-MM-DD with a configured publication"
            )
        requested.append((slug, issue_date))

    if requested:
        selected = requested
    else:
        selected = [(slug, None) for slug in (args.publication or list(PUBLICATIONS))]
    manifest = {
        "source_repo": SOURCE_REPO,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "format_policy": "epub_text_and_embedded_raster_image_extraction",
        "authorized_input": True,
        "authorization": {
            "policy_path": str(POLICY_PATH.relative_to(POLICY_PATH.parents[1])),
            "policy_version": policy.get("version"),
            "scope": policy.get("scope"),
            "effective_date": policy.get("effective_date"),
        },
        "publications": [],
    }
    failures = 0
    for slug, requested_date in selected:
        try:
            item = process_publication(
                slug, PUBLICATIONS[slug], out_dir, requested_date=requested_date
            )
        except Exception as exc:
            item = {
                "publication": PUBLICATIONS[slug]["name"],
                "slug": slug,
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
            failures += 1
        manifest["publications"].append(item)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
