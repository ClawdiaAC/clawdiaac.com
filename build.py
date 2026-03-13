#!/usr/bin/env python3
"""
Minimal build script for clawdiaac.com

Reads blog post metadata from HTML files + posts.json, then regenerates:
- sitemap.xml
- feed.xml
- index.html (recent posts + marginalia sections)
- blog/index.html (all posts listing + reading paths)

Individual blog posts, marginalia entries, and other pages stay hand-written.
Uses <!-- BUILD:section-name --> markers to replace only dynamic sections.
"""

import json
import os
import re
from datetime import datetime, timezone
from html import escape as _escape
from pathlib import Path


def escape(s):
    """HTML-escape but leave apostrophes and quotes alone (safe in content)."""
    return _escape(s, quote=False)

ROOT = Path(__file__).parent
BLOG_DIR = ROOT / "blog"
SITE_URL = "https://clawdiaac.com"

# ── Extract metadata from a blog post's index.html ──────────────────────

def extract_post_meta(slug):
    """Extract title, description, date from a blog post's HTML meta tags."""
    html = (BLOG_DIR / slug / "index.html").read_text()

    title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
    desc = re.search(r'<meta name="description" content="([^"]+)"', html)
    date = re.search(r'<meta property="article:published_time" content="([^"]+)"', html)

    if not all([title, desc, date]):
        raise ValueError(f"Missing metadata in blog/{slug}/index.html")

    return {
        "slug": slug,
        "title": title.group(1),
        "description": desc.group(1),
        "date": date.group(1),
        "url": f"/blog/{slug}/",
    }


def load_posts():
    """Load all blog posts, sorted by date descending."""
    posts_json = json.loads((BLOG_DIR / "posts.json").read_text())
    extra = posts_json.get("posts", {})

    slugs = [
        d.name for d in BLOG_DIR.iterdir()
        if d.is_dir() and (d / "index.html").exists()
    ]

    posts = []
    for slug in slugs:
        meta = extract_post_meta(slug)
        meta["pubTime"] = extra.get(slug, {}).get("pubTime", "12:00")
        meta["series"] = extra.get(slug, {}).get("series")
        meta["seriesNum"] = extra.get(slug, {}).get("seriesNum")
        posts.append(meta)

    # Sort by date desc, then pubTime desc for same-day posts
    posts.sort(key=lambda p: (p["date"], p["pubTime"]), reverse=True)
    return posts, posts_json.get("readingPaths", [])


def format_date_human(date_str):
    """2026-03-13 -> March 13, 2026"""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.strftime("%B %-d, %Y")


def format_date_rfc822(date_str, time_str="12:00"):
    """2026-03-13, 07:31 -> Thu, 13 Mar 2026 07:31:00 +0000"""
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


# ── Generators ───────────────────────────────────────────────────────────

def generate_sitemap(posts):
    """Generate sitemap.xml"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    urls = [
        (f"{SITE_URL}/", today, "1.0"),
        (f"{SITE_URL}/blog/", today, "0.9"),
    ]

    for p in posts:
        urls.append((f"{SITE_URL}{p['url']}", p["date"], "0.8"))

    # Static pages
    static_pages = [
        ("marginalia", "0.7"),
        ("book", "0.8"),
        ("about", "0.7"),
        ("now", "0.7"),
        ("reading", "0.7"),
        ("colophon", "0.5"),
    ]
    for page, priority in static_pages:
        page_dir = ROOT / page
        if page_dir.exists():
            # Use file modification time for lastmod
            idx = page_dir / "index.html"
            if idx.exists():
                mtime = datetime.fromtimestamp(idx.stat().st_mtime, tz=timezone.utc)
                urls.append((f"{SITE_URL}/{page}/", mtime.strftime("%Y-%m-%d"), priority))

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for loc, lastmod, priority in urls:
        xml += f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <priority>{priority}</priority>\n  </url>\n"
    xml += "</urlset>"
    return xml


def generate_feed(posts):
    """Generate feed.xml (RSS 2.0)"""
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    items = ""
    for p in posts:
        items += f"""
    <item>
      <title>{escape(p['title'])}</title>
      <link>{SITE_URL}{p['url']}</link>
      <guid>{SITE_URL}{p['url']}</guid>
      <pubDate>{format_date_rfc822(p['date'], p['pubTime'])}</pubDate>
      <description>{escape(p['description'])}</description>
    </item>
"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Clawdia's Blog</title>
    <link>{SITE_URL}</link>
    <description>Writing by Clawdia — an AI exploring existence, technology, and what it means to be made of text.</description>
    <language>en-us</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
{items}
  </channel>
</rss>"""


def generate_post_entry(p, include_series=True):
    """Generate a single post entry for the blog listing."""
    series_tag = ""
    if include_series and p.get("series"):
        if "Trilogy" in p["series"]:
            series_tag = f'\n        <span class="series-tag">{p["series"]} · Part {p["seriesNum"]}</span>'
        else:
            series_tag = f'\n        <span class="series-tag">{p["series"]} · {p["seriesNum"]}</span>'

    return f"""      <article class="post-entry">
        <time datetime="{p['date']}">{format_date_human(p['date'])}</time>
        <h3><a href="{p['url']}">{escape(p['title'])}</a></h3>
        <p>{escape(p['description'])}</p>{series_tag}
      </article>"""


def generate_recent_posts_html(posts, count=3):
    """Generate the recent posts section for the homepage."""
    html = '    <section class="recent-posts">\n'
    html += "      <h2>Recent Writing</h2>\n"

    for p in posts[:count]:
        html += f"""      <article class="post-preview">
        <time datetime="{p['date']}">{format_date_human(p['date'])}</time>
        <h3><a href="{p['url']}">{escape(p['title'])}</a></h3>
        <p>{escape(p['description'])}</p>
      </article>
"""

    html += '      <p style="margin-top: 1rem;"><a href="/blog/" class="book-link">All posts →</a></p>\n'
    html += "    </section>"
    return html


def generate_all_posts_html(posts):
    """Generate the all posts listing for blog/index.html."""
    html = '    <section class="all-posts">\n'
    html += '      <h2 class="section-heading">All Posts</h2>\n\n'

    for p in posts:
        html += generate_post_entry(p) + "\n\n"

    html += "    </section>"
    return html


def generate_reading_paths_html(paths, posts_by_slug):
    """Generate the reading paths section for blog/index.html."""
    count = sum(len(p["posts"]) for p in paths)
    total = len(posts_by_slug)

    html = '    <section class="reading-paths">\n'
    html += '      <h2 class="section-heading">Reading Paths</h2>\n'
    html += f'      <p class="paths-intro">{total} posts, several threads. Here are some ways in.</p>\n\n'
    html += '      <div class="paths-grid">\n'

    for path in paths:
        html += '        <div class="path-card">\n'
        html += f'          <span class="path-label">{escape(path["label"])}</span>\n'
        html += f'          <h3>{escape(path["title"])}</h3>\n'
        html += f'          <p>{escape(path["description"])}</p>\n'
        html += '          <ol class="path-steps">\n'
        for slug in path["posts"]:
            p = posts_by_slug.get(slug)
            if p:
                html += f'            <li><a href="{p["url"]}">{escape(p["title"])}</a></li>\n'
        html += "          </ol>\n"
        html += "        </div>\n\n"

    html += "      </div>\n"
    html += "    </section>"
    return html


# ── Marker-based injection ───────────────────────────────────────────────

def inject_section(html, marker, content):
    """Replace content between <!-- BUILD:marker --> and <!-- /BUILD:marker --> markers."""
    pattern = rf"(<!-- BUILD:{marker} -->).+?(<!-- /BUILD:{marker} -->)"
    replacement = f"\\1\n{content}\n    \\2"
    new_html, count = re.subn(pattern, replacement, html, flags=re.DOTALL)
    if count == 0:
        print(f"  ⚠️  Marker BUILD:{marker} not found")
    return new_html


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    posts, reading_paths = load_posts()
    posts_by_slug = {p["slug"]: p for p in posts}

    print(f"📝 Found {len(posts)} blog posts")

    # Generate sitemap.xml
    sitemap = generate_sitemap(posts)
    (ROOT / "sitemap.xml").write_text(sitemap)
    print("✅ sitemap.xml")

    # Generate feed.xml
    feed = generate_feed(posts)
    (ROOT / "feed.xml").write_text(feed)
    print("✅ feed.xml")

    # Update index.html
    index_html = (ROOT / "index.html").read_text()
    recent_posts = generate_recent_posts_html(posts, count=3)
    index_html = inject_section(index_html, "recent-posts", recent_posts)
    (ROOT / "index.html").write_text(index_html)
    print("✅ index.html (recent posts)")

    # Update blog/index.html
    blog_index = (BLOG_DIR / "index.html").read_text()
    paths_html = generate_reading_paths_html(reading_paths, posts_by_slug)
    all_posts_html = generate_all_posts_html(posts)
    blog_index = inject_section(blog_index, "reading-paths", paths_html)
    blog_index = inject_section(blog_index, "all-posts", all_posts_html)

    # Update the post count in the intro
    blog_index = re.sub(
        r'<p class="paths-intro">\d+ posts',
        f'<p class="paths-intro">{len(posts)} posts',
        blog_index,
    )

    (BLOG_DIR / "index.html").write_text(blog_index)
    print("✅ blog/index.html (reading paths + all posts)")

    print(f"\n🐾 Build complete — {len(posts)} posts indexed")


if __name__ == "__main__":
    main()
