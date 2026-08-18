---
name: marketing
description: Read and update the "Sojourn Marketing" Google Sheet — the log of where Sojourn has been posted (Reddit, HackerNews, LinkedIn, ...) and how each post did. Use when adding a marketing entry, checking what's already been posted, or reviewing traction.
---

# Sojourn Marketing Sheet

Tracks Sojourn's marketing in one Google Sheet
(`1VZPdG0y7YN0T2jB7BFQiXgGghtluIskCcrAvyAtUlCg`) with three tabs:

- **Marketing** — one row per post/comment on a channel (the source of promotion).
- **App Store Connect** — one row per day of App Store analytics (the result).
- **Website** — one row per day of trysojourn.app analytics from PostHog.

## Marketing tab

One row per post:

| Column | Meaning |
| --- | --- |
| `Date` | `M/D/YYYY` when it was posted |
| `Medium` | Reddit, HackerNews, LinkedIn, ... |
| `Upvotes` | Upvote / like count |
| `Comments` | Comment count |
| `Views` | View count |
| `Clicks` | Referral clicks to the site |
| `Link` | URL to the post |
| `Notes` | Free text, e.g. `moderated` |

## App Store Connect tab

One row per day, newest at the top. Left columns are the daily totals from the
Acquisition dashboard; the right columns break **First-Time Downloads** down by
Apple's `Source Type`, so they always sum to First-Time Downloads.

| Column | Meaning |
| --- | --- |
| `Date` | `M/D/YYYY` |
| `Impressions` | App Store impressions |
| `Page Views` | Product page views |
| `First-Time Downloads` | New downloads |
| `Redownloads` | Redownloads |
| `Page View Conversion` | Downloads &divide; page views |
| `Impression Conversion` | Downloads &divide; impressions |
| `App Store Search`, `App Store Browse`, `Web Referrer`, `App Referrer`, `Other` | First-time downloads by Apple `Source Type` (`Web Referrer` is the collective social/links bucket) |

## Website tab

One row per day of `trysojourn.app` analytics from PostHog, newest at the top. Each
event column is a daily count of that PostHog event on the `trysojourn.app` host
(`properties.$host`). The header-to-event mapping lives in `posthog.EVENTS`.

| Column | PostHog event |
| --- | --- |
| `Date` | `M/D/YYYY` |
| `Page Views` | `$pageview` |
| `app_store_click` | `app_store_click` |
| `topic_reader_open` | `topic_reader_open` |
| `topic_peak_open` | `topic_peek_open` (the header reads "peak"; the event is "peek") |
| `topic_handoff` | `topic_handoff` |
| `rageclick` | `$rageclick` |

## Setup (one time)

The skill authenticates with a Google service account so it can run without a
browser flow.

1. In Google Cloud, create a service account and enable the **Google Sheets API**
   and **Google Drive API** on its project.
2. Download the service account's JSON key and save it as
   `.service-account.json` in this skill folder. It is gitignored.
3. Open the Sheet and **Share** it with the service account's `client_email`
   (the `...@...iam.gserviceaccount.com` address), granting **Editor**.

The Python venv lives at `.venv/` in this folder (also gitignored). Recreate it
if missing:

```
python3 -m venv .venv && .venv/bin/python -m pip install gspread google-auth pyjwt cryptography
```

### App Store Connect key (for the App Store Connect tab)

The App Store analytics come from the App Store Connect API, authenticated with an
**individual** API key (Users and Access → Integrations → App Store Connect API →
Individual Keys). An individual key inherits your account's access, so it can read
analytics; a team key with only App Manager access cannot.

Key material lives in the repo-root `.appstoreconnect/` folder (the whole folder is
gitignored):

```
.appstoreconnect/
  private_keys/ApiKey_<KEY_ID>.p8   # the downloaded key
  key.json                          # {"key_id": "...", "app_id": "..."}
  state.json                        # analytics report request ids (created by the skill)
```

Individual keys sign the JWT with `sub: "user"` and no issuer id. The Analytics
Reports API is asynchronous: the skill requests a report once, and Apple takes hours
(up to a day) to provision the data before any rows are available.

### PostHog key (for the Website tab)

The Website analytics come from PostHog (US cloud, `us.posthog.com`), queried with a
**personal** API key (Settings → Personal API keys). Save it in the **repo-root
`.env`** as `POSTHOG_API_KEY=...` (gitignored). The skill discovers the project id from
`/api/users/@me/` and pulls daily event counts with a HogQL query, so no project id
needs to be configured.

### Reddit session (for `refresh`)

`refresh` reads Reddit stats from the public `.json` endpoint. Reddit blocks
unauthenticated/datacenter requests (403/429), so the request is sent as a
logged-in user via a saved cookie:

1. In a browser logged into Reddit, open DevTools → **Storage** → **Cookies** →
   `https://www.reddit.com`.
2. Copy the **`reddit_session`** cookie value (it's HttpOnly, so `document.cookie`
   in the console will not show it, use the Storage panel).
3. Save it to `.reddit-cookie` in this folder as `reddit_session=<value>`. It is
   gitignored.

`reddit_session` is long-lived (months). When `refresh` starts returning 403/429,
the cookie has expired, repeat the steps above.

### Hacker News session (for `refresh`)

Story scores come from the public API, but HN shows a **comment's** score only to
its author, so `refresh` scrapes it from the logged-in HTML. This needs your HN
login cookie:

1. In a browser logged into `news.ycombinator.com`, open DevTools → **Storage** →
   **Cookies** → `https://news.ycombinator.com`.
2. Copy the **`user`** cookie value (looks like `username&<hash>`).
3. Save it to `.hn-cookie` in this folder as `user=<value>`. It is gitignored.

Without it, HN story stats still work; only comment upvotes are skipped. Comment
scores are visible for **your own** comments only, HN never exposes anyone else's.

## Usage

Run from this skill folder using its venv:

```
# List every row
.venv/bin/python sheet.py list

# Append a marketing entry
.venv/bin/python sheet.py add \
  --date 8/11/2026 \
  --medium Reddit \
  --views 352 --comments 0 \
  --link https://www.reddit.com/r/Christianity/comments/... \
  --notes moderated
```

`--date`, `--medium`, and `--link` are required; `--upvotes`, `--comments`,
`--views`, `--clicks`, and `--notes` are optional.

### Refresh stats ("update marketing" updates ALL tabs)

`refresh` updates the whole spreadsheet, not just one tab. **"Update marketing"
means update the Marketing, App Store Connect, and Website tabs.**

```
# Preview without writing
.venv/bin/python sheet.py refresh --dry-run

# Fetch and update all tabs
.venv/bin/python sheet.py refresh
```

It runs three steps:

1. **Marketing tab** — crawls every `Reddit` and `HackerNews` row, fetches the post
   or comment, and writes back **Upvotes** and **Comments**.
2. **App Store Connect tab** — reads the analytics reports, aggregates them into one
   row per calendar date, and **upserts**, **most recent day on top** (row 1 is the
   header, row 2 is a totals row, so new days go in at row 3, pushing older days down;
   the totals-row formulas are re-pinned to start at row 3 after each insert, since
   Sheets would otherwise bump the range past the new day). A date already in the sheet
   is **rewritten in place** when its numbers change, because Apple revises the most
   recent days for a day or two after they first appear (so a midday run sees partial
   numbers that later fill in). New days are inserted; older days that have aged out of
   Apple's reporting window are left untouched. Impressions, page views, downloads, and
   redownloads come from the **Standard** reports, which carry the complete daily totals
   and stay a step ahead of the Detailed reports. Skips gracefully with a message while
   Apple is still provisioning the reports.

   **Source attribution.** First-time downloads are split by Apple's `Source Type`
   (`App Store Search`, `App Store Browse`, `Web Referrer`, `App Referrer`, `Other`) from
   the same **Standard** report, mapped via `appstore.SOURCE_TYPES`. This is complete and
   not thresholded, so the columns always sum to First-Time Downloads. The site-level
   referrer domain (Reddit vs LinkedIn vs HackerNews) lives only in the `Source Info`
   field of the volume-gated **Detailed** report, which Apple withholds at low volume, so
   link-driven installs are reported collectively as **`Web Referrer`** rather than per
   site. If Apple starts emitting domains at higher volume, `Web Referrer` can be split
   back out from `Source Info`.
3. **Website tab** — queries PostHog (HogQL) for daily counts of each mapped event on
   the `trysojourn.app` host and **upserts**, **most recent day on top** (no totals
   row; new days insert at row 2). The current day is still accumulating, so a date
   already in the sheet is rewritten in place when its counts change. Skips gracefully
   with a message when `POSTHOG_API_KEY` is missing or the query fails.

- Random sleeps between requests (`--min-sleep` / `--max-sleep`, seconds) keep it
  gentle on the sites. Reddit backs off and retries on 403/429.
- **Reddit**: handles post permalinks (`/comments/<id>/...`) and comment permalinks
  (`/comments/<id>/comment/<cid>/`). For a comment, Upvotes is the comment's score
  and Comments is its reply count. Chat share links (`/c/chat.../s/...`) are skipped.
- **Hacker News**: stories use the JSON API (`score`, `descendants`); comments use
  the JSON API for reply count and the logged-in HTML scrape for the score.
- A value is only written when it's available, so cells like a manual view count or
  an unavailable score are never clobbered.

## Notes

- Dates are written as-is with `USER_ENTERED`, so Sheets parses `8/11/2026` as a date.
- `sheet.py list` prints raw CSV, handy for a quick scan or piping.
- **Views** are fetched for Reddit **posts and comments** you authored. Reddit shows a
  view count only to the author, in the logged-in web page (never the JSON API), so
  `refresh` scrapes it via the `.reddit-cookie` session and writes column E:
  - **Comments** — from the dedicated insight page `reddit.com/commentstats/t1_<id>`,
    which server-renders `aria-label="N views"`.
  - **Posts** — `N views` beside the eye icon on the post page, just before its
    `/poststats/<id>` link.
  - **Removed/moderated posts** and content you don't own render no insight, so they're
    left blank. **Hacker News** exposes no views at all. Fill any remaining Views (e.g.
    LinkedIn) manually.
