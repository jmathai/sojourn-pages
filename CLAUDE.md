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
- No "this, not that". Say what a thing is and stop. Constructions like "a conversation,
  not a search box", "the whole passage, not a snippet", "answered gently, never pushed",
  "read it whole instead of in pieces", or "built rather than argued about" are a tell, and
  they get worse the more of them sit near each other. Rewrite each one as a plain positive
  statement. This covers the whole family: `X, not Y`, `not X, but Y`, `X instead of Y`,
  `X rather than Y`, and `never Y` used for punch. It applies to headings, body copy, and
  metadata alike.
- Write the way people actually talk. Short common words over polished ones. "Tap a verse
  and the lines around it come too" beats "every verse opens into the passage around it".
  If a sentence sounds like it was written to be admired, rewrite it.
- Two exceptions, both narrow. A contrast that is the actual point can stay when it is
  definitional ("time is credited action by action rather than end to end") or when removing
  it would change the meaning. And verbatim WEB scripture is never touched.

### The topic studies are a separate voice

`/topics/{topic}` study prose (`topics/*/index.html`, `topic-template.html`, and the FAQ
text mirrored into their JSON-LD) is exempt from the "this, not that" rule. That writing is
teaching, and its contrasts carry the meaning: "it isn't quite grief, which is tied to a loss
you can name", "the promise isn't that the loss didn't matter, it's that it gets undone".
Leave them alone. The rest of the Voice rules, em dashes included, still apply there.

Everything else is product voice and follows the rules above: the home page, `/redemptive-ai/`,
`/topics/` (the list page chrome, not the studies), `/writings/` list copy, `/privacy/`, the
demo captions in `index.html` and `sojourn-phone-demo.html`, and all metadata.

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

## Images

Every raster asset lives in `assets/` and is served from `/assets/<name>`. Screenshots are
the heaviest thing the site ships, so they are always resized and re-encoded before they
land in the repo. Never commit a file straight out of Photos, Downloads, or a simulator.

**Required tools.** `brew install jpeg-turbo webp`. Check with `which cjpeg cwebp jpegtran`
before encoding anything. `sips` ships with macOS and is fine for resizing, but its JPEG
encoder is much worse than libjpeg-turbo (it produced 128KB where `cjpeg` produced 73KB on
the same picture), and it writes top-down BMPs that `cjpeg` rejects with `Empty BMP image`,
so convert through PPM when piping between them.

**Every image ships as both WebP and JPEG**, as a `<picture>` with the WebP first:

```html
<picture>
  <source srcset="/assets/<name>.webp" type="image/webp">
  <img src="/assets/<name>.jpg" width="816" height="1766" alt="..." decoding="async">
</picture>
```

WebP runs roughly 40% smaller than JPEG at the same visible quality, so it is worth the
second file every time. `<source>` wins over `<img>`, which means **a stale `.webp` beside a
new `.jpg` silently serves the old picture to most browsers**. Regenerate both together or
delete both.

**Encoding.** Resize to the width the page actually renders (816 for the phone shots), then
take exactly one lossy step from the most original source available. Encoding a JPEG that
came from another JPEG stacks generation loss, so reach for the PNG or the screenshot
original when there is one.

```
sips --resampleWidth 816 -s format bmp in.png --out t.bmp   # resize, lossless
cjpeg -quality 80 -progressive -optimize -sample 1x1 -outfile out.jpg t.ppm
cwebp -q 80 -m 6 in.png -o out.webp
```

Keep `-sample 1x1` (no chroma subsampling) on anything with text in it; the screenshots are
all text. Quality 80 holds up on serif body copy. `jpegtran -copy none -optimize -progressive`
is a free lossless pass that also strips metadata, so run it and keep the result if smaller.

**Crossfading two shots.** When one screenshot fades into another to animate something (the
notification landing on `/sermons/`), the two captures have to come from the same session,
seconds apart, with only the thing being animated different between them. Even then they
are not pixel identical: a PNG and a JPEG of the same moment differ by a few levels
everywhere, which is small enough to ignore. If a pair ever does drift visibly, crop the
changing region out of one capture and lay that strip over the other with CSS instead of
fading two full frames.

**One clock across a set.** Every screenshot in the same hero or carousel has to agree on
its status bar, because they fade into each other: same time, same battery, same signal,
same presence or absence of the dynamic island. Shots taken on different devices or hours
apart will visibly jump. When a reshoot is not possible, rebuild the odd one's status bar
from a good one: wipe the bar down to the app's own background colour, then composite the
good shot's glyphs back on by deriving a per-pixel alpha from how far each source pixel
falls below its own background (`alpha = (bg - pixel) / bg`, then `out = bg_target *
(1 - alpha)`). That keeps the real system font and antialiasing and leaves no patch seam.
Watch the soft edges: the island's antialiasing trails four rows past where it looks like
it ends, and a leftover delta of 4 is invisible alone but reads as a streak on flat paper.

## Header navigation

Every public page carries the same header nav, so a reader can always reach the two
surfaces the app itself has tabs for. It mirrors the app: **Chat** is the home page
(`/`) and **Sermons** is `/sermons/`.

The wordmark and the nav sit together in a left-hand group; whatever the page already
had on the right (the `Scripture, unhurried` note, or the App Store link) stays put.

```html
<header class="site-head">
  <div class="head-left">
    <a href="/" class="mark"><span style="color:var(--rubric);">S</span>ojourn</a>
    <nav class="site-nav" aria-label="Site"><a href="/">Chat</a><a href="/sermons/">Sermons</a></nav>
  </div>
  <a href="https://apps.apple.com/..." class="get">...</a>
</header>
```

- Mark the current page with `aria-current="page"` on its own link, and only there. The
  home page sets it on Chat, `/sermons/` sets it on Sermons, every other page sets it on
  neither.
- The nav's font is declared on `.site-nav a` itself, never left to inherit. Some pages
  style `.site-head a` directly, and that rule would otherwise render the nav in 22px serif.
- The header is `flex-wrap:wrap` with `gap:10px 16px`. Without it the mark, the nav, and
  the App Store link overflow a phone; wrapping drops the App Store link to its own line
  instead of hiding it.
- A new page gets the nav by copying a template. The four templates in the repo root all
  carry it, so anything generated from them inherits it.
- `/whats-new/` is the one exception. It is an in-app web view (`noindex`), so site nav
  there would walk a user out of the app. Leave it without a header.

## Rules

- Editing a post's markdown means re-rendering **both** `writings/<slug>/index.html`
  and (if title/date/body changed) `writings/index.html`. Never let them drift.
- The templates in the repo root are the single source of truth for chrome and
  styling. Do not fork their CSS into posts — copy the template, swap the content.
- A new public page carries the header nav (see **Header navigation**). Copying a
  template gives it to you; a hand-built page has to add it, `/whats-new/` excepted.
- Post links are always root-absolute: `/writings/<slug>/`.
- After adding or removing a post, regenerate the sitemap and llms.txt: run
  `python3 generate_seo.py` from the repo root (it discovers posts by scanning `writings/`).
- Before pushing, run `python3 generate_seo.py --check`. It exits non-zero if the sitemap
  or `llms.txt` is stale, or if any page is missing its canonical, is missing a meta
  description, has one over 160 characters, or carries invalid JSON-LD.
