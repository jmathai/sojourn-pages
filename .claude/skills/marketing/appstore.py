# Pulls App Store Connect analytics (daily downloads and engagement, broken down by source).
# Authenticates with an individual App Store Connect API key (sub:"user", no issuer id).
import csv
import gzip
import io
import json
import time
import urllib.request
from pathlib import Path

import jwt

ASC_DIR = Path(__file__).resolve().parents[3] / ".appstoreconnect"
KEY_JSON = ASC_DIR / "key.json"
STATE_JSON = ASC_DIR / "state.json"
BASE = "https://api.appstoreconnect.apple.com"

DOWNLOADS_REPORT = "App Downloads Detailed"
ENGAGEMENT_REPORT = "App Store Discovery and Engagement Detailed"

# Apple's download Source Type, mapped to the App Store tab's source columns.
# Apple only exposes the referrer domain (Reddit vs LinkedIn) in the privacy-
# thresholded Detailed report, which withholds it at low volume, so downloads are
# attributed by Source Type instead. Anything unlisted collapses into "Other" so the
# columns always sum to first-time downloads.
SOURCE_TYPES = {
    "app store search": "App Store Search",
    "app store browse": "App Store Browse",
    "web referrer": "Web Referrer",
    "app referrer": "App Referrer",
}
SOURCE_COLUMNS = ("App Store Search", "App Store Browse", "Web Referrer", "App Referrer", "Other")


def _config():
    return json.loads(KEY_JSON.read_text()), json.loads(STATE_JSON.read_text())


def _token(key_id):
    now = int(time.time())
    p8 = ASC_DIR / "private_keys" / f"ApiKey_{key_id}.p8"
    return jwt.encode(
        {"sub": "user", "iat": now, "exp": now + 300, "aud": "appstoreconnect-v1"},
        p8.read_text(), algorithm="ES256", headers={"kid": key_id, "typ": "JWT"},
    )


def _call(key_id, path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + _token(key_id)})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _report_ids(key_id, request_id):
    data = _call(key_id, f"/v1/analyticsReportRequests/{request_id}/reports?limit=200")
    return {r["attributes"]["name"]: r["id"] for r in data.get("data", [])}


def _daily_instances(key_id, report_id):
    data = _call(
        key_id,
        f"/v1/analyticsReports/{report_id}/instances?limit=200&filter%5Bgranularity%5D=DAILY",
    )
    return data.get("data", [])


def _download_instance(key_id, instance_id):
    rows = []
    segs = _call(key_id, f"/v1/analyticsReportInstances/{instance_id}/segments")
    for seg in segs.get("data", []):
        raw = urllib.request.urlopen(seg["attributes"]["url"], timeout=120).read()
        text = gzip.decompress(raw).decode("utf-8", "replace")
        rows.extend(csv.DictReader(io.StringIO(text), delimiter="\t"))
    return rows


def instance_count():
    """DAILY report instances available across both requests. 0 while Apple is still provisioning."""
    key, state = _config()
    kid = key["key_id"]
    total = 0
    for request_id in (state.get("ongoing_request_id"), state.get("snapshot_request_id")):
        if not request_id:
            continue
        for report_id in _report_ids(kid, request_id).values():
            total += len(_daily_instances(kid, report_id))
    return total


# The Standard reports carry the complete daily aggregates (totals and Source Type),
# and stay a step ahead of the privacy-thresholded Detailed reports. Everything the
# App Store tab needs comes from these two.
DOWNLOADS_STANDARD = "App Downloads Standard"
ENGAGEMENT_STANDARD = "App Store Discovery and Engagement Standard"


def _source(row):
    """Map a download row's Apple Source Type to a source column, else 'Other'."""
    return SOURCE_TYPES.get((row.get("Source Type") or "").strip().lower(), "Other")


def _instances(kid, state, name, _cache={}):
    """Every DAILY instance of a report across both requests, as (processingDate, id)."""
    out = []
    for request_id in (state.get("snapshot_request_id"), state.get("ongoing_request_id")):
        if not request_id:
            continue
        reports = _cache.get(request_id)
        if reports is None:
            reports = _cache[request_id] = _report_ids(kid, request_id)
        report_id = reports.get(name)
        if not report_id:
            continue
        for inst in _daily_instances(kid, report_id):
            out.append((inst["attributes"].get("processingDate", ""), inst["id"]))
    return sorted(out, key=lambda t: t[0])


def daily_rows():
    """Aggregate the analytics reports into one metrics dict per calendar date.

    Each instance holds a rolling window of dates; instances are applied oldest
    processingDate first so a newer regeneration overwrites (never double-counts)
    an overlapping date.
    """
    key, state = _config()
    kid = key["key_id"]

    # Daily totals and Source Type attribution from the Standard report, which is
    # complete and freshest. First-time downloads are bucketed by Source Type, so the
    # source buckets always sum to the first-time total.
    downloads = {}
    for _, iid in _instances(kid, state, DOWNLOADS_STANDARD):
        window = {}
        for r in _download_instance(kid, iid):
            slot = window.setdefault(r["Date"], {"first": 0, "redownloads": 0, "sources": {}})
            count = int(r.get("Counts") or 0)
            dtype = r.get("Download Type")
            if dtype == "First-time download":
                slot["first"] += count
                bucket = _source(r)
                slot["sources"][bucket] = slot["sources"].get(bucket, 0) + count
            elif dtype == "Redownload":
                slot["redownloads"] += count
        downloads.update(window)

    engagement = {}
    for _, iid in _instances(kid, state, ENGAGEMENT_STANDARD):
        window = {}
        for r in _download_instance(kid, iid):
            slot = window.setdefault(r["Date"], {"impressions": 0, "page_views": 0})
            count = int(r.get("Counts") or 0)
            if r.get("Event") == "Impression":
                slot["impressions"] += count
            elif r.get("Event") == "Page view":
                slot["page_views"] += count
        engagement.update(window)

    rows = []
    for date in sorted(set(downloads) | set(engagement)):
        dl = downloads.get(date, {"first": 0, "redownloads": 0, "sources": {}})
        eng = engagement.get(date, {"impressions": 0, "page_views": 0})
        rows.append({
            "date": date,
            "impressions": eng["impressions"],
            "page_views": eng["page_views"],
            "first_time_downloads": dl["first"],
            "redownloads": dl["redownloads"],
            "sources": dl["sources"],
        })
    return rows
