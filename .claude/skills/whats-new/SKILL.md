---
name: whats-new
description: Build and maintain Sojourn's "What's new" in-app page at /whats-new/ — a pre-generated overview of what a user gains by updating, keyed by the build version they're on. Use when adding a new release, editing the update copy, or regenerating the per-version overviews.
---

# Sojourn What's New

This skill maintains `/whats-new/` — a page shown in an in-app web view (nearly full
screen) that tells a user on an older build what updating will get them.

The app opens the page with a hash naming the user's current build, e.g.
`#version_2`. The page looks that key up and shows a single, aggregated overview of
everything added since that build. It is **not** a range picker and **not** a raw
changelog list: each overview is written copy that reads like a person telling a
friend what's new. Every overview is pre-generated and baked into the page, so the
web view does no work at runtime beyond a lookup.

## Output layout

```
whats-new/
  releases.json    # source of truth — human-authored raw notes per release
  index.html       # the page; carries the pre-generated overviews in a data block
```

- `whats-new/releases.json` is authored by hand. It holds `latest` (the newest build's
  version key) and a `releases` array, newest first. Each release has a `version` (the
  key the app passes in the hash), a `date`, and `highlights` (raw notes, plainly
  written).
- `whats-new/index.html` is served at `/whats-new/`. Its chrome, CSS, and render JS are
  the single source of truth for how the page looks and behaves — never fork them. The
  only part this skill regenerates is the JSON data block between the
  `<!-- WHATS-NEW-DATA:START -->` and `<!-- WHATS-NEW-DATA:END -->` markers.
- `version` is treated as an opaque string key. It can be an integer build number
  (`"2"`) or a semver string (`"1.2.0"`); the page reads whatever follows `version_` in
  the hash and looks it up.

## Regenerating the overviews

Whenever `releases.json` changes (a release is added, or notes are edited), regenerate
the data block:

1. Read `whats-new/releases.json`.
2. For **every** release whose `version` is behind `latest` (i.e. every release except
   `latest` itself), write one overview covering all releases newer than it, up to and
   including `latest`. A user on that build sees exactly this when the app passes their
   version.
3. Each overview is an object under `updates[<version>]` with:
   - `since` — a short human label for the build they're on (e.g. `"version 2"`).
   - `intro` — one or two warm sentences framing what they've been missing. Scale the
     tone to the gap: a single build behind is "a small update, but a welcome one"; many
     builds behind is "quite a bit has landed."
   - `items` — the highlights, aggregated across all the newer releases and rewritten as
     `{ "title", "text" }` pairs. Merge duplicates and order newest-feeling first. Don't
     just concatenate the raw `highlights`; turn them into copy.
4. Set the data block's top-level `latest` to match `releases.json`.
5. There is **no** entry for `latest` itself. When the app passes the latest version (or
   an unknown key), the page shows its built-in "you're all caught up" state.
6. Replace only the JSON between the two markers in `index.html`. Leave everything else
   untouched. After writing, confirm the block is valid JSON.

## Voice

Follow Sojourn's voice (see the root `CLAUDE.md`). Warm, plain, and human; it must not
read as AI-drafted. **No em dashes anywhere**, including titles and copy: use a comma, a
period, a colon, parentheses, or reword. This page quotes no scripture, so the
quote-never-compose rule does not apply here; if that ever changes, verify every verse
against the WEB source before shipping it.
