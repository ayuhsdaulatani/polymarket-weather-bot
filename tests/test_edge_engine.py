from src.edge_engine import bucket_probability, evaluate, rank_picks


def test_bucket_probability_centered_bucket_is_likely():
    # Forecast high is 94F, bucket is 94-95F -> should capture a decent chunk
    bucket = {"low": 94.0, "high": 95.0, "unit": "F"}
    prob = bucket_probability(bucket, forecast_temp_max_f=94.0)
    assert prob > 0.15


def test_bucket_probability_far_bucket_is_unlikely():
    bucket = {"low": 60.0, "high": 61.0, "unit": "F"}
    prob = bucket_probability(bucket, forecast_temp_max_f=94.0)
    assert prob < 0.01


def test_bucket_probability_unbounded_below():
    bucket = {"low": None, "high": 87.0, "unit": "F"}
    prob = bucket_probability(bucket, forecast_temp_max_f=94.0)
    assert 0 <= prob < 0.06


def test_bucket_probability_unbounded_above():
    bucket = {"low": 106.0, "high": None, "unit": "F"}
    prob = bucket_probability(bucket, forecast_temp_max_f=94.0)
    assert 0 <= prob < 0.05


def test_bucket_probability_celsius_conversion():
    # 94F ~= 34.4C, bucket 34-35C should be likely
    bucket = {"low": 34.0, "high": 35.0, "unit": "C"}
    prob = bucket_probability(bucket, forecast_temp_max_f=94.0)
    assert prob > 0.15


def _pick(market_price, bucket, forecast_high):
    parsed = {
        "bucket": bucket,
        "market_price": market_price,
        "question": "q",
        "city": "nyc",
        "target_date": "2026-06-11",
        "bucket_label": "94-95°F",
    }
    forecast = {"temp_max_f": forecast_high}
    return evaluate(parsed, forecast)


def test_evaluate_finds_edge_when_market_overprices_unlikely_bucket():
    # Market says 60% for a bucket far below the forecast high -> model << 0.60
    result = _pick(0.60, {"low": None, "high": 87.0, "unit": "F"}, 94.0)
    assert result is not None
    assert result["recommendation"] == "NO"
    assert result["edge"] < 0


def test_evaluate_skips_outside_sweet_spot():
    result = _pick(0.95, {"low": 94.0, "high": 95.0, "unit": "F"}, 94.0)
    assert result is None


def test_evaluate_skips_small_edge():
    result = _pick(0.70, {"low": 94.0, "high": 95.0, "unit": "F"}, 94.0)
    # depending on std dev this may or may not be None; just ensure no crash
    assert result is None or abs(result["edge"]) >= 0.10


def test_rank_picks_orders_by_abs_edge():
    picks = [{"edge": 0.1}, {"edge": -0.4}, {"edge": 0.25}]
    ranked = rank_picks(picks, top_n=2)
    assert ranked[0]["edge"] == -0.4
    assert ranked[1]["edge"] == 0.25
