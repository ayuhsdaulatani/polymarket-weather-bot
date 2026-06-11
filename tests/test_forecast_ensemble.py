from src.config import TEMP_BIAS_CORRECTION_F, US_MODEL_WEIGHTS
from src.forecast_ensemble import summarize_daily, weighted_median


def test_weighted_median_picks_value_at_half_total_weight():
    # sorted: 1(w1), 2(w1), 3(w2) -> total=4, half=2 -> cumulative reaches 2 at value=2
    assert weighted_median([3, 1, 2], [2, 1, 1]) == 2


def test_summarize_daily_basic():
    daily = {
        "time": ["2026-06-11", "2026-06-12"],
        "temperature_2m_max_ecmwf_ifs025": [96.0, 95.8],
        "temperature_2m_max_gfs_seamless": [96.8, 92.8],
        "temperature_2m_max_icon_seamless": [90.4, 92.2],
        "temperature_2m_max_gem_seamless": [93.2, 92.6],
        "temperature_2m_max_jma_seamless": [81.4, 81.4],
        "temperature_2m_max_meteofrance_seamless": [91.3, 86.1],
    }
    summary = summarize_daily(daily)

    assert len(summary) == 2

    day1 = summary[0]
    assert day1["date"] == "2026-06-11"
    assert day1["model_count"] == 6
    # weighted median (ecmwf x2.0, gfs x1.5, others x1.0; half of total 7.5 = 3.75)
    # sorted: 81.4, 90.4, 91.3, 93.2(cum=4.0 >= 3.75) -> 93.2, plus bias correction
    assert day1["predicted_high_f"] == round(93.2 + TEMP_BIAS_CORRECTION_F, 1)
    assert day1["min_f"] == 81.4
    assert day1["max_f"] == 96.8
    assert day1["spread_f"] == round(96.8 - 81.4, 1)


def test_summarize_daily_with_us_weights_drops_regional_models():
    daily = {
        "time": ["2026-06-11"],
        "temperature_2m_max_ecmwf_ifs025": [96.0],
        "temperature_2m_max_gfs_seamless": [96.8],
        "temperature_2m_max_icon_seamless": [90.4],
        "temperature_2m_max_gem_seamless": [93.2],
        "temperature_2m_max_jma_seamless": [81.4],
        "temperature_2m_max_meteofrance_seamless": [91.3],
    }
    summary = summarize_daily(daily, weights=US_MODEL_WEIGHTS)

    assert len(summary) == 1
    day1 = summary[0]
    # JMA/Meteo-France excluded entirely
    assert day1["model_count"] == 4
    assert "jma_seamless" not in day1["per_model"]
    assert "meteofrance_seamless" not in day1["per_model"]
    # spread should be tighter without the 81.4 outlier
    assert day1["min_f"] == 90.4
    assert day1["max_f"] == 96.8


def test_summarize_daily_handles_missing_models():
    daily = {
        "time": ["2026-06-11"],
        "temperature_2m_max_ecmwf_ifs025": [90.0],
        "temperature_2m_max_gfs_seamless": [None],
    }
    summary = summarize_daily(daily)
    assert len(summary) == 1
    assert summary[0]["model_count"] == 1
    assert summary[0]["predicted_high_f"] == round(90.0 + TEMP_BIAS_CORRECTION_F, 1)


def test_summarize_daily_skips_days_with_no_data():
    daily = {"time": ["2026-06-11"], "temperature_2m_max_ecmwf_ifs025": [None]}
    assert summarize_daily(daily) == []
