# Polymarket Weather Bot

An analysis bot that finds mispriced weather markets on [Polymarket](https://polymarket.com) by
comparing the market's implied probability against an actual weather forecast from
[Open-Meteo](https://open-meteo.com) (free, no API key required).

This is a **signal/analysis bot** — it does not place bets automatically. It outputs a daily
report of recommended picks with reasoning.

## How it works

1. **Fetch markets** — pull active weather-related markets from the Polymarket gamma API
   (`src/polymarket_client.py`)
2. **Parse** — extract city, target date, and condition (rain / temp above / temp below) from
   each market's question (`src/parser.py`)
3. **Forecast** — fetch Open-Meteo's forecast for that city and date (`src/openmeteo_client.py`)
4. **Edge calculation** — compute a model probability from the forecast and compare it to the
   market price. If the gap exceeds a threshold and the market is in the "sweet spot"
   (60-85% priced), it's flagged as a pick (`src/edge_engine.py`)
5. **Report** — write ranked picks to `data/output/YYYY-MM-DD.md` and `.json`
   (`src/main.py`)

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
- Temperature predictions use a normal distribution around Open-Meteo's forecasted high/low
  with an assumed ±4°F std dev (`TEMP_STD_DEV_F`)

## Roadmap

- [ ] Expand city list / improve question parsing for more market phrasings
- [ ] Tune `TEMP_STD_DEV_F` against historical forecast accuracy
- [ ] Add a daily scheduled run (cron / Claude Code routine)
- [ ] Optional: auto-post picks to Gmail/Drive (see Polymarket System notes)
