---
name: topics
description: Build and maintain Sojourn topic pages at /topics/{topic} — data-driven scripture study pages that reuse the app's peek-sheet and chapter-reader interactions. Use when creating a new topic page, editing topic content (reflection, study arc, seeded conversation), or turning the topic templates into the data-driven, WEB-verified system.
---

# Sojourn Topic Pages

This skill builds the `/topics/{topic}` pages: static study pages that let a visitor
experience Sojourn's core interaction — scripture citations as doors into the text —
before installing the app.

## Output layout

Each topic is its own folder, mirroring the `writings/<slug>/index.html` convention:

```
topics/
  <slug>/index.html    # the topic page — content authored directly here
  <slug>/og.png        # generated 1200×630 social share image (see below)
  index.html           # the topics index
```

- Author a topic page by copying `topic-template.html` and replacing its content,
  keeping the chrome, styles, and interaction JS intact ("copy the template, swap the
  content", the same way the writings pages are made). There is **no JSON or other
  intermediate data file** — the HTML is the single source of truth for a topic's prose,
  study arc, and seeded conversation.
- Scripture is the one exception to authoring directly: every verse's text is read
  verbatim from the WEB database **at generation time** and embedded into the HTML.
  Never hand-type or paraphrase scripture. The database is a build-time tool only — the
  shipped `index.html` must be fully self-contained, with all verse text (including the
  full chapter-source blocks the reader uses) baked in. The page never queries the
  database or fetches scripture at runtime.
- The topics index is authored the same way, by copying `topic-list-template.html`.
- A topic is served at `/topics/<slug>/`; the index at `/topics/`. `<slug>` is the topic
  slug (e.g. `envy` → `topics/envy/index.html`, served at `/topics/envy/`).
- Update `topics/index.html` whenever a topic is added, removed, or its card state
  (live vs. "coming soon") changes.
- Every topic also ships a generated `og.png` social card and per-topic OG/Twitter meta
  tags — see **Social share image (og.png)** below. Regenerate the image whenever the
  topic's title, subhead, or accent word changes.

## Guidelines

The full design, interaction model, page anatomy, systematization contract, and the
Envy prototype content pack live in **`sojourn-topic-page-handoff.md`** alongside this
file. That document is the source of truth — follow it exactly. `topic-template.html`
and `topic-list-template.html` in the repo root are the visual + interaction reference;
where they conflict with the prose spec, the templates win (see the "Deltas" section of
the handoff).

**One deliberate override of the handoff:** ignore its "Systematization contract" and
the JSON-driven generator it describes (`topics/<slug>.json`, build-time rendering from
a data file). Topic content lives directly in the HTML per the Output layout above. The
handoff still governs everything else — design language, page anatomy, interaction
model, and the "quote scripture, never compose it" rule.

Non-negotiable, and reinforced by the scripture-database rule below: **the page never
generates or paraphrases scripture.** Prose is the hallway; scripture is the rooms.

## Environment setup (first use)

Create a virtualenv that belongs to this skill and work inside it. Never install into
the system Python.

```bash
VENV="$(dirname "$0")/.venv"
[ -d "$VENV" ] || python3 -m venv "$VENV"
source "$VENV/bin/activate"
```

Install any Python dependencies the build needs into this venv only. The social-share-image
step needs **Pillow** (`"$VENV/bin/pip" install Pillow`); the scripture step needs only the
standard library.

## Social share image (og.png)

Every topic page ships a 1200×630 social share card at `topics/<slug>/og.png`, generated
deterministically from the page's own HTML — no manual design step. Generate it whenever a
topic is created, or its title/subhead/accent changes:

```bash
"$VENV/bin/python" .claude/skills/topics/generate_og.py <slug>
```

`generate_og.py` reads the topic's `index.html` (the single source of truth): the title from
`<h1 class="topic">`, the subhead from `.subhead`, and the accent word from an optional
`data-og-accent` attribute on the `<h1>`. The vendored **EB Garamond** font lives in
`.claude/skills/topics/fonts/` and is checked in — never fetched at build.

- **Accent word.** The title word set in Sojourn red defaults to the whole title, which is
  right for single-word topics like *Envy*. For a multi-word title, mark the accent word on
  the heading so it carries into the card without changing the page's appearance:
  `<h1 class="topic" data-og-accent="Anger">Slow to anger</h1>`.
- **Design.** Warm paper `#F2EDE3`; title in EB Garamond (accent word `#A32E22`, rest
  `#3A342D`); subhead in muted `#787064`; the `Sojourn` wordmark and "Stay awhile in
  scripture." near the bottom. It is a sibling of the App Store screenshots — nothing else
  on the canvas.

### Per-topic meta tags (in the page `<head>`)

Carry these on every topic page, using the topic's **absolute** URL (relative URLs break
scrapers):

```html
<meta property="og:image" content="https://trysojourn.app/topics/<slug>/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="<Title>, a Bible study from Sojourn">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="<mirrors og:title>">
<meta name="twitter:description" content="<mirrors og:description>">
<meta name="twitter:image" content="https://trysojourn.app/topics/<slug>/og.png">
```

## Per-topic requirements (metadata, structured data, conversation, links)

Beyond the study prose, every topic page carries the following. All of it is verified
locally by **`CHECKLIST.md`** (local-first ordering, in this skill) and **`verify-scripture.py`**
(run `python3 .claude/skills/topics/verify-scripture.py topics/<slug>/index.html` from the repo root).
Run the checklist end to end before shipping.

**Voice split.** On-page copy is poetic (reflection, arc, conversation). Page *metadata* is
query-shaped and must name the subject:

- `<title>` = `What the Bible Says About {Topic} · Sojourn` (segments joined with ` &middot; `,
  never an em dash). Every topic title contains the word **Bible**.
- `<meta name="description">` is query-shaped and also contains **Bible**, e.g.
  `A Bible study on {topic} from Sojourn: {poetic subhead}. Every verse is a door into the
  chapter around it.`
- `og:title` mirrors `<title>`; `og:description` may keep the poetic subhead; `twitter:title`
  / `twitter:description` mirror the OG pair. The `<h1>` and on-page copy never change for SEO.

**JSON-LD** — two inline `<script type="application/ld+json">` blocks in the head:

- `Article`: `headline` = `What the Bible Says About {Topic}` (no ` · Sojourn` suffix), `description`
  = the meta description, `url` = the canonical, `image` = **exactly** the `og:image` URL,
  `datePublished` set honestly per page, `dateModified` bumped on material changes, `publisher`
  = Sojourn.
- `FAQPage`: one entry per single-turn exchange plus the **opener** of the two-turn exchange;
  the two-turn's follow-up is **not** its own entry. Answer `text` is the first paragraph of
  the visible answer with door markup flattened to `"quote" (Reference)`, matching the rendered
  page verbatim. If the conversation wording changes, update the JSON.

**Seeded conversation — four exchanges:** disarming → two-turn (the single exchange with a
follow-up) → **distinction** → hope-shaped close. The distinction exchange absorbs the topic's
highest-volume synonym or "X vs Y" query where natural (e.g. envy vs jealousy). Every quoted
fragment is a live door, byte-verified against WEB.

**Doors are inline anchors.** Each inline door is `<a class="door" href="#src-{chapter}" …>`,
never a `<button>`: a true inline element (trailing punctuation must hug the reference), and
with JS off it degrades to an in-page anchor that reveals the hidden `.chapter-source` block via
`:target`. Leave no whitespace/newline between a door and the punctuation that follows it.

**Sibling links.** Above the footer: `{Topic} often travels with — A · B · C` (2–4 links).
Point them at the sibling slugs once those pages exist; until then point them at `/topics/` and
leave `<!-- TODO: resolve sibling links when pages ship: … -->`.

**CTA.** The handoff link's label is a single text node (`Continue in Sojourn`) so no markup can
swallow the space.

## Scripture database (WEB translation)

Bible text is served from a read-only SQLite file. **Never write, quote, or paraphrase
scripture from your own memory** — every verse shown to the user must be read verbatim
from this database. You may recall verse *references* from your own knowledge, but you
must resolve each one against the DB before displaying its text.

Download it into this skill's directory on first use, then reuse the cached copy:

```bash
DB="$(dirname "$0")/web-backend.sqlite"
[ -f "$DB" ] || curl -fSL -o "$DB" \
  https://storage.googleapis.com/sojourn-prod-public/data/bible_translations/web/web-backend.sqlite
```

### Finding relevant verses

1. From the conversation, name the references you think fit (you know scripture well).
2. Resolve each against the DB. If a reference returns no row, you misremembered it —
   drop it, don't invent text.
3. To surface less-obvious verses, keyword-search the text for terms you'd expect in
   matching verses.

### Schema
`verses(translation, book, chapter, verse, ref, text)` — `ref` is `BOOK.chapter.verse`
where `BOOK` is the USFM code (`GEN`, `PSA`, `JHN`, `1CO`, `REV`, …). Indexed on `ref`.
The file also holds a `verse_embeddings` table; ignore it, exact lookup is all you need.

### Resolve a reference (verbatim text)
```sql
SELECT text FROM verses WHERE ref = 'ROM.5.3';
```

### Keyword search for discovery
```sql
SELECT ref, text FROM verses WHERE text LIKE '%sluggard%';
```
