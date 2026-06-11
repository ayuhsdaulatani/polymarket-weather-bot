from src.parser import find_city, parse_bucket, parse_event


def test_find_city_match():
    result = find_city("Highest temperature in NYC on June 11?")
    assert result is not None
    assert result[0] == "nyc"


def test_find_city_no_match():
    assert find_city("Will the Lakers win tonight?") is None


def test_parse_bucket_range():
    assert parse_bucket("88-89°F") == {"low": 88.0, "high": 89.0, "unit": "F"}


def test_parse_bucket_below():
    assert parse_bucket("87°F or below") == {"low": None, "high": 87.0, "unit": "F"}


def test_parse_bucket_above():
    assert parse_bucket("106°F or higher") == {"low": 106.0, "high": None, "unit": "F"}


def test_parse_bucket_single_celsius():
    assert parse_bucket("23°C") == {"low": 23.0, "high": 23.0, "unit": "C"}


def test_parse_bucket_unrecognized():
    assert parse_bucket("not a bucket") is None


def _market(group_item_title, price="0.5", end_date="2026-06-11T12:00:00Z"):
    return {
        "id": "1",
        "question": f"Will the highest temperature be {group_item_title} on June 11?",
        "groupItemTitle": group_item_title,
        "outcomePrices": json_prices(price),
        "endDate": end_date,
    }


def json_prices(yes_price):
    import json
    return json.dumps([yes_price, str(round(1 - float(yes_price), 4))])


def test_parse_event_returns_bucket_markets():
    event = {
        "title": "Highest temperature in NYC on June 11?",
        "markets": [
            _market("87°F or below", "0.001"),
            _market("88-89°F", "0.0175"),
            _market("106°F or higher", "0.0005"),
        ],
    }
    parsed = parse_event(event)
    assert len(parsed) == 3
    assert parsed[0]["city"] == "nyc"
    assert parsed[0]["target_date"] == "2026-06-11"
    assert parsed[1]["bucket"] == {"low": 88.0, "high": 89.0, "unit": "F"}
    assert parsed[1]["market_price"] == 0.0175


def test_parse_event_unknown_city_returns_empty():
    event = {
        "title": "Highest temperature in Atlantis on June 11?",
        "markets": [_market("88-89°F")],
    }
    assert parse_event(event) == []


def test_parse_event_non_temperature_returns_empty():
    event = {"title": "Will the Lakers win the title?", "markets": []}
    assert parse_event(event) == []
