"""
Backtest the forecast-error (std dev) assumptions in src/config.py against real
historical forecast accuracy.

For each tradeable city and each model used in its ensemble, pulls Open-Meteo's
"previous runs" API (forecasts as they were actually issued N days before the
target date) and compares the ensemble's predicted daily high to the observed
daily high from the archive API. Reports the actual forecast error (mean +
std dev) per lead time, alongside the current TEMP_STD_DEV_BY_LEAD_DAYS table.

Usage:
    python -m scripts.backtest
"""

import statistics
from collections import defaultdict

import requests

from src.config import (
    CITY_COORDS,
    TEMP_STD_DEV_BY_LEAD_DAYS,
    TEMP_STD_DEV_MAX_LEAD,
    TRADEABLE_CITIES,
    model_weights_for_city as _weights_for,
)
from src.forecast_ensemble import weighted_median

PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

LEAD_DAYS = [0, 1, 2, 3, 4]
PAST_DAYS = 30


def _hourly_var(lead: int) -> str:
    return "temperature_2m" if lead == 0 else f"temperature_2m_previous_day{lead}"


def _daily_max_by_date(times: list[str], values: list[float | None]) -> dict[str, float]:
    """Collapse hourly (time, value) pairs into a per-date max, ignoring Nones."""
    by_date: dict[str, list[float]] = defaultdict(list)
    for t, v in zip(times, values):
        if v is None:
            continue
        by_date[t[:10]].append(v)
    return {d: max(vals) for d, vals in by_date.items() if vals}


def fetch_model_forecasts(lat: float, lon: float, model: str) -> dict[int, dict[str, float]]:
    """Per lead time, a dict of {date: predicted_high_f} from a single model's past runs."""
    variables = ",".join(_hourly_var(lead) for lead in LEAD_DAYS)
    resp = requests.get(
        PREVIOUS_RUNS_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": variables,
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
            "past_days": PAST_DAYS,
            "models": model,
        },
        timeout=30,
    )
    resp.raise_for_status()
    hourly = resp.json().get("hourly", {})
    times = hourly.get("time", [])

    result = {}
    for lead in LEAD_DAYS:
        key = _hourly_var(lead)
        values = hourly.get(key)
        if values is None:
            continue
        result[lead] = _daily_max_by_date(times, values)
    return result


def fetch_actual_highs(lat: float, lon: float) -> dict[str, float]:
    resp = requests.get(
        ARCHIVE_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "past_days": PAST_DAYS,
            "daily": "temperature_2m_max",
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
        },
        timeout=30,
    )
    resp.raise_for_status()
    daily = resp.json().get("daily", {})
    return dict(zip(daily.get("time", []), daily.get("temperature_2m_max", [])))


def run() -> dict[int, list[float]]:
    """Returns {lead_days: [signed errors across all cities/dates]}."""
    errors_by_lead: dict[int, list[float]] = defaultdict(list)

    for city in sorted(TRADEABLE_CITIES):
        lat, lon = CITY_COORDS[city]
        weights = _weights_for(city)

        actual = fetch_actual_highs(lat, lon)

        per_model_per_lead: dict[str, dict[int, dict[str, float]]] = {}
        for model in weights:
            try:
                per_model_per_lead[model] = fetch_model_forecasts(lat, lon, model)
            except Exception as e:
                print(f"  [{city}] skipping {model}: {e}")

        for lead in LEAD_DAYS:
            for date, actual_high in actual.items():
                model_values = []
                model_w = []
                for model, by_lead in per_model_per_lead.items():
                    by_date = by_lead.get(lead, {})
                    if date in by_date:
                        model_values.append(by_date[date])
                        model_w.append(weights[model])

                if not model_values:
                    continue

                predicted = weighted_median(model_values, model_w)
                errors_by_lead[lead].append(predicted - actual_high)

        print(f"{city.title()} done")

    return errors_by_lead


def report(errors_by_lead: dict[int, list[float]]) -> None:
    print()
    print(f"{'Lead (days)':>12} {'N':>5} {'Mean error':>12} {'Std dev':>10} {'Current config':>16}")
    for lead in LEAD_DAYS:
        errors = errors_by_lead.get(lead, [])
        if not errors:
            continue
        mean_err = statistics.mean(errors)
        std_err = statistics.stdev(errors) if len(errors) > 1 else 0.0
        current = TEMP_STD_DEV_BY_LEAD_DAYS.get(lead, TEMP_STD_DEV_MAX_LEAD)
        print(f"{lead:>12} {len(errors):>5} {mean_err:>+12.2f} {std_err:>10.2f} {current:>16.2f}")


if __name__ == "__main__":
    errors = run()
    report(errors)
