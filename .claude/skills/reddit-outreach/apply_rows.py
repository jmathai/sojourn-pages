#!/usr/bin/env python3
"""Posts the replies you marked Apply in the "Reddit Posts" tab, then records the result.

Designed to be run unattended, which is exactly why it is cautious:

  - It only touches rows whose Status is exactly Apply, and it reads the Response
    straight from the sheet, so whatever you edited there is what gets posted.
  - Every row ends in a terminal state (Posted with the permalink, or Failed with the
    reason). Without that, a second unattended run would comment twice on one thread.
  - It paces itself like a person reading and replying, not like a script: minutes
    between comments, a cooldown per subreddit, and a hard cap per run.
  - It enforces the same 10% Sojourn-link budget as post_rows.py, because you can edit
    a link into a draft after it was written.

Usage (from this folder):
    ../marketing/.venv/bin/python apply_rows.py --dry-run
    ../marketing/.venv/bin/python apply_rows.py
    ../marketing/.venv/bin/python apply_rows.py --max 3 --min-gap 360 --max-gap 900
"""
import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import tab
from post_rows import LINK_BUDGET, has_link, post_id
from tab import APPLY, COL_RESPONSE, COL_RESULT, COL_STATUS, COL_URL, FAILED, POSTED

HERE = Path(__file__).resolve().parent
MARKETING = HERE.parent / "marketing"
COOKIE_PATH = MARKETING / ".reddit-cookie"
OAUTH_PATH = HERE / ".reddit-oauth.json"
UA = "sojourn-outreach/1.0 (by /u/jmathai)"

# Defaults chosen to look like a person working through their inbox, not a bot.
DEFAULT_MIN_GAP = 240      # 4 minutes
DEFAULT_MAX_GAP = 900      # 15 minutes
SUBREDDIT_COOLDOWN = 2700  # 45 minutes between comments in the same subreddit
DEFAULT_MAX_PER_RUN = 5


def fail(msg, code=2):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)


# --- authentication ---------------------------------------------------------------

def oauth_token():
    """Access token from a Reddit script app, if credentials are present.

    This is the sanctioned way to write to Reddit. Cookie posting works but looks like
    a browser being automated, which is the pattern that gets accounts actioned, so
    prefer this whenever it is configured.

    .reddit-oauth.json: {"client_id": "...", "client_secret": "...",
                         "username": "...", "password": "..."}
    """
    if not OAUTH_PATH.exists():
        return None
    creds = json.loads(OAUTH_PATH.read_text())
    data = urllib.parse.urlencode({
        "grant_type": "password",
        "username": creds["username"],
        "password": creds["password"],
    }).encode()
    import base64
    basic = base64.b64encode(
        f"{creds['client_id']}:{creds['client_secret']}".encode()).decode()
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token", data=data,
        headers={"Authorization": f"Basic {basic}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["access_token"]


def cookie_session():
    if not COOKIE_PATH.exists():
        fail(f"No Reddit credentials: expected {OAUTH_PATH} or {COOKIE_PATH}.")
    cookie = COOKIE_PATH.read_text().strip()
    req = urllib.request.Request(
        "https://www.reddit.com/api/me.json",
        headers={"User-Agent": UA, "Accept": "application/json", "Cookie": cookie})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read()).get("data", {})
    if not data.get("modhash"):
        fail("The reddit_session cookie is present but carries no write token; refresh it.")
    return cookie, data["modhash"], data.get("name")


# --- posting ----------------------------------------------------------------------

def thing_id(url):
    """Reddit's fullname for what we are replying to: t1_ for a comment, t3_ for a post."""
    m = re.search(r"/comment/([a-z0-9]+)", url)
    if m:
        return "t1_" + m.group(1)
    pid = post_id(url)
    return "t3_" + pid if pid else None


def subreddit_of(url):
    m = re.search(r"/r/([A-Za-z0-9_]+)", url)
    return m.group(1).lower() if m else ""


def submit(auth, parent, text):
    """Post one comment. Returns its permalink, or raises with Reddit's own message."""
    payload = {"api_type": "json", "thing_id": parent, "text": text}
    if auth["kind"] == "oauth":
        req = urllib.request.Request(
            "https://oauth.reddit.com/api/comment",
            data=urllib.parse.urlencode(payload).encode(),
            headers={"Authorization": f"Bearer {auth['token']}", "User-Agent": UA})
    else:
        payload["uh"] = auth["modhash"]
        req = urllib.request.Request(
            "https://www.reddit.com/api/comment",
            data=urllib.parse.urlencode(payload).encode(),
            headers={"User-Agent": UA, "Cookie": auth["cookie"],
                     "X-Modhash": auth["modhash"]})
    with urllib.request.urlopen(req, timeout=40) as r:
        body = json.loads(r.read())

    errors = body.get("json", {}).get("errors") or []
    if errors:
        raise RuntimeError("; ".join(" ".join(str(p) for p in e) for e in errors))
    things = body.get("json", {}).get("data", {}).get("things") or []
    if not things:
        raise RuntimeError(f"no comment returned by Reddit: {json.dumps(body)[:300]}")
    data = things[0].get("data", {})
    link = data.get("permalink")
    return ("https://www.reddit.com" + link) if link else f"posted (id {data.get('id')})"


# --- main -------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Post the replies marked Apply in the sheet.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be posted, touch nothing")
    ap.add_argument("--max", type=int, default=DEFAULT_MAX_PER_RUN,
                    help=f"Most comments to post this run (default {DEFAULT_MAX_PER_RUN})")
    ap.add_argument("--min-gap", type=int, default=DEFAULT_MIN_GAP,
                    help=f"Minimum seconds between comments (default {DEFAULT_MIN_GAP})")
    ap.add_argument("--max-gap", type=int, default=DEFAULT_MAX_GAP,
                    help=f"Maximum seconds between comments (default {DEFAULT_MAX_GAP})")
    ap.add_argument("--sub-cooldown", type=int, default=SUBREDDIT_COOLDOWN,
                    help=f"Seconds before reusing a subreddit (default {SUBREDDIT_COOLDOWN})")
    ap.add_argument("--over-budget", action="store_true",
                    help="Post linked replies even if they exceed the 10%% link budget")
    args = ap.parse_args()

    if args.min_gap > args.max_gap:
        fail("--min-gap cannot exceed --max-gap")

    ws = tab.ensure()
    rows = tab.read(ws)

    queued, total, linked = [], 0, 0
    for i, row in enumerate(rows[1:], start=2):  # sheet rows are 1-based, header is row 1
        if not any(c.strip() for c in row):
            continue
        status = row[COL_STATUS].strip()
        response = row[COL_RESPONSE].strip()
        if status in (POSTED,):
            total += 1
            if has_link(response):
                linked += 1
            continue
        if status != APPLY:
            continue
        url = tab.url_of(row[COL_URL])
        if not thing_id(url):
            queued.append((i, url, response, "unusable url"))
            continue
        if not response:
            queued.append((i, url, response, "empty response"))
            continue
        queued.append((i, url, response, None))

    if not queued:
        print("Nothing marked Apply. Set a row's Status to Apply and run again.")
        return

    # Budget check across everything already posted plus what this run would add.
    would_link = sum(1 for _, _, resp, err in queued if err is None and has_link(resp))
    proj_total = total + sum(1 for _, _, _, err in queued if err is None)
    proj_ratio = ((linked + would_link) / proj_total) if proj_total else 0.0
    print(f"link budget: {linked + would_link}/{proj_total} posted replies would carry a "
          f"Sojourn link ({proj_ratio:.0%}), cap {LINK_BUDGET:.0%}")
    block_links = proj_ratio > LINK_BUDGET and not args.over_budget
    if block_links:
        print("  over budget: linked replies will be left as Apply and skipped this run.")

    auth = None
    if not args.dry_run:
        token = oauth_token()
        if token:
            auth = {"kind": "oauth", "token": token}
            print("posting via the Reddit API (script app credentials)")
        else:
            cookie, modhash, name = cookie_session()
            auth = {"kind": "cookie", "cookie": cookie, "modhash": modhash}
            print(f"posting via the saved browser session as u/{name} "
                  "(no .reddit-oauth.json found)")

    last_by_sub, posted, failed, skipped = {}, 0, 0, 0
    for n, (rownum, url, response, err) in enumerate(queued):
        if posted >= args.max:
            print(f"reached --max {args.max}; leaving the rest marked {APPLY} for the next run")
            break

        label = f"row {rownum} {url}"
        if err:
            print(f"skip {label}: {err}")
            if not args.dry_run:
                ws.update(values=[[FAILED, err]], range_name=f"E{rownum}:F{rownum}",
                          value_input_option="USER_ENTERED")
            failed += 1
            continue
        if block_links and has_link(response):
            print(f"skip {label}: would exceed the link budget")
            skipped += 1
            continue

        sub = subreddit_of(url)
        since = time.time() - last_by_sub.get(sub, 0)
        if sub in last_by_sub and since < args.sub_cooldown:
            wait = int(args.sub_cooldown - since)
            print(f"holding {wait}s before commenting in r/{sub} again")
            if not args.dry_run:
                time.sleep(wait)

        if args.dry_run:
            print(f"would post to {label}\n    {response[:200]}")
            posted += 1
            last_by_sub[sub] = time.time()
            continue

        try:
            permalink = submit(auth, thing_id(url), response)
            ws.update(values=[[POSTED, permalink]], range_name=f"E{rownum}:F{rownum}",
                      value_input_option="USER_ENTERED")
            posted += 1
            last_by_sub[sub] = time.time()
            print(f"posted {label} -> {permalink}")
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, KeyError) as exc:
            reason = getattr(exc, "reason", None) or str(exc)
            if isinstance(exc, urllib.error.HTTPError):
                reason = f"HTTP {exc.code}: {exc.read()[:200].decode('utf-8', 'replace')}"
            ws.update(values=[[FAILED, str(reason)[:500]]], range_name=f"E{rownum}:F{rownum}",
                      value_input_option="USER_ENTERED")
            failed += 1
            print(f"FAILED {label}: {reason}")

        remaining = [q for q in queued[n + 1:] if q[3] is None]
        if remaining and posted < args.max:
            gap = random.randint(args.min_gap, args.max_gap)
            stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(f"[{stamp}Z] waiting {gap}s ({gap // 60}m) before the next comment")
            time.sleep(gap)

    verb = "would post" if args.dry_run else "posted"
    print(f"{verb} {posted}, failed {failed}, skipped {skipped}")


if __name__ == "__main__":
    main()
