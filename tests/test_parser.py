from src.parser import find_city, find_date, parse_market


def test_find_city_match():
    result = find_city("Will it rain in New York on June 15, 2026?")
    assert result is not None
    assert result[0] == "new york"


def test_find_city_no_match():
    assert find_city("Will the Lakers win tonight?") is None


def test_find_date_from_text():
    assert find_date("Will it rain on June 15, 2026?") == "2026-06-15"


def test_find_date_fallback_to_end_date():
    assert find_date("Will it rain in NYC?", "2026-06-20T00:00:00Z") == "2026-06-20"


def test_parse_market_rain():
    market = {
        "id": "1",
        "question": "Will it rain in Chicago on June 15, 2026?",
        "endDate": "2026-06-15T00:00:00Z",
        "outcomePrices": '["0.65", "0.35"]',
    }
    parsed = parse_market(market)
    assert parsed["city"] == "chicago"
    assert parsed["condition"] == "rain"
    assert parsed["target_date"] == "2026-06-15"
    assert parsed["market_price"] == 0.65


def test_parse_market_temp_above():
    market = {
        "id": "2",
        "question": "Will the high temperature in Miami be above 95°F on July 4, 2026?",
        "endDate": "2026-07-04T00:00:00Z",
        "outcomePrices": '["0.40", "0.60"]',
    }
    parsed = parse_market(market)
    assert parsed["condition"] == "temp_above"
    assert parsed["threshold"] == 95.0


def test_parse_market_unknown_returns_none():
    market = {"id": "3", "question": "Will the Lakers win the title?", "outcomePrices": "[]"}
    assert parse_market(market) is None
