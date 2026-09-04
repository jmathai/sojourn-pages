# Sojourn — writing & publishing

Static site published from this repo's root. This file describes how to draft and
publish blog posts. Follow it exactly.

## Layout

```
writings/
  <slug>.md              # source posts, flat — one file per post
  <slug>/index.html      # generated page for each <slug>.md
  index.html             # generated list of all posts
```

- Source markdown lives directly in `writings/` (flat, no subfolders).
- Every `writings/<slug>.md` gets a folder `writings/<slug>/` containing an
  `index.html` rendered from `blog-template.html`.
- `writings/index.html` lists every post, rendered from `blog-list-template.html`.
- A post is served at `/writings/<slug>/`; the list is served at `/writings/`.
- `<slug>` is the markdown filename minus `.md`. Never rename or invent slugs —
  the filename is the slug.

## Voice

The writing is the point. Every post should read like a real person wrote it, not
a machine.

- Informal, warm, and friendly. Write like you're talking to a friend you respect,
  not lecturing a room.
- Well articulated. Warm does not mean sloppy. Say things clearly and let good
  sentences do the work.
- It must not sound AI-drafted. Avoid the tells: no "delve", "tapestry",
  "in a world where", "it's important to note", tidy rule-of-three lists, or hedgy
  throat-clearing. Cut filler. Let sentences vary in length.
- No em dashes anywhere in copy we author. This is a hard rule and it is site-wide: not in
  post prose, not in topic-page prose, and not in metadata (page titles, meta descriptions,
  `og:`/`twitter:` tags, JSON-LD, image `alt`). Use a comma, a period, a colon, parentheses,
  or reword. Separate title segments with ` &middot; ` (`·`), never ` — `. The only exception
  is verbatim WEB scripture, which keeps its original punctuation (`&mdash;` included).
- Prefer plain words, contractions, and concrete images over abstraction.

## Post front matter

Every `writings/<slug>.md` starts with a YAML front matter block:

```markdown
---
title: On envy, and the long work of loving what is not ours
date: 2026-07-30
category: Reading
author: A. Writer
---

The post body in markdown follows here...
```

- `title` — post title. Maps to `<h1>`, `<title>` (as `{title} &middot; Sojourn`), and the list item link text.
- `date` — `YYYY-MM-DD`. Controls list ordering (newest first).
- `category` — the small eyebrow label above the title (e.g. `Reading`). Maps to `.post-meta`.
- `author` — maps to the byline `<b>`.
- Read time is **computed**, not stored: `max(1, round(body_words / 200))` min, rendered as `N min read` in the byline.
- `summary` is **derived**, not stored: when rendering the list, write a one or two
  sentence teaser that captures the post from its body. It maps to `.summary` in the
  list and is not shown on the post page. Follow the same Voice rules as post prose.

## Rendering a post (`writings/<slug>/index.html`)

Start from `blog-template.html` and replace the placeholder content, keeping the
header, footer, and all `<style>` untouched:

- `<title>` → `{title} &middot; Sojourn`
- `<meta name="description">` → the post's derived `summary` (see below), for search results
- `<link rel="canonical">` → `https://trysojourn.app/writings/<slug>/`
- Author + article metadata (for search and answer-engine attribution):
  `<meta name="author">` and `article:author` → `{author}`; `og:type` → `article`;
  `article:published_time` → `{date}`; `article:modified_time` → the date the body last
  changed (`{date}` until then).
- Social card: `og:site_name` `Sojourn`, `og:title` `{title}`, `og:description` (the
  summary), `og:url` (the canonical), `og:image` `/writings/<slug>/og.png` (with
  `og:image:width` 1200, `og:image:height` 630, and an `og:image:alt`), and the matching
  `twitter:` summary_large_image tags.
- Social share card: generate `writings/<slug>/og.png` with the topics skill's generator,
  `generate_og.py writing:<slug>`. It reads the post's own `og:title` and `og:description`,
  so render those tags first. Regenerate whenever the title or summary changes.
- JSON-LD `BlogPosting`: `headline` `{title}`, `description` (summary), `url` +
  `mainEntityOfPage` (canonical), `datePublished`/`dateModified` (as above), `inLanguage`
  `en`, `image` `/writings/<slug>/og.png`, `author` a Person `{author}`, publisher Sojourn.
- `.post-meta` → `{category}`
- `<h1>` → `{title}`
- `.byline` → `By <b>{author}</b> &middot; {read_time} min read`
- `.prose` → the rendered markdown body (everything after the front matter)

Markdown → HTML mapping inside `.prose`:

| Markdown | HTML |
| --- | --- |
| paragraph | `<p>` |
| `## Heading` | `<h2>` |
| `### Heading` | `<h3>` |
| `**bold**` | `<strong>` |
| `*italic*` | `<em>` |
| `[text](url)` | `<a href="url">` |
| `- item` / `1. item` | `<ul>`/`<ol>` with `<li>` |
| `> quote` | `<blockquote><p>…</p></blockquote>` (add `<cite>…</cite>` if attributed) |
| `` `code` `` | `<code>` |
| fenced ` ``` ` block | `<pre><code>…</code></pre>` |
| `---` | `<hr>` |
| `![alt](src)` | `<figure><img src="src" alt="alt"><figcaption>…</figcaption></figure>` (figcaption only if the markdown supplies a caption) |

Scripture citations are the site's signature element, and they carry its core promise.

**Quote, never compose (site-wide).** Any scripture shown anywhere on the site, in posts,
topic pages, or any future page, is quoted verbatim from the World English Bible and verified
against the WEB source. It is never written, paraphrased, or recalled from memory. Resolve
every reference against the WEB data before showing its text, and keep the source's original
punctuation (`&mdash;` included, the one place em dashes are allowed). Today the verifier lives
with its only consumer, the topics skill (`.claude/skills/topics/verify-scripture.py`); when a
second surface starts quoting scripture (a post's `<citation>`, say), promote it to its own
skill and run it there too.

When the markdown quotes scripture, render it with the custom `<citation>` element rather than
a blockquote:

```html
<citation>
  <span class="ref">1 Corinthians 13:4&ndash;5</span>
  <span class="v">4</span>Love is patient and kind. Love does not <em>envy</em>… <span class="v">5</span>keeps no record of wrongs.
</citation>
```

- `.ref` is the reference line. `.v` spans are optional verse numbers — drop them for plain quotation.
- Wrap an emphasized phrase in `<em>` inside a citation to give it the amber highlight.

Escape HTML-significant characters in prose (`&`, `<`, `>`) and prefer entities
like `&ndash;` and `&middot;` to match the existing templates. Never use `&mdash;`
or a literal em dash in post output.

## Keeping the list in sync (`writings/index.html`)

Whenever a post is added, removed, or its `title`/`date`/body changes,
regenerate `writings/index.html` from `blog-list-template.html`:

- One `<li class="post-item">` per post, ordered by `date` **newest first**.
- Header, footer, lede, and `<style>` stay as in the template.
- Each item:

```html
<li class="post-item">
  <h2><a href="/writings/<slug>/">{title}</a></h2>
  <p class="summary">{summary}</p>
  <a class="more" href="/writings/<slug>/">Read more <span class="arr">&rarr;</span></a>
</li>
```

## Rules

- Editing a post's markdown means re-rendering **both** `writings/<slug>/index.html`
  and (if title/date/body changed) `writings/index.html`. Never let them drift.
- The templates in the repo root are the single source of truth for chrome and
  styling. Do not fork their CSS into posts — copy the template, swap the content.
- Post links are always root-absolute: `/writings/<slug>/`.
- After adding or removing a post, regenerate the sitemap and llms.txt: run
  `python3 generate_seo.py` from the repo root (it discovers posts by scanning `writings/`).
- Before pushing, run `python3 generate_seo.py --check`. It exits non-zero if the sitemap
  or `llms.txt` is stale, or if any page is missing its canonical, is missing a meta
  description, has one over 160 characters, or carries invalid JSON-LD.
