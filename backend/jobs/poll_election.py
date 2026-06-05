#!/usr/bin/env python3
"""Store an election-results snapshot — from the upstream API or a manual file.

Two modes:
  * API mode (no args): run on the 4-minute systemd timer. Fetches
    ELECTION_API_URL (optionally via ELECTION_API_PROXY), validates, and stores
    a snapshot when the data changed. If ELECTION_API_URL is unset, exits 0 —
    the pipeline stays dormant until the real API + Armenia routing exist.

  * Manual mode (--file PATH): load a JSON array from PATH ('-' = stdin),
    validate it, and store it as a source='manual' snapshot. Use this to update
    the public /election JSON by hand while the API isn't available yet, e.g.:
        python jobs/poll_election.py --file - < feed.json

Both modes share the store-only-on-change rule (skips insert if identical to the
most recent snapshot) and the same shape validation.

Exit codes: 0 = stored / skipped-unchanged / not-configured; 1 = error.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

# Mirror main.py: make `database` importable when run as a standalone script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[poll_election {ts}] {msg}", flush=True)


def canonical(parties):
    """Stable serialization so identical data always hashes identically."""
    return json.dumps(parties, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate(data):
    """Loose shape check: a non-empty list of party objects with vote fields."""
    if not isinstance(data, list) or not data:
        raise ValueError("payload is not a non-empty JSON array")
    for i, party in enumerate(data):
        if not isinstance(party, dict):
            raise ValueError(f"party[{i}] is not an object")
        if "votes" not in party and "percent" not in party:
            raise ValueError(f"party[{i}] missing 'votes'/'percent' — unexpected shape")
    return data


def fetch(url, proxy, timeout, headers):
    import requests  # imported lazily so the rest is testable without the dep

    proxies = {"http": proxy, "https": proxy} if proxy else None
    resp = requests.get(url, proxies=proxies, headers=headers or None, timeout=timeout)
    return resp.status_code, resp.json()


def latest_hash(db):
    row = db.execute(
        "SELECT content_hash FROM election_snapshots ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row["content_hash"] if row else None


def store(parties, source, http_status):
    """Insert a snapshot unless it is identical to the most recent one."""
    payload = canonical(parties)
    content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    db = get_db()
    try:
        if latest_hash(db) == content_hash:
            log(f"unchanged ({len(parties)} parties, hash {content_hash[:12]}) — skip insert.")
            return 0
        db.execute(
            "INSERT INTO election_snapshots (fetched_at, source, payload, content_hash, http_status) "
            "VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), source, payload, content_hash, http_status),
        )
        db.commit()
        log(f"stored {source} snapshot: {len(parties)} parties, hash {content_hash[:12]}.")
        return 0
    finally:
        db.close()


def run_manual(path):
    try:
        text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        parties = validate(json.loads(text))
    except (OSError, json.JSONDecodeError, ValueError) as e:
        log(f"ERROR: cannot load manual file {path!r}: {e}")
        return 1
    return store(parties, "manual", None)


def load_config():
    """Read CMS-managed config from election_config; tolerant if table absent."""
    try:
        db = get_db()
        try:
            row = db.execute(
                "SELECT source_mode, api_url, api_proxy, api_headers, api_timeout "
                "FROM election_config WHERE id = 1"
            ).fetchone()
            return dict(row) if row else {}
        finally:
            db.close()
    except Exception:  # noqa: BLE001 — table may not exist on an un-migrated DB
        return {}


def run_api():
    cfg = load_config()

    # DB config wins; environment is the fallback (e.g. before the CMS is used).
    mode = (cfg.get("source_mode") or "").strip()
    if mode and mode != "api":
        log(f"source_mode='{mode}' (not 'api') — skip poll.")
        return 0

    url = (cfg.get("api_url") or os.environ.get("ELECTION_API_URL", "")).strip()
    if not url:
        log("no api_url configured (DB or env) — pipeline dormant, nothing to do.")
        return 0

    proxy = (cfg.get("api_proxy") or os.environ.get("ELECTION_API_PROXY", "")).strip()
    timeout = float(cfg.get("api_timeout") or os.environ.get("ELECTION_API_TIMEOUT", "30"))
    raw_headers = (cfg.get("api_headers") or os.environ.get("ELECTION_API_HEADERS", "")).strip()
    try:
        headers = json.loads(raw_headers) if raw_headers else None
    except json.JSONDecodeError as e:
        log(f"ERROR: api_headers is not valid JSON: {e}")
        return 1

    try:
        status, data = fetch(url, proxy, timeout, headers)
    except Exception as e:  # network / proxy / JSON decode
        log(f"ERROR: fetch failed via proxy={proxy or 'direct'}: {e!r}")
        return 1

    if status != 200:
        log(f"ERROR: upstream returned HTTP {status}")
        return 1

    try:
        parties = validate(data)
    except ValueError as e:
        log(f"ERROR: invalid payload, not storing: {e}")
        return 1

    return store(parties, "api", status)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Store an election-results snapshot.")
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="Manual mode: store a JSON array from PATH ('-' for stdin) as source='manual'.",
    )
    args = parser.parse_args(argv)
    return run_manual(args.file) if args.file else run_api()


if __name__ == "__main__":
    sys.exit(main())
