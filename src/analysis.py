"""Shared pipeline: fetch events, score every bucket, optionally filter by city."""

from src.edge_engine import days_ahead_for, score_bucket
from src.openmeteo_client import get_forecast
from src.parser import parse_event
from src.polymarket_client import fetch_temperature_events

# Open-Meteo's forecast endpoint only covers today through ~16 days ahead.
MAX_FORECAST_LEAD_DAYS = 14


def scored_buckets(cities: set[str] | None = None) -> list[dict]:
    """
    Fetch all active "Highest temperature" events and return a scored result
    for every temperature bucket (no edge/sweet-spot filtering).

    If `cities` is given, only buckets for those cities (matching the keys
    used in CITY_COORDS) are included.
    """
    events = fetch_temperature_events()

    results = []
    forecast_cache: dict[tuple[float, float, str], dict | None] = {}

    for event in events:
        bucket_markets = parse_event(event)
        if not bucket_markets:
            continue

        first = bucket_markets[0]
        if cities and first["city"] not in cities:
            continue

        days_ahead = days_ahead_for(first["target_date"])
        if not (0 <= days_ahead <= MAX_FORECAST_LEAD_DAYS):
            continue

        cache_key = (first["lat"], first["lon"], first["target_date"])
        if cache_key not in forecast_cache:
            try:
                forecast_cache[cache_key] = get_forecast(*cache_key)
            except Exception:
                forecast_cache[cache_key] = None
        forecast = forecast_cache[cache_key]
        if not forecast:
            continue

        for bucket_market in bucket_markets:
            scored = score_bucket(bucket_market, forecast)
            if scored:
                results.append(scored)

    return results
