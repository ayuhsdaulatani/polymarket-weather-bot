"""
Multi-model ensemble forecast for daily high temperature.

Open-Meteo can return forecasts from several independent weather models in
one request. Combining them with a weighted median gives a more accurate
"highest temp today/tomorrow" estimate than any single model, and the spread
between models is a useful confidence signal.
"""

import requests

from src.config import GLOBAL_MODEL_WEIGHTS, OPEN_METEO_URL, TEMP_BIAS_CORRECTION_F, bias_correction_for
from src.openmeteo_client import observed_high_so_far

# Default model set if no weights are given (used by callers/tests that
# don't care about region-specific tuning).
MODELS = list(GLOBAL_MODEL_WEIGHTS)


def weighted_median(values: list[float], weights: list[float]) -> float:
    """
    Weighted median: the value at which cumulative weight first reaches half
    of the total weight, after sorting by value.
    """
    pairs = sorted(zip(values, weights))
    total = sum(weights)
    cumulative = 0.0
    for value, weight in pairs:
        cumulative += weight
        if cumulative >= total / 2:
            return value
    return pairs[-1][0]


def summarize_daily(
    daily: dict,
    weights: dict[str, float] = GLOBAL_MODEL_WEIGHTS,
    city: str | None = None,
) -> list[dict]:
    """
    Turn Open-Meteo's per-model `daily` response into one summary row per
    date: weighted-median/min/max high temp across the given models, plus
    the per-model breakdown.

    The bias correction is per-city and per-lead-time when `city` is given
    (see CITY_BIAS_CORRECTION_F in config), otherwise a flat global default.
    Lead time is assumed to be the row's position (`time[0]` = lead 0/today).
    """
    dates = daily.get("time", [])
    results = []

    for i, day in enumerate(dates):
        per_model = {}
        for model in weights:
            key = f"temperature_2m_max_{model}"
            values = daily.get(key)
            if values is None or i >= len(values) or values[i] is None:
                continue
            per_model[model] = values[i]

        if not per_model:
            continue

        values = list(per_model.values())
        model_weights = [weights[m] for m in per_model]
        raw_median = weighted_median(values, model_weights)

        bias = bias_correction_for(city, i) if city else TEMP_BIAS_CORRECTION_F
        results.append({
            "date": day,
            "predicted_high_f": round(raw_median + bias, 1),
            "min_f": round(min(values), 1),
            "max_f": round(max(values), 1),
            "spread_f": round(max(values) - min(values), 1),
            "model_count": len(values),
            "per_model": per_model,
        })

    return results


def get_ensemble_forecast(
    lat: float,
    lon: float,
    forecast_days: int = 3,
    weights: dict[str, float] = GLOBAL_MODEL_WEIGHTS,
    city: str | None = None,
) -> list[dict]:
    """
    Fetch and summarize the multi-model daily high temp forecast for a
    location. For "today" (the first row), the prediction is floored at the
    highest temperature already observed so far today, since the day's high
    can't be lower than what's already happened.
    """
    resp = requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max",
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
            "forecast_days": forecast_days,
            "models": ",".join(weights),
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    rows = summarize_daily(data.get("daily", {}), weights=weights, city=city)

    if rows:
        try:
            observed = observed_high_so_far(lat, lon, rows[0]["date"])
        except Exception:
            observed = None
        if observed is not None and observed > rows[0]["predicted_high_f"]:
            rows[0]["predicted_high_f"] = round(observed, 1)
            rows[0]["observed_floor_applied"] = True

    return rows
