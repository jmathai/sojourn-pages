#!/usr/bin/env python3
"""Finds Reddit posts (and thread comments) Sojourn could usefully answer.

This script only *retrieves and filters*. Deciding whether a candidate is actually
worth answering, and writing the answer, is the model's job (see SKILL.md): a keyword
match is a lead, not a verdict. Keeping judgment out of here is deliberate, so the
script stays boring and predictable while the hard part stays with the reader.

Retrieval differs by subreddit on purpose:
  - Faith subs are paged from /new and filtered locally. Reddit's relevance search is
    loose (an "AI" query there returns "Off-Topic Friday"), so local filtering over a
    complete listing beats trusting their matcher.
  - AI/tech subs are searched, because their volume is far too high to page.

Usage (from this folder):
    ../marketing/.venv/bin/python find_posts.py --days 3 --out candidates.json
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARKETING = HERE.parent / "marketing"
REPO = HERE.parent.parent.parent
COOKIE_PATH = MARKETING / ".reddit-cookie"   # shared with the marketing skill
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0"

# --- what to look in -------------------------------------------------------------
# Edit these lists freely; they are the whole configuration surface of the skill.

FAITH_SUBS = [
    "Christianity", "TrueChristian", "Christian", "Bible",
    "OrthodoxChristianity", "AcademicBiblical", "Catholicism", "Reformed",
]

AI_SUBS = [
    "artificial", "ArtificialInteligence", "OpenAI", "ChatGPT",
    "philosophy", "technology", "Futurology",
]

# Terms that mark a post as being about AI at all.
AI_TERMS = [
    "ai", "a.i.", "artificial intelligence", "chatgpt", "chat gpt", "llm",
    "large language model", "chatbot", "claude", "gemini", "copilot",
    "machine learning", "algorithm", "robot",
]

# Terms that mark a post as being about faith/Christianity at all.
FAITH_TERMS = [
    "christian", "christianity", "church", "faith", "god", "jesus", "christ",
    "bible", "scripture", "scriptural", "theology", "theological", "gospel",
    "prayer", "pray", "soul", "sin", "pastor", "priest", "sermon", "worship",
]

# Terms that mark a post as being about ethics/morality.
ETHICS_TERMS = [
    "ethic", "ethics", "ethical", "moral", "morality", "morally", "ought",
    "should we", "is it wrong", "is it right", "responsibility", "responsible",
    "conscience", "virtue", "harm", "alignment", "dignity",
]

# Topic pages live in the repo; synonyms are how real people phrase them.
TOPIC_SYNONYMS = {
    "anger": ["anger", "angry", "rage", "resentment", "bitter", "bitterness", "temper", "furious"],
    "anxiety": ["anxiety", "anxious", "worry", "worried", "worrying", "panic", "overwhelmed", "stressed"],
    "contentment": ["contentment", "content with", "satisfied", "never enough", "comparison", "gratitude", "grateful"],
    "despair": ["despair", "hopeless", "hopelessness", "no hope", "giving up", "given up", "what's the point"],
    "envy": ["envy", "envious", "jealous", "jealousy", "comparing myself", "resent their"],
    "fear": ["fear", "afraid", "scared", "terrified", "dread", "frightened"],
    "generosity": ["generosity", "generous", "tithe", "tithing", "giving money", "greed", "greedy", "stingy"],
    "grief": ["grief", "grieving", "grieve", "mourning", "mourn", "passed away", "died", "death of", "funeral", "loss of"],
    "lust": ["lust", "lustful", "porn", "pornography", "sexual temptation", "purity", "masturbat"],
    "obedience": ["obedience", "obey", "obeying", "submit to god", "submission", "god's will", "gods will", "calling"],
    "sadness": ["sadness", "sad", "depressed", "depression", "despondent", "numb"],
}

# Posts carrying these are people in crisis, not marketing opportunities. The script
# flags them so the reader can skip them; see SKILL.md for why that matters.
CRISIS_TERMS = [
    "suicide", "suicidal", "kill myself", "killing myself", "end my life", "end it all",
    "want to die", "better off dead", "self harm", "self-harm", "cutting myself",
    "overdose", "raped", "rape", "molested", "abusing me", "abusive husband",
    "abusive wife", "abusive parents", "beat me",
]

QUESTION_MARKERS = [
    "?", "how do", "how can", "what do", "what does", "why do", "why does",
    "should i", "can someone", "advice", "help me", "struggling", "confused",
    "does anyone", "thoughts on", "am i wrong",
]


def fail(msg, code=2):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)


def cookie():
    if not COOKIE_PATH.exists():
        fail(
            f"No Reddit session cookie at {COOKIE_PATH}.\n"
            "The marketing skill's README explains how to save one: copy the reddit_session\n"
            "cookie from a logged-in browser (DevTools > Storage > Cookies) into that file."
        )
    return COOKIE_PATH.read_text().strip()


def get_json(url, tries=4, sleep=1.5):
    """Fetch JSON as the logged-in user, backing off on Reddit's throttles."""
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json", "Cookie": cookie()}
    )
    delay = 8
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                out = json.loads(r.read())
            time.sleep(sleep)  # be a polite guest
            return out
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 500, 502, 503) and attempt < tries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            if e.code == 403:
                fail(
                    "Reddit returned 403 even after retries, which almost always means the\n"
                    "reddit_session cookie has expired. Refresh it and run again."
                )
            raise
        except urllib.error.URLError:
            if attempt < tries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    return None


def me():
    """The logged-in username, so we never suggest replying to ourselves."""
    data = get_json("https://www.reddit.com/api/me.json", sleep=0.5)
    return (data or {}).get("data", {}).get("name")


# --- dedupe ----------------------------------------------------------------------

def post_id(url_or_permalink):
    m = re.search(r"/comments/([a-z0-9]+)", url_or_permalink or "")
    return m.group(1) if m else None


def already_engaged():
    """Post ids already in the sheet, from the Marketing log and the Reddit Posts tab.

    Reading both is what keeps runs from resurfacing the same thread: Marketing holds
    what was actually posted, Reddit Posts holds what this skill already surfaced.
    Returns an empty set (with a warning) if the sheet can't be reached, since a
    missing dedupe is worth a duplicate row, not a failed run.
    """
    ids = set()
    try:
        sys.path.insert(0, str(MARKETING))
        import sheet as marketing_sheet

        for tab_name, col in (("Marketing", "Link"), ("Reddit Posts", "Url")):
            try:
                ws = marketing_sheet.worksheet(tab_name)
                # FORMULA so the Reddit Posts tab's HYPERLINK cells yield real permalinks.
                rows = ws.get_all_values(value_render_option="FORMULA")
            except Exception as exc:
                sys.stderr.write(f"note: could not read the {tab_name} tab ({exc})\n")
                continue
            if not rows:
                continue
            header = [c.strip().lower() for c in rows[0]]
            try:
                idx = header.index(col.lower())
            except ValueError:
                idx = 6 if tab_name == "Marketing" else 0
            for row in rows[1:]:
                if len(row) > idx:
                    cell = row[idx]
                    m = re.search(r'HYPERLINK\(\s*"([^"]+)"', cell or "", re.I)
                    pid = post_id(m.group(1) if m else cell)
                    if pid:
                        ids.add(pid)
    except Exception as exc:
        sys.stderr.write(f"note: dedupe skipped, sheet unavailable ({exc})\n")
    return ids


# --- matching --------------------------------------------------------------------

def hits(text, terms):
    """Terms present in text. Word-bounded for short/ambiguous terms so 'ai' doesn't
    match 'said' and 'sad' doesn't match 'sadly' by accident."""
    found = []
    for t in terms:
        if len(t) <= 4 or t.isalpha() and len(t) <= 6:
            if re.search(rf"(?<![a-z]){re.escape(t)}(?![a-z])", text):
                found.append(t)
        elif t in text:
            found.append(t)
    return found


def classify(title, body, subreddit):
    """Return (buckets, matched_terms, topics, crisis) for a post.

    A post can land in more than one bucket; that is useful signal rather than a
    problem, so nothing here forces a single label.
    """
    text = f"{title}\n{body}".lower()
    ai = hits(text, AI_TERMS)
    faith = hits(text, FAITH_TERMS)
    ethics = hits(text, ETHICS_TERMS)
    in_faith_sub = subreddit.lower() in {s.lower() for s in FAITH_SUBS}

    buckets, matched = [], []
    if ai and (faith or in_faith_sub):
        buckets.append("faith-and-ai")
        matched += ai + faith
    if ai and ethics:
        buckets.append("ai-ethics")
        matched += ai + ethics

    title_l = title.lower()
    topics, in_title = [], []
    for slug, syns in TOPIC_SYNONYMS.items():
        if hits(text, syns):
            topics.append(slug)
            if hits(title_l, syns):
                in_title.append(slug)

    # A feeling word somewhere in a long post is weak evidence: plenty of threads mention
    # sadness without asking anything answerable. Require that the person is actually
    # asking, and that the topic is either in the title or echoed by a second topic, so
    # what survives is a question worth answering rather than a keyword sighting.
    if topics and (in_faith_sub or faith) and asks_something(title, body):
        if in_title or len(topics) >= 2:
            buckets.append("topic-question")
            matched += topics

    crisis = hits(text, CRISIS_TERMS)
    return sorted(set(buckets)), sorted(set(matched)), topics, crisis


def asks_something(title, body):
    text = f"{title}\n{body}".lower()
    return any(m in text for m in QUESTION_MARKERS)


def topic_slugs_on_disk():
    d = REPO / "topics"
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir() and (p / "index.html").exists())


# --- retrieval -------------------------------------------------------------------

def page_new(sub, pages, cutoff_ts):
    """Page /new for a subreddit until we pass the time window."""
    out, after = [], None
    for _ in range(pages):
        url = f"https://www.reddit.com/r/{sub}/new.json?limit=100&raw_json=1"
        if after:
            url += f"&after={after}"
        data = get_json(url)
        if not data:
            break
        children = data.get("data", {}).get("children", [])
        if not children:
            break
        out += [c["data"] for c in children if c.get("kind") == "t3"]
        after = data["data"].get("after")
        if not after or (out and out[-1].get("created_utc", 0) < cutoff_ts):
            break
    return out


def search_subs(subs, terms, t="week", limit=100):
    """One relevance search across several subs, for volumes too high to page."""
    sub_clause = " OR ".join(f"subreddit:{s}" for s in subs)
    term_clause = " OR ".join(f'"{x}"' if " " in x else x for x in terms)
    q = f"({sub_clause}) ({term_clause})"
    url = (
        "https://www.reddit.com/search.json?q="
        + urllib.parse.quote(q)
        + f"&sort=new&t={t}&limit={limit}&raw_json=1&include_over_18=off"
    )
    data = get_json(url)
    return [c["data"] for c in (data or {}).get("data", {}).get("children", []) if c.get("kind") == "t3"]


def thread_comments(permalink, username, limit=40):
    """Top-level comments on one thread, as reply candidates.

    Reddit's search endpoint ignores type=comment, so the only way to find a comment
    worth answering is to open a thread we already like and look inside it.
    """
    url = f"https://www.reddit.com{permalink.rstrip('/')}.json?limit={limit}&raw_json=1&sort=top"
    data = get_json(url)
    if not data or len(data) < 2:
        return []
    out = []
    for child in data[1].get("data", {}).get("children", []):
        if child.get("kind") != "t1":
            continue
        c = child["data"]
        body = c.get("body") or ""
        if (
            c.get("author") in (username, "AutoModerator", "[deleted]")
            or c.get("stickied")
            or len(body) < 60
            or body in ("[removed]", "[deleted]")
        ):
            continue
        out.append(
            {
                "comment_id": c.get("id"),
                "author": c.get("author"),
                "ups": c.get("ups"),
                "excerpt": re.sub(r"\s+", " ", body)[:400],
                "url": "https://www.reddit.com" + c.get("permalink", ""),
                "asks_something": asks_something("", body),
            }
        )
    return out


# --- main ------------------------------------------------------------------------

def build(args):
    username = me()
    seen = set() if args.no_dedupe else already_engaged()
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - args.days * 86400

    raw, fetched = {}, 0
    for sub in FAITH_SUBS:
        for p in page_new(sub, args.pages, cutoff):
            fetched += 1
            raw[p["id"]] = p
    for p in search_subs(AI_SUBS, AI_TERMS + ETHICS_TERMS, t=args.search_window):
        fetched += 1
        raw.setdefault(p["id"], p)

    candidates, skipped = [], {"old": 0, "already_engaged": 0, "own_post": 0, "unusable": 0, "no_match": 0}
    for p in raw.values():
        if p.get("created_utc", 0) < cutoff:
            skipped["old"] += 1
            continue
        if p["id"] in seen:
            skipped["already_engaged"] += 1
            continue
        if p.get("author") == username:
            skipped["own_post"] += 1
            continue
        if p.get("locked") or p.get("archived") or p.get("removed_by_category") or p.get("over_18"):
            skipped["unusable"] += 1
            continue

        title = p.get("title") or ""
        body = re.sub(r"\s+", " ", p.get("selftext") or "")
        buckets, matched, topics, crisis = classify(title, body, p.get("subreddit", ""))
        if not buckets:
            skipped["no_match"] += 1
            continue

        age_h = round((now.timestamp() - p["created_utc"]) / 3600, 1)
        candidates.append(
            {
                "id": p["id"],
                "kind": "post",
                "url": "https://www.reddit.com" + p.get("permalink", ""),
                "subreddit": p.get("subreddit"),
                "title": title,
                "body": body[:1500],
                "author": p.get("author"),
                "created_utc": p["created_utc"],
                "age_hours": age_h,
                "num_comments": p.get("num_comments"),
                "ups": p.get("ups"),
                "buckets": buckets,
                "matched_terms": matched,
                "suggested_topics": topics,
                "crisis_flags": crisis,
                "asks_something": asks_something(title, body),
            }
        )

    # Freshest first: on Reddit a day-old thread is already cold, so recency beats score.
    candidates.sort(key=lambda c: (-c["created_utc"],))

    if args.with_comments:
        for c in candidates[: args.with_comments]:
            if c["crisis_flags"]:
                continue
            path = urllib.parse.urlsplit(c["url"]).path
            c["thread_comments"] = thread_comments(path, username)

    return {
        "generated": now.isoformat(timespec="seconds"),
        "as_user": username,
        "window_days": args.days,
        "topic_pages": topic_slugs_on_disk(),
        "counts": {"fetched": fetched, "unique": len(raw), "candidates": len(candidates), "skipped": skipped},
        "candidates": candidates,
    }


def main():
    ap = argparse.ArgumentParser(description="Find Reddit posts Sojourn could answer.")
    ap.add_argument("--days", type=float, default=3, help="Only posts this new (default 3)")
    ap.add_argument("--pages", type=int, default=2, help="Pages of /new per faith sub (100 each, default 2)")
    ap.add_argument("--search-window", default="week", help="Reddit t= window for AI subs (hour/day/week/month)")
    ap.add_argument("--with-comments", type=int, default=5, metavar="N",
                    help="Also pull thread comments for the N freshest candidates (default 5, 0 to skip)")
    ap.add_argument("--no-dedupe", action="store_true", help="Do not drop posts already in the sheet")
    ap.add_argument("--out", default="candidates.json", help="Where to write the JSON (default candidates.json)")
    args = ap.parse_args()

    result = build(args)
    Path(args.out).write_text(json.dumps(result, indent=2))
    c = result["counts"]
    print(f"fetched {c['fetched']} posts ({c['unique']} unique) -> {c['candidates']} candidates")
    print(f"skipped: {c['skipped']}")
    print(f"wrote {args.out}")
    for cand in result["candidates"][:15]:
        flag = " [CRISIS]" if cand["crisis_flags"] else ""
        print(f"  r/{cand['subreddit']} {cand['age_hours']}h {','.join(cand['buckets'])}{flag}: {cand['title'][:70]}")


if __name__ == "__main__":
    main()
