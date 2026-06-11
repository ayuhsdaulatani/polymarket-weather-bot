"""Fetch forecast data from Open-Meteo (free, no API key required)."""

import requests

from src.config import OPEN_METEO_URL


def get_forecast(lat: float, lon: float, target_date: str) -> dict | None:
    """
    Get the daily forecast for a given lat/lon and date (YYYY-MM-DD).

    Returns a dict with precipitation probability (%), max/min temp (F),
    and weather code, or None if the date is outside the forecast range.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_probability_max,temperature_2m_max,"
                 "temperature_2m_min,weathercode",
        "temperature_unit": "fahrenheit",
        "timezone": "auto",
        "start_date": target_date,
        "end_date": target_date,
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    if target_date not in dates:
        return None

    idx = dates.index(target_date)
    return {
        "date": target_date,
        "precip_probability": daily["precipitation_probability_max"][idx],
        "temp_max_f": daily["temperature_2m_max"][idx],
        "temp_min_f": daily["temperature_2m_min"][idx],
        "weathercode": daily["weathercode"][idx],
    }
