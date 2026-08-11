# Reads, appends, and refreshes rows in the "Sojourn Marketing" Google Sheet.
# Writes via a service-account key; refresh pulls Reddit stats using a saved session cookie.
import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import gspread

SHEET_ID = "1VZPdG0y7YN0T2jB7BFQiXgGghtluIskCcrAvyAtUlCg"
KEY_PATH = Path(__file__).parent / ".service-account.json"
COOKIE_PATH = Path(__file__).parent / ".reddit-cookie"
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
    if not COOKIE_PATH.exists():
        sys.exit(
            f"No Reddit session cookie at {COOKIE_PATH}.\n"
            "Copy the reddit_session cookie from a logged-in browser and save it there."
        )
    cookie = COOKIE_PATH.read_text().strip()
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


def cmd_refresh(args):
    ws = worksheet()
    rows = ws.get_all_values()
    updates = []
    for i, row in enumerate(rows[1:], start=2):
        medium = (row[1] if len(row) > 1 else "").strip()
        link = (row[6] if len(row) > 6 else "").strip()
        if medium.lower() != "reddit" or not link:
            continue
        try:
            stats = reddit_stats(link)
        except Exception as e:
            print(f"row {i}: FETCH FAILED ({type(e).__name__}: {e}) {link}")
            continue
        if stats is None:
            print(f"row {i}: skip (not a post/comment URL) {link}")
            continue
        up, cm = stats["upvotes"], stats["comments"]
        print(f"row {i}: upvotes={up} comments={cm}  {link}")
        if not args.dry_run:
            updates.append({"range": f"C{i}", "values": [[str(up)]]})
            updates.append({"range": f"D{i}", "values": [[str(cm)]]})
        time.sleep(random.uniform(args.min_sleep, args.max_sleep))

    if args.dry_run:
        print("(dry run — nothing written; views are left untouched, Reddit's API doesn't expose them)")
    elif updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")
        print(f"Updated {len(updates) // 2} Reddit rows (upvotes + comments).")
    else:
        print("No Reddit rows updated.")


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
