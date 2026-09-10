# btc

Historical and continuously-updating BTC/USDT price data for 2026, sourced
from Binance's public REST API (no API key required).

## What's in here

- `scripts/fetch_btc_history.py` — one-time backfill script. Paginates
  through Binance's klines endpoint and writes a CSV.
- `scripts/update_latest.py` — incremental updater. Looks at the last
  timestamp already saved and only fetches what's new. This is what the
  scheduled workflow calls.
- `.github/workflows/update-btc-data.yml` — runs `update_latest.py` every
  hour on GitHub's own servers and commits any new rows automatically.
- `data/` — the CSVs live here once you generate them.

## 1. Backfill 2026 so far

```bash
pip install -r requirements.txt

python scripts/fetch_btc_history.py --interval 1h --start 2026-01-01 --end $(date -u +%F) --out data/btc_1h_2026.csv
python scripts/fetch_btc_history.py --interval 1m --start 2026-01-01 --end $(date -u +%F) --out data/btc_1m_2026.csv
```

- `1h` for Jan 1 – now is a few thousand rows, finishes in seconds.
- `1m` for the same range is roughly 350,000+ rows and will take a few
  minutes because of pagination and the polite rate-limit delay.

Commit the resulting CSVs and push:

```bash
git add data/ requirements.txt scripts/ .github/
git commit -m "Backfill 2026 BTC price history"
git push
```

## 2. Keep it updating automatically

Once the workflow file is pushed to your default branch, GitHub Actions
will run `update_latest.py` every hour, append any new candles to the
existing CSVs, and commit/push the changes for you — no server of your own
needed. You can also trigger it manually from the **Actions** tab
("Run workflow").

If you'd rather update from your own machine/cron instead of GitHub
Actions, just run:

```bash
python scripts/update_latest.py
git add data/ && git commit -m "Update BTC data" && git push
```

## About "every second"

True second-by-second BTC price data for the *whole* year isn't something
any provider (Binance included) makes available as a historical backfill —
exchanges only retain 1-second klines for a short recent rolling window
(days, not months), and full tick-level history is generally a paid
product. `INTERVAL_MS` in `fetch_btc_history.py` does include `1s` if you
want to experiment with a recent short window, but for a durable, complete
2026 dataset, minute/hour resolution is the realistic option — that's
what's wired up here.

If you later want genuine per-second granularity *going forward*, the
cleanest approach is a small always-on process (not GitHub Actions, which
only supports schedules down to ~1 minute intervals in practice) that
subscribes to Binance's WebSocket trade stream and appends every tick.
Happy to build that separately if you want it.

## Data source & disclaimer

Data comes from Binance's public market data API (BTCUSDT pair). This is
exchange trade data, not a blended "market price" — fine for most personal
projects, but worth noting if you need a specific index/reference price
methodology.
