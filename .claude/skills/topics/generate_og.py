#!/usr/bin/env python3
# Generates a topic's 1200x630 social share image from its rendered index.html.
# Reads title / subhead / accent word from the HTML (the single source of truth).
import os, re, sys, html, argparse
from PIL import Image, ImageDraw, ImageFont

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(SKILL_DIR, "..", "..", ".."))
FONT = os.path.join(SKILL_DIR, "fonts", "EBGaramond.ttf")
FONT_ITALIC = os.path.join(SKILL_DIR, "fonts", "EBGaramond-Italic.ttf")

W, H = 1200, 630
BG    = (0xF2, 0xED, 0xE3)   # warm paper
INK   = (0x3A, 0x34, 0x2D)   # title / wordmark
RED   = (0xA3, 0x2E, 0x22)   # Sojourn red accent
MUTED = (0x78, 0x70, 0x64)   # subhead / tagline

def font(size, weight="Regular", italic=False):
    f = ImageFont.truetype(FONT_ITALIC if italic else FONT, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f

def _text(pattern, doc, flags=re.S):
    m = re.search(pattern, doc, flags)
    if not m:
        return None
    inner = re.sub(r"<[^>]+>", "", m.group(1))          # strip inline tags (e.g. <b>)
    return re.sub(r"\s+", " ", html.unescape(inner)).strip()

def read_topic(slug):
    path = os.path.join(REPO, "topics", slug, "index.html")
    doc = open(path, encoding="utf-8").read()
    title = _text(r'<h1[^>]*class="topic"[^>]*>(.*?)</h1>', doc)
    subhead = _text(r'<p[^>]*class="subhead"[^>]*>(.*?)</p>', doc)
    m = re.search(r'<h1[^>]*class="topic"[^>]*\bdata-og-accent="([^"]*)"', doc)
    accent = html.unescape(m.group(1)).strip() if m else title  # default: whole title
    if not title or not subhead:
        raise SystemExit(f"could not read title/subhead from {path}")
    return title, subhead, accent

def title_runs(title, accent):
    """Split the title into colored runs, accent phrase in red."""
    i = title.lower().find(accent.lower()) if accent else -1
    if i < 0:
        return [(title, INK)]
    runs = []
    if title[:i]:        runs.append((title[:i], INK))
    runs.append((title[i:i+len(accent)], RED))
    if title[i+len(accent):]: runs.append((title[i+len(accent):], INK))
    return runs

def draw_runs(draw, runs, fnt, cy):
    total = sum(draw.textlength(t, font=fnt) for t, _ in runs)
    x = (W - total) / 2
    for t, color in runs:
        draw.text((x, cy), t, font=fnt, fill=color, anchor="lm")
        x += draw.textlength(t, font=fnt)

def draw_centered(draw, text, fnt, cy, color):
    draw.text((W / 2, cy), text, font=fnt, fill=color, anchor="mm")

def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines

def fit_title(draw, title, start=164, min_size=64, max_w=1000):
    size = start
    while size > min_size:
        f = font(size, "SemiBold")
        if draw.textlength(title, font=f) <= max_w:
            break
        size -= 2
    return font(size, "SemiBold"), size

def generate(slug):
    title, subhead, accent = read_topic(slug)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    title_font, tsize = fit_title(d, title)
    title_cy = 236
    draw_runs(d, title_runs(title, accent), title_font, title_cy)

    sub_font = font(44, "Regular", italic=True)
    lines = wrap(d, subhead, sub_font, 900)
    step = 60
    top = title_cy + tsize / 2 + 60
    for i, line in enumerate(lines):
        draw_centered(d, line, sub_font, top + i * step, MUTED)

    mark = font(46, "SemiBold")
    draw_runs(d, [("S", RED), ("ojourn", INK)], mark, 512)
    draw_centered(d, "Stay awhile in scripture.", font(27, "Regular"), 560, MUTED)

    out = os.path.join(REPO, "topics", slug, "og.png")
    img.save(out, "PNG")
    print(f"wrote {out}  ({W}x{H})  title='{title}' accent='{accent}'")
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate a topic's OG share image from its index.html")
    ap.add_argument("slug", help="topic slug, e.g. envy")
    generate(ap.parse_args().slug)
