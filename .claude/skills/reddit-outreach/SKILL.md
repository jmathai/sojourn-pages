---
name: reddit-outreach
description: Find Reddit posts and comments where Sojourn can add genuine value, draft replies in a human voice, log them to the "Reddit Posts" tab of the Sojourn Marketing sheet, and post the ones marked Apply. Use this whenever the user wants to find Reddit threads to comment on or reply to, asks where they should be commenting, wants outreach or engagement leads, mentions finding posts about faith and AI, the ethics of AI, or questions matching a Sojourn topic page (anger, anxiety, contentment, despair, envy, fear, generosity, grief, lust, obedience, sadness), or asks to apply, post, or publish drafted Reddit replies. Also use it when they say "find posts I can comment on", "any good threads today", "draft some Reddit replies", or "post the approved rows".
---

# Reddit outreach

Sojourn grows when a real person asks a real question and gets a real answer. This skill
finds those questions, drafts answers worth reading, and keeps the whole pipeline in one
place: the "Reddit Posts" tab of the Sojourn Marketing sheet
(`1VZPdG0y7YN0T2jB7BFQiXgGghtluIskCcrAvyAtUlCg`).

The split of labor matters. The scripts do retrieval, filtering, dedupe, sheet mechanics,
and pacing. You do the judgment: whether a thread deserves an answer, what that answer
says, and whether it earns a link. A keyword match is a lead, not a verdict.

## The pipeline

```
find_posts.py  -->  you judge + draft  -->  post_rows.py  -->  (human reviews sheet)  -->  apply_rows.py
   candidates            rows.json          Status=Pending        Status=Apply            Status=Posted
```

All four scripts run on the marketing skill's virtualenv and share its Reddit cookie, so
there is nothing extra to install:

```bash
cd .claude/skills/reddit-outreach
../marketing/.venv/bin/python find_posts.py --days 3 --out candidates.json
```

## Step 1: find candidates

```bash
../marketing/.venv/bin/python find_posts.py --days 3 --with-comments 5 --out candidates.json
```

It pages `/new` for the faith subreddits and filters locally (Reddit's relevance search
is too loose to trust: an "AI" query in r/Christianity returns "Off-Topic Friday"), and
searches the high-volume AI subreddits where paging is not practical. It drops posts that
are locked, archived, NSFW, older than the window, authored by you, or already in the
sheet, then classifies what survives into three buckets:

- **faith-and-ai**: AI terms in a faith context
- **ai-ethics**: AI terms alongside ethics/morality terms
- **topic-question**: language matching a topic page, in a faith context

Each candidate carries `matched_terms`, `suggested_topics`, `age_hours`,
`num_comments`, `asks_something`, and `crisis_flags`. For the freshest few it also
includes `thread_comments`, since replying to a specific comment inside a good thread is
often better than adding the twentieth top-level reply.

Subreddit lists, term lists, and topic synonyms are all at the top of `find_posts.py`.
Edit them there when the targeting drifts.

## Step 2: judge each candidate

This is the part that decides whether the whole effort reads as help or as spam. Read the
post body, not just the title, and keep a candidate only when **you can say something
specifically useful about what this person actually asked.** A generic answer that would
fit fifty threads is worse than silence: it costs the account's credibility and teaches
the subreddit to tune you out.

Drop a candidate when:

- **It carries `crisis_flags`.** Someone describing suicidal thoughts, self-harm, or
  abuse needs a human being, not an app. Do not draft a reply with a product in it. If
  the thread genuinely calls for a word of care, say so to the user and let them answer
  personally as themselves.
- **You have nothing particular to add.** Rhetorical questions, debates already answered
  well, jokes, memes, news links, venting that asks for nothing.
- **The thread is cold or crowded.** A day-old thread with 200 comments will bury you.
- **The subreddit forbids it.** Several faith subs restrict self-promotion and app links.
  The marketing sheet already has a `moderated` row and a post that stopped rendering
  stats, which is what a removal looks like from the outside. When in doubt, answer the
  question and skip the link entirely.
- **You would be answering your own post.** The script filters your account, but
  crossposts and alts slip through.

Prefer candidates that are a few hours old, have single-digit comment counts, and ask an
answerable question. Those are the ones where a thoughtful reply is actually read.

## Step 3: draft the reply

Write like a person who knows the topic and happens to have built something relevant.
The repo's Voice rules in `CLAUDE.md` apply, and two of them are load-bearing here:

- **No em dashes.** Use a comma, a period, a colon, parentheses, or reword.
- **It must not read as AI-drafted.** No "delve", no "tapestry", no "it's important to
  note", no tidy rule-of-three lists, no throat-clearing preamble. Vary sentence length.
  Cut filler. On Reddit the cost of sounding synthetic is not just a bad impression, it
  is being called out as a bot in public, under the account's real name.

Shape of a good reply: answer the question first, in two to five sentences. Be concrete.
If scripture belongs in it, quote it accurately (see below). Then stop. A short reply that
answers the question outperforms a long one that circles it.

### The link budget: at most 10% of replies

Most replies should carry no link at all. Include one only when it genuinely helps the
person who asked, which in practice means a topic page that addresses their exact
question, not the App Store page. Use the real URLs:

- a topic page: `https://trysojourn.app/topics/<slug>/` (the slugs live in `topics/`)
- the app, rarely: the App Store listing

`post_rows.py` and `apply_rows.py` both measure the share of replies containing a Sojourn
link across the tab's whole history and refuse to push it past 10%. The check is strict,
which has a consequence worth knowing up front: 10% of a small tab is zero links, so the
first linked reply only becomes possible once there are about ten rows. That is the cap
working, not a bug. When you hit it, drop the link and let the reply stand on its own,
which is usually the better comment anyway. `--over-budget` exists but treat it as a
decision you are making, not a default.

### Quoting scripture

The site's promise is that scripture is quoted verbatim from the World English Bible,
never composed or recalled from memory, and a Reddit reply is no different: getting a
verse wrong in public undoes the credibility the whole project runs on. So look it up
instead of typing it from memory, even for a verse you are sure of:

```bash
../marketing/.venv/bin/python verse.py "Matthew 11:28-30"
# “Come to me, all you who labor and are heavily burdened, and I will give you rest. ...
```

`verse.py` reads the WEB database that lives with the topics skill and prints the text
exactly as the WEB has it, punctuation included (the one place em dashes are allowed).
Paste what it prints. If the database is missing it tells you the download command. If a
reference will not resolve, cite it by reference alone or leave it out.

## Step 4: write the rows

Build a JSON file and append it. Check it with `--dry-run` first: it prints the drafts and
the link budget without touching the sheet.

```json
[
  {
    "url": "https://www.reddit.com/r/Christianity/comments/abc123/why_do_i_feel_envious/",
    "post": "Why do I feel envious of people at church?",
    "comment": "",
    "response": "Envy usually shows up where we already feel behind..."
  }
]
```

`comment` is the excerpt of the comment you are replying to, and stays blank when you are
replying to the post itself. When you are replying to a comment, use that comment's own
permalink as `url` so the reply lands in the right place.

```bash
../marketing/.venv/bin/python post_rows.py rows.json --dry-run
../marketing/.venv/bin/python post_rows.py rows.json
```

Rows land with **Status = Pending**. The script applies the tab schema, writes clickable
links, and skips threads already present.

## Step 5: apply the approved rows

The user reviews the tab, edits any Response text in place, and sets Status to **Apply**
on the rows they want posted (or **Skip** to pass). Then:

```bash
../marketing/.venv/bin/python apply_rows.py --dry-run   # show what would post
../marketing/.venv/bin/python apply_rows.py             # actually post
```

`apply_rows.py` posts only rows whose Status is exactly Apply, reads the Response from the
sheet so edits are honored, and writes a terminal status to every row it touches:
**Posted** with the new comment's permalink in Result, or **Failed** with the reason.
That terminal state is what makes an unattended re-run safe; without it a second run would
comment twice on the same thread.

It paces itself deliberately: 4 to 15 minutes between comments (randomized), 45 minutes
before commenting in the same subreddit again, and at most 5 comments per run. Those are
flags (`--min-gap`, `--max-gap`, `--sub-cooldown`, `--max`) but the defaults exist because
rapid-fire commenting is the single clearest bot signal there is, and getting the account
actioned costs far more than a slow run. A run posting five comments takes roughly half an
hour to an hour by design.

### Posting credentials

By preference it posts through a Reddit **script app** (OAuth), which is the sanctioned
write path. Create one at `https://www.reddit.com/prefs/apps` and save:

```json
// .claude/skills/reddit-outreach/.reddit-oauth.json   (gitignored)
{"client_id": "...", "client_secret": "...", "username": "...", "password": "..."}
```

Without that file it falls back to the saved browser session from the marketing skill,
which works but looks like an automated browser, the pattern most likely to get an
account flagged. Tell the user this when it happens; the script prints which path it used.

## After posting

Comments that go out are marketing activity, so add the ones worth tracking to the
Marketing tab with the marketing skill, and its `refresh` will then follow their upvotes,
replies, and views like any other row.

## Boundaries worth keeping

This pipeline posts under a real person's account in communities with their own rules and
their own patience. Two habits keep it honest: never post a reply you would be
embarrassed to have quoted back to you, and never let the volume outrun the value. If a
run produces only one candidate worth answering, one is the right number of comments.
