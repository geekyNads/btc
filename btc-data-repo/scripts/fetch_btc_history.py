#!/usr/bin/env python3
"""
Backfill historical BTC/USDT OHLCV data from Binance's public REST API.

No API key required. Paginates automatically (Binance caps each response at
1000 candles) and stays well under public rate limits.

Usage:
    python scripts/fetch_btc_history.py --interval 1h --start 2026-01-01 --end 2026-09-10 --out data/btc_1h_2026.csv
    python scripts/fetch_btc_history.py --interval 1m --start 2026-01-01 --end 2026-09-10 --out data/btc_1m_2026.csv

Supported --interval values: 1m, 1h, 1d (1s is also technically supported by
Binance but only for very recent history -- see README for why full-year
per-second backfill isn't realistically available from any provider).
"""
import argparse
import csv
import time
from datetime import datetime, timezone
import requests

BASE_URL = "https://api.binance.com/api/v3/klines"
SYMBOL = "BTCUSDT"
MAX_LIMIT = 1000

INTERVAL_MS = {
    "1s": 1_000,
    "1m": 60_000,
    "1h": 3_600_000,
    "1d": 86_400_000,
}


def to_ms(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def fetch_klines(symbol, interval, start_ms, end_ms, session):
    """Fetch all klines between start_ms and end_ms, paginating as needed."""
    rows = []
    cursor = start_ms
    step_ms = INTERVAL_MS[interval] * MAX_LIMIT

    while cursor < end_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": cursor,
            "endTime": min(cursor + step_ms, end_ms),
            "limit": MAX_LIMIT,
        }
        resp = session.get(BASE_URL, params=params, timeout=15)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            print(f"Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue

        resp.raise_for_status()
        batch = resp.json()

        if not batch:
            cursor += step_ms
            continue

        rows.extend(batch)
        last_open_time = batch[-1][0]
        cursor = last_open_time + INTERVAL_MS[interval]

        last_dt = datetime.fromtimestamp(last_open_time / 1000, tz=timezone.utc)
        print(f"Fetched {len(batch)} candles, up to {last_dt.isoformat()}")

        time.sleep(0.25)  # be polite to the API

    return rows


def write_csv(rows, out_path):
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "open_time_ms", "open", "high", "low", "close", "volume"])
        for r in rows:
            open_time_ms = r[0]
            ts = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc).isoformat()
            writer.writerow([ts, open_time_ms, r[1], r[2], r[3], r[4], r[5]])
    print(f"Wrote {len(rows)} rows to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Backfill BTC OHLCV data from Binance")
    parser.add_argument("--interval", choices=list(INTERVAL_MS.keys()), default="1h")
    parser.add_argument("--start", default="2026-01-01", help="YYYY-MM-DD (UTC)")
    parser.add_argument("--end", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"), help="YYYY-MM-DD (UTC)")
    parser.add_argument("--symbol", default=SYMBOL)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    start_ms = to_ms(args.start)
    end_ms = to_ms(args.end)

    session = requests.Session()
    rows = fetch_klines(args.symbol, args.interval, start_ms, end_ms, session)
    write_csv(rows, args.out)


if __name__ == "__main__":
    main()
