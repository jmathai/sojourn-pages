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

Install any Python dependencies the build needs into this venv only.

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
