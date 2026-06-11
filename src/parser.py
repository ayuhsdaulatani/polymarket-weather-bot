"""Parse "Highest temperature in X on Y?" events into per-bucket market info."""

import json
import re

from src.config import CITY_COORDS

BUCKET_RANGE_RE = re.compile(r"(-?\d+)\s*-\s*(-?\d+)\s*.?\s*([FC])", re.IGNORECASE)
BUCKET_BELOW_RE = re.compile(r"(-?\d+)\s*.?\s*([FC])\s*or below", re.IGNORECASE)
BUCKET_ABOVE_RE = re.compile(r"(-?\d+)\s*.?\s*([FC])\s*or (?:higher|above)", re.IGNORECASE)
BUCKET_SINGLE_RE = re.compile(r"^(-?\d+)\s*.?\s*([FC])$", re.IGNORECASE)


def find_city(text: str) -> tuple[str, float, float] | None:
    """Find a known city name in the text. Returns (name, lat, lon)."""
    lowered = text.lower()
    for name, (lat, lon) in CITY_COORDS.items():
        if name in lowered:
            return name, lat, lon
    return None


def parse_bucket(group_item_title: str) -> dict | None:
    """
    Parse a bucket label like "88-89°F", "87°F or below", "106°F or higher",
    or "23°C" into {"low": float|None, "high": float|None, "unit": "F"|"C"}.

    `low`/`high` of None mean unbounded in that direction.
    """
    title = group_item_title.strip()

    match = BUCKET_BELOW_RE.search(title)
    if match:
        return {"low": None, "high": float(match.group(1)), "unit": match.group(2).upper()}

    match = BUCKET_ABOVE_RE.search(title)
    if match:
        return {"low": float(match.group(1)), "high": None, "unit": match.group(2).upper()}

    match = BUCKET_RANGE_RE.search(title)
    if match:
        return {
            "low": float(match.group(1)),
            "high": float(match.group(2)),
            "unit": match.group(3).upper(),
        }

    match = BUCKET_SINGLE_RE.search(title)
    if match:
        value = float(match.group(1))
        return {"low": value, "high": value, "unit": match.group(2).upper()}

    return None


def _yes_price(market: dict) -> float | None:
    """Extract the implied probability of "Yes" from outcomePrices."""
    prices = market.get("outcomePrices")
    if not prices:
        return None
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except ValueError:
            return None
    try:
        return float(prices[0])
    except (IndexError, ValueError, TypeError):
        return None


def parse_event(event: dict) -> list[dict]:
    """
    Parse a "Highest temperature in X on Y?" event into one entry per
    temperature bucket market. Returns [] if the event isn't a recognized
    temperature event, its city is unknown, or it has no usable markets.
    """
    title = event.get("title") or ""
    if "highest temperature" not in title.lower():
        return []

    city = find_city(title)
    if not city:
        return []
    city_name, lat, lon = city

    markets = event.get("markets") or []
    if not markets:
        return []

    end_date = markets[0].get("endDate")
    if not end_date:
        return []
    target_date = end_date[:10]

    parsed = []
    for market in markets:
        bucket = parse_bucket(market.get("groupItemTitle") or "")
        if not bucket:
            continue

        price = _yes_price(market)
        if price is None:
            continue

        parsed.append({
            "market_id": market.get("id"),
            "question": market.get("question"),
            "bucket_label": market.get("groupItemTitle"),
            "city": city_name,
            "lat": lat,
            "lon": lon,
            "target_date": target_date,
            "bucket": bucket,
            "market_price": price,
        })

    return parsed
