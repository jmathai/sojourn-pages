#!/usr/bin/env python3
# Verifies every quoted scripture fragment on a topic page matches the local WEB source.
# Run from the repo root: python3 .claude/skills/topics/verify-scripture.py topics/<slug>/index.html
# (exits non-zero on any mismatch)
import os, re, sys, json, html, sqlite3, unicodedata

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(SKILL_DIR, "..", "..", ".."))
DB = os.path.join(SKILL_DIR, "web-backend.sqlite")
DB_URL = "https://storage.googleapis.com/sojourn-prod-public/data/bible_translations/web/web-backend.sqlite"

USFM = {
    "Genesis":"GEN","Exodus":"EXO","Leviticus":"LEV","Numbers":"NUM","Deuteronomy":"DEU",
    "Joshua":"JOS","Judges":"JDG","Ruth":"RUT","1 Samuel":"1SA","2 Samuel":"2SA",
    "1 Kings":"1KI","2 Kings":"2KI","1 Chronicles":"1CH","2 Chronicles":"2CH","Ezra":"EZR",
    "Nehemiah":"NEH","Esther":"EST","Job":"JOB","Psalm":"PSA","Psalms":"PSA","Proverbs":"PRO",
    "Ecclesiastes":"ECC","Song of Solomon":"SNG","Isaiah":"ISA","Jeremiah":"JER",
    "Lamentations":"LAM","Ezekiel":"EZK","Daniel":"DAN","Hosea":"HOS","Joel":"JOL","Amos":"AMO",
    "Obadiah":"OBA","Jonah":"JON","Micah":"MIC","Nahum":"NAM","Habakkuk":"HAB","Zephaniah":"ZEP",
    "Haggai":"HAG","Zechariah":"ZEC","Malachi":"MAL","Matthew":"MAT","Mark":"MRK","Luke":"LUK",
    "John":"JHN","Acts":"ACT","Romans":"ROM","1 Corinthians":"1CO","2 Corinthians":"2CO",
    "Galatians":"GAL","Ephesians":"EPH","Philippians":"PHP","Colossians":"COL",
    "1 Thessalonians":"1TH","2 Thessalonians":"2TH","1 Timothy":"1TI","2 Timothy":"2TI",
    "Titus":"TIT","Philemon":"PHM","Hebrews":"HEB","James":"JAS","1 Peter":"1PE","2 Peter":"2PE",
    "1 John":"1JN","2 John":"2JN","3 John":"3JN","Jude":"JUD","Revelation":"REV",
}

def norm(s):
    """Decode entities and normalize typography for comparison (words/letters must still match)."""
    s = html.unescape(s)
    s = (s.replace("“",'"').replace("”",'"')
           .replace("‘","'").replace("’","'")
           .replace("–","-").replace("—","-").replace("…","..."))
    s = unicodedata.normalize("NFC", s)
    return re.sub(r"\s+", " ", s).strip()

def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)

def load_db():
    if not os.path.exists(DB):
        sys.stderr.write(f"WEB db missing at {DB}\n  download: curl -fSL -o '{DB}' {DB_URL}\n")
        sys.exit(2)
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    return con

class Verifier:
    def __init__(self, con):
        self.con = con
        self.fails = []
        self.checked = 0

    def web_range(self, ref):
        """ref like 'Genesis 4:3-5' / '1 Samuel 18:9' -> normalized concatenated WEB text, or None."""
        m = re.match(r"^(.+?)\s+(\d+):(\d+)(?:[-–](\d+))?$", ref.strip())
        if not m:
            return None
        book, ch, v1, v2 = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4) or m.group(3))
        code = USFM.get(book)
        if not code:
            return None
        rows = self.con.execute(
            "SELECT text FROM verses WHERE book=? AND chapter=? AND verse BETWEEN ? AND ? ORDER BY verse",
            (code, ch, v1, v2)).fetchall()
        if not rows:
            return None
        return norm(" ".join(r["text"] for r in rows))

    def fail(self, kind, ref, got, expected):
        self.fails.append((kind, ref, got, expected))

    def check_equal(self, kind, ref, got):
        self.checked += 1
        exp = self.web_range(ref)
        if exp is None:
            self.fail(kind, ref, got, "<no WEB rows / unknown book>"); return
        if norm(got) != exp:
            self.fail(kind, ref, norm(got), exp)

    def check_substring(self, kind, ref, quote):
        self.checked += 1
        exp = self.web_range(ref)
        if exp is None:
            self.fail(kind, ref, quote, "<no WEB rows / unknown book>"); return
        q = norm(quote).strip('"').strip()
        if q not in exp:
            self.fail(kind, ref, q, exp)

def run(path):
    doc = open(path, encoding="utf-8").read()
    con = load_db()
    v = Verifier(con)

    # A. Reader chapter sources: every verse span byte-matches WEB
    for sec in re.finditer(r'<section class="chapter-source"[^>]*data-book="([^"]+)"[^>]*data-chapter="(\d+)"[^>]*>(.*?)</section>', doc, re.S):
        book, ch, body = sec.group(1), int(sec.group(2)), sec.group(3)
        for cv in re.finditer(r'<span class="cv" data-n="(\d+)">(.*?)</span>\s*(?=<span class="cv"|$)', body, re.S):
            n = cv.group(1)
            text = strip_tags(re.sub(r'<span class="v">\d+</span>', "", cv.group(2)))
            v.check_equal("chapter-source", f"{book} {ch}:{n}", text)

    # B. Set passages: blockquote text == WEB range from figcaption .ref
    for fig in re.finditer(r'<figure class="setpass[^"]*"[^>]*>(.*?)</figure>', doc, re.S):
        block = fig.group(1)
        bq = re.search(r'<blockquote>(.*?)</blockquote>', block, re.S)
        ref = re.search(r'<span class="ref">(.*?)</span>', block, re.S)
        if bq and ref:
            text = strip_tags(re.sub(r'<span class="v">\d+</span>', "", bq.group(1)))
            v.check_equal("set-passage", html.unescape(strip_tags(ref.group(1))), text)

    # C. Inline doors (arc + conversation): quoted snippet is a substring of WEB range
    for door in re.finditer(r'<(?:button|a) class="door"[^>]*>(.*?)<span class="door-ref">(.*?)</span>\s*</(?:button|a)>', doc, re.S):
        quote = strip_tags(door.group(1)).strip().strip('“”"')
        ref = html.unescape(strip_tags(door.group(2)))
        v.check_substring("inline-door", ref, quote)

    # D. JSON-LD FAQ answers: each "quote" (Reference) is a substring of WEB range
    for blk in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
        try:
            data = json.loads(blk.group(1))
        except json.JSONDecodeError as e:
            v.fail("json-ld", "(parse)", str(e), "valid JSON"); continue
        if data.get("@type") == "FAQPage":
            for qa in data.get("mainEntity", []):
                ans = qa.get("acceptedAnswer", {}).get("text", "")
                for mq in re.finditer(r'"([^"]+)"\s*\(([^)]+)\)', ans):
                    v.check_substring("faq-answer", mq.group(2), mq.group(1))

    print(f"scripture: checked {v.checked} fragments in {os.path.relpath(path, REPO)}")
    if v.fails:
        print(f"\nFAILED — {len(v.fails)} mismatch(es):\n")
        for kind, ref, got, exp in v.fails:
            print(f"  [{kind}] {ref}")
            print(f"      page: {got!r}")
            print(f"      WEB : {exp!r}\n")
        return 1
    print("OK — every quoted fragment byte-matches the local WEB source.")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("usage: verify-scripture.py topics/<slug>/index.html\n"); sys.exit(2)
    sys.exit(run(sys.argv[1]))
