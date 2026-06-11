# Polymarket Weather Bot

An analysis bot that finds mispriced "Highest temperature in [City] on [date]?" markets on
[Polymarket](https://polymarket.com) by comparing each degree-bucket's price against an actual
weather forecast from [Open-Meteo](https://open-meteo.com) (free, no API key required).

This is a **signal/analysis bot** — it does not place bets automatically. It outputs a daily
report of recommended picks with reasoning.

## How it works

1. **Fetch events** — pull active "Highest temperature in X on Y?" events from the Polymarket
   gamma public-search API (`src/polymarket_client.py`)
2. **Parse** — extract the city, target date, and each temperature bucket (e.g. "88-89°F",
   "87°F or below") from the event's markets (`src/parser.py`)
3. **Forecast** — fetch a 6-model ensemble forecast (ECMWF, GFS, ICON, GEM, JMA, Meteo-France)
   from Open-Meteo and combine them with a weighted median, with per-city model weights and
   bias correction applied (`src/forecast_ensemble.py`, `src/openmeteo_client.py`)
4. **Edge calculation** — model each bucket's probability as a normal distribution centered on
   the (bias-corrected) forecast, using a per-city standard deviation, and compare it to the
   market price. If the market is in the "sweet spot" (60-85% priced) and the model/market gap
   exceeds a threshold, it's flagged as a pick (`src/edge_engine.py`)
5. **Report** — write ranked picks to `data/output/YYYY-MM-DD.md` and `.json` (`src/main.py`)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Run

```bash
python -m src.main
```

### Streamlit app

```bash
streamlit run app.py
```

Shows "Today's Picks" (top edge picks across all tradeable cities), a per-city highest-temp
forecast table with the best matching bucket, and an experimental edge-picks explorer.

## Run tests

```bash
python -m pytest
```

## Run the backtest

```bash
python scripts/backtest.py
```

Pulls ~90 days of Open-Meteo's previous-runs forecast history (`temperature_2m_previous_dayN`)
and compares it against the archive API's actual observed highs, per city and per model. Used
to derive the ensemble weights, bias corrections, and std-dev tables in `src/config.py` below.

## Strategy notes

- **Sweet spot:** only consider markets priced 60-85% (`EDGE_MIN_PRICE` / `EDGE_MAX_PRICE` in
  `src/config.py`) — enough payout to be worth it, with a real lean either way
- **Minimum edge:** model probability must differ from market price by at least `MIN_EDGE`
  (default 0.10) to be flagged
- Each bucket's probability is `P(low - 0.5 <= forecast_high <= high + 0.5)` under a normal
  distribution centered on the bias-corrected ensemble forecast, with a per-city,
  per-lead-time standard deviation (`src/edge_engine.py`, `bucket_probability_with_std`)

### Backtest-derived tuning (90-day, per city)

- **Per-city model weights** (`CITY_MODEL_WEIGHTS`): ICON dropped for LA/SF (badly biased low,
  especially SF's marine layer), GEM also dropped for SF, GEM halved for NYC (worst model
  there). Other tradeable cities use the default US weight set.
- **Per-city bias correction** (`CITY_BIAS_CORRECTION_F`): the weighted-median forecast is
  adjusted by `-(measured mean error)` per city and lead day (0-4), so it's unbiased on
  average. Cities without a table fall back to a flat global correction.
- **Per-city std dev by lead time** (`CITY_STD_DEV_BY_LEAD_DAYS` /
  `CITY_STD_DEV_MAX_LEAD`): bucket probabilities use each city's measured forecast error
  instead of one global number. Miami is tight and well-behaved (~1-2.1°F across leads); NYC
  and SF are much wider and noisier at multi-day leads (up to ~4.5-4.7°F).
- **Skewness check**: forecast errors were checked for skew and found modest/inconsistent
  (-0.83 to +0.88 across cities) — not significant enough to justify a skew-normal model, so
  errors are still treated as normal.
- **Same-day observed-high floor**: for "today" markets, `observed_high_so_far()` checks
  hourly temps already recorded today (converted to local time via `utc_offset_seconds`) and
  floors the forecast at that value, since the day's actual high can't be lower than what's
  already happened.

## Known limitations

- **Single-degree °C buckets (Seoul, Shanghai, etc.)** can show large "NO" edges that are
  likely false positives: a 1°C-wide bucket can almost never reach 60%+ probability under a
  normal-distribution model, so any such bucket priced in the sweet spot will look like a huge
  edge even when it isn't. These markets likely round to wider bands than their label
  suggests — needs verification against actual resolution rules before treating these as real
  picks.
- City matching is substring-based on `CITY_COORDS` — ambiguous or unlisted cities are
  silently skipped.
- Per-city bias/std-dev/model-weight tuning only covers the `TRADEABLE_CITIES` set
  (NYC, Miami, Chicago, LA, SF) — other cities use global defaults.

## Roadmap

- [ ] Verify resolution rules for non-US (°C) temperature events and fix bucket width
      assumptions accordingly
- [ ] Re-run the backtest periodically (forecast accuracy drifts with seasons)
- [ ] Add a daily scheduled run (cron / Claude Code routine)
- [ ] Optional: auto-post picks to Gmail/Drive (see Polymarket System notes)
