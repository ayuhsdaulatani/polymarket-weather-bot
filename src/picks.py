"""Generate daily 'best bet' picks: the highest-edge bucket per city/date."""

from src.analysis import buckets_by_city_date
from src.config import CITY_COORDS, model_weights_for_city
from src.edge_engine import bucket_probability_with_std, days_ahead_for, std_dev_f
from src.forecast_ensemble import get_ensemble_forecast


def confidence_label(probability: float, spread_f: float) -> str:
    """High confidence needs both a strong probability and tight model agreement."""
    if probability >= 0.40 and spread_f <= 4:
        return "high"
    if probability >= 0.25:
        return "medium"
    return "low"


def best_bucket_for_forecast(bucket_markets: list[dict], predicted_high_f: float, std_f: float) -> dict | None:
    """Of the live buckets for a city/date, return the one most likely to contain the predicted high."""
    best = None
    for bm in bucket_markets:
        prob = bucket_probability_with_std(bm["bucket"], predicted_high_f, std_f)
        if best is None or prob > best["probability"]:
            best = {
                "bucket_label": bm["bucket_label"],
                "probability": prob,
                "market_price": bm.get("market_price"),
            }
    return best


def daily_picks(cities: list[str], forecast_days: int = 4, top_n: int = 5, min_edge: float = 0.05) -> list[dict]:
    """
    For each tradeable city/date, find the bucket with the highest model
    probability and compare it to the market price. Return the top picks by
    edge (model probability minus market price), highest edge first.
    """
    bucket_map = buckets_by_city_date(set(cities))

    rows = []
    for city in cities:
        lat, lon = CITY_COORDS[city]
        weights = model_weights_for_city(city)
        for day in get_ensemble_forecast(lat, lon, forecast_days=forecast_days, weights=weights):
            bucket_markets = bucket_map.get((city, day["date"]), [])
            if not bucket_markets:
                continue

            days_ahead = days_ahead_for(day["date"])
            std = max(std_dev_f(days_ahead), day["spread_f"] / 2)

            best = best_bucket_for_forecast(bucket_markets, day["predicted_high_f"], std)
            if best is None or best["market_price"] is None:
                continue

            edge = best["probability"] - best["market_price"]
            note = None
            if best["market_price"] < 0.02 and 0.2 <= best["probability"] <= 0.8:
                note = "Market price looks stale/illiquid -- verify before betting"

            rows.append({
                "city": city,
                "date": day["date"],
                "predicted_high_f": day["predicted_high_f"],
                "spread_f": day["spread_f"],
                "bucket_label": best["bucket_label"],
                "probability": round(best["probability"], 3),
                "market_price": best["market_price"],
                "edge": round(edge, 3),
                "confidence": confidence_label(best["probability"], day["spread_f"]),
                "note": note,
            })

    picks = [r for r in rows if r["edge"] >= min_edge]
    picks.sort(key=lambda r: r["edge"], reverse=True)
    return picks[:top_n]
