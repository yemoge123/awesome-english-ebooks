#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath

from magazine_epub_extract import (
    PUBLICATIONS,
    SOURCE_REPO,
    load_authorization_policy,
    parse_epub,
    safe_name,
)


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def validate_local_source(
    *,
    publication: str,
    source_file: str,
    data: bytes,
    expected_source_sha: str,
    expected_size: int | None = None,
):
    if publication not in PUBLICATIONS:
        raise RuntimeError(f"Unknown publication: {publication}")
    root = PUBLICATIONS[publication]["root"].rstrip("/") + "/"
    normalized = source_file.replace("\\", "/").lstrip("/")
    if not normalized.startswith(root):
        raise RuntimeError(
            f"Source path {source_file!r} is outside authorized root {root!r}"
        )
    if not normalized.lower().endswith(".epub"):
        raise RuntimeError("Verified local import accepts EPUB only")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_source_sha):
        raise RuntimeError("expected_source_sha must be a 40-character lowercase Git blob SHA")
    actual_sha = git_blob_sha1(data)
    if actual_sha != expected_source_sha:
        raise RuntimeError(
            f"Git blob SHA mismatch: actual={actual_sha} expected={expected_source_sha}"
        )
    if expected_size is not None and len(data) != expected_size:
        raise RuntimeError(
            f"Source size mismatch: actual={len(data)} expected={expected_size}"
        )
    return normalized, actual_sha


def write_issue_output(
    *,
    publication: str,
    issue_date: str,
    source_file: str,
    source_sha: str,
    data: bytes,
    out_dir: Path,
):
    docs = parse_epub(data)
    issue_out = out_dir / publication / issue_date
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
                image_name = (
                    f"{i:03d}-{j:02d}-{safe_name(PurePosixPath(epub_path).stem)}{suffix}"
                )
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
                    "source_epub": source_file,
                    "source_sha": source_sha,
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
    return {
        "publication": PUBLICATIONS[publication]["name"],
        "slug": publication,
        "issue_date": issue_date,
        "source_repo": SOURCE_REPO,
        "source_file": source_file,
        "source_sha": source_sha,
        "source_size": len(data),
        "selected_format": "epub",
        "ingest_mode": "verified_local_epub",
        "provenance_verification": "git_blob_sha_match",
        "status": "ok",
        "article_count": len(index),
        "block_count": sum(item.get("block_count", 0) for item in index),
        "image_count": sum(len(item.get("images") or []) for item in index),
        "index_file": f"{publication}/{issue_date}/index.json",
    }


def main(argv=None):
    policy = load_authorization_policy()
    parser = argparse.ArgumentParser(
        description=(
            "Import an already-materialized authorized magazine EPUB after "
            "verifying its exact Git blob SHA. This path performs no network I/O."
        )
    )
    parser.add_argument("--publication", required=True, choices=sorted(PUBLICATIONS))
    parser.add_argument("--issue-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--input", required=True, help="Local EPUB path")
    parser.add_argument("--source-file", required=True, help="Authorized GitHub repo path")
    parser.add_argument("--expected-source-sha", required=True, help="Git blob SHA from master")
    parser.add_argument("--expected-size", type=int)
    parser.add_argument("--out", default="magazine-readable")
    args = parser.parse_args(argv)

    try:
        dt.date.fromisoformat(args.issue_date)
    except ValueError as exc:
        parser.error(f"invalid --issue-date {args.issue_date!r}: {exc}")

    input_path = Path(args.input)
    data = input_path.read_bytes()
    source_file, source_sha = validate_local_source(
        publication=args.publication,
        source_file=args.source_file,
        data=data,
        expected_source_sha=args.expected_source_sha,
        expected_size=args.expected_size,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    item = write_issue_output(
        publication=args.publication,
        issue_date=args.issue_date,
        source_file=source_file,
        source_sha=source_sha,
        data=data,
        out_dir=out_dir,
    )
    manifest = {
        "source_repo": SOURCE_REPO,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "format_policy": "verified_local_epub_text_and_embedded_raster_image_extraction",
        "authorized_input": True,
        "authorization": {
            "policy_version": policy.get("version"),
            "scope": policy.get("scope"),
            "effective_date": policy.get("effective_date"),
        },
        "network_io": False,
        "publications": [item],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
