#!/usr/bin/env python3
"""Appends drafted replies to the "Reddit Posts" tab of the Sojourn Marketing sheet.

This script owns the sheet mechanics (schema, clickable links, dedupe, the 10% link
budget) and nothing else. The drafts themselves come from a JSON file the model writes,
because the wording is judgment work that does not belong in a script.

Input JSON: a list of objects, or {"rows": [...]}, each with
    url       (required) the Reddit post or comment permalink being answered
    post      (required) the thread's title
    comment   (optional) excerpt of the comment being replied to; blank for a post
    response  (required) the drafted reply

Usage (from this folder):
    ../marketing/.venv/bin/python post_rows.py rows.json --dry-run
    ../marketing/.venv/bin/python post_rows.py rows.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

import tab
from tab import COL_RESPONSE, COL_URL, PENDING

# A reply "carries a link" if it points anywhere at Sojourn. Kept in one place so the
# writer and the poster measure the budget the same way.
LINK_PATTERNS = [r"trysojourn\.app", r"apps\.apple\.com/[^\s)]*sojourn", r"sojourn\.app"]
LINK_BUDGET = 0.10


def has_link(text):
    t = (text or "").lower()
    return any(re.search(p, t) for p in LINK_PATTERNS)


def post_id(url):
    m = re.search(r"/comments/([a-z0-9]+)", url or "")
    return m.group(1) if m else None


def link_formula(url):
    """A clickable cell labeled with the subreddit, so the row reads at a glance."""
    safe = url.replace('"', '""')
    label = "open"
    m = re.search(r"/r/([A-Za-z0-9_]+)", url)
    if m:
        label = f"r/{m.group(1)}"
    return f'=HYPERLINK("{safe}", "{label}")'


def load_rows(path):
    data = json.loads(Path(path).read_text())
    rows = data["rows"] if isinstance(data, dict) else data
    out = []
    for i, r in enumerate(rows, 1):
        missing = [k for k in ("url", "post", "response") if not (r.get(k) or "").strip()]
        if missing:
            sys.exit(f"row {i} is missing required field(s): {', '.join(missing)}")
        if not post_id(r["url"]):
            sys.exit(f"row {i} has a url that is not a Reddit post or comment: {r['url']}")
        out.append({
            "url": r["url"].strip(),
            "post": r["post"].strip(),
            "comment": (r.get("comment") or "").strip(),
            "response": r["response"].strip(),
        })
    return out


def main():
    ap = argparse.ArgumentParser(description="Append drafted Reddit replies to the sheet.")
    ap.add_argument("rows_json", help="JSON file of rows to append")
    ap.add_argument("--dry-run", action="store_true", help="Print what would be written and stop")
    ap.add_argument("--allow-duplicates", action="store_true",
                    help="Write rows whose thread is already in the tab")
    ap.add_argument("--over-budget", action="store_true",
                    help="Append even if it pushes linked replies past the 10%% budget")
    args = ap.parse_args()

    rows = load_rows(args.rows_json)
    ws = tab.ensure()
    existing = tab.read(ws)[1:]  # formulas intact; header handled by tab.ensure()

    known = set()
    prior_total = prior_linked = 0
    for row in existing:
        if not any(c.strip() for c in row):
            continue
        prior_total += 1
        pid = post_id(tab.url_of(row[COL_URL]))
        if pid:
            known.add(pid)
        if has_link(row[COL_RESPONSE]):
            prior_linked += 1

    fresh, dupes = [], []
    for r in rows:
        pid = post_id(r["url"])
        if pid in known and not args.allow_duplicates:
            dupes.append(r)
            continue
        known.add(pid)
        fresh.append(r)

    # The link budget is cumulative over the tab's history, not per run: a run of three
    # rows where one carries a link is 33% on its own but may still be fine overall.
    new_linked = sum(1 for r in fresh if has_link(r["response"]))
    total = prior_total + len(fresh)
    linked = prior_linked + new_linked
    ratio = (linked / total) if total else 0.0
    # Strict on purpose: 10% of a small tab really is zero or one link. That means the
    # first linked reply only becomes possible around the tenth row, which is the correct
    # reading of a 10% cap rather than an inconvenience to work around.
    over = ratio > LINK_BUDGET

    print(f"link budget: {linked}/{total} replies carry a Sojourn link ({ratio:.0%}), cap {LINK_BUDGET:.0%}")
    if over and not args.over_budget:
        linked_rows = [r["url"] for r in fresh if has_link(r["response"])]
        sys.exit(
            "refusing to append: this would put the tab over the 10% link budget.\n"
            "Drop the link from some of these drafts (the reply should stand on its own\n"
            "without it) and run again, or pass --over-budget if you really mean it:\n  "
            + "\n  ".join(linked_rows)
        )

    def cells(r):
        return [link_formula(r["url"]), r["post"], r["comment"], r["response"], PENDING, ""]

    if args.dry_run:
        for r in fresh:
            mark = " [has link]" if has_link(r["response"]) else ""
            print(f"would append{mark}: {r['url']}\n    {r['response'][:160]}")
        for r in dupes:
            print(f"would skip (already in tab): {r['url']}")
        print(f"{len(fresh)} to append, {len(dupes)} skipped")
        return

    if fresh:
        ws.append_rows([cells(r) for r in fresh], value_input_option="USER_ENTERED")
    print(f"Reddit Posts: appended {len(fresh)} row(s) as {PENDING}"
          + (f", skipped {len(dupes)} already present" if dupes else ""))


if __name__ == "__main__":
    main()
