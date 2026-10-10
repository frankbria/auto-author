#!/usr/bin/env python3
"""Staging health probe (#916): the API health check plus the frontend root.

No AI, no auth, public URLs only. It catches infra drift between deploys (the
#537 Atlas credential outage left /health answering 503 for days) now that the
E2E suite only runs after a deploy. The API must answer 200 with
{"status": "healthy"}; the frontend root must answer 200. Each attempt checks
both; it exits 0 on the first fully healthy attempt and 1 after the last.

Run: python3 scripts/staging_health_probe.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("API_HEALTH_URL", "https://api.dev.autoauthor.app/api/v1/health")
FRONTEND = os.environ.get("FRONTEND_URL", "https://dev.autoauthor.app/")
ATTEMPTS = int(os.environ.get("PROBE_ATTEMPTS", "3"))
DELAY = float(os.environ.get("PROBE_DELAY", "20"))


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as res:
            return res.status, res.read(500).decode(errors="replace")
    except urllib.error.HTTPError as err:
        return err.code, err.read(500).decode(errors="replace")
    except OSError as err:  # refused, DNS, TLS, timeout (URLError is an OSError)
        return None, str(err)


def problems():
    found = []
    status, body = fetch(API)
    try:
        verdict = json.loads(body).get("status")
    except (ValueError, AttributeError):
        verdict = None
    if status != 200 or verdict != "healthy":
        found.append(f"{API} -> {status} {body!r}")
    status, body = fetch(FRONTEND)
    if status != 200:
        found.append(f"{FRONTEND} -> {status} {body[:200]!r}")
    return found


def main():
    for attempt in range(1, ATTEMPTS + 1):
        found = problems()
        if not found:
            print(f"healthy: {API} and {FRONTEND} (attempt {attempt}/{ATTEMPTS})")
            return 0
        print(f"attempt {attempt}/{ATTEMPTS} failed: " + "; ".join(found))
        if attempt < ATTEMPTS:
            time.sleep(DELAY)
    return 1


if __name__ == "__main__":
    sys.exit(main())
