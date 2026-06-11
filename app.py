"""
Streamlit UI for the Polymarket weather bot.

Run with:
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

from src.analysis import scored_buckets
from src.config import EDGE_MAX_PRICE, EDGE_MIN_PRICE, MIN_EDGE, TRADEABLE_CITIES

st.set_page_config(page_title="Polymarket Weather Bot", layout="wide")
st.title("Polymarket Weather Bot")
st.caption(
    "Compares Polymarket 'Highest temperature' bucket prices against an "
    "Open-Meteo forecast model."
)

all_cities = sorted(TRADEABLE_CITIES) if TRADEABLE_CITIES else []
selected_cities = st.multiselect(
    "Cities (only these are tradeable for you)",
    options=all_cities,
    default=all_cities,
)

if st.button("Refresh picks", type="primary") or "data" not in st.session_state:
    with st.spinner("Fetching markets and forecasts..."):
        st.session_state["data"] = scored_buckets(cities=set(selected_cities) or None)

rows = st.session_state.get("data", [])
rows = [r for r in rows if r["city"] in selected_cities] if selected_cities else rows

if not rows:
    st.info("No data yet — click 'Refresh picks'.")
    st.stop()

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

st.subheader("Picks (in sweet spot, edge ≥ threshold)")
in_sweet_spot = df["Market price (Yes)"].between(EDGE_MIN_PRICE, EDGE_MAX_PRICE)
has_edge = df["Edge"].abs() >= MIN_EDGE
picks_df = df[in_sweet_spot & has_edge].sort_values("Edge", key=abs, ascending=False)

if picks_df.empty:
    st.write("No picks above the edge threshold right now.")
else:
    st.dataframe(picks_df, use_container_width=True, hide_index=True)
    same_day = picks_df[picks_df["Days ahead"] == 0]
    if not same_day.empty:
        st.warning(
            "Same-day picks (Days ahead = 0) can be unreliable: a confident "
            "market price often means traders already see the live "
            "temperature, while Open-Meteo's forecast may be stale. "
            "Treat 1+ day picks as more trustworthy."
        )

st.subheader("All scored buckets")
st.dataframe(
    df.sort_values(["City", "Date", "Bucket"]),
    use_container_width=True,
    hide_index=True,
)
