#!/usr/bin/env python3
"""Schema for the "Reddit Posts" tab: header, Status dropdown, colors, layout.

Both post_rows.py (which fills the tab) and apply_rows.py (which acts on it) import
this, so the two can never disagree about which column means what. Running it directly
re-applies the schema, which is safe at any time:

    ../marketing/.venv/bin/python tab.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARKETING = HERE.parent / "marketing"
sys.path.insert(0, str(MARKETING))

import sheet as marketing_sheet  # noqa: E402  (path must be set first)

TAB = "Reddit Posts"
HEADER = ["Url", "Title of reddit post", "Title of comment", "Response", "Status", "Result"]

# Column indexes (0-based), named so the scripts read clearly.
COL_URL, COL_POST, COL_COMMENT, COL_RESPONSE, COL_STATUS, COL_RESULT = range(6)

PENDING, SKIP, APPLY, POSTED, FAILED = "Pending", "Skip", "Apply", "Posted", "Failed"

# Pending/Skip/Apply are the three you set by hand. Posted and Failed are written by
# apply_rows.py so an unattended re-run can tell what it already did: without a
# terminal state, a second run would comment twice on the same thread.
STATUSES = [PENDING, SKIP, APPLY, POSTED, FAILED]

STATUS_COLORS = {
    PENDING: (1.00, 0.95, 0.80),   # amber: waiting on you
    SKIP:    (0.91, 0.91, 0.91),   # grey: deliberately passed over
    APPLY:   (0.83, 0.93, 0.84),   # green: cleared to post
    POSTED:  (0.81, 0.89, 0.95),   # blue: done, see Result
    FAILED:  (0.97, 0.84, 0.86),   # red: see Result for why
}


def read(ws=None):
    """Rows of the tab with formulas intact, padded to the header width.

    Reading with the default render option would hand back the *display* text of the Url
    column ("r/Christianity") instead of the HYPERLINK formula holding the real
    permalink. Everything downstream needs the permalink, so every reader goes through
    here: dedupe silently stops working otherwise, and the poster would mark good rows
    Failed for having an "unusable url".
    """
    ws = ws or marketing_sheet.worksheet(TAB)
    try:
        rows = ws.get_all_values(value_render_option="FORMULA")
    except TypeError:  # older gspread: same thing through get()
        rows = ws.get(value_render_option="FORMULA")
    return [list(r) + [""] * (len(HEADER) - len(r)) for r in rows]


def url_of(cell):
    """The permalink in a Url cell, whether it holds a HYPERLINK formula or a bare URL."""
    cell = (cell or "").strip()
    m = re.search(r'HYPERLINK\(\s*"([^"]+)"', cell, re.I)
    return m.group(1) if m else cell


def ensure(ws=None):
    """Apply the schema to the tab. Idempotent: safe to call on every write."""
    ws = ws or marketing_sheet.worksheet(TAB)
    values = ws.get_all_values()
    first = values[0] if values else []

    if [c.strip() for c in first[: len(HEADER)]] != HEADER:
        ws.update(values=[HEADER], range_name="A1:F1", value_input_option="USER_ENTERED")

    sid = ws.id
    last = max(ws.row_count, 1000)
    requests = [
        # Freeze the header so long drafts stay readable while scrolling.
        {"updateSheetProperties": {
            "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount"}},
        {"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold"}},
        # The Status dropdown. strict+showCustomUi is what renders it as a chip list
        # rather than a free-text cell, so a typo can't silently mean "do nothing".
        {"setDataValidation": {
            "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": last,
                      "startColumnIndex": COL_STATUS, "endColumnIndex": COL_STATUS + 1},
            "rule": {
                "condition": {"type": "ONE_OF_LIST",
                              "values": [{"userEnteredValue": s} for s in STATUSES]},
                "strict": True, "showCustomUi": True}}},
        # Let the drafted reply wrap instead of running off the screen.
        {"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": last,
                      "startColumnIndex": COL_RESPONSE, "endColumnIndex": COL_RESPONSE + 1},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP",
                                           "verticalAlignment": "TOP"}},
            "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": COL_RESPONSE,
                      "endIndex": COL_RESPONSE + 1},
            "properties": {"pixelSize": 520}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": COL_POST,
                      "endIndex": COL_COMMENT + 1},
            "properties": {"pixelSize": 260}, "fields": "pixelSize"}},
    ]

    # Rebuild the color rules from scratch so re-running never stacks duplicates.
    existing = ws.spreadsheet.fetch_sheet_metadata().get("sheets", [])
    for s in existing:
        if s["properties"]["sheetId"] != sid:
            continue
        for i in range(len(s.get("conditionalFormats", [])) - 1, -1, -1):
            requests.append({"deleteConditionalFormatRule": {"sheetId": sid, "index": i}})

    for i, (status, (r, g, b)) in enumerate(STATUS_COLORS.items()):
        requests.append({"addConditionalFormatRule": {
            "index": i,
            "rule": {
                "ranges": [{"sheetId": sid, "startRowIndex": 1, "endRowIndex": last,
                            "startColumnIndex": COL_STATUS, "endColumnIndex": COL_STATUS + 1}],
                "booleanRule": {
                    "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": status}]},
                    "format": {"backgroundColor": {"red": r, "green": g, "blue": b}}}}}})

    ws.spreadsheet.batch_update({"requests": requests})
    return ws


if __name__ == "__main__":
    ensure()
    print(f"{TAB}: schema applied ({', '.join(STATUSES)} dropdown on column E)")
