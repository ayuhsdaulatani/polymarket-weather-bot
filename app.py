"""
Streamlit UI for the Polymarket weather bot.

Run with:
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

from src.analysis import buckets_by_city_date, scored_buckets
from src.config import (
    CITY_COORDS,
    EDGE_MAX_PRICE,
    EDGE_MIN_PRICE,
    MIN_EDGE,
    TRADEABLE_CITIES,
    model_weights_for_city,
)
from src.edge_engine import days_ahead_for, std_dev_f
from src.forecast_ensemble import get_ensemble_forecast
from src.picks import best_bucket_for_forecast, confidence_label, daily_picks

st.set_page_config(page_title="Polymarket Weather Bot", layout="wide")
st.title("Polymarket Weather Bot")

tradeable = sorted(TRADEABLE_CITIES) if TRADEABLE_CITIES else sorted(CITY_COORDS)

# ---------------------------------------------------------------------------
# Today's picks — the bot's own top picks, refreshed daily
# ---------------------------------------------------------------------------
st.header("Today's Picks")
st.caption(
    "The bot's own top picks: the bucket with the biggest gap between model "
    "probability and market price, ranked by edge."
)

if st.button("Refresh picks", type="primary", key="refresh_top_picks") or "top_picks" not in st.session_state:
    with st.spinner("Computing today's picks..."):
        st.session_state["top_picks"] = daily_picks(tradeable, forecast_days=4, top_n=5)

top_picks = st.session_state.get("top_picks", [])

if top_picks:
    picks_df = pd.DataFrame([
        {
            "City": p["city"].title(),
            "Date": p["date"],
            "Bet this range": p["bucket_label"],
            "Predicted High (°F)": p["predicted_high_f"],
            "Spread (°F)": p["spread_f"],
            "Probability": f"{p['probability']:.0%}",
            "Market price (Yes)": p["market_price"],
            "Edge": f"{p['edge']:+.0%}",
            "Confidence": p["confidence"],
            "Note": p["note"] or "",
        }
        for p in top_picks
    ])
    st.dataframe(picks_df, use_container_width=True, hide_index=True)
else:
    st.info("No picks clear the minimum edge today.")

st.divider()

# ---------------------------------------------------------------------------
# Highest temp forecast — the main thing: "will the high be over X?"
# ---------------------------------------------------------------------------
st.header("Highest Temp Forecast")
st.caption(
    "Predicted daily high (°F) per city, blended across 6 independent weather "
    "models. Use this for 'will the high be over X' bets."
)

forecast_days = st.slider("Days ahead to show", 1, 7, 3)

if st.button("Refresh forecast", type="primary") or "forecast" not in st.session_state:
    with st.spinner("Fetching multi-model forecasts and markets..."):
        forecast_rows = []
        for city in tradeable:
            lat, lon = CITY_COORDS[city]
            weights = model_weights_for_city(city)
            for day in get_ensemble_forecast(lat, lon, forecast_days=forecast_days, weights=weights):
                forecast_rows.append({"city": city, **day})
        st.session_state["forecast"] = forecast_rows
        st.session_state["bucket_map"] = buckets_by_city_date(set(tradeable))

forecast_rows = st.session_state.get("forecast", [])
bucket_map = st.session_state.get("bucket_map", {})


if forecast_rows:
    table_rows = []
    for r in forecast_rows:
        bucket_markets = bucket_map.get((r["city"], r["date"]), [])
        days_ahead = days_ahead_for(r["date"])
        std = max(std_dev_f(days_ahead), r["spread_f"] / 2)
        best = best_bucket_for_forecast(bucket_markets, r["predicted_high_f"], std)
        table_rows.append({
            "City": r["city"].title(),
            "Date": r["date"],
            "Predicted High (°F)": r["predicted_high_f"],
            "Model range": f"{r['min_f']} – {r['max_f']}",
            "Spread (°F)": r["spread_f"],
            "Bet this range": best["bucket_label"] if best else "—",
            "Probability": f"{best['probability']:.0%}" if best else "—",
            "Confidence": confidence_label(best["probability"], r["spread_f"]) if best else "—",
            "Market price (Yes)": best["market_price"] if best else None,
        })

    forecast_df = pd.DataFrame(table_rows)
    st.dataframe(forecast_df, use_container_width=True, hide_index=True)

    with st.expander("Per-model breakdown"):
        for r in forecast_rows:
            st.write(f"**{r['city'].title()} — {r['date']}**: {r['per_model']}")

    st.info(
        "'Bet this range' is the actual Polymarket bucket (e.g. '88-89°F') "
        "most likely to contain the predicted high, based on the ensemble "
        "forecast and an uncertainty band that widens when models disagree "
        "(spread). High confidence = probability ≥40% with model spread "
        "≤4°F; medium = probability ≥25%; below that = low — there's no "
        "clearly favored bucket."
    )
else:
    st.info("Click 'Refresh forecast' to load.")

st.divider()

# ---------------------------------------------------------------------------
# Edge picks — secondary: market price vs single-model bucket probabilities
# ---------------------------------------------------------------------------
st.header("Edge Picks (experimental)")
st.caption(
    "Compares Polymarket 'Highest temperature' bucket prices against a "
    "single-model forecast. Less reliable than the table above for same-day markets."
)

selected_cities = st.multiselect("Cities", options=tradeable, default=tradeable)

if st.button("Refresh picks") or "data" not in st.session_state:
    with st.spinner("Fetching markets and forecasts..."):
        st.session_state["data"] = scored_buckets(cities=set(selected_cities) or None)

rows = st.session_state.get("data", [])
rows = [r for r in rows if r["city"] in selected_cities] if selected_cities else rows

if rows:
    df = pd.DataFrame([
        {
            "City": r["city"].title(),
            "Date": r["target_date"],
            "Days ahead": r["days_ahead"],
            "Bucket": r["bucket_label"],
            "Market price (Yes)": r["market_price"],
            "Model probability": r["model_probability"],
            "Edge": r["edge"],
            "Confidence": r["confidence"],
            "Recommendation": r["recommendation"],
            "Forecast high (°F)": r["forecast"]["temp_max_f"],
            "Question": r["question"],
        }
        for r in rows
    ])

    in_sweet_spot = df["Market price (Yes)"].between(EDGE_MIN_PRICE, EDGE_MAX_PRICE)
    has_edge = df["Edge"].abs() >= MIN_EDGE
    picks_df = df[in_sweet_spot & has_edge].sort_values("Edge", key=abs, ascending=False)

    if picks_df.empty:
        st.write("No picks above the edge threshold right now.")
    else:
        st.dataframe(picks_df, use_container_width=True, hide_index=True)

    with st.expander("All scored buckets"):
        st.dataframe(
            df.sort_values(["City", "Date", "Bucket"]),
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("Click 'Refresh picks' to load.")
