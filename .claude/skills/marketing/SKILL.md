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

### Refresh Reddit stats

Crawls every row where `Medium` is `Reddit`, fetches the post or comment via the
Reddit `.json` endpoint, and writes back **Upvotes** and **Comments**:

```
# Preview without writing
.venv/bin/python sheet.py refresh --dry-run

# Fetch and update the sheet
.venv/bin/python sheet.py refresh
```

- Random sleeps between requests (`--min-sleep` / `--max-sleep`, seconds) keep it
  gentle on Reddit. Backs off and retries on 403/429.
- Handles both post permalinks (`/comments/<id>/...`) and comment permalinks
  (`/comments/<id>/comment/<cid>/`). For a comment, Upvotes is the comment's score
  and Comments is its reply count.
- Chat share links (`/c/chat.../s/...`) and non-Reddit rows are skipped.

## Notes

- Dates are written as-is with `USER_ENTERED`, so Sheets parses `8/11/2026` as a date.
- `sheet.py list` prints raw CSV, handy for a quick scan or piping.
- **Views are never fetched.** Reddit only exposes `view_count` to a post's owner
  and returns `null` over the API, so `refresh` leaves the Views column alone.
  Fill it manually from Reddit's post insights if you want it.
