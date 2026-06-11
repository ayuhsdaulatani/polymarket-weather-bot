"""Compute model probabilities for temperature buckets and find edges vs market price."""

import math

from src.config import EDGE_MAX_PRICE, EDGE_MIN_PRICE, MIN_EDGE

# Assumed forecast error (std dev, in the bucket's own units) for Open-Meteo's
# temperature_2m_max when used a few days out.
TEMP_STD_DEV = 4.0


def _normal_cdf(x: float, mean: float, std: float) -> float:
    """P(X <= x) for X ~ Normal(mean, std). Supports +/- inf for x."""
    return 0.5 * (1 + math.erf((x - mean) / (std * math.sqrt(2))))


def bucket_probability(bucket: dict, forecast_temp_max_f: float) -> float:
    """
    Estimate P(actual high temp falls in this bucket) using a normal
    distribution centered on the Open-Meteo forecast, with a half-degree
    continuity correction at each bucket edge.
    """
    if bucket["unit"] == "C":
        mean = (forecast_temp_max_f - 32) * 5 / 9
    else:
        mean = forecast_temp_max_f

    low_bound = -math.inf if bucket["low"] is None else bucket["low"] - 0.5
    high_bound = math.inf if bucket["high"] is None else bucket["high"] + 0.5

    return _normal_cdf(high_bound, mean, TEMP_STD_DEV) - _normal_cdf(low_bound, mean, TEMP_STD_DEV)


def evaluate(parsed_market: dict, forecast: dict) -> dict | None:
    """
    Combine a parsed bucket market and its forecast into a pick recommendation.
    Returns None if the market price is missing, outside the sweet spot, or
    the edge is below the minimum threshold.
    """
    market_price = parsed_market.get("market_price")
    if market_price is None:
        return None

    if not (EDGE_MIN_PRICE <= market_price <= EDGE_MAX_PRICE):
        return None

    model_prob = bucket_probability(parsed_market["bucket"], forecast["temp_max_f"])
    edge = model_prob - market_price

    if abs(edge) < MIN_EDGE:
        return None

    return {
        **parsed_market,
        "forecast": forecast,
        "model_probability": round(model_prob, 3),
        "edge": round(edge, 3),
        "recommendation": "YES" if edge > 0 else "NO",
        "confidence": _confidence_label(abs(edge)),
    }


def _confidence_label(edge_abs: float) -> str:
    if edge_abs >= 0.30:
        return "high"
    if edge_abs >= 0.20:
        return "medium"
    return "low"


def rank_picks(picks: list[dict], top_n: int = 3) -> list[dict]:
    """Sort picks by absolute edge (descending) and return the top N."""
    return sorted(picks, key=lambda p: abs(p["edge"]), reverse=True)[:top_n]
