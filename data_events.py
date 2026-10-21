"""
Retrieve GENOME events between a set of countries and aggregate them per month.

All outputs are 3D arrays with shape [month, actor country, recipient country]
(except the *_period arrays, which are summed over the whole period: [actor, recipient]).

The country order follows `landen`, the month order follows the period start..eind.
Page 1 of every request (max. 250 events) is free; additional pages require an API key
and cost 1 credit per event.

Requires: pip install requests numpy pandas
"""

import calendar
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

BASE = "https://genome.app.hcss.nl/api"
MAX_EVENTS = 2000      # safeguard: more events for one pair in one month means the filter failed
WORKERS = 5            # parallel requests (keep low to avoid overloading the server)


def _country_ids(session, landen):
    """Map ISO-2 codes to GENOME country ids."""
    r = session.get(f"{BASE}/countries", timeout=60)
    r.raise_for_status()
    data = r.json()
    countries = data["countries"] if isinstance(data, dict) else data

    iso2_to_id = {}
    for c in countries:
        code = c.get("iso_alpha2")
        if code:
            # duplicate codes exist for historical states (e.g. 'German Federal Republic');
            # the lowest id is the current state
            iso2_to_id[code] = min(c["id"], iso2_to_id.get(code, c["id"]))

    missing = [l for l in landen if l not in iso2_to_id]
    if missing:
        raise ValueError(f"Unknown country code(s) in GENOME: {missing}")
    return [iso2_to_id[l] for l in landen]


def _fetch_events(session, api_key, actor_id, recipient_id, date_from, date_to):
    """All events from actor to recipient between two dates (handles pagination)."""
    params = {
        "actor_country_id": actor_id,
        "recipient_country_id": recipient_id,
        "event_date_from": date_from,
        "event_date_to": date_to,
        "page": 1,
    }
    r = session.get(f"{BASE}/events", params=params, timeout=60)     # page 1: free
    r.raise_for_status()
    first = r.json()
    events = list(first["events"])

    if first["total"] > MAX_EVENTS:
        raise RuntimeError(
            f"{first['total']} events for one pair in one month: the country filter "
            "does not seem to work. Stopped to save credits.")

    for page in range(2, first["total_pages"] + 1):                  # extra pages: API key
        if not api_key:
            print(f"  {first['total']} events, but only the first 250 without an API key")
            break
        r = session.get(f"{BASE}/events", params={**params, "page": page},
                        headers={"x-api-key": api_key}, timeout=60)
        if r.status_code == 402:
            print("  Out of credits:", r.json().get("detail"))
            break
        r.raise_for_status()
        events.extend(r.json()["events"])
        time.sleep(0.3)
    return events


def _role_ids(role):
    """Set of country ids for one role (actor / recipient) of an event."""
    return {c["id"] for c in (role or {}).get("countries", []) if c.get("id") is not None}


def data_genome(api_key, landen, start, eind):
    """
    Returns (in this order):
        ev_count_period      [A, B]     number of events over the whole period
        ev_intensity_period  [A, B]     summed intensity over the whole period
        ev_intensity_sum     [T, A, B]  summed intensity per month
        ev_intensity_mean    [T, A, B]  mean intensity per event per month (NaN if no events)
        ev_count             [T, A, B]  number of events per month
        ev_conflict          [T, A, B]  number of CONFLICT events per month
        ev_coop              [T, A, B]  number of COOPERATION events per month
    """
    session = requests.Session()
    months = pd.period_range(start, eind, freq="M").strftime("%Y-%m").tolist()
    ids = _country_ids(session, landen)
    print("GENOME ids:", dict(zip(landen, ids)))

    T, N = len(months), len(landen)
    ev_count = np.zeros((T, N, N))
    ev_intensity_sum = np.zeros((T, N, N))
    ev_conflict = np.zeros((T, N, N))
    ev_coop = np.zeros((T, N, N))
    ev_intensity_mean = np.full((T, N, N), np.nan)

    # one task per (month, actor, recipient)
    tasks = []
    for t, month in enumerate(months):
        y, m = map(int, month.split("-"))
        date_from = f"{month}-01"
        date_to = f"{month}-{calendar.monthrange(y, m)[1]:02d}"
        for a in range(N):
            for b in range(N):
                if a != b:
                    tasks.append((t, a, b, date_from, date_to))

    def run(task):
        t, a, b, date_from, date_to = task
        events = _fetch_events(session, api_key, ids[a], ids[b], date_from, date_to)
        # keep only events where A really is an actor and B really is a recipient
        events = [e for e in events
                  if ids[a] in _role_ids(e.get("actor"))
                  and ids[b] in _role_ids(e.get("recipient"))]
        return task, events

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for k, (task, events) in enumerate(pool.map(run, tasks), 1):
            t, a, b, _, _ = task
            intensities = [e["intensity"] for e in events if e.get("intensity") is not None]
            ev_count[t, a, b] = len(events)
            ev_intensity_sum[t, a, b] = sum(intensities)
            ev_conflict[t, a, b] = sum(e["category"] == "CONFLICT" for e in events)
            ev_coop[t, a, b] = sum(e["category"] == "COOPERATION" for e in events)
            if intensities:
                ev_intensity_mean[t, a, b] = np.mean(intensities)
            if k % 50 == 0 or k == len(tasks):
                print(f"  {k}/{len(tasks)} requests done")

    ev_count_period = ev_count.sum(axis=0)
    ev_intensity_period = ev_intensity_sum.sum(axis=0)
    return (ev_count_period, ev_intensity_period, ev_intensity_sum, ev_intensity_mean,
            ev_count, ev_conflict, ev_coop)