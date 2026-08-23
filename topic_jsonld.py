#!/usr/bin/env python3
# Injects Article + BreadcrumbList + FAQPage JSON-LD into each topic page, built from
# the page's own title, description, and visible conversation Q&A. Idempotent: rewrites
# the block between the SOJOURN-JSONLD markers. Run after adding or editing a topic.
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "https://trysojourn.app"
START = "<!-- SOJOURN-JSONLD:START -->"
END = "<!-- SOJOURN-JSONLD:END -->"
ORG = {"@type": "Organization", "name": "Sojourn", "url": BASE + "/",
       "logo": BASE + "/assets/favicon-512.png"}


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def first(pattern, text, default=""):
    m = re.search(pattern, text, re.S)
    return m.group(1).strip() if m else default


def build(text, url):
    title = clean(first(r"<title>(.*?)</title>", text))
    title = re.sub(r"\s*·\s*Sojourn$", "", title)
    topic = clean(first(r'<h1 class="topic"[^>]*>(.*?)</h1>', text))
    desc = html.unescape(first(r'<meta name="description" content="(.*?)"', text))
    image = url + "og.png"

    qs = re.findall(r'class="q"[^>]*>(.*?)</p>', text, re.S)
    ans = re.findall(r'class="a"[^>]*>(.*?)</p>', text, re.S)
    faq = [(clean(q), clean(a)) for q, a in zip(qs, ans) if clean(q) and clean(a)]

    graph = [
        {
            "@type": "Article",
            "headline": title,
            "name": title,
            "description": desc,
            "about": {"@type": "Thing", "name": topic},
            "image": image,
            "inLanguage": "en",
            "url": url,
            "mainEntityOfPage": url,
            "author": ORG,
            "publisher": ORG,
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "Topics", "item": BASE + "/topics/"},
                {"@type": "ListItem", "position": 3, "name": topic, "item": url},
            ],
        },
    ]
    if faq:
        graph.append({
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in faq
            ],
        })
    return {"@context": "https://schema.org", "@graph": graph}


def inject(path):
    text = path.read_text()
    url = first(r'<link rel="canonical" href="(.*?)"', text)
    if not url:
        print(f"skip {path} (no canonical)")
        return False
    payload = json.dumps(build(text, url), indent=2, ensure_ascii=False)
    block = f'{START}\n<script type="application/ld+json">\n{payload}\n</script>\n{END}'

    if START in text and END in text:
        new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    else:
        new = text.replace("</head>", block + "\n</head>", 1)
    if new != text:
        path.write_text(new)
        return True
    return False


def main():
    changed = 0
    for path in sorted((ROOT / "topics").glob("*/index.html")):
        if inject(path):
            changed += 1
            print(f"updated {path.relative_to(ROOT)}")
    print(f"Topic JSON-LD: {changed} page(s) updated")


if __name__ == "__main__":
    main()
