"""Fetch active "Highest temperature in X on Y?" events from the Polymarket
gamma public-search API.

Each event groups several markets together, one per temperature bucket
(e.g. "88-89°F", "87°F or below", "106°F or higher"), each with its own
Yes/No price.
"""

import requests

from src.config import MAX_SEARCH_PAGES, SEARCH_API_URL, SEARCH_QUERY


def fetch_temperature_events() -> list[dict]:
    """Return all active "Highest temperature in X on Y?" events."""
    events = []
    for page in range(1, MAX_SEARCH_PAGES + 1):
        resp = requests.get(
            SEARCH_API_URL,
            params={"q": SEARCH_QUERY, "events_status": "active", "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        page_events = data.get("events", [])
        if not page_events:
            break
        events.extend(page_events)

        if not data.get("pagination", {}).get("hasMore"):
            break

    return events
