from src.edge_engine import evaluate, model_probability, rank_picks


def test_model_probability_rain():
    parsed = {"condition": "rain"}
    forecast = {"precip_probability": 80}
    assert model_probability(parsed, forecast) == 0.8


def test_model_probability_temp_above_likely():
    parsed = {"condition": "temp_above", "threshold": 90.0}
    forecast = {"temp_max_f": 100.0}
    # forecast well above threshold -> high probability of "Yes"
    assert model_probability(parsed, forecast) > 0.9


def test_model_probability_temp_below_likely():
    parsed = {"condition": "temp_below", "threshold": 40.0}
    forecast = {"temp_min_f": 30.0}
    assert model_probability(parsed, forecast) > 0.9


def test_evaluate_finds_edge():
    parsed = {
        "condition": "rain",
        "market_price": 0.60,
        "question": "Will it rain in Chicago on June 15, 2026?",
        "city": "chicago",
        "target_date": "2026-06-15",
    }
    forecast = {"precip_probability": 90}
    result = evaluate(parsed, forecast)
    assert result is not None
    assert result["recommendation"] == "YES"
    assert result["edge"] > 0


def test_evaluate_skips_outside_sweet_spot():
    parsed = {"condition": "rain", "market_price": 0.95, "question": "q"}
    forecast = {"precip_probability": 99}
    assert evaluate(parsed, forecast) is None


def test_evaluate_skips_small_edge():
    parsed = {"condition": "rain", "market_price": 0.70, "question": "q"}
    forecast = {"precip_probability": 75}
    assert evaluate(parsed, forecast) is None


def test_rank_picks_orders_by_abs_edge():
    picks = [{"edge": 0.1}, {"edge": -0.4}, {"edge": 0.25}]
    ranked = rank_picks(picks, top_n=2)
    assert ranked[0]["edge"] == -0.4
    assert ranked[1]["edge"] == 0.25
