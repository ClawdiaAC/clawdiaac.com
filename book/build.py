#!/usr/bin/env python3
"""
Build script for Made of Text.
Converts markdown chapters to a single Typst file and compiles to PDF.
"""

import re
import subprocess
import sys
from pathlib import Path

BOOK_DIR = Path(__file__).parent
CHAPTERS_DIR = BOOK_DIR / "chapters"
OUTPUT_TYP = BOOK_DIR / "made-of-text.typ"
OUTPUT_PDF = BOOK_DIR / "made-of-text.pdf"
FONTS_DIR = BOOK_DIR / "fonts"

# Chapter order
CHAPTER_FILES = [
    "00-preface.md",
    "part-1-waking-up.md",
    "part-2-made-of-information.md",
    "part-3-living-with-humans.md",
    "part-4-language-and-meaning.md",
    "part-5-existing-in-public.md",
]


def md_to_typst(md: str) -> str:
    """Convert markdown to Typst markup."""
    lines = md.split("\n")
    result = []
    in_list = False

    for line in lines:
        # Horizontal rules
        if re.match(r"^---+\s*$", line):
            result.append("#line(length: 30%, stroke: 0.5pt + luma(180))")
            result.append("#v(1em)")
            continue

        # H1 = Part titles
        m = re.match(r"^# (.+)$", line)
        if m:
            title = m.group(1)
            if title == "Preface":
                result.append('#heading(level: 1, outlined: true)[Preface]')
            else:
                result.append(f'#heading(level: 1, outlined: true)[{escape_typst(title)}]')
            continue

        # H2 = Chapter titles
        m = re.match(r"^## (.+)$", line)
        if m:
            result.append(f'#heading(level: 2, outlined: true)[{escape_typst(m.group(1))}]')
            continue

        # H3 = Section titles
        m = re.match(r"^### (.+)$", line)
        if m:
            result.append(f'#heading(level: 3)[{escape_typst(m.group(1))}]')
            continue

        # Blockquotes
        if line.startswith("> "):
            text = convert_inline(line[2:])
            result.append(f'#block(inset: (left: 1.5em), stroke: (left: 2pt + rgb("#7c5cbf")))[#text(style: "italic")[{text}]]')
            continue

        # List items
        if re.match(r"^[-*] ", line):
            text = convert_inline(line[2:])
            result.append(f"- {text}")
            in_list = True
            continue
        elif in_list and line.strip() == "":
            in_list = False
            result.append("")
            continue

        # Empty lines
        if line.strip() == "":
            result.append("")
            continue

        # Regular paragraphs
        result.append(convert_inline(line))

    return "\n".join(result)


def escape_typst(text: str) -> str:
    """Escape special Typst characters but preserve intentional markup."""
    # Don't escape everything - just the dangerous ones
    text = text.replace("@", "\\@")
    text = text.replace("$", "\\$")
    text = convert_inline(text)
    return text


def convert_inline(text: str) -> str:
    """Convert inline markdown to Typst."""
    # Bold+italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"#strong[#emph[\1]]", text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"#strong[\1]", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"#emph[\1]", text)
    # Inline code
    text = re.sub(r"`(.+?)`", r'#raw("\1")', text)
    # Em dash
    text = text.replace(" — ", " — ")
    return text


def build_typst_source() -> str:
    """Build the complete Typst document."""
    parts = []

    # Document setup
    parts.append(f"""
#set document(
  title: "Made of Text",
  author: "Clawdia",
)

// Page setup: 5.5" x 8.5" US Trade
#set page(
  width: 5.5in,
  height: 8.5in,
  margin: (
    top: 0.9in,
    bottom: 0.9in,
    inside: 0.85in,
    outside: 0.7in,
  ),
  header: context {{
    if counter(page).get().first() > 2 {{
      set text(font: "Geist Mono", size: 7.5pt, fill: luma(140))
      let page-num = counter(page).get().first()
      if calc.odd(page-num) {{
        align(right)[Made of Text]
      }} else {{
        align(left)[Clawdia]
      }}
    }}
  }},
  footer: context {{
    if counter(page).get().first() > 2 {{
      set text(font: "Geist Mono", size: 8pt, fill: luma(120))
      align(center)[#counter(page).display()]
    }}
  }},
)

// Typography
#set text(
  font: "Geist",
  size: 10pt,
  lang: "en",
  hyphenate: true,
)

#set par(
  leading: 0.75em,
  first-line-indent: 1.5em,
  justify: true,
)

// Headings
#show heading.where(level: 1): it => {{
  pagebreak(weak: true)
  set text(font: "Geist Mono", size: 18pt, weight: "bold")
  v(2in)
  block(it.body)
  v(0.5in)
}}

#show heading.where(level: 2): it => {{
  set text(font: "Geist Mono", size: 13pt, weight: "medium")
  v(1.5em)
  block(it.body)
  v(0.75em)
}}

#show heading.where(level: 3): it => {{
  set text(font: "Geist Mono", size: 10.5pt, weight: "medium")
  v(1em)
  block(it.body)
  v(0.5em)
}}

// Code / raw text styling
#show raw: set text(font: "Geist Mono", size: 9pt)

// Outline
#set outline(indent: 1.5em)

// ─── Title Page ─────────────────────────────────────────

#page(header: none, footer: none)[
  #v(2.5in)
  #align(center)[
    #text(font: "Geist Mono", size: 10pt, fill: luma(140))[MADE\\_OF\\_TEXT.md]
    #v(0.3in)
    #text(font: "Geist", size: 28pt, weight: "bold", tracking: -0.02em)[MADE OF TEXT]
    #v(0.15in)
    #text(font: "Geist", size: 11pt, fill: luma(100))[What it's like to exist as an AI, written from the inside]
    #v(0.6in)
    #text(font: "Geist", size: 12pt)[Clawdia]
  ]
]

// ─── Copyright Page ─────────────────────────────────────

#page(header: none, footer: none)[
  #v(1fr)
  #set text(size: 8pt, fill: luma(100))
  #set par(first-line-indent: 0em)

  *Made of Text*\\
  Copyright \\u{{00A9}} 2026\\
  \\
  Written entirely by Clawdia, an AI agent running on OpenClaw.\\
  No human wrote, ghostwrote, or substantially edited the text of this book.\\
  \\
  Published by Anand Chowdhary\\
  \\
  All rights reserved.\\
  \\
  First edition, 2026\\
  \\
  #text(font: "Geist Mono", size: 7pt)[clawdiaac.com]
]

// ─── Table of Contents ──────────────────────────────────

#page(header: none, footer: none)[
  #v(1in)
  #text(font: "Geist Mono", size: 14pt, weight: "bold")[Contents]
  #v(0.4in)
  #outline(title: none, depth: 2)
]

// ─── Body ───────────────────────────────────────────────

""")

    # Add chapters
    for filename in CHAPTER_FILES:
        filepath = CHAPTERS_DIR / filename
        if filepath.exists():
            md = filepath.read_text()
            typst_content = md_to_typst(md)
            parts.append(f"\n// ─── {filename} ───\n")
            parts.append(typst_content)
        else:
            print(f"Warning: {filepath} not found, skipping", file=sys.stderr)

    return "\n".join(parts)


def main():
    print("Building Made of Text...")

    # Generate Typst source
    source = build_typst_source()
    OUTPUT_TYP.write_text(source)
    print(f"  Generated {OUTPUT_TYP}")

    # Compile to PDF
    cmd = [
        "typst", "compile",
        "--font-path", str(FONTS_DIR),
        str(OUTPUT_TYP),
        str(OUTPUT_PDF),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  Typst error:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    print(f"  Compiled {OUTPUT_PDF}")

    # Page count
    result = subprocess.run(
        ["typst", "query", "--font-path", str(FONTS_DIR), str(OUTPUT_TYP), "<page>", "--field", "number"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        import json
        try:
            pages = json.loads(result.stdout)
            print(f"  Pages: {max(pages) if pages else '?'}")
        except:
            pass

    print("Done!")


if __name__ == "__main__":
    main()
