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

# Referrer domains Apple reports, mapped to the Marketing sheet's Medium names.
# Everything not listed collapses into "Other".
SOURCE_CHANNELS = {
    "reddit.com": "Reddit",
    "news.ycombinator.com": "HackerNews",
    "linkedin.com": "LinkedIn",
    "lnkd.in": "LinkedIn",
}


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
