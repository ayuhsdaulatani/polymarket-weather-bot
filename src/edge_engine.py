"""Compute model probabilities from forecast data and find edges vs market price."""

import math

from src.config import EDGE_MAX_PRICE, EDGE_MIN_PRICE, MIN_EDGE

# Assumed forecast error (std dev, in Fahrenheit) for Open-Meteo's
# temperature_2m_max/min when used a few days out.
TEMP_STD_DEV_F = 4.0


def _normal_cdf(x: float, mean: float, std: float) -> float:
    """P(X <= x) for X ~ Normal(mean, std)."""
    return 0.5 * (1 + math.erf((x - mean) / (std * math.sqrt(2))))


def model_probability(parsed_market: dict, forecast: dict) -> float:
    """
    Estimate the probability the market resolves "Yes" based on the
    Open-Meteo forecast.
    """
    condition = parsed_market["condition"]

    if condition == "rain":
        return forecast["precip_probability"] / 100.0

    if condition == "temp_above":
        # P(actual max temp > threshold)
        return 1 - _normal_cdf(
            parsed_market["threshold"], forecast["temp_max_f"], TEMP_STD_DEV_F
        )

    if condition == "temp_below":
        # P(actual min temp < threshold)
        return _normal_cdf(
            parsed_market["threshold"], forecast["temp_min_f"], TEMP_STD_DEV_F
        )

    raise ValueError(f"Unknown condition: {condition}")


def evaluate(parsed_market: dict, forecast: dict) -> dict | None:
    """
    Combine a parsed market and its forecast into a pick recommendation.
    Returns None if the market price is missing or outside the sweet spot,
    or if the edge is below the minimum threshold.
    """
    market_price = parsed_market.get("market_price")
    if market_price is None:
        return None

    if not (EDGE_MIN_PRICE <= market_price <= EDGE_MAX_PRICE):
        return None

    model_prob = model_probability(parsed_market, forecast)
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
