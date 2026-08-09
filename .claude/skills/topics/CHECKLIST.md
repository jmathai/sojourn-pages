# Topic page verification checklist

Run this before shipping any `/topics/{slug}/`. Replace `{slug}` with the topic slug
(e.g. `envy`) and `{Topic}` with its title-cased name (e.g. `Envy`). **Everything through
section C runs against local files or `localhost` — production is never a verification
target except the two post-deploy items in E.**

Serve locally first:

```bash
python3 -m http.server 8931   # then browse http://localhost:8931/topics/{slug}/
```

---

## A. Local static checks — `topics/{slug}/index.html`

- [ ] `<title>` equals `What the Bible Says About {Topic} · Sojourn` and contains the word **Bible**.
- [ ] `<meta name="description">` is present and contains the word **Bible**.
- [ ] `og:image`, `og:image:width` (1200), `og:image:height` (630), `og:image:alt`, and
      `twitter:card` (`summary_large_image`) are all present.
- [ ] `og:image` is an **absolute** production URL (`https://trysojourn.app/topics/{slug}/og.png`)
      **and** the file exists locally at `topics/{slug}/og.png`, is a **1200×630 PNG with no alpha**.
- [ ] Both JSON-LD blocks (`Article`, `FAQPage`) are present and parse as valid JSON.
- [ ] Every `FAQPage` answer's text matches the rendered page's visible conversation answer
      (tags stripped, doors flattened to `"quote" (Reference)`). The two-turn exchange's
      follow-up is **not** its own FAQ entry.
- [ ] `Article.image` matches `og:image` exactly.
- [ ] All chapter text and conversation content is present in the raw HTML (no client fetching).
- [ ] `rel="canonical"` and `og:url` are `https://trysojourn.app/topics/{slug}/` and match.
- [ ] Sibling-links line present above the footer with **2–4** links.
- [ ] Heading hierarchy is `h1 → h2` with no skipped levels (`The study` / `The conversation`
      are real `<h2>`).
- [ ] No swallowed-space defects in anchor text (e.g. the CTA reads `Continue in Sojourn`).

Most of A can be checked mechanically; see `scripts/` and the one-off snippet the build uses.
The title/meta/tag/JSON-LD/heading/sibling assertions are pure string/DOM checks against the
local file.

## B. Local scripture verification — script, not manual

```bash
python3 .claude/skills/topics/verify-scripture.py topics/{slug}/index.html
```

- [ ] Exits `0`. Every quoted fragment — chapter-source verses, set-passage blockquotes,
      inline-door snippets, conversation quotes, and JSON-LD answer quotes — matches the local
      WEB source data. On any mismatch it fails loudly with the reference and a page-vs-WEB diff.
      This is the **"quote, never compose"** enforcement.

## C. Local interaction checks — serve locally, drive headless

Automate with the repo's Playwright (`.claude` plugin) where possible; otherwise perform manually
in a browser against `localhost`.

- [ ] Peek sheet opens from **every** inline door; **Dismiss** restores the exact scroll position.
- [ ] Reader opens scrolled to the highlighted verse; **Done** returns to the prior scroll position.
- [ ] Desktop (≥768px): the peek is width-constrained and horizontally centered (not a stretched,
      full-bleed mobile sheet).
- [ ] With JavaScript disabled, each door is an `<a href="#src-{chapter}">` whose target exists on
      the page and becomes visible via the `.chapter-source:target` rule — i.e. doors degrade to
      working in-page anchor links.

## D. Deploy.

## E. Post-deploy spot checks (the only checks that require production)

- [ ] The `og:image` absolute URL resolves on production (path mapping confirmed); sanity-check the
      share card in a scraper debugger (e.g. the Facebook Sharing Debugger or `curl -s` of the page,
      grepping `og:image`).
- [ ] On a real iOS device, the Universal Link / Smart App Banner behaves: `https://trysojourn.app/open?topic={slug}`
      opens the app into the topic study if topic handling exists; otherwise the App Store fallback
      works cleanly.
