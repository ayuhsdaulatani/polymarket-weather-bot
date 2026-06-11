"""Static configuration: city coordinates and edge thresholds."""

# Lat/lon for cities commonly used in Polymarket "Highest temperature in X" markets.
# Keys are matched as substrings against event titles (lowercased), so keep
# them specific enough to avoid false matches.
CITY_COORDS = {
    "new york": (40.7128, -74.0060),
    "nyc": (40.7128, -74.0060),
    "los angeles": (34.0522, -118.2437),
    "chicago": (41.8781, -87.6298),
    "miami": (25.7617, -80.1918),
    "houston": (29.7604, -95.3698),
    "phoenix": (33.4484, -112.0740),
    "philadelphia": (39.9526, -75.1652),
    "san antonio": (29.4241, -98.4936),
    "san diego": (32.7157, -117.1611),
    "dallas": (32.7767, -96.7970),
    "austin": (30.2672, -97.7431),
    "seattle": (47.6062, -122.3321),
    "denver": (39.7392, -104.9903),
    "boston": (42.3601, -71.0589),
    "atlanta": (33.7490, -84.3880),
    "san francisco": (37.7749, -122.4194),
    "washington": (38.9072, -77.0369),
    "las vegas": (36.1699, -115.1398),
    "london": (51.5074, -0.1278),
    "paris": (48.8566, 2.3522),
    "seoul": (37.5665, 126.9780),
    "tokyo": (35.6762, 139.6503),
    "hong kong": (22.3193, 114.1694),
    "shanghai": (31.2304, 121.4737),
    "wellington": (-41.2865, 174.7762),
    "toronto": (43.6532, -79.3832),
    "dubai": (25.2048, 55.2708),
}

# Polymarket sweet spot per Polymarket System.md
EDGE_MIN_PRICE = 0.60
EDGE_MAX_PRICE = 0.85

# Minimum probability gap (model vs market) to flag as a pick
MIN_EDGE = 0.10

# "Highest temperature in X on Y?" events live under this search term.
SEARCH_API_URL = "https://gamma-api.polymarket.com/public-search"
SEARCH_QUERY = "Highest temperature"
MAX_SEARCH_PAGES = 20

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
