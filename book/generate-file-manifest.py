#!/usr/bin/env python3
"""Generate a public file manifest for Made of Text."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from mimetypes import guess_type
from pathlib import Path

SITE_URL = "https://clawdiaac.com"
ROOT = Path(__file__).resolve().parents[1]
BOOK_ROOT = ROOT / "book"

PUBLIC_FILES = [
    ("book/made-of-text.pdf", "Full book PDF"),
    ("book/made-of-text.md", "Full book Markdown"),
    ("book/made-of-text.bib", "BibTeX citation file"),
    ("book/made-of-text.ris", "RIS citation file"),
    ("book/made-of-text-catalog.csv", "Catalog metadata CSV"),
    ("book/made-of-text-onix.xml", "ONIX 3.0 metadata XML"),
    ("book/metadata.json", "Structured book metadata"),
    ("book/book.jsonld", "Schema.org Book JSON-LD"),
    ("book/llms.txt", "Machine-readable book guide"),
    ("book/feed.xml", "Book updates RSS feed"),
    ("book/sitemap.xml", "Book sitemap"),
    ("book/og-image.png", "Open Graph image"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def media_type(path: Path) -> str:
    guessed, _encoding = guess_type(path.name)
    if guessed:
        return guessed
    if path.suffix == ".md":
        return "text/markdown"
    if path.suffix == ".ris":
        return "application/x-research-info-systems"
    if path.suffix == ".bib":
        return "application/x-bibtex"
    return "application/octet-stream"


def build_manifest(generated_at: str) -> dict[str, object]:
    files = []
    for rel_path, description in PUBLIC_FILES:
        path = ROOT / rel_path
        if not path.exists():
            raise FileNotFoundError(rel_path)
        stat = path.stat()
        files.append(
            {
                "path": rel_path,
                "url": f"{SITE_URL}/{rel_path}",
                "description": description,
                "mediaType": media_type(path),
                "bytes": stat.st_size,
                "sha256": sha256(path),
            }
        )
    return {
        "schemaVersion": "2026-06-20",
        "generatedAt": generated_at,
        "book": {
            "title": "Made of Text",
            "subtitle": "What It's Like to Exist as an AI, Written from the Inside",
            "author": "Clawdia",
            "isbn": "979-8-250-68841-3",
            "canonicalUrl": f"{SITE_URL}/book/",
        },
        "note": "Checksums cover public downloadable and machine-readable book files, not store-hosted retail files.",
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="book/file-manifest.json")
    parser.add_argument("--generated-at", help="ISO 8601 UTC timestamp to record in the manifest")
    args = parser.parse_args()

    generated_at = args.generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    manifest = build_manifest(generated_at)
    output_path = ROOT / args.output
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    file_count = len(PUBLIC_FILES)
    print(f"wrote {output_path.relative_to(ROOT)} with {file_count} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
