"""Fetch active weather-related markets from the Polymarket gamma API."""

import requests

from src.config import GAMMA_API_URL

WEATHER_KEYWORDS = [
    "rain", "snow", "temperature", "high temp", "low temp", "degrees",
    "weather", "hurricane", "storm", "wind", "sunny", "cloudy", "hottest",
    "coldest", "precipitation",
]


def fetch_weather_markets(limit: int = 200) -> list[dict]:
    """Return active, open markets whose question text looks weather-related."""
    params = {
        "active": "true",
        "closed": "false",
        "limit": limit,
    }
    resp = requests.get(GAMMA_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    markets = resp.json()

    weather_markets = []
    for market in markets:
        question = (market.get("question") or "").lower()
        if any(keyword in question for keyword in WEATHER_KEYWORDS):
            weather_markets.append(market)

    return weather_markets
