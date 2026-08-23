#!/usr/bin/env python3
# Generates sitemap.xml for trysojourn.app by scanning the site's public pages.
# Run after adding or removing a topic or writing so the sitemap stays current.
import datetime
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


def main():
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    items = pages()
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
    print(f"Wrote sitemap.xml with {len(items)} urls")


if __name__ == "__main__":
    main()
