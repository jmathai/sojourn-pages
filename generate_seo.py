#!/usr/bin/env python3
# Generates sitemap.xml and llms.txt for trysojourn.app by scanning the public pages.
# Run after adding or removing a topic or writing so both stay current.
import argparse
import datetime
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "https://trysojourn.app"


def _uncommitted():
    """Paths with staged, unstaged, or untracked changes, relative to the repo root."""
    try:
        out = subprocess.run(["git", "status", "--porcelain"],
                             cwd=ROOT, capture_output=True, text=True).stdout
    except Exception:
        return set()
    # Porcelain lines are "XY path", and renames read "XY old -> new".
    return {line[3:].split(" -> ")[-1].strip().strip('"')
            for line in out.splitlines() if line[3:].strip()}


UNCOMMITTED = _uncommitted()


def lastmod(path):
    """Date the page last changed.

    A page edited but not yet committed changed today, whatever its last commit
    says. Using the commit date for those would make the sitemap stale the moment
    it is generated, since it is written and committed alongside the pages it
    describes."""
    rel = str(path.relative_to(ROOT))
    if rel in UNCOMMITTED:
        return datetime.date.today().isoformat()
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", rel],
            cwd=ROOT, capture_output=True, text=True,
        ).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    return datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()


def pages():
    """(url path, file, priority) for every indexable page, newest sections discovered.

    The in-app /whats-new/ page is intentionally excluded (it is noindex)."""
    items = [
        ("/", ROOT / "index.html", "1.0"),
        ("/topics/", ROOT / "topics" / "index.html", "0.9"),
    ]
    items += [(f"/topics/{p.parent.name}/", p, "0.8")
              for p in sorted((ROOT / "topics").glob("*/index.html"))]
    items.append(("/writings/", ROOT / "writings" / "index.html", "0.6"))
    items += [(f"/writings/{p.parent.name}/", p, "0.6")
              for p in sorted((ROOT / "writings").glob("*/index.html"))]
    items.append(("/privacy/", ROOT / "privacy" / "index.html", "0.3"))
    return [(url, f, prio) for url, f, prio in items if f.exists()]


def meta(path):
    """(link title, description) pulled from a page's <title> and meta description."""
    text = path.read_text(errors="ignore")
    t = re.search(r"<title>(.*?)</title>", text, re.S)
    d = re.search(r'<meta name="description" content="(.*?)"', text, re.S)
    title = html.unescape(t.group(1).strip()) if t else path.parent.name
    title = re.sub(r"\s*·\s*Sojourn$", "", title)
    title = re.sub(r"^Sojourn\s*·\s*", "", title)
    desc = html.unescape(d.group(1).strip()) if d else ""
    return title, desc


def build_sitemap(items):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url, f, prio in items:
        lines += [
            "  <url>",
            f"    <loc>{BASE}{url}</loc>",
            f"    <lastmod>{lastmod(f)}</lastmod>",
            f"    <priority>{prio}</priority>",
            "  </url>",
        ]
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def build_llms(items):
    """A curated map of the site for LLMs and answer engines (see llmstxt.org)."""
    by_url = {url: (f, prio) for url, f, prio in items}
    home_title, home_desc = meta(by_url["/"][0])
    lines = [
        "# Sojourn",
        "",
        f"> {home_desc}",
        "",
        "Sojourn is an iOS app and website (https://trysojourn.app) for reading and "
        "reflecting on scripture. Each topic below is a study that quotes the World "
        "English Bible verbatim, with every verse a door into the chapter around it.",
    ]

    def section(heading, prefix, exclude=()):
        rows = [(url, f) for url, (f, _) in by_url.items()
                if url.startswith(prefix) and url not in exclude]
        if not rows:
            return
        lines.append("")
        lines.append(f"## {heading}")
        for url, f in rows:
            title, desc = meta(f)
            lines.append(f"- [{title}]({BASE}{url})" + (f": {desc}" if desc else ""))

    section("Topics", "/topics/")
    section("Writings", "/writings/")
    section("About", "/privacy/")
    return "\n".join(lines) + "\n"


DESC_MAX = 160          # Google truncates search snippets around 150-160 characters


def audit(items):
    """Problems a search console would flag, checked against the pages themselves."""
    problems = []
    for url, f, _ in items:
        text = f.read_text(errors="ignore")
        expected = f"{BASE}{url}"

        m = re.search(r'<link rel="canonical" href="([^"]+)"', text)
        if not m:
            problems.append(f"{url} has no canonical")
        elif m.group(1) != expected:
            problems.append(f"{url} canonical is {m.group(1)}, expected {expected}")

        m = re.search(r'<meta name="description" content="([^"]*)"', text)
        if not m or not m.group(1).strip():
            problems.append(f"{url} has no meta description")
        else:
            n = len(html.unescape(m.group(1)))
            if n > DESC_MAX:
                problems.append(f"{url} description is {n} chars, over {DESC_MAX}")

        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                                text, re.S):
            try:
                json.loads(block)
            except ValueError as e:
                problems.append(f"{url} has invalid JSON-LD ({e})")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify without writing; exit 1 if anything is stale or missing")
    args = ap.parse_args()

    items = pages()
    problems = audit(items)

    if args.check:
        for name, build in (("sitemap.xml", build_sitemap), ("llms.txt", build_llms)):
            path = ROOT / name
            current = path.read_text() if path.exists() else None
            if current != build(items):
                problems.append(f"{name} is out of date, re-run without --check")
        for p in problems:
            print(f"  {p}")
        print(f"{len(problems)} problem(s)" if problems
              else f"{len(items)} urls, sitemap and llms.txt current, head tags clean")
        return 1 if problems else 0

    (ROOT / "sitemap.xml").write_text(build_sitemap(items))
    (ROOT / "llms.txt").write_text(build_llms(items))
    print(f"Wrote sitemap.xml and llms.txt ({len(items)} urls)")
    for p in problems:
        print(f"  head-tag problem: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
