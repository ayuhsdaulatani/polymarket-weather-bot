"""
Backtest the forecast-error assumptions in src/config.py against real
historical forecast accuracy, broken out per city and per model.

For each tradeable city and each model in its ensemble, pulls Open-Meteo's
"previous runs" API (forecasts as they were actually issued N days before the
target date) and compares to the observed daily high from the archive API.

Reports, per city and lead time:
  - ensemble error (mean/std/skew) using the current model weights
  - per-model error (mean/std), to inform re-tuning model weights

Usage:
    python -m scripts.backtest
"""

import statistics
from collections import defaultdict

import requests

from src.config import (
    CITY_COORDS,
    TEMP_BIAS_CORRECTION_F,
    TEMP_STD_DEV_BY_LEAD_DAYS,
    TEMP_STD_DEV_MAX_LEAD,
    TRADEABLE_CITIES,
    model_weights_for_city as _weights_for,
)
from src.forecast_ensemble import weighted_median

PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

LEAD_DAYS = [0, 1, 2, 3, 4]
PAST_DAYS = 90


def _hourly_var(lead: int) -> str:
    return "temperature_2m" if lead == 0 else f"temperature_2m_previous_day{lead}"


def _daily_max_by_date(times: list[str], values: list[float | None]) -> dict[str, float]:
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
        timeout=60,
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
        timeout=60,
    )
    resp.raise_for_status()
    daily = resp.json().get("daily", {})
    return dict(zip(daily.get("time", []), daily.get("temperature_2m_max", [])))


def _skewness(values: list[float]) -> float:
    """Sample skewness (Fisher-Pearson). 0 = symmetric, >0 = long right tail."""
    n = len(values)
    if n < 3:
        return 0.0
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    if std == 0:
        return 0.0
    m3 = sum((x - mean) ** 3 for x in values) / n
    return m3 / (std ** 3)


def run() -> dict:
    """
    Returns {city: {
        "ensemble_errors": {lead: [errors]},
        "model_errors": {model: {lead: [errors]}},
    }}
    """
    results = {}

    # de-dupe cities that share coordinates (e.g. "new york"/"nyc")
    seen_coords = {}
    cities = []
    for city in sorted(TRADEABLE_CITIES):
        coord = CITY_COORDS[city]
        if coord in seen_coords:
            continue
        seen_coords[coord] = city
        cities.append(city)

    for city in cities:
        lat, lon = CITY_COORDS[city]
        weights = _weights_for(city)

        actual = fetch_actual_highs(lat, lon)

        per_model_per_lead: dict[str, dict[int, dict[str, float]]] = {}
        for model in weights:
            try:
                per_model_per_lead[model] = fetch_model_forecasts(lat, lon, model)
            except Exception as e:
                print(f"  [{city}] skipping {model}: {e}")

        ensemble_errors: dict[int, list[float]] = defaultdict(list)
        model_errors: dict[str, dict[int, list[float]]] = {m: defaultdict(list) for m in weights}

        for lead in LEAD_DAYS:
            for date, actual_high in actual.items():
                model_values = []
                model_w = []
                for model, by_lead in per_model_per_lead.items():
                    by_date = by_lead.get(lead, {})
                    if date in by_date:
                        predicted = by_date[date]
                        model_values.append(predicted)
                        model_w.append(weights[model])
                        model_errors[model][lead].append(predicted - actual_high)

                if not model_values:
                    continue

                ensemble_pred = weighted_median(model_values, model_w)
                ensemble_errors[lead].append(ensemble_pred - actual_high)

        results[city] = {
            "ensemble_errors": ensemble_errors,
            "model_errors": model_errors,
        }
        print(f"{city.title()} done")

    return results


def report(results: dict) -> None:
    print()
    print("=" * 78)
    print("ENSEMBLE ERROR BY CITY AND LEAD TIME (predicted - actual, °F)")
    print("=" * 78)
    print(f"{'City':<16}{'Lead':>5}{'N':>5}{'Mean':>8}{'Std':>8}{'Skew':>8}{'Cur. bias':>11}{'Cur. std':>10}")
    for city, data in results.items():
        for lead in LEAD_DAYS:
            errors = data["ensemble_errors"].get(lead, [])
            if not errors:
                continue
            mean_err = statistics.mean(errors)
            std_err = statistics.stdev(errors) if len(errors) > 1 else 0.0
            skew = _skewness(errors)
            cur_std = TEMP_STD_DEV_BY_LEAD_DAYS.get(lead, TEMP_STD_DEV_MAX_LEAD)
            print(
                f"{city.title():<16}{lead:>5}{len(errors):>5}{mean_err:>+8.2f}{std_err:>8.2f}"
                f"{skew:>+8.2f}{TEMP_BIAS_CORRECTION_F:>11.2f}{cur_std:>10.2f}"
            )

    print()
    print("=" * 78)
    print("PER-MODEL ERROR BY CITY (lead 1, mean +/- std, °F) -- for re-tuning weights")
    print("=" * 78)
    for city, data in results.items():
        print(f"\n{city.title()}:")
        for model, by_lead in data["model_errors"].items():
            errors = by_lead.get(1, [])
            if not errors:
                continue
            mean_err = statistics.mean(errors)
            std_err = statistics.stdev(errors) if len(errors) > 1 else 0.0
            print(f"  {model:<18} mean={mean_err:>+6.2f}  std={std_err:>5.2f}  n={len(errors)}")


if __name__ == "__main__":
    results = run()
    report(results)
