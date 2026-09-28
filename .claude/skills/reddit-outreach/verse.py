#!/usr/bin/env python3
"""Prints WEB scripture verbatim, so a drafted reply never quotes from memory.

The site's promise is that scripture is quoted exactly as the World English Bible has
it. A Reddit reply is no different: a misquoted verse in public undoes the credibility
the whole project runs on. Look it up here, paste what it prints.

Usage (from this folder):
    ../marketing/.venv/bin/python verse.py "Matthew 11:28-30"
    ../marketing/.venv/bin/python verse.py "Philippians 4:6" --numbers
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "topics" / "web-backend.sqlite"
DB_URL = ("https://storage.googleapis.com/sojourn-prod-public/data/"
          "bible_translations/web/web-backend.sqlite")

# Same book-to-USFM map the topics skill's verifier uses, so references resolve alike.
USFM = {
    "Genesis": "GEN", "Exodus": "EXO", "Leviticus": "LEV", "Numbers": "NUM",
    "Deuteronomy": "DEU", "Joshua": "JOS", "Judges": "JDG", "Ruth": "RUT",
    "1 Samuel": "1SA", "2 Samuel": "2SA", "1 Kings": "1KI", "2 Kings": "2KI",
    "1 Chronicles": "1CH", "2 Chronicles": "2CH", "Ezra": "EZR", "Nehemiah": "NEH",
    "Esther": "EST", "Job": "JOB", "Psalm": "PSA", "Psalms": "PSA", "Proverbs": "PRO",
    "Ecclesiastes": "ECC", "Song of Solomon": "SNG", "Isaiah": "ISA", "Jeremiah": "JER",
    "Lamentations": "LAM", "Ezekiel": "EZK", "Daniel": "DAN", "Hosea": "HOS",
    "Joel": "JOL", "Amos": "AMO", "Obadiah": "OBA", "Jonah": "JON", "Micah": "MIC",
    "Nahum": "NAM", "Habakkuk": "HAB", "Zephaniah": "ZEP", "Haggai": "HAG",
    "Zechariah": "ZEC", "Malachi": "MAL", "Matthew": "MAT", "Mark": "MRK",
    "Luke": "LUK", "John": "JHN", "Acts": "ACT", "Romans": "ROM",
    "1 Corinthians": "1CO", "2 Corinthians": "2CO", "Galatians": "GAL",
    "Ephesians": "EPH", "Philippians": "PHP", "Colossians": "COL",
    "1 Thessalonians": "1TH", "2 Thessalonians": "2TH", "1 Timothy": "1TI",
    "2 Timothy": "2TI", "Titus": "TIT", "Philemon": "PHM", "Hebrews": "HEB",
    "James": "JAS", "1 Peter": "1PE", "2 Peter": "2PE", "1 John": "1JN",
    "2 John": "2JN", "3 John": "3JN", "Jude": "JUD", "Revelation": "REV",
}


def lookup(ref, numbers=False):
    m = re.match(r"^(.+?)\s+(\d+):(\d+)(?:\s*[-–]\s*(\d+))?$", ref.strip())
    if not m:
        sys.exit(f'cannot parse reference: {ref!r} (expected e.g. "Matthew 11:28-30")')
    book, ch = m.group(1).strip(), int(m.group(2))
    v1, v2 = int(m.group(3)), int(m.group(4) or m.group(3))
    code = USFM.get(book) or USFM.get(book.title())
    if not code:
        sys.exit(f"unknown book: {book!r}")
    if not DB.exists():
        sys.exit(f"WEB db missing at {DB}\n  download: curl -fSL -o '{DB}' {DB_URL}")

    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT verse, text FROM verses WHERE book=? AND chapter=? AND verse BETWEEN ? AND ?"
        " ORDER BY verse", (code, ch, v1, v2)).fetchall()
    if not rows:
        sys.exit(f"no WEB rows for {ref}")
    if numbers:
        return " ".join(f"{r['verse']} {r['text']}" for r in rows)
    return " ".join(r["text"] for r in rows)


def main():
    ap = argparse.ArgumentParser(description="Print WEB scripture verbatim.")
    ap.add_argument("reference", help='e.g. "Matthew 11:28-30"')
    ap.add_argument("--numbers", action="store_true", help="Include verse numbers")
    args = ap.parse_args()
    print(lookup(args.reference, args.numbers))


if __name__ == "__main__":
    main()
