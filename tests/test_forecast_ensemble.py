from src.forecast_ensemble import summarize_daily


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
    # median of [96.0, 96.8, 90.4, 93.2, 81.4, 91.3]
    assert day1["predicted_high_f"] == 92.2
    assert day1["min_f"] == 81.4
    assert day1["max_f"] == 96.8
    assert day1["spread_f"] == round(96.8 - 81.4, 1)


def test_summarize_daily_handles_missing_models():
    daily = {
        "time": ["2026-06-11"],
        "temperature_2m_max_ecmwf_ifs025": [90.0],
        "temperature_2m_max_gfs_seamless": [None],
    }
    summary = summarize_daily(daily)
    assert len(summary) == 1
    assert summary[0]["model_count"] == 1
    assert summary[0]["predicted_high_f"] == 90.0


def test_summarize_daily_skips_days_with_no_data():
    daily = {"time": ["2026-06-11"], "temperature_2m_max_ecmwf_ifs025": [None]}
    assert summarize_daily(daily) == []
