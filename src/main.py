"""
Daily entrypoint: scan Polymarket "Highest temperature in X" events (limited
to TRADEABLE_CITIES), compare each degree-bucket's price against the
Open-Meteo forecast, and report any buckets with an edge.

Usage:
    python -m src.main
"""

import json
from datetime import date
from pathlib import Path

from src.analysis import scored_buckets
from src.config import EDGE_MAX_PRICE, EDGE_MIN_PRICE, MIN_EDGE, TRADEABLE_CITIES
from src.edge_engine import rank_picks

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "output"


def run() -> list[dict]:
    scored = scored_buckets(cities=TRADEABLE_CITIES or None)
    print(f"Scored {len(scored)} buckets across tradeable cities")

    picks = [
        s for s in scored
        if EDGE_MIN_PRICE <= s["market_price"] <= EDGE_MAX_PRICE
        and abs(s["edge"]) >= MIN_EDGE
    ]
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
