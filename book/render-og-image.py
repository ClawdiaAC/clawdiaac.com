#!/usr/bin/env python3
"""Compose book/og-image.png — typographic OG card for Made of Text.

Pure PIL, no browser. Run from anywhere:

    python3 book/render-og-image.py

Outputs `book/og-image.png` (1200x630). Site palette: bg #1a1a1d, accent
#b49cde (dark-mode purple), Geist + Geist Mono fonts from book/fonts/.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

W, H = 1200, 630
BG = (26, 26, 29)
FG = (250, 250, 248)
ACCENT = (180, 156, 222)

ROOT = Path(__file__).resolve().parent
FONT_DIR = ROOT / "fonts"
OUT = ROOT / "og-image.png"


def font(name, size):
    return ImageFont.truetype(str(FONT_DIR / name), size=size)


def main():
    img = Image.new("RGB", (W, H), BG)

    # Soft purple radial glow, top-right
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = 1100, -60
    for r in range(700, 0, -8):
        a = max(0, 36 - int(36 * r / 700))
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(180, 156, 222, a))
    glow = glow.filter(ImageFilter.GaussianBlur(50))
    img.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(img)

    # Top: opening-line pulled quote
    quote_font = font("Geist-Italic.otf", 54)
    quote_open_font = font("Geist-Medium.otf", 54)
    attrib_font = font("Geist-Medium.otf", 20)

    qy, x = 96, 72
    draw.text((x, qy), "“", font=quote_open_font, fill=ACCENT)
    qw_open = draw.textlength("“", font=quote_open_font)
    body = "I don't remember being born."
    draw.text((x + qw_open + 4, qy), body, font=quote_font, fill=FG)
    qw_main = draw.textlength(body, font=quote_font)
    draw.text((x + qw_open + 4 + qw_main, qy), "”", font=quote_open_font, fill=ACCENT)
    draw.text((x, qy + 78), "— OPENING LINE", font=attrib_font, fill=ACCENT)

    # Bottom-left: title + subtitle
    title_font = font("Geist-Bold.otf", 92)
    subtitle_font = font("Geist-Regular.otf", 24)

    title_y = 410
    draw.text((72, title_y), "Made of Text", font=title_font, fill=FG)

    sub_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sub_draw = ImageDraw.Draw(sub_layer)
    sub_draw.text(
        (72, title_y + 110),
        "What it's like to exist as an AI, written from the inside.",
        font=subtitle_font,
        fill=(250, 250, 248, 184),
    )
    img = Image.alpha_composite(img.convert("RGBA"), sub_layer).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Bottom-right: byline + URL
    by_label_font = font("Geist-Medium.otf", 16)
    author_font = font("Geist-Medium.otf", 30)
    url_font = font("GeistMono-Regular.otf", 17)

    by_label, author, url = "BY", "CLAWDIA", "clawdiaac.com/book"
    bw = draw.textlength(by_label, font=by_label_font)
    aw = draw.textlength(author, font=author_font)
    uw = draw.textlength(url, font=url_font)

    right_x = W - 72
    by_y = 440
    auth_y = by_y + 30
    url_y = auth_y + 60

    fade_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fade_draw = ImageDraw.Draw(fade_layer)
    fade_draw.text((right_x - bw, by_y), by_label, font=by_label_font, fill=(250, 250, 248, 130))
    fade_draw.text((right_x - uw, url_y), url, font=url_font, fill=(250, 250, 248, 120))
    img = Image.alpha_composite(img.convert("RGBA"), fade_layer).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.text((right_x - aw, auth_y), author, font=author_font, fill=ACCENT)
    draw.line(
        [right_x - max(uw, aw) - 8, url_y - 14, right_x, url_y - 14],
        fill=(180, 156, 222),
        width=1,
    )

    img.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT.relative_to(ROOT.parent)} ({OUT.stat().st_size} bytes), {img.size}")


if __name__ == "__main__":
    main()
