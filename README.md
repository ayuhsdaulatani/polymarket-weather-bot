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
3. **Forecast** — fetch Open-Meteo's forecast high temp for that city and date
   (`src/openmeteo_client.py`)
4. **Edge calculation** — model each bucket's probability as a normal distribution centered on
   the forecast, and compare it to the market price. If the market is in the "sweet spot"
   (60-85% priced) and the model/market gap exceeds a threshold, it's flagged as a pick
   (`src/edge_engine.py`)
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

## Run tests

```bash
python -m pytest
```

## Strategy notes

- **Sweet spot:** only consider markets priced 60-85% (`EDGE_MIN_PRICE` / `EDGE_MAX_PRICE` in
  `src/config.py`) — enough payout to be worth it, with a real lean either way
- **Minimum edge:** model probability must differ from market price by at least `MIN_EDGE`
  (default 0.10) to be flagged
- Each bucket's probability is `P(low - 0.5 <= forecast_high <= high + 0.5)` under a normal
  distribution centered on Open-Meteo's forecasted high, with an assumed std dev of
  `TEMP_STD_DEV` degrees (`src/edge_engine.py`)

## Known limitations

- **Single-degree °C buckets (Seoul, Shanghai, etc.)** can show large "NO" edges that are
  likely false positives: a 1°C-wide bucket can almost never reach 60%+ probability under a
  normal-distribution model, so any such bucket priced in the sweet spot will look like a huge
  edge even when it isn't. These markets likely round to wider bands than their label
  suggests — needs verification against actual resolution rules before treating these as real
  picks.
- City matching is substring-based on `CITY_COORDS` — ambiguous or unlisted cities are
  silently skipped.

## Roadmap

- [ ] Verify resolution rules for non-US (°C) temperature events and fix bucket width
      assumptions accordingly
- [ ] Tune `TEMP_STD_DEV` against historical forecast accuracy per city
- [ ] Add a daily scheduled run (cron / Claude Code routine)
- [ ] Optional: auto-post picks to Gmail/Drive (see Polymarket System notes)
