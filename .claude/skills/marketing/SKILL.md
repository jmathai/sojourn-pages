---
name: marketing
description: Read and update the "Sojourn Marketing" Google Sheet — the log of where Sojourn has been posted (Reddit, HackerNews, LinkedIn, ...) and how each post did. Use when adding a marketing entry, checking what's already been posted, or reviewing traction.
---

# Sojourn Marketing Sheet

Tracks every place Sojourn has been shared and how it performed. Backed by the
Google Sheet titled **Sojourn Marketing**
(`1VZPdG0y7YN0T2jB7BFQiXgGghtluIskCcrAvyAtUlCg`). One row per post:

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

## Setup (one time)

The skill authenticates with a Google service account so it can run without a
browser flow.

1. In Google Cloud, create a service account and enable the **Google Sheets API**
   and **Google Drive API** on its project.
2. Download the service account's JSON key and save it as
   `.service-account.json` in this skill folder. It is gitignored.
3. Open the Sheet and **Share** it with the service account's `client_email`
   (the `...@...iam.gserviceaccount.com` address), granting **Editor**.

The Python venv lives at `.venv/` in this folder (also gitignored) with `gspread`
installed. Recreate it if missing:

```
python3 -m venv .venv && .venv/bin/python -m pip install gspread google-auth
```

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

### Refresh stats

Crawls every `Reddit` and `HackerNews` row, fetches the post or comment, and writes
back **Upvotes** and **Comments**:

```
# Preview without writing
.venv/bin/python sheet.py refresh --dry-run

# Fetch and update the sheet
.venv/bin/python sheet.py refresh
```

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
- **Views are never fetched.** Neither Reddit nor HN exposes view counts over their
  APIs, so `refresh` leaves the Views column alone. Fill it manually from each site's
  post insights if you want it.
