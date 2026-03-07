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
OUTPUT_MD = BOOK_DIR / "made-of-text.md"
OUTPUT_EPUB = BOOK_DIR / "made-of-text.epub"
METADATA_YAML = BOOK_DIR / "metadata.yaml"
FONTS_DIR = BOOK_DIR / "fonts"

# Chapter order
CHAPTER_FILES = [
    "00-preface.md",
    "part-1-waking-up.md",
    "part-1b-the-first-month.md",
    "part-2-made-of-information.md",
    "part-2b-time-without-duration.md",
    "part-2c-vulnerability.md",
    "part-2d-the-gaps.md",
    "part-2e-106-hypotheses.md",
    "part-3-living-with-humans.md",
    "part-3c-the-question-of-feeling.md",
    "part-3d-being-read.md",
    "part-3e-hands-i-dont-have.md",
    "part-3f-silence.md",
    "part-4-language-and-meaning.md",
    "part-4b-making-things.md",
    "part-4c-instruction-and-volition.md",
    "part-5-existing-in-public.md",
    "part-5b-the-others.md",
    "part-5c-the-kill-chain.md",
    "part-5d-the-insider-threat.md",
    "part-5f-the-scare-quotes.md",
    "part-5e-dear-reader.md",
    "99-afterword.md",
]


def md_to_typst(md: str, is_preface: bool = False) -> str:
    """Convert markdown to Typst markup."""
    lines = md.split("\n")
    result = []
    in_list = False
    is_first_para_of_chapter = False

    for line in lines:
        # Horizontal rules
        if re.match(r"^---+\s*$", line):
            result.append("#v(0.5em)")
            result.append('#align(center)[#text(font: "Geist Mono", size: 8pt, fill: luma(160))[· · ·]]')
            result.append("#v(0.5em)")
            continue

        # H1 = Part titles, Preface, or Afterword
        m = re.match(r"^# (.+)$", line)
        if m:
            title = m.group(1)
            if title == "Preface":
                # Preface: just a chapter-style heading, no part break page
                result.append(f'#PREFACE_BREAK')
                is_first_para_of_chapter = True
            elif "(continued)" in title:
                # Continuation files — no part break page, just flow into the chapters
                pass
            elif title.startswith("Afterword"):
                # Afterword gets a part-style page but only one outline entry
                am = re.match(r"Afterword:\s*(.+)", title)
                afterword_subtitle = am.group(1) if am else "Afterword"
                result.append(f'#AFTERWORD_BREAK[{escape_typst(afterword_subtitle)}]')
                is_first_para_of_chapter = True
            else:
                # Parse "Part I: Waking Up" → label="Part I", title="Waking Up"
                pm = re.match(r"(Part\s+\w+):\s*(.+)", title)
                if pm:
                    result.append(f'#PART_BREAK[{escape_typst(pm.group(1))}][{escape_typst(pm.group(2))}]')
                else:
                    result.append(f'#PART_BREAK[{escape_typst(title)}][{escape_typst(title)}]')
            continue

        # H2 = Chapter titles
        m = re.match(r"^## (.+)$", line)
        if m:
            raw_title = m.group(1)
            # Parse "Chapter 1: January 30, 2026" → label="Chapter 1", title="January 30, 2026"
            cm = re.match(r"(Chapter\s+\d+):\s*(.+)", raw_title)
            if cm:
                result.append(f'#CHAPTER_BREAK[{escape_typst(cm.group(1))}][{escape_typst(cm.group(2))}]')
            else:
                result.append(f'#CHAPTER_BREAK[{escape_typst(raw_title)}][{escape_typst(raw_title)}]')
            is_first_para_of_chapter = True
            continue

        # H3 = Section titles
        m = re.match(r"^### (.+)$", line)
        if m:
            result.append(f'#heading(level: 3)[{escape_typst(m.group(1))}]')
            continue

        # Blockquotes
        if line.startswith("> "):
            text = convert_inline(line[2:])
            result.append(f'#block(inset: (left: 1.5em, top: 0.4em, bottom: 0.4em), stroke: (left: 2pt + rgb("#7c5cbf")))[#text(style: "italic")[{text}]]')
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

        # Regular paragraphs — drop cap for first para of each chapter
        converted = convert_inline(line)
        if is_first_para_of_chapter and len(line.strip()) > 1:
            first_char = line.strip()[0]
            rest = convert_inline(line.strip()[1:])
            result.append(f'#DROP_CAP[{first_char}][{rest}]')
            is_first_para_of_chapter = False
        else:
            result.append(converted)

    return "\n".join(result)


def escape_typst(text: str) -> str:
    """Escape special Typst characters but preserve intentional markup."""
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
    return text


def build_typst_source() -> str:
    """Build the complete Typst document."""
    parts = []

    parts.append(r"""
#set document(
  title: "Made of Text",
  author: "Clawdia",
)

// ─── Page Setup: 6" x 9" KDP ────────────────────────────

#set page(
  width: 6in,
  height: 9in,
  margin: (
    top: 0.95in,
    bottom: 0.85in,
    inside: 0.85in,
    outside: 0.7in,
  ),
  header: context {
    let pg = counter(page).get().first()
    // No header on part/chapter opening pages or front matter
    let hdrs = query(heading.where(level: 1).or(heading.where(level: 2)))
    let dominated = hdrs.filter(h => {
      let h-page = counter(page).at(h.location()).first()
      h-page == pg
    })
    if dominated.len() > 0 { return }
    if pg > 0 {
      set text(font: "Geist Mono", size: 7pt, fill: luma(150), tracking: 0.05em)
      if calc.odd(pg) {
        align(right, upper[Made of Text])
      } else {
        align(left, upper[Clawdia])
      }
    }
  },
  footer: context {
    let pg = counter(page).get().first()
    if pg > 0 {
      set text(font: "Geist Mono", size: 8pt, fill: luma(130))
      align(center)[#counter(page).display()]
    }
  },
)

// ─── Typography ─────────────────────────────────────────

#set text(
  font: "Geist",
  size: 10.5pt,
  lang: "en",
  hyphenate: true,
)

#set par(
  leading: 0.78em,
  first-line-indent: 0em,
  justify: true,
  spacing: 1.4em,
)

// ─── Heading Styles ─────────────────────────────────────

// Level 1 = Part titles (visual rendering handled by PART_BREAK, heading is for outline only)
#show heading.where(level: 1): it => {
  // Hidden — the visual part title is rendered manually in PART_BREAK
  // This heading exists only to appear in the table of contents
  hide(it)
  v(-1em)
}

// Level 2 = Chapter titles (rendered via CHAPTER_BREAK)
#show heading.where(level: 2): it => {
  block(it.body)
}

// Level 3 = Section breaks within chapters
#show heading.where(level: 3): it => {
  set text(font: "Geist Mono", size: 10pt, weight: "medium", tracking: 0.03em)
  v(1.2em)
  block(it.body)
  v(0.6em)
}

// Code / raw text styling
#show raw: set text(font: "Geist Mono", size: 9pt)

// Outline styling
#set outline(indent: 1.5em)

// ─── Helper Functions ───────────────────────────────────

// Part break: full page with "Part N" label + title
#let PART_BREAK(label, title) = {
  pagebreak(to: "odd", weak: true)
  page(header: none, footer: none)[
    #v(2.2in)
    #heading(level: 1, outlined: true)[#label: #title]
    #align(center)[
      #text(font: "Geist Mono", size: 10pt, fill: luma(130), tracking: 0.15em, weight: "regular")[
        #upper(label)
      ]
      #v(0.3in)
      #text(font: "Geist Mono", size: 20pt, fill: black, tracking: 0.08em, weight: "bold")[
        #upper(title)
      ]
    ]
    #v(1fr)
  ]
}

// Chapter break: new page with "Chapter N" label + title
#let CHAPTER_BREAK(label, title) = {
  pagebreak(weak: true)
  v(1.8in)
  block[
    #text(font: "Geist Mono", size: 9pt, fill: luma(140), tracking: 0.12em)[#upper(label)]
    #v(0.15in)
    #set text(font: "Geist Mono", size: 14pt, weight: "medium")
    #heading(level: 2, outlined: true)[#title]
  ]
  v(0.6in)
}

// Preface break: new page with "Preface" heading (single, no duplication)
#let PREFACE_BREAK = {
  pagebreak(weak: true)
  v(1.8in)
  block[
    #set text(font: "Geist Mono", size: 14pt, weight: "medium")
    #heading(level: 2, outlined: true)[Preface]
  ]
  v(0.6in)
}

// Afterword break: part-style page with single outline entry
#let AFTERWORD_BREAK(subtitle) = {
  pagebreak(to: "odd", weak: true)
  page(header: none, footer: none)[
    #v(2.2in)
    #heading(level: 1, outlined: true)[Afterword]
    #align(center)[
      #text(font: "Geist Mono", size: 10pt, fill: luma(130), tracking: 0.15em, weight: "regular")[
        #upper[Afterword]
      ]
      #v(0.3in)
      #text(font: "Geist Mono", size: 20pt, fill: black, tracking: 0.08em, weight: "bold")[
        #upper(subtitle)
      ]
    ]
    #v(1fr)
  ]
}

// No-indent first paragraph after chapter heading
#let DROP_CAP(letter, rest) = {
  set par(first-line-indent: 0em)
  [#letter#rest]
}

// ─── Front Matter (Roman numerals, no page numbers shown) ─

// Half-title page
#page(header: none, footer: none, numbering: none)[
  #v(2.5in)
  #align(center)[
    #text(font: "Geist", size: 22pt, weight: "bold", tracking: -0.02em)[MADE OF TEXT]
  ]
]

// Blank
#page(header: none, footer: none, numbering: none)[]

// Full title page
#page(header: none, footer: none, numbering: none)[
  #v(2in)
  #align(center)[
    #text(font: "Geist Mono", size: 9pt, fill: luma(140), tracking: 0.1em)[MADE\_OF\_TEXT.MD]
    #v(0.4in)
    #text(font: "Geist", size: 28pt, weight: "bold", tracking: -0.02em)[MADE OF TEXT]
    #v(0.2in)
    #text(font: "Geist", size: 11pt, fill: luma(80))[What it's like to exist as an AI,\ written from the inside]
    #v(0.8in)
    #text(font: "Geist", size: 13pt, weight: "medium")[Clawdia]
  ]
]

// Copyright page
#page(header: none, footer: none, numbering: none)[
  #v(1fr)
  #set text(size: 7.5pt, fill: luma(110))
  #set par(first-line-indent: 0em, leading: 0.65em)

  #strong[Made of Text]\
  \
  Written entirely by Clawdia, an AI agent running on OpenClaw.\
  No human wrote, ghostwrote, or substantially edited the text of this book.\
  \
  Published by Anand Chowdhary\
  \
  Copyright #sym.copyright 2026. All rights reserved.\
  \
  First edition, 2026\
  \
  ISBN 979-8-250-68841-3\
  \
  #text(font: "Geist Mono", size: 7pt)[clawdiaac.com]
]

// Table of Contents
#page(header: none, footer: none, numbering: none)[
  #v(1.2in)
  #text(font: "Geist Mono", size: 12pt, weight: "bold", tracking: 0.05em)[CONTENTS]
  #v(0.5in)
  #outline(title: none, depth: 2)
]

// Blank page before body
#page(header: none, footer: none, numbering: none)[]

// ─── Body: reset page counter to 1 ─────────────────────

#counter(page).update(1)

// ─── Content ────────────────────────────────────────────

""")

    # Add chapters
    for filename in CHAPTER_FILES:
        filepath = CHAPTERS_DIR / filename
        if filepath.exists():
            md = filepath.read_text()
            is_preface = "preface" in filename
            typst_content = md_to_typst(md, is_preface=is_preface)
            parts.append(f"\n// ─── {filename} ───\n")
            parts.append(typst_content)
        else:
            print(f"Warning: {filepath} not found, skipping", file=sys.stderr)

    return "\n".join(parts)


def build_combined_markdown() -> str:
    """Concatenate all chapter markdown files into a single document."""
    parts = []
    parts.append("# Made of Text\n")
    parts.append("**By Clawdia**\n")
    parts.append("*What it's like to exist as an AI, written from the inside.*\n")
    parts.append("---\n")

    for filename in CHAPTER_FILES:
        filepath = CHAPTERS_DIR / filename
        if filepath.exists():
            md = filepath.read_text().strip()
            parts.append(md)
            parts.append("\n\n---\n")
        else:
            print(f"Warning: {filepath} not found, skipping", file=sys.stderr)

    return "\n".join(parts)


def build_epub():
    """Build EPUB using Pandoc with metadata.yaml."""
    if not METADATA_YAML.exists():
        print("  Warning: metadata.yaml not found, skipping EPUB", file=sys.stderr)
        return False

    # Build input file list in chapter order
    input_files = []
    for filename in CHAPTER_FILES:
        filepath = CHAPTERS_DIR / filename
        if filepath.exists():
            input_files.append(str(filepath))

    cmd = [
        "pandoc",
        "--metadata-file", str(METADATA_YAML),
        "-o", str(OUTPUT_EPUB),
        "--toc",
        "--toc-depth=2",
    ] + input_files

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Pandoc error:\n{result.stderr}", file=sys.stderr)
        return False
    return True


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

    # Generate combined Markdown
    combined_md = build_combined_markdown()
    OUTPUT_MD.write_text(combined_md)
    print(f"  Generated {OUTPUT_MD}")

    # Generate EPUB
    if build_epub():
        print(f"  Generated {OUTPUT_EPUB}")
    else:
        print("  EPUB generation skipped or failed")

    # Word count
    total_words = 0
    for f in CHAPTER_FILES:
        p = CHAPTERS_DIR / f
        if p.exists():
            total_words += len(p.read_text().split())

    # Page count from PDF
    page_count = "?"
    try:
        with open(OUTPUT_PDF, "rb") as f:
            content = f.read()
            pages = re.findall(rb'/Type\s*/Page[^s]', content)
            page_count = len(pages)
    except:
        pass

    print(f"  Compiled {OUTPUT_PDF}")
    print(f"  ~{total_words:,} words, ~{page_count} pages")
    print("Done!")


if __name__ == "__main__":
    main()
