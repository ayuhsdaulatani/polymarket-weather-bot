"""
Daily entrypoint: scan Polymarket "Highest temperature in X" events, compare
each degree-bucket's price against the Open-Meteo forecast, and report any
buckets with an edge.

Usage:
    python -m src.main
"""

import json
from datetime import date
from pathlib import Path

from src.edge_engine import evaluate, rank_picks
from src.openmeteo_client import get_forecast
from src.parser import parse_event
from src.polymarket_client import fetch_temperature_events

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "output"


def run() -> list[dict]:
    events = fetch_temperature_events()
    print(f"Fetched {len(events)} 'Highest temperature' events")

    picks = []
    forecast_cache: dict[tuple[float, float, str], dict | None] = {}

    for event in events:
        bucket_markets = parse_event(event)
        if not bucket_markets:
            continue

        first = bucket_markets[0]
        cache_key = (first["lat"], first["lon"], first["target_date"])
        if cache_key not in forecast_cache:
            forecast_cache[cache_key] = get_forecast(*cache_key)
        forecast = forecast_cache[cache_key]
        if not forecast:
            continue

        for bucket_market in bucket_markets:
            result = evaluate(bucket_market, forecast)
            if result:
                picks.append(result)

    return rank_picks(picks, top_n=10)


def write_report(picks: list[dict]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    json_path = OUTPUT_DIR / f"{today}.json"
    json_path.write_text(json.dumps(picks, indent=2))

    md_path = OUTPUT_DIR / f"{today}.md"
    lines = [f"# Polymarket Weather Picks — {today}", ""]
    if not picks:
        lines.append("No edges found above the minimum threshold today.")
    for pick in picks:
        lines.append(f"## {pick['question']}")
        lines.append(f"- City: {pick['city'].title()} | Date: {pick['target_date']}")
        lines.append(f"- Bucket: {pick['bucket_label']}")
        lines.append(f"- Market price (Yes): {pick['market_price']:.3f}")
        lines.append(f"- Model probability: {pick['model_probability']:.3f}")
        lines.append(f"- Edge: {pick['edge']:+.3f} ({pick['confidence']} confidence)")
        lines.append(f"- Recommendation: **{pick['recommendation']}**")
        lines.append(f"- Forecast high: {pick['forecast']['temp_max_f']}°F")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return md_path


if __name__ == "__main__":
    found_picks = run()
    report_path = write_report(found_picks)
    print(f"Wrote {len(found_picks)} picks to {report_path}")
