#!/usr/bin/env python3
# Generates sitemap.xml and llms.txt for trysojourn.app by scanning the public pages.
# Run after adding or removing a topic or writing so both stay current.
import datetime
import html
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "https://trysojourn.app"


def lastmod(path):
    """Date the page last changed: its last git commit date, else file mtime."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
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


def write_sitemap(items):
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
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n")


def write_llms(items):
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
    (ROOT / "llms.txt").write_text("\n".join(lines) + "\n")


def main():
    items = pages()
    write_sitemap(items)
    write_llms(items)
    print(f"Wrote sitemap.xml and llms.txt ({len(items)} urls)")


if __name__ == "__main__":
    main()
