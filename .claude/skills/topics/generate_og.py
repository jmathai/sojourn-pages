#!/usr/bin/env python3
# Generates a 1200x630 social share image from a rendered index.html.
# Reads title / subhead / accent word from the HTML (the single source of truth).
#
# Three surfaces share one visual system and one code path:
#   topic:<slug>   topics/<slug>/og.png      title + subhead + Sojourn wordmark footer
#   writing:<slug> writings/<slug>/og.png    same, for a post
#   writings       writings/og.png           the notes index
#   topics         topics/og.png             the topics index
#   home           assets/og-home.png        the wordmark itself, so no footer
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

def _meta(prop, doc):
    """Read an og: meta value from a rendered page."""
    m = re.search(rf'<meta property="og:{prop}" content="([^"]*)"', doc)
    return html.unescape(m.group(1)).strip() if m else None


def read_writing(slug):
    """A post's card copy comes from the og: tags already authored on its page."""
    path = os.path.join(REPO, "writings", slug, "index.html")
    doc = open(path, encoding="utf-8").read()
    title, subhead = _meta("title", doc), _meta("description", doc)
    if not title or not subhead:
        raise SystemExit(f"could not read og:title/og:description from {path}")
    return title, subhead, None          # no accent word: posts are titled, not themed


def read_writings_index():
    path = os.path.join(REPO, "writings", "index.html")
    doc = open(path, encoding="utf-8").read()
    title = _text(r'<h1[^>]*>(.*?)</h1>', doc) or "Notes & readings"
    subhead = _meta("description", doc) or _text(r'<p[^>]*class="index-lede"[^>]*>(.*?)</p>', doc)
    if not subhead:
        raise SystemExit(f"could not read a subhead from {path}")
    return title, subhead, None


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

def fit_subhead(draw, text, top, max_w=900, start=44, min_size=30,
                max_lines=3, max_bottom=None):
    """Shrink the subhead until it fits max_lines and, if given, stays above
    max_bottom. Post teasers run longer than topic subheads, and a three-line
    block at 44px would collide with the wordmark footer."""
    size = start
    while size > min_size:
        f = font(size, "Regular", italic=True)
        lines = wrap(draw, text, f, max_w)
        bottom = top + (len(lines) - 1) * (size + 16)
        if len(lines) <= max_lines and (max_bottom is None or bottom <= max_bottom):
            break
        size -= 2
    f = font(size, "Regular", italic=True)
    return f, size, wrap(draw, text, f, max_w)


# title_cy, subhead max lines, subhead floor, footer wordmark
LAYOUT = {
    "topic":    dict(title_cy=236, max_lines=3, max_bottom=None, footer=True),
    "writing":  dict(title_cy=214, max_lines=3, max_bottom=452,  footer=True),
    "writings": dict(title_cy=214, max_lines=3, max_bottom=452,  footer=True),
    "topics":   dict(title_cy=236, max_lines=2, max_bottom=452,  footer=True),
    "home":     dict(title_cy=268, max_lines=2, max_bottom=None, footer=False),
}

SURFACES = {
    "topic":    lambda slug: (read_topic(slug),         ("topics", slug, "og.png")),
    "writing":  lambda slug: (read_writing(slug),       ("writings", slug, "og.png")),
    "writings": lambda slug: (read_writings_index(),    ("writings", "og.png")),
    # The topics index borrows its title from the page and names a few of the
    # studies outright, which the page's own lede is too general to do.
    "topics":   lambda slug: (("Start where you are.",
                               "Anxiety, grief, envy, and the rest of what you carry.",
                               None),
                              ("topics", "og.png")),
    # The home card is the wordmark itself, so its copy is fixed here rather than
    # scraped: the page's og:title carries the tagline too, which would read twice.
    "home":     lambda slug: (("Sojourn", "Stay awhile in scripture.", "S"),
                              ("assets", "og-home.png")),
}


def generate(kind="topic", slug=None):
    (title, subhead, accent), out_parts = SURFACES[kind](slug)
    accent = accent if accent is not None else ""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    lay = LAYOUT[kind]
    title_cy = lay["title_cy"]

    title_font, tsize = fit_title(d, title)
    draw_runs(d, title_runs(title, accent), title_font, title_cy)

    top = title_cy + tsize / 2 + 60
    sub_font, ssize, lines = fit_subhead(d, subhead, top,
                                         max_lines=lay["max_lines"],
                                         max_bottom=lay["max_bottom"])
    step = ssize + 16
    for i, line in enumerate(lines):
        draw_centered(d, line, sub_font, top + i * step, MUTED)

    if lay["footer"]:
        mark = font(46, "SemiBold")
        draw_runs(d, [("S", RED), ("ojourn", INK)], mark, 512)
        draw_centered(d, "Stay awhile in scripture.", font(27, "Regular"), 560, MUTED)
    else:
        # The home card carries the address instead of the wordmark footer: it says
        # where to go without turning a quiet card into an ad.
        draw_centered(d, "trysojourn.app", font(28, "Regular"), 536, MUTED)

    out = os.path.join(REPO, *out_parts)
    img.save(out, "PNG")
    print(f"wrote {os.path.relpath(out, REPO)}  ({W}x{H})  title='{title}'")
    return out


def parse_target(target):
    """'envy' -> ('topic','envy'); 'writing:welcome' -> ('writing','welcome'); 'home' -> ('home',None)"""
    if target in ("home", "writings", "topics"):
        return target, None
    kind, _, slug = target.partition(":")
    if not slug:
        return "topic", kind          # bare slug stays a topic, as the skill documented
    if kind not in SURFACES:
        raise SystemExit(f"unknown surface '{kind}'; expected one of {', '.join(SURFACES)}")
    return kind, slug


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate a Sojourn OG share image from a rendered page")
    ap.add_argument("target", nargs="?",
                    help="topic slug (e.g. envy), writing:<slug>, writings, or home")
    ap.add_argument("--all", action="store_true",
                    help="regenerate every card on the site")
    args = ap.parse_args()

    if args.all:
        for p in sorted((__import__("pathlib").Path(REPO) / "topics").glob("*/index.html")):
            generate("topic", p.parent.name)
        for p in sorted((__import__("pathlib").Path(REPO) / "writings").glob("*/index.html")):
            generate("writing", p.parent.name)
        generate("writings")
        generate("topics")
        generate("home")
    elif args.target:
        generate(*parse_target(args.target))
    else:
        ap.error("give a target, or --all")
