# Sojourn Topic Pages — Design Handoff

## What we're building

A static web page template for `trysojourn.app/topics/{topic}` that lets a visitor **experience** Sojourn's core interaction — scripture citations as doors into the text — before installing the app. The prototype topic is **Envy** (`/topics/envy`). The template must be built so a static site generator can later render any topic from a data file (see "Systematization contract" at the end).

This is not a marketing page. It is a miniature of the app: a written topical study, set in the app's own visual language, where every scripture reference behaves the way it does in the app. The page should feel like the reading experience it is selling.

**Design principle carried over from the app:** the page never generates or paraphrases scripture. It quotes the World English Bible (WEB) exactly, from data. Prose is the hallway; scripture is the rooms.

---

## Reuse of the app's UX

You already know Sojourn's interaction model. This page reuses it directly, with static-appropriate reductions.

### Kept — must match the app's behavior and visual language

1. **Inline verse citations ("doors")**
   - Rendered exactly like the app: quoted snippet + reference, blue text, dotted underline. Example: `"envy rots the bones" (Proverbs 14:30)`.
   - Tap/click → peek sheet rises.

2. **Peek sheet**
   - Bottom sheet on mobile (grabber handle, warm paper background, reference as header in the app's sans-style header treatment, verse text in the serif).
   - Shows the cited verse (or verse range) with a sentence or two of surrounding context where the range is short.
   - Two actions, exactly as in the app: **Keep reading** (primary, soft blue pill) and **Dismiss** (secondary, outlined).
   - On desktop (≥ 768px): the same sheet presented as a centered modal or anchored popover — same content, same actions, same paper.

3. **Chapter reader**
   - Full-screen (mobile) / large modal (desktop) reader showing the entire chapter containing the citation.
   - The cited verse(s) highlighted in the app's warm yellow highlight.
   - Superscript verse numbers, WEB text, identical typography to the app's reader.
   - Header: chapter title centered (e.g., **Proverbs 14**), **Done** action right-aligned.
   - Scroll position opens at the highlighted verse.
   - Dismissing returns the visitor to their exact scroll position on the page.

### Cut — deliberately absent in the static version

- **No chapter paging** (no ‹ 13 / 15 › navigation). The reader header shows only the current chapter and Done.
- **No Insights, no "Put it in action," no branch chips.**
- **No live conversation input.** The one input-shaped element on the page is a handoff affordance (see Section 4 below), not a working composer.
- **No accounts, no trail persistence, no notifications** — nothing that implies state.

These cuts should read as calm simplicity, not missing features. The UX principles (doors, peek, context, return-to-place) remain fully intact.

---

## Page anatomy (top to bottom)

### 0. Header
Minimal. Sojourn wordmark (serif, ink) left; a single quiet link to the app ("Get the app" or the App Store badge) right. No nav bar beyond this. Apple Smart App Banner meta tag present for iOS Safari.

### 1. Opening reflection
- H1: the topic name, large serif (e.g., **Envy**), with a one-line subhead in the muted ink color.
- 150–250 words of handmade reflection. No scripture yet. Tone: the app's — plain, unhurried, pastoral without being preachy.
- Content comes from the topic data file (`reflection`). For the prototype, use the draft in the Envy content pack below (marked for the author's rewrite).

### 2. The study arc
The heart of the page. An ordered sequence of **beats**. Each beat is:
- A short transition in editorial voice (1–3 sentences, serif, ink), containing zero or more inline verse doors.
- A **set passage**: several verses quoted in full, visually distinguished — indented block on the paper background, slightly larger leading, reference below-right in muted ink. The set passage is itself a door: tapping it (or a quiet "Read the whole chapter" affordance beneath it) opens the chapter reader directly, skipping the peek.

Scripture must visually dominate this section. If a beat's transition is longer than its passage, the balance is wrong.

Envy's arc (references and order in the content pack): Genesis 4 → 1 Samuel 18 → Proverbs 14:30 → Psalm 73 → James 3 → Philippians 4 / 1 Corinthians 13.

### 3. Seeded conversation
Four **independent** exchanges presented in the app's chat visual language: user bubble (right-aligned, warm gray pill) and Sojourn's answer as open text on the paper, citations as live doors — exactly like the app's conversation screen.

- Exchange order: disarming → two-turn → distinction → hope-shaped close.
- Exactly one exchange (the second) contains a follow-up turn, demonstrating that the app listens. All others are single-turn.
- A short section intro line above them, e.g. "Questions people bring to this topic in Sojourn." Honest framing: curated, not simulated.
- Below the exchanges: one input-shaped element, visually matching the app's composer (rounded field, muted placeholder "Ask your own…", red send affordance). Tapping anywhere on it triggers the handoff (Section 4). It never accepts text.
- Full copy for all four exchanges is in the Envy content pack.

### 4. Handoff
- Primary CTA after the seeded conversation and repeated at page end: **Continue in Sojourn** — deep link (Universal Link) carrying the topic, e.g. `https://trysojourn.app/open?topic=envy`, falling back to the App Store product page.
- The link's promise: the visitor lands *inside* an envy study in the app, not on a blank home screen.
- One quiet line beneath, and only for non-iOS visitors if platform detection is available: "Sojourn is on iPhone today — leave an email and we'll tell you when that changes." Single email field, nothing else.
- Supporting line near the CTA (small, muted): "In Sojourn, these become one conversation — yours."

### 5. Footer
Nearly silent. Links: Topics index (`/topics`), 3–4 related topics ("Envy often travels with — Anger · Contentment · Comparison"), privacy, and the wordmark. Related-topic links are data-driven (`relatedTopics` in the data file).

---

## Design language

- **Background:** the app's warm paper (#F5F1E8 family). No white cards, no shadows heavier than the peek sheet's.
- **Type:** the app's serif for all reading content (headings, prose, scripture). The app's UI sans only where the app uses it (sheet headers, buttons, chat bubbles' user text).
- **Accent:** Sojourn red (#A32E22) used sparingly — one accent word in the H1 subhead at most, the composer send affordance, nothing else.
- **Links/doors:** the app's blue with dotted underline. This is the only blue on the page.
- **Highlight:** the app's warm yellow for cited verses in the reader.
- **Density:** generous line-height, wide margins, one column, max measure ~68ch. The page should scroll long and feel calm.
- **Nothing marketing-shaped:** no feature grids, no testimonials, no screenshots of the app (the page *is* the app), no badges except the single App Store badge in header/handoff.

---

## Technical requirements

- **Static-first:** all prose, all set passages, all seeded exchanges, and the full text of every referenced chapter present in the generated HTML (chapters may live in inline JSON or hidden markup hydrated by the reader). No client-side fetching of scripture. No external APIs.
- **Interactivity:** vanilla JS or a minimal framework — peek sheet, chapter reader, scroll restoration. Everything degrades: with JS off, doors fall back to anchor links targeting the chapter text rendered at page bottom (visually hidden until targeted) or to `/read/{book}/{chapter}` if that route exists later.
- **Weight:** target < 100KB HTML+CSS+JS before chapter data; chapter data lazy-hydrated but included in the document.
- **Schema.org:** `Article` for the page; `FAQPage` for the seeded exchanges (question + first answer paragraph, plain text only).
- **Meta:** canonical URL, per-topic OG image (paper background, topic word in serif with red accent — same aesthetic as the App Store screenshot set), Apple Smart App Banner meta tag.
- **Scripture source:** WEB translation only, rendered verbatim from data. The design must include no affordance for editing, paraphrasing, or generating scripture text.

---

## Systematization contract (for the Claude Code phase)

Build the prototype so the following separation already exists, even if hand-wired:

**1. Topic data file** (`topics/envy.json` — one per topic):
```json
{
  "slug": "envy",
  "title": "Envy",
  "subhead": "…",
  "reflection": "…",
  "arc": [
    { "transition": "… with inline door syntax …",
      "passage": { "book": "Genesis", "chapter": 4, "verses": "1-8" } }
  ],
  "seededConversation": [
    { "turns": [ { "q": "…", "a": "… with inline door syntax …" } ] }
  ],
  "relatedTopics": ["anger", "contentment", "comparison"],
  "ogAccentWord": "Envy"
}
```
- Inline door syntax in prose fields: `[[“quoted snippet” (Book C:V)]]` — the generator resolves the reference against the WEB dataset, verifies the quoted snippet matches the source text exactly (build fails on mismatch), and renders the door.

**2. WEB dataset:** local, keyed by book/chapter/verse. The template's peek and reader consume only this. This is the enforcement point for "quote, never compose."

**3. Template:** renders any valid topic file. Page 16 should cost only writing — reflection, arc curation, Q&A — never design or engineering.

---

## Envy content pack (prototype content)

- **Subhead (draft):** "What scripture knows about wanting what isn't yours."
- **Reflection:** DRAFT-BY-AUTHOR — placeholder paragraph acceptable in prototype; do not polish AI-drafted copy here.
- **Arc beats:** Genesis 4:1–8 (envy's first appearance and its trajectory) → 1 Samuel 18:6–9 (Saul watching David) → Proverbs 14:30 (set as a single-verse beat) → Psalm 73:1–5, 16–17, 25–28 (the honest prayer of the envious) → James 3:13–18 (envy in community) → Philippians 4:10–13 + 1 Corinthians 13:4 (the contentment turn).
- **Seeded conversation:** the four exchanges as drafted in the working session of 2026-08-07 ("What if I envy something good…", "How do I pray when I can't stop comparing…" [two-turn], "Is admiration different from envy…", "Can envy actually be healed…"). All quoted scripture fragments in these exchanges must be verified against the WEB dataset before ship; treat current drafts as copy pending verification.
- **Related topics:** anger, contentment, comparison (comparison may redirect to envy until it exists).

---

## Acceptance criteria

1. A visitor with no context can read the full envy study, open at least one peek sheet, read one full chapter, return to their place, and reach the App Store — without confusion and without anything on the page implying features that aren't there.
2. Every scripture reference on the page is tappable and resolves correctly.
3. The page is visually indistinguishable in spirit from the app: someone who later installs Sojourn should feel recognition, not novelty.
4. View-source shows all study prose, passages, and Q&A in the HTML.
5. The design contains nothing that would embarrass the "AI points to scripture, never writes it" position under skeptical scrutiny.

---

## Implementation status & Claude Code instructions

Two working reference templates now exist in the project root. They are the visual + interaction source of truth. Your job is to turn them into the data-driven, WEB-verified system described in the "Systematization contract" above — **without changing their look or behavior.**

### Files
- **`topic-template.html`** — a single, fully working topic page, hand-wired with the **Envy** content. Everything renders statically and all interactions work with vanilla JS (no build step, no dependencies).
- **`topic-list-template.html`** — the `/topics` index: a responsive card grid of topics.

### What `topic-template.html` already implements (keep intact)
- **Header / footer** matching the app + site (`Sojourn · Topics · Writings`; App Store link).
- **Opening reflection** — `.opening` section: kicker, `h1.topic`, italic `.subhead` (one red accent word), `.reflection` prose. Reflection copy is DRAFT — pending author rewrite.
- **The study** — `.arc` section, `.arc-label` "The study", one `.beat` per arc step. Each beat = `.transition` prose (with inline `.door` buttons) + a `figure.setpass` (verses in full, `figcaption` with reference + "Read the whole chapter"). `.setpass.single` is the single-verse treatment (Proverbs 14:30). Current arc order: Genesis 4 → 1 Samuel 18 → Proverbs 14:30 → Psalm 73 → James 3 → Philippians 4 / 1 Cor 13.
- **The conversation** — `.convo` section, `.arc-label` "The conversation" (styled to match "The study"). **One** seeded, multi-turn conversation (not four independent exchanges — this changed from the original spec) in `.exchange` (user `.q` bubbles, Sojourn `.a` prose, inline `.door`s). It is written to read as continuable in the app. There is **no** fake composer (removed).
- **Handoff** — `.handoff` section: `h2` "Continue this conversation, in Sojourn." + App Store-style `.cta` deep link (`/open?topic=envy`). No support paragraph, no non-iOS email line (both removed).
- **Interactions (vanilla JS at bottom of file):**
  - `.door` click → **peek sheet** (`#peek`): cited verse(s) in full plus one muted context verse before/after when the range is short; **Keep reading** / **Dismiss**.
  - `figure.setpass` click, or peek's Keep reading → **chapter reader** (`#reader`): full chapter, cited verses highlighted in warm yellow, scrolled to the first highlight.
  - Body scroll locked while open; **scroll position is restored exactly** on close (restoration forces `scroll-behavior:auto` to avoid a smooth up-then-down jump — do not regress this).
  - Esc / scrim / Done close. PostHog events: `topic_peek_open`, `topic_reader_open`, `topic_handoff`.
- **Chapter data** — the seven referenced chapters (Genesis 4, 1 Samuel 18, Proverbs 14, Psalm 73, James 3, Philippians 4, 1 Corinthians 13) are embedded verbatim as hidden `<section class="chapter-source" id="src-{slug}" data-book data-chapter data-title>` blocks holding `<span class="cv" data-n="N">`. These are **both** the JS data source **and** the no-JS fallback (each becomes visible via `:target` when its `#src-…` anchor is hit). **This embedded text is prototype-grade and must be verified verbatim against the real WEB dataset before ship.**

### What `topic-list-template.html` already implements
- `.topic-grid` of cards. **Envy** is the only live card (`<a class="topic" href="/topics/envy/">` with a `.verse` reference). All other topics (**Anger, Contentment, Fear, Anxiety, Grief**) are non-linked `<span class="topic soon">` cards showing a muted "Coming soon…" tag instead of a verse. (Note: "Comparison" was replaced by "Fear" and the coming-soon treatment replaces per-topic links — reflect this in the topics manifest.)

### Deltas from the original spec (above) — the templates win where they conflict
1. Seeded conversation is **one continuable multi-turn thread**, not four independent exchanges.
2. **No fake composer** element.
3. Handoff has **no** non-iOS email capture and **no** "In Sojourn, these become one conversation" support line.
4. Topics index links **only Envy**; others are "Coming soon…". Topic set is Envy, Anger, Contentment, Fear, Anxiety, Grief.
5. Em-dashes have been removed from all site copy per house style — do not reintroduce them in generated prose (scripture text keeps its original WEB punctuation).

### Your task (systematization)
1. **Extract** the Envy page's content into `topics/envy.json` per the Systematization contract schema, extended for: single multi-turn `seededConversation`, `setpass` beats with `single` flag, and `relatedTopics` (the footer "travels with" list). Keep inline door syntax `[[“snippet” (Book C:V)]]`.
2. **Stand up the WEB dataset** (local, keyed by book/chapter/verse) and make the peek/reader/chapter-source render from it. Replace the hand-embedded chapter blocks with generated ones. The snippet-match build check is the enforcement point for "quote, never compose" — build must fail on any mismatch.
3. **Turn both HTML files into templates** that render any valid topic file and a topics manifest (the manifest drives the index cards, including live-vs-"coming soon" state). Adding a topic must cost only writing (reflection, arc curation, conversation) — never design or engineering.
4. Preserve all interaction behavior, the no-JS `:target` fallback, PostHog events, accessibility (dialog roles, Esc), and the scroll-restoration fix.
5. Keep OG/meta, canonical, and Apple Smart App Banner tags per-topic.
