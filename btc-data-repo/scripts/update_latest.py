#!/usr/bin/env python3
"""
Append the newest BTC candles to the existing CSVs. Designed to run on a
schedule (see .github/workflows/update-btc-data.yml) so the dataset keeps
growing without a full re-backfill each time.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

import requests

from fetch_btc_history import SYMBOL, INTERVAL_MS, fetch_klines

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

FILES = {
    "1h": DATA_DIR / "btc_1h_2026.csv",
    "1m": DATA_DIR / "btc_1m_2026.csv",
}

DEFAULT_START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def last_open_time_ms(path):
    if not path.exists():
        return None
    with open(path, "r") as f:
        rows = list(csv.reader(f))
    if len(rows) <= 1:
        return None
    return int(rows[-1][1])


def append_csv(path, rows):
    write_header = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp_utc", "open_time_ms", "open", "high", "low", "close", "volume"])
        for r in rows:
            open_time_ms = r[0]
            ts = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc).isoformat()
            writer.writerow([ts, open_time_ms, r[1], r[2], r[3], r[4], r[5]])


def main():
    session = requests.Session()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    for interval, path in FILES.items():
        last_ms = last_open_time_ms(path)
        start_ms = (last_ms + INTERVAL_MS[interval]) if last_ms else int(DEFAULT_START.timestamp() * 1000)

        if start_ms >= now_ms:
            print(f"{interval}: already up to date")
            continue

        rows = fetch_klines(SYMBOL, interval, start_ms, now_ms, session)
        if rows:
            append_csv(path, rows)
            print(f"{interval}: appended {len(rows)} rows")
        else:
            print(f"{interval}: no new rows")


if __name__ == "__main__":
    main()
