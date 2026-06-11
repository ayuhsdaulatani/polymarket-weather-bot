"""Compute model probabilities for temperature buckets and find edges vs market price."""

import math
from datetime import date, datetime

from src.config import (
    EDGE_MAX_PRICE,
    EDGE_MIN_PRICE,
    MIN_EDGE,
    TEMP_STD_DEV_BY_LEAD_DAYS,
    TEMP_STD_DEV_MAX_LEAD,
)


def _normal_cdf(x: float, mean: float, std: float) -> float:
    """P(X <= x) for X ~ Normal(mean, std). Supports +/- inf for x."""
    return 0.5 * (1 + math.erf((x - mean) / (std * math.sqrt(2))))


def std_dev_f(days_ahead: int) -> float:
    """Approximate forecast error (std dev, °F) for a given lead time."""
    if days_ahead < 0:
        days_ahead = 0
    return TEMP_STD_DEV_BY_LEAD_DAYS.get(days_ahead, TEMP_STD_DEV_MAX_LEAD)


def days_ahead_for(target_date: str, today: date | None = None) -> int:
    """Number of days between today and the target date (YYYY-MM-DD)."""
    today = today or date.today()
    target = datetime.strptime(target_date, "%Y-%m-%d").date()
    return (target - today).days


def bucket_probability(bucket: dict, forecast_temp_max_f: float, days_ahead: int = 1) -> float:
    """
    Estimate P(actual high temp falls in this bucket) using a normal
    distribution centered on the Open-Meteo forecast, with a half-degree
    continuity correction at each bucket edge. The standard deviation widens
    with lead time (`days_ahead`) and is converted to °C for °C-labeled
    buckets.
    """
    std = std_dev_f(days_ahead)

    if bucket["unit"] == "C":
        mean = (forecast_temp_max_f - 32) * 5 / 9
        std = std / 1.8
    else:
        mean = forecast_temp_max_f

    low_bound = -math.inf if bucket["low"] is None else bucket["low"] - 0.5
    high_bound = math.inf if bucket["high"] is None else bucket["high"] + 0.5

    return _normal_cdf(high_bound, mean, std) - _normal_cdf(low_bound, mean, std)


def score_bucket(parsed_market: dict, forecast: dict) -> dict | None:
    """
    Combine a parsed bucket market and its forecast into a scored result
    (model probability, edge, recommendation) with no filtering applied.
    Returns None only if the market price is missing.
    """
    market_price = parsed_market.get("market_price")
    if market_price is None:
        return None

    days_ahead = days_ahead_for(parsed_market["target_date"])
    model_prob = bucket_probability(
        parsed_market["bucket"], forecast["temp_max_f"], days_ahead
    )
    edge = model_prob - market_price

    return {
        **parsed_market,
        "forecast": forecast,
        "days_ahead": days_ahead,
        "model_probability": round(model_prob, 3),
        "edge": round(edge, 3),
        "recommendation": "YES" if edge > 0 else "NO",
        "confidence": _confidence_label(abs(edge)),
    }


def evaluate(parsed_market: dict, forecast: dict) -> dict | None:
    """
    Score a bucket market and return it only if it's a "pick": market price
    in the sweet spot (EDGE_MIN_PRICE-EDGE_MAX_PRICE) and the edge meets
    MIN_EDGE.
    """
    scored = score_bucket(parsed_market, forecast)
    if scored is None:
        return None

    if not (EDGE_MIN_PRICE <= scored["market_price"] <= EDGE_MAX_PRICE):
        return None

    if abs(scored["edge"]) < MIN_EDGE:
        return None

    return scored


def _confidence_label(edge_abs: float) -> str:
    if edge_abs >= 0.30:
        return "high"
    if edge_abs >= 0.20:
        return "medium"
    return "low"


def rank_picks(picks: list[dict], top_n: int = 3) -> list[dict]:
    """Sort picks by absolute edge (descending) and return the top N."""
    return sorted(picks, key=lambda p: abs(p["edge"]), reverse=True)[:top_n]
