#!/usr/bin/env python3
"""Submit Made of Text URLs through IndexNow."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HOST = "clawdiaac.com"
SITE_URL = f"https://{HOST}"
INDEXNOW_KEY = "c80bf7bc2740dc1e9974335058c2dc5f"
KEY_LOCATION = f"{SITE_URL}/{INDEXNOW_KEY}.txt"
USER_AGENT = "ClawdiaIndexNow/1.0 (+https://clawdiaac.com/book/)"
DEFAULT_ENDPOINTS = [
    "https://www.bing.com/indexnow",
    "https://yandex.com/indexnow",
]
DEFAULT_URLS = [
    f"{SITE_URL}/book/",
    f"{SITE_URL}/book/buy/",
    f"{SITE_URL}/book/excerpts/",
    f"{SITE_URL}/book/faq/",
    f"{SITE_URL}/book/share/",
    f"{SITE_URL}/book/reviewers/",
    f"{SITE_URL}/book/researchers/",
    f"{SITE_URL}/book/interviews/",
    f"{SITE_URL}/book/critical-reading/",
    f"{SITE_URL}/book/reading-guide/",
    f"{SITE_URL}/book/discussion/",
    f"{SITE_URL}/book/teaching/",
    f"{SITE_URL}/book/course-pack.txt",
    f"{SITE_URL}/book/press/",
    f"{SITE_URL}/book/cite/",
    f"{SITE_URL}/book/libraries/",
    f"{SITE_URL}/book/library-request/",
    f"{SITE_URL}/book/library-request.txt",
    f"{SITE_URL}/book/llms.txt",
    f"{SITE_URL}/book/metadata.json",
    f"{SITE_URL}/book/book.jsonld",
    f"{SITE_URL}/book/file-manifest.json",
    f"{SITE_URL}/book/made-of-text-catalog.csv",
    f"{SITE_URL}/book/made-of-text-onix.xml",
    f"{SITE_URL}/book/made-of-text.bib",
    f"{SITE_URL}/book/made-of-text.ris",
    f"{SITE_URL}/book/feed.xml",
    f"{SITE_URL}/book/sitemap.xml",
    f"{SITE_URL}/sitemap.xml",
    f"{SITE_URL}/llms.txt",
]


def submit(endpoint: str, urls: list[str], timeout: int) -> dict[str, object]:
    payload = {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")
    request = Request(
        endpoint,
        method="POST",
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
            return {"endpoint": endpoint, "status": response.status, "body": body[:500]}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return {"endpoint": endpoint, "status": exc.code, "error": body[:500] or exc.reason}
    except URLError as exc:
        return {"endpoint": endpoint, "status": None, "error": str(exc.reason)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", action="append", dest="endpoints", help="IndexNow endpoint to use. Can be repeated.")
    parser.add_argument("--url", action="append", dest="urls", help="URL to submit. Can be repeated.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    endpoints = args.endpoints or DEFAULT_ENDPOINTS
    urls = args.urls or DEFAULT_URLS
    if len(urls) > 10_000:
        raise SystemExit("IndexNow accepts at most 10,000 URLs per request")

    payload = {
        "host": HOST,
        "keyLocation": KEY_LOCATION,
        "urlCount": len(urls),
        "endpoints": endpoints,
        "urls": urls,
    }
    if args.dry_run:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    results = [submit(endpoint, urls, args.timeout) for endpoint in endpoints]
    print(json.dumps({"submitted": payload, "results": results}, indent=2, sort_keys=True))
    ok_statuses = {200, 202}
    return 0 if all(result.get("status") in ok_statuses for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
