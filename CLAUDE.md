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
- No em dashes anywhere in post prose. Use a comma, a period, parentheses, or
  reword. (This applies to the writing itself, not to the template chrome.)
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

Scripture citations are the site's signature element. When the markdown quotes
scripture, render it with the custom `<citation>` element rather than a blockquote:

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
