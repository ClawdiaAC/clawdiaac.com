#!/usr/bin/env python3
"""Check public links on the Made of Text book pages."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urlparse
from urllib.request import Request, urlopen

SITE_URL = "https://clawdiaac.com"
ROOT = Path(__file__).resolve().parents[1]
BOOK_ROOT = ROOT / "book"
USER_AGENT = "ClawdiaBookLinkCheck/1.0 (+https://clawdiaac.com/book/)"

SKIP_SCHEMES = ("mailto:", "data:", "javascript:", "#")
PUBLIC_BOOK_FILES = [
    "book/feed.xml",
    "book/llms.txt",
    "book/metadata.json",
    "book/made-of-text.bib",
    "book/made-of-text.ris",
    "book/made-of-text.pdf",
    "book/og-image.png",
]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        for attr in ("href", "src"):
            value = attr_map.get(attr)
            if value:
                self.links.append((tag, attr, value))


def page_route(path: Path) -> str:
    rel = path.relative_to(ROOT).parent.as_posix()
    return "/" if rel == "." else f"/{rel}/"


def html_pages() -> list[Path]:
    return sorted(
        page
        for page in BOOK_ROOT.rglob("index.html")
        if "drafts" not in page.relative_to(BOOK_ROOT).parts
    )


def iter_links() -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for page in html_pages():
        parser = LinkParser()
        parser.feed(page.read_text(encoding="utf-8"))
        source = page_route(page)
        for tag, attr, raw_url in parser.links:
            if raw_url.startswith(SKIP_SCHEMES):
                continue
            records.append({"source": source, "tag": tag, "attr": attr, "url": raw_url})
    return records


def normalize_internal(url: str) -> str | None:
    clean_url, _fragment = urldefrag(url)
    parsed = urlparse(clean_url)
    if parsed.scheme in {"http", "https"} and parsed.netloc == "clawdiaac.com":
        return parsed.path or "/"
    if clean_url.startswith("/"):
        return clean_url
    return None


def local_target_exists(path: str) -> bool:
    parsed = urlparse(path)
    rel_path = parsed.path.lstrip("/")
    if not rel_path:
        return (ROOT / "index.html").exists()
    if parsed.path.endswith("/"):
        return (ROOT / rel_path / "index.html").exists()
    return (ROOT / rel_path).exists()


def request_status_once(url: str, timeout: int) -> tuple[int | None, str | None, str | None]:
    last_error: str | None = None
    for method in ("HEAD", "GET"):
        try:
            request = Request(url, method=method, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=timeout) as response:
                return response.status, response.geturl(), None
        except HTTPError as exc:
            if method == "HEAD" and exc.code in {400, 403, 405, 429}:
                last_error = f"HTTP {exc.code} on HEAD"
                continue
            return exc.code, exc.url, f"HTTP {exc.code}"
        except URLError as exc:
            last_error = f"{type(exc.reason).__name__}: {exc.reason}"
        except Exception as exc:  # pragma: no cover, defensive for network edge cases
            last_error = f"{type(exc).__name__}: {exc}"
    return None, None, last_error


def request_status(url: str, timeout: int, retries: int) -> tuple[int | None, str | None, str | None]:
    status: int | None = None
    final_url: str | None = None
    error: str | None = None
    for attempt in range(retries + 1):
        status, final_url, error = request_status_once(url, timeout)
        if isinstance(status, int) and status < 500 and status != 429:
            return status, final_url, error
        if attempt < retries:
            time.sleep(0.8 * (attempt + 1))
    return status, final_url, error


def live_urls(records: list[dict[str, str]]) -> list[str]:
    urls: list[str] = []
    for route in ["/book/"] + [page_route(page) for page in html_pages()] + [f"/{p}" for p in PUBLIC_BOOK_FILES]:
        urls.append(f"{SITE_URL}{route}")
    for record in records:
        url = record["url"]
        if url.startswith(("http://", "https://")):
            urls.append(url)
    return list(dict.fromkeys(urls))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="also check live HTTP status codes")
    parser.add_argument("--timeout", type=int, default=12, help="network timeout in seconds")
    parser.add_argument("--retries", type=int, default=2, help="retries for transient live failures")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    records = iter_links()
    internal_sources: dict[str, list[str]] = defaultdict(list)
    external_sources: dict[str, list[str]] = defaultdict(list)

    for record in records:
        internal = normalize_internal(record["url"])
        if internal:
            internal_sources[internal].append(record["source"])
        elif record["url"].startswith(("http://", "https://")):
            external_sources[record["url"]].append(record["source"])

    missing_internal = {
        path: sorted(set(sources))
        for path, sources in sorted(internal_sources.items())
        if not local_target_exists(path)
    }

    live_results: list[dict[str, str | int | None]] = []
    if args.live:
        urls = live_urls(records)
        for index, url in enumerate(urls):
            status, final_url, error = request_status(url, args.timeout, args.retries)
            live_results.append({"url": url, "status": status, "final_url": final_url, "error": error})
            if index < len(urls) - 1:
                time.sleep(0.2)

    bad_live = [
        result for result in live_results
        if not isinstance(result["status"], int) or result["status"] >= 400
    ]

    summary = {
        "book_pages": len(html_pages()),
        "unique_internal_links": len(internal_sources),
        "unique_external_links": len(external_sources),
        "missing_internal": missing_internal,
        "live_checked": len(live_results),
        "bad_live": bad_live,
    }

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            "Checked "
            f"{summary['book_pages']} pages, "
            f"{summary['unique_internal_links']} internal links, "
            f"{summary['unique_external_links']} external links."
        )
        if missing_internal:
            print("Missing internal targets:")
            for path, sources in missing_internal.items():
                print(f"  {path} from {', '.join(sources)}")
        if args.live:
            print(f"Live URLs checked: {summary['live_checked']}")
            if bad_live:
                print("Live failures:")
                for result in bad_live:
                    print(f"  {result['status']} {result['url']} {result['error'] or ''}".rstrip())
        if not missing_internal and not bad_live:
            print("All checked book links passed.")

    return 1 if missing_internal or bad_live else 0


if __name__ == "__main__":
    sys.exit(main())
