"""Fetch forecast data from Open-Meteo (free, no API key required)."""

from datetime import datetime, timedelta, timezone

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


def observed_high_so_far(lat: float, lon: float, target_date: str) -> float | None:
    """
    For `target_date` (typically today), return the highest hourly temp
    (°F) already observed/forecast up to now. Open-Meteo's hourly forecast
    for past hours of "today" reflects near-real-time observations, so this
    tells us the actual high so far -- the real high can only be >= this.

    Returns None if `target_date` has no hourly data (e.g. it's not today).
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m",
        "temperature_unit": "fahrenheit",
        "timezone": "auto",
        "start_date": target_date,
        "end_date": target_date,
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    if not times:
        return None

    # Open-Meteo returns naive local times for the requested location
    # (timezone=auto). Convert "now" to that location's local time using the
    # response's UTC offset.
    utc_offset = data.get("utc_offset_seconds", 0)
    now_local = datetime.now(timezone.utc) + timedelta(seconds=utc_offset)
    now_local = now_local.replace(tzinfo=None)

    values = [
        t for time_str, t in zip(times, temps)
        if t is not None and datetime.fromisoformat(time_str) <= now_local
    ]
    return max(values) if values else None
