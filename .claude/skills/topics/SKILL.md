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
- `FAQPage`: one entry for the opener, plus any **later turn whose question stands on its own** as a
  search query (e.g. "Is envy the same as jealousy?"). **Skip pure follow-ups** that only make sense
  as a reply (e.g. "But it comes right back the next morning"). Each entry's answer `text` is the
  visible answer with door markup flattened to `"quote" (Reference)`, matching the rendered page
  verbatim. Update the JSON whenever the conversation wording changes.

**Seeded conversation — one conversation, 2–3 turns.** A single `.exchange`, never more than one
(one connected thread, not several separate Q&As). A turn is one question and Sojourn's answer:
write an opener plus **one or two** follow-ups. The opener must **stand on its own** (assume it is
read cold, so state its context and don't lean on the study above); the follow-ups deepen that same
thread. Fold the topic's highest-volume tension or "X vs Y" angle in where it fits naturally. Every
quoted fragment is a live door, byte-verified against WEB.

**Doors are inline anchors.** Each inline door is `<a class="door" href="#src-{chapter}" …>`,
never a `<button>`: a true inline element (trailing punctuation must hug the reference), and
with JS off it degrades to an in-page anchor that reveals the hidden `.chapter-source` block via
`:target`. Leave no whitespace/newline between a door and the punctuation that follows it.

**Read alongside (sibling cross-links).** The footer's `.travels` block, labelled exactly
`Read alongside`, points to other **live** topics only (never coming-soon ones). Maintain it for
two goals at once: **relevance** (a reader who cares about this topic would plausibly want that one
next) and **distribution** (every topic stays reachable and inbound links aren't all piled on one
hub). Both *companions* (topics that travel together, e.g. Anger & Envy) and true *opposites*
(e.g. Envy & Generosity) count as related; unrelated pairs get no link.

Whenever you add, remove, or rename a topic, **re-derive every live topic's list, not just the new
page's** — a new topic changes the graph for everyone. Procedure:

1. List the live topics.
2. **Relevance.** For each topic, rank the others by how closely they relate, strongest first.
   Prefer reciprocity: if A lists B, B should list A unless B's slots are already filled by
   stronger matches.
3. **Draft** each list as its 1–3 most-related topics (most-related first).
4. **Distribution pass.** *No orphans:* every live topic must be linked from at least one other;
   if one isn't, add it to the list of its most-related topic. *No monopoly:* don't let one topic
   collect every inbound link while a related topic sits at zero — when choosing between
   comparably-relevant targets, pick the one with fewer inbound links. Never invent an irrelevant
   link just to even out counts; relevance wins when there's no relevant alternative.
5. Cap each list at **3** links (with only 2–3 live topics, 1–2 is normal), then regenerate the
   footer `.travels` block on every affected page.

**Inline cross-links (`.xref`).** Beyond the footer, whenever a page's *prose* names another
**live** topic as a genuine reference (a distinction it draws, an antidote it names, a sibling it
defines itself against), link that word's **first** mention to the topic:
`<a class="xref" href="/topics/{slug}/">word</a>`. `.xref` is cite-blue with a **solid** underline,
deliberately distinct from the **dotted** scripture `.door` (navigate vs. open-a-peek); never let the
two be confused. Rules:

- Link only genuine topic references. Never the page's own topic word, never words inside quoted
  scripture, and never an incidental use of a common emotion word (e.g. "the fear of losing" where
  the Fear study isn't the point). First mention only, not every occurrence.
- These are **bidirectional and prose-driven.** When you add a topic, also sweep every existing live
  page for prose mentions of the new topic and link them (backlinks), and link the new page's
  mentions of existing topics. A page whose prose names no sibling simply gets no inline xref — the
  footer `.travels` still backlinks it.
- The `.xref` style ships in `topic-template.html`; keep it when copying the template.

**CTA.** The handoff is an App Store download badge: `<a class="cta" href="{App Store URL}">` with
the Apple-logo SVG and a stacked two-line label — `Download on the` over `App Store`, each line its
own text node (`.cta-top` / `.cta-store`) so no markup can swallow a space. It links straight to the
App Store listing (`https://apps.apple.com/us/app/trysojourn/id6792011966`), not a topic deep link.
The `<h2>` above it still reads `Continue this conversation, in Sojourn.`

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
