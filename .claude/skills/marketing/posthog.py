# Pulls daily website metrics from PostHog for the trysojourn.app host.
# Authenticates with a personal API key read from the repo-root .env (POSTHOG_API_KEY).
import json
import urllib.request
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
HOST = "us.posthog.com"
SITE_HOST = "trysojourn.app"

# Website sheet column header -> PostHog event name. The order defines the columns
# after Date.
EVENTS = {
    "Page Views": "$pageview",
    "app_store_click": "app_store_click",
    "topic_reader_open": "topic_reader_open",
    "topic_peek_open": "topic_peek_open",
    "topic_handoff": "topic_handoff",
    "rageclick": "$rageclick",
}


def _key():
    if not ENV_PATH.exists():
        raise FileNotFoundError(f"No .env at {ENV_PATH} for POSTHOG_API_KEY.")
    for line in ENV_PATH.read_text().splitlines():
        if line.startswith("POSTHOG_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise KeyError("POSTHOG_API_KEY not set in .env")


def _call(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"https://{HOST}{path}", data=data, method=method,
        headers={"Authorization": "Bearer " + _key(), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _project_id(_cache={}):
    if "id" not in _cache:
        _cache["id"] = _call("/api/users/@me/")["team"]["id"]
    return _cache["id"]


def daily_rows(days=90):
    """One dict per calendar date of website metrics on the trysojourn.app host.

    Keys are the Website sheet's column headers; values are that day's event counts.
    Only days with at least one event on the host appear.
    """
    counts = ", ".join(
        f"countIf(event = '{ev}') as c{i}" for i, ev in enumerate(EVENTS.values())
    )
    query = (
        f"select toDate(timestamp) as day, {counts} from events "
        f"where properties.$host = '{SITE_HOST}' "
        f"and timestamp >= now() - interval {int(days)} day "
        f"group by day order by day"
    )
    res = _call(
        f"/api/projects/{_project_id()}/query/", "POST",
        {"query": {"kind": "HogQLQuery", "query": query}},
    )
    rows = []
    for r in res.get("results", []):
        row = {"date": r[0]}
        for i, header in enumerate(EVENTS):
            row[header] = r[i + 1]
        rows.append(row)
    return rows
