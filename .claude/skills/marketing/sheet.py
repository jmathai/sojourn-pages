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

SHEET_ID = "1VZPdG0y7YN0T2jB7BFQiXgGghtluIskCcrAvyAtUlCg"
KEY_PATH = Path(__file__).parent / ".service-account.json"
REDDIT_COOKIE_PATH = Path(__file__).parent / ".reddit-cookie"
HN_COOKIE_PATH = Path(__file__).parent / ".hn-cookie"
COLUMNS = ["Date", "Medium", "Upvotes", "Comments", "Views", "Clicks", "Link", "Notes"]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0"


def worksheet():
    if not KEY_PATH.exists():
        sys.exit(
            f"No service-account key at {KEY_PATH}.\n"
            "Create one in Google Cloud, share the sheet with its client_email, "
            "and save the JSON there."
        )
    client = gspread.service_account(filename=str(KEY_PATH))
    return client.open_by_key(SHEET_ID).sheet1


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
            if e.code in (403, 429) and attempt < tries - 1:
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


def cmd_refresh(args):
    fetchers = {"reddit": reddit_stats, "hackernews": hn_stats}
    ws = worksheet()
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
        print(f"row {i}: upvotes={up} comments={cm}  {link}")
        if not args.dry_run:
            if up is not None:
                updates.append({"range": f"C{i}", "values": [[str(up)]]})
                changed_rows.add(i)
            if cm is not None:
                updates.append({"range": f"D{i}", "values": [[str(cm)]]})
                changed_rows.add(i)
        time.sleep(random.uniform(args.min_sleep, args.max_sleep))

    if args.dry_run:
        print("(dry run — nothing written; Views are left untouched, neither API exposes them)")
    elif updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")
        print(f"Updated {len(changed_rows)} rows (upvotes and/or comments).")
    else:
        print("No rows updated.")


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
