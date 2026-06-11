"""Parse Polymarket weather market questions into structured data."""

import re
from datetime import datetime

from src.config import CITY_COORDS

RAIN_RE = re.compile(r"\b(rain|snow|precipitation)\b", re.IGNORECASE)
TEMP_ABOVE_RE = re.compile(
    r"\b(above|over|higher than|more than)\s+(\d+)\s*°?\s*f", re.IGNORECASE
)
TEMP_BELOW_RE = re.compile(
    r"\b(below|under|lower than|less than)\s+(\d+)\s*°?\s*f", re.IGNORECASE
)
DATE_RE = re.compile(r"\b(\w+ \d{1,2}(?:st|nd|rd|th)?,? \d{4})\b")


def find_city(question: str) -> tuple[str, float, float] | None:
    """Find a known city name in the question text. Returns (name, lat, lon)."""
    lowered = question.lower()
    for name, (lat, lon) in CITY_COORDS.items():
        if name in lowered:
            return name, lat, lon
    return None


def find_date(question: str, end_date_iso: str | None = None) -> str | None:
    """
    Try to extract a target date (YYYY-MM-DD) from the question text.
    Falls back to the market's end date if no date is mentioned.
    """
    match = DATE_RE.search(question)
    if match:
        raw = match.group(1).replace(",", "").replace("st", "").replace(
            "nd", ""
        ).replace("rd", "").replace("th", "")
        for fmt in ("%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

    if end_date_iso:
        try:
            return datetime.fromisoformat(
                end_date_iso.replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
        except ValueError:
            return None

    return None


def parse_market(market: dict) -> dict | None:
    """
    Parse a raw gamma API market dict into structured info needed for
    a prediction, or None if it can't be parsed (unsupported question type
    or unknown city).
    """
    question = market.get("question") or ""

    city = find_city(question)
    if not city:
        return None
    city_name, lat, lon = city

    target_date = find_date(question, market.get("endDate"))
    if not target_date:
        return None

    if RAIN_RE.search(question):
        condition = "rain"
        threshold = None
    elif TEMP_ABOVE_RE.search(question):
        condition = "temp_above"
        threshold = float(TEMP_ABOVE_RE.search(question).group(2))
    elif TEMP_BELOW_RE.search(question):
        condition = "temp_below"
        threshold = float(TEMP_BELOW_RE.search(question).group(2))
    else:
        return None

    return {
        "market_id": market.get("id"),
        "question": question,
        "city": city_name,
        "lat": lat,
        "lon": lon,
        "target_date": target_date,
        "condition": condition,
        "threshold": threshold,
        "market_price": _yes_price(market),
    }


def _yes_price(market: dict) -> float | None:
    """Extract the implied probability of "Yes" from outcomePrices."""
    prices = market.get("outcomePrices")
    if not prices:
        return None
    if isinstance(prices, str):
        import json
        try:
            prices = json.loads(prices)
        except ValueError:
            return None
    try:
        return float(prices[0])
    except (IndexError, ValueError, TypeError):
        return None
