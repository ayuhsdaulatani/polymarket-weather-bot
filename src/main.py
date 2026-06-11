"""
Daily entrypoint: scan Polymarket weather markets, compare against
Open-Meteo forecasts, and report any picks with an edge.

Usage:
    python -m src.main
"""

import json
from datetime import date
from pathlib import Path

from src.edge_engine import evaluate, rank_picks
from src.openmeteo_client import get_forecast
from src.parser import parse_market
from src.polymarket_client import fetch_weather_markets

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "output"


def run() -> list[dict]:
    markets = fetch_weather_markets()
    print(f"Fetched {len(markets)} weather-related markets")

    picks = []
    for market in markets:
        parsed = parse_market(market)
        if not parsed:
            continue

        forecast = get_forecast(parsed["lat"], parsed["lon"], parsed["target_date"])
        if not forecast:
            continue

        result = evaluate(parsed, forecast)
        if result:
            picks.append(result)

    return rank_picks(picks)


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
        lines.append(f"- Market price (Yes): {pick['market_price']:.2f}")
        lines.append(f"- Model probability: {pick['model_probability']:.2f}")
        lines.append(f"- Edge: {pick['edge']:+.2f} ({pick['confidence']} confidence)")
        lines.append(f"- Recommendation: **{pick['recommendation']}**")
        lines.append(f"- Forecast: {pick['forecast']}")
        lines.append("")
    md_path.write_text("\n".join(lines))

    return md_path


if __name__ == "__main__":
    found_picks = run()
    report_path = write_report(found_picks)
    print(f"Wrote {len(found_picks)} picks to {report_path}")
