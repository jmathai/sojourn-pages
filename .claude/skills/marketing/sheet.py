# Reads, appends, and refreshes rows in the "Sojourn Marketing" Google Sheet.
# Writes via a service-account key; refresh pulls Reddit (cookie) and Hacker News stats.
import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import gspread

sys.path.insert(0, str(Path(__file__).resolve().parent))
import appstore

SHEET_ID = "1VZPdG0y7YN0T2jB7BFQiXgGghtluIskCcrAvyAtUlCg"
KEY_PATH = Path(__file__).parent / ".service-account.json"
REDDIT_COOKIE_PATH = Path(__file__).parent / ".reddit-cookie"
HN_COOKIE_PATH = Path(__file__).parent / ".hn-cookie"
MARKETING_SHEET = "Marketing"
APPSTORE_SHEET = "App Store Connect"
COLUMNS = ["Date", "Medium", "Upvotes", "Comments", "Views", "Clicks", "Link", "Notes"]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0"


def worksheet(title=MARKETING_SHEET):
    if not KEY_PATH.exists():
        sys.exit(
            f"No service-account key at {KEY_PATH}.\n"
            "Create one in Google Cloud, share the sheet with its client_email, "
            "and save the JSON there."
        )
    client = gspread.service_account(filename=str(KEY_PATH))
    return client.open_by_key(SHEET_ID).worksheet(title)


def cmd_list(args):
    for row in worksheet().get_all_values():
        print(",".join(row))


def cmd_add(args):
    ws = worksheet()
    row = [
        args.date, args.medium, args.upvotes, args.comments,
        args.views, args.clicks, args.link, args.notes,
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    print("Added: " + ",".join(row))


def reddit_json(path, tries=4):
    if not REDDIT_COOKIE_PATH.exists():
        sys.exit(
            f"No Reddit session cookie at {REDDIT_COOKIE_PATH}.\n"
            "Copy the reddit_session cookie from a logged-in browser and save it there."
        )
    cookie = REDDIT_COOKIE_PATH.read_text().strip()
    url = "https://www.reddit.com" + path.rstrip("/") + ".json?raw_json=1"
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json", "Cookie": cookie}
    )
    delay = 10
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 500, 502, 503) and attempt < tries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def count_replies(comment):
    replies = comment.get("replies")
    if not replies:
        return 0
    total = 0
    for child in replies["data"]["children"]:
        if child.get("kind") == "t1":
            total += 1 + count_replies(child["data"])
    return total


def reddit_stats(url):
    """Return {upvotes, comments} for a Reddit post or comment URL, or None if neither."""
    path = urllib.parse.urlsplit(url).path
    if "/comments/" not in path:
        return None
    data = reddit_json(path)
    if "/comment/" in path:
        comment = data[1]["data"]["children"][0]["data"]
        return {"upvotes": comment.get("ups"), "comments": count_replies(comment)}
    post = data[0]["data"]["children"][0]["data"]
    return {"upvotes": post.get("ups"), "comments": post.get("num_comments")}


def _parse_count(s):
    """'352' / '1,234' / '12.3K' / '1.1M' -> int."""
    s = s.replace(",", "").strip().rstrip(".")
    mult = 1
    if s and s[-1] in "Kk":
        mult, s = 1000, s[:-1]
    elif s and s[-1] in "Mm":
        mult, s = 1_000_000, s[:-1]
    return int(float(s) * mult)


def _reddit_html(url, tries=3):
    """Fetch a Reddit web page as the logged-in user, or None. Backs off on 5xx/403/429."""
    cookie = REDDIT_COOKIE_PATH.read_text().strip()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cookie": cookie})
    delay = 8
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 500, 502, 503) and attempt < tries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return None


def reddit_views(url):
    """Return a Reddit post's or comment's view count, or None.

    View counts are shown only to the author, in the logged-in web page (never the
    JSON API). Comments carry theirs on a dedicated insight page as
    aria-label="N views"; posts render 'N views' beside the eye icon, just before the
    post's /poststats/ link. Returns None for removed content or content the session
    doesn't own (no insight rendered).
    """
    path = urllib.parse.urlsplit(url).path
    comment = re.search(r"/comment/([a-z0-9]+)", path)
    if comment:
        html = _reddit_html(f"https://www.reddit.com/commentstats/t1_{comment.group(1)}")
        if html is None:
            return None
        m = re.search(r'aria-label="([\d][\d,.]*\s*[KMkm]?)\s*views?"', html)
        return _parse_count(m.group(1)) if m else None

    post = re.search(r"/comments/([a-z0-9]+)", path)
    if not post:
        return None
    html = _reddit_html(url)
    if html is None:
        return None
    anchor = html.find(f"/poststats/{post.group(1)}")
    if anchor < 0:
        return None  # no stats bar (removed post, or not the author)
    m = re.search(r"([\d][\d,.]*\s*[KMkm]?)\s*views?\b", html[max(0, anchor - 300):anchor])
    return _parse_count(m.group(1)) if m else None


def hn_item(item_id):
    url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def hn_count_replies(item):
    total = 0
    for kid_id in item.get("kids", []):
        kid = hn_item(kid_id)
        if kid and not kid.get("deleted") and not kid.get("dead"):
            total += 1 + hn_count_replies(kid)
    return total


def hn_comment_score(item_id):
    """Scrape a comment's score, which HN renders only to its author, via the saved cookie."""
    if not HN_COOKIE_PATH.exists():
        return None
    cookie = HN_COOKIE_PATH.read_text().strip()
    url = f"https://news.ycombinator.com/item?id={item_id}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cookie": cookie})
    with urllib.request.urlopen(req, timeout=25) as r:
        html = r.read().decode("utf-8", "replace")
    match = re.search(rf'id="score_{item_id}">(\d+)\s+point', html)
    return int(match.group(1)) if match else None


def hn_stats(url):
    """Return {upvotes, comments} for a Hacker News story or comment URL, or None.

    Stories expose their score over the JSON API. Comment scores are author-only, so
    they are scraped from the logged-in HTML; upvotes is None if unavailable. For a
    comment, comments is the recursive reply count.
    """
    ids = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("id")
    if not ids:
        return None
    item = hn_item(ids[0])
    if item is None:
        return None
    if item.get("type") == "comment":
        return {"upvotes": hn_comment_score(ids[0]), "comments": hn_count_replies(item)}
    return {"upvotes": item.get("score"), "comments": item.get("descendants")}


APPSTORE_COLUMNS = [
    "Date", "Impressions", "Page Views", "First-Time Downloads", "Redownloads",
    "Page View Conversion", "Impression Conversion", *appstore.SOURCE_COLUMNS,
]


def mdy(iso_date):
    """'2026-08-12' -> '8/12/2026' to match the sheet's date style."""
    y, m, d = iso_date.split("-")
    return f"{int(m)}/{int(d)}/{int(y)}"


def appstore_row(metrics):
    """Build a sheet row (APPSTORE_COLUMNS order) from an appstore.daily_rows() entry."""
    imp = metrics["impressions"]
    pv = metrics["page_views"]
    total = metrics["first_time_downloads"] + metrics["redownloads"]
    pv_conversion = f"{round(100 * total / pv, 1)}%" if pv else ""
    imp_conversion = f"{round(100 * total / imp, 1)}%" if imp else ""
    sources = metrics["sources"]
    return [
        mdy(metrics["date"]), imp, pv,
        metrics["first_time_downloads"], metrics["redownloads"],
        pv_conversion, imp_conversion,
        *(sources.get(c, 0) for c in appstore.SOURCE_COLUMNS),
    ]


def insert_appstore_rows(rows):
    """Insert daily rows into the App Store Connect tab with the most recent day on top.

    Row 1 is the header and row 2 is a pinned totals row, so days are inserted oldest-first
    at row 3: each newer day pushes older ones down and the newest ends up directly under
    the totals row.
    """
    ws = worksheet(APPSTORE_SHEET)
    for row in sorted(rows, key=lambda r: _date_key(r[0])):
        ws.insert_row(row, index=3, value_input_option="USER_ENTERED")
    pin_totals_row(ws)


def pin_totals_row(ws):
    """Force the totals row (row 2) formula ranges to start at row 3.

    Inserting a row at row 3 makes Sheets bump each totals range's start down a row
    (e.g. SUM(B3:B1000) -> SUM(B4:B1000)), which would drop the newest day from the
    totals. Re-pinning the start back to row 3 keeps every day counted, whatever
    function each cell uses (SUM, AVERAGE, ...). A no-op when row 2 holds no formulas.
    """
    formulas = (ws.get("A2:L2", value_render_option="FORMULA") or [[]])[0]
    formulas += [""] * (12 - len(formulas))
    pinned = [
        re.sub(r"([A-Za-z]+\()([A-Z]+)\d+", r"\g<1>\g<2>3", f, count=1)
        if isinstance(f, str) and f.startswith("=") else f
        for f in formulas
    ]
    if pinned != formulas:
        ws.update([pinned], "A2:L2", value_input_option="USER_ENTERED")


def _date_key(mdy_str):
    """Chronological sort key for an 'M/D/YYYY' date string."""
    m, d, y = (int(x) for x in mdy_str.split("/"))
    return (y, m, d)


def refresh_marketing(args):
    """Update the Marketing tab: scrape Reddit and Hacker News rows for upvotes and comments."""
    fetchers = {"reddit": reddit_stats, "hackernews": hn_stats}
    ws = worksheet(MARKETING_SHEET)
    rows = ws.get_all_values()
    updates = []
    changed_rows = set()
    for i, row in enumerate(rows[1:], start=2):
        medium = (row[1] if len(row) > 1 else "").strip().lower()
        link = (row[6] if len(row) > 6 else "").strip()
        fetch = fetchers.get(medium)
        if not fetch or not link:
            continue
        try:
            stats = fetch(link)
        except Exception as e:
            print(f"row {i}: FETCH FAILED ({type(e).__name__}: {e}) {link}")
            continue
        if stats is None:
            print(f"row {i}: skip (unrecognized URL) {link}")
            continue
        up, cm = stats["upvotes"], stats["comments"]
        views = reddit_views(link) if medium == "reddit" else None
        suffix = f" views={views}" if views is not None else ""
        print(f"row {i}: upvotes={up} comments={cm}{suffix}  {link}")
        if not args.dry_run:
            if up is not None:
                updates.append({"range": f"C{i}", "values": [[str(up)]]})
                changed_rows.add(i)
            if cm is not None:
                updates.append({"range": f"D{i}", "values": [[str(cm)]]})
                changed_rows.add(i)
            if views is not None:
                updates.append({"range": f"E{i}", "values": [[str(views)]]})
                changed_rows.add(i)
        time.sleep(random.uniform(args.min_sleep, args.max_sleep))

    if args.dry_run:
        print("(dry run — nothing written; Views are left untouched, neither API exposes them)")
    elif updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")
        print(f"Marketing: updated {len(changed_rows)} rows (upvotes and/or comments).")
    else:
        print("Marketing: no rows updated.")


def refresh_appstore(args):
    """Upsert the App Store Connect tab from the analytics report, most recent day on top.

    Apple revises the most recent days for a day or two after they first appear, so a
    date already in the sheet is rewritten in place when its numbers change, not just
    skipped. New days are inserted; older days that have aged out of Apple's reporting
    window are left as they are.
    """
    try:
        metrics = appstore.daily_rows()
    except Exception as e:
        print(f"App Store: skipped ({type(e).__name__}: {e})")
        return
    if not metrics:
        print("App Store: no data yet (Apple is still provisioning the analytics report).")
        return

    ws = worksheet(APPSTORE_SHEET)
    grid = ws.get_all_values()
    date_row = {r[0]: i + 1 for i, r in enumerate(grid) if i >= 2 and r and r[0]}

    # The conversion columns (indices 5 and 6) are derived from page views,
    # impressions, and downloads, which are compared directly, and the sheet reformats
    # their percent, so they're left out of the change check to avoid rewriting every
    # row on every run.
    def comparable(cells):
        return [c for i, c in enumerate(cells) if i not in (5, 6)]

    updates, inserts = [], []
    for m in metrics:
        row = appstore_row(m)
        rn = date_row.get(row[0])
        if rn is None:
            inserts.append(row)
        elif comparable([str(c) for c in row]) != comparable((grid[rn - 1] + [""] * 12)[:12]):
            updates.append((rn, row))

    if args.dry_run:
        print(f"App Store: {len(metrics)} day(s) available, {len(updates)} changed, {len(inserts)} new (dry run):")
        for _, row in sorted(updates):
            print("  update " + ",".join(str(c) for c in row))
        for row in sorted(inserts, key=lambda r: _date_key(r[0])):
            print("  insert " + ",".join(str(c) for c in row))
        return

    if updates:
        ws.batch_update(
            [{"range": f"A{rn}:L{rn}", "values": [row]} for rn, row in updates],
            value_input_option="USER_ENTERED",
        )
    if inserts:
        insert_appstore_rows(inserts)
    if updates or inserts:
        print(f"App Store: {len(updates)} updated, {len(inserts)} inserted.")
    else:
        print(f"App Store: up to date ({len(metrics)} day(s) available, all current).")


def cmd_refresh(args):
    """Update marketing stats: both the Marketing tab and the App Store Connect tab."""
    refresh_marketing(args)
    refresh_appstore(args)


def main():
    parser = argparse.ArgumentParser(description="Interact with the Sojourn Marketing sheet.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Print every row as CSV").set_defaults(func=cmd_list)

    add = sub.add_parser("add", help="Append a marketing entry")
    add.add_argument("--date", required=True, help="M/D/YYYY")
    add.add_argument("--medium", required=True, help="Reddit, HackerNews, LinkedIn, ...")
    add.add_argument("--upvotes", default="")
    add.add_argument("--comments", default="")
    add.add_argument("--views", default="")
    add.add_argument("--clicks", default="", help="referral clicks")
    add.add_argument("--link", required=True)
    add.add_argument("--notes", default="", help="e.g. 'moderated'")
    add.set_defaults(func=cmd_add)

    refresh = sub.add_parser("refresh", help="Scrape Reddit rows, update upvotes and comments")
    refresh.add_argument("--dry-run", action="store_true", help="Print what would change, write nothing")
    refresh.add_argument("--min-sleep", type=float, default=3.0, help="Min seconds between requests")
    refresh.add_argument("--max-sleep", type=float, default=7.0, help="Max seconds between requests")
    refresh.set_defaults(func=cmd_refresh)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
