"""
Streamlit UI for the Polymarket weather bot.

Run with:
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

from src.analysis import scored_buckets
from src.config import CITY_COORDS, EDGE_MAX_PRICE, EDGE_MIN_PRICE, MIN_EDGE, TRADEABLE_CITIES
from src.forecast_ensemble import get_ensemble_forecast

st.set_page_config(page_title="Polymarket Weather Bot", layout="wide")
st.title("Polymarket Weather Bot")

tradeable = sorted(TRADEABLE_CITIES) if TRADEABLE_CITIES else sorted(CITY_COORDS)

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
    with st.spinner("Fetching multi-model forecasts..."):
        forecast_rows = []
        for city in tradeable:
            lat, lon = CITY_COORDS[city]
            for day in get_ensemble_forecast(lat, lon, forecast_days=forecast_days):
                forecast_rows.append({"city": city, **day})
        st.session_state["forecast"] = forecast_rows

forecast_rows = st.session_state.get("forecast", [])

if forecast_rows:
    forecast_df = pd.DataFrame([
        {
            "City": r["city"].title(),
            "Date": r["date"],
            "Predicted High (°F)": r["predicted_high_f"],
            "Model range": f"{r['min_f']} – {r['max_f']}",
            "Spread (°F)": r["spread_f"],
            "Models used": r["model_count"],
        }
        for r in forecast_rows
    ])
    st.dataframe(forecast_df, use_container_width=True, hide_index=True)

    with st.expander("Per-model breakdown"):
        for r in forecast_rows:
            st.write(f"**{r['city'].title()} — {r['date']}**: {r['per_model']}")

    st.info(
        "Lower spread = models agree = more confident. A spread of 10°F+ "
        "means models disagree a lot — be cautious betting an exact threshold."
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
