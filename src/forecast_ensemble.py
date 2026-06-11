"""
Multi-model ensemble forecast for daily high temperature.

Open-Meteo can return forecasts from several independent weather models in
one request. Averaging/medianing across them gives a more accurate "highest
temp today/tomorrow" estimate than any single model, and the spread between
models is a useful confidence signal.
"""

import statistics

import requests

from src.config import OPEN_METEO_URL

MODELS = [
    "ecmwf_ifs025",
    "gfs_seamless",
    "icon_seamless",
    "gem_seamless",
    "jma_seamless",
    "meteofrance_seamless",
]


def summarize_daily(daily: dict, models: list[str] = MODELS) -> list[dict]:
    """
    Turn Open-Meteo's per-model `daily` response into one summary row per
    date: median/mean/min/max high temp across models, plus the per-model
    breakdown.
    """
    dates = daily.get("time", [])
    results = []

    for i, day in enumerate(dates):
        per_model = {}
        for model in models:
            key = f"temperature_2m_max_{model}"
            values = daily.get(key)
            if values is None or i >= len(values) or values[i] is None:
                continue
            per_model[model] = values[i]

        if not per_model:
            continue

        values = list(per_model.values())
        results.append({
            "date": day,
            "predicted_high_f": round(statistics.median(values), 1),
            "mean_f": round(statistics.mean(values), 1),
            "min_f": round(min(values), 1),
            "max_f": round(max(values), 1),
            "spread_f": round(max(values) - min(values), 1),
            "model_count": len(values),
            "per_model": per_model,
        })

    return results


def get_ensemble_forecast(lat: float, lon: float, forecast_days: int = 3) -> list[dict]:
    """Fetch and summarize the multi-model daily high temp forecast for a location."""
    resp = requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max",
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
            "forecast_days": forecast_days,
            "models": ",".join(MODELS),
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return summarize_daily(data.get("daily", {}))
