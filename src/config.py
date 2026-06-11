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
    # Added after surveying all active "Highest temperature" events
    "amsterdam": (52.3676, 4.9041),
    "ankara": (39.9334, 32.8597),
    "beijing": (39.9042, 116.4074),
    "buenos aires": (-34.6037, -58.3816),
    "busan": (35.1796, 129.0756),
    "cape town": (-33.9249, 18.4241),
    "chengdu": (30.5728, 104.0668),
    "chongqing": (29.4316, 106.9123),
    "guangzhou": (23.1291, 113.2644),
    "helsinki": (60.1699, 24.9384),
    "istanbul": (41.0082, 28.9784),
    "jeddah": (21.4858, 39.1925),
    "karachi": (24.8607, 67.0011),
    "kuala lumpur": (3.1390, 101.6869),
    "lucknow": (26.8467, 80.9462),
    "madrid": (40.4168, -3.7038),
    "manila": (14.5995, 120.9842),
    "mexico city": (19.4326, -99.1332),
    "milan": (45.4642, 9.1900),
    "moscow": (55.7558, 37.6173),
    "munich": (48.1351, 11.5820),
    "panama city": (8.9824, -79.5199),
    "qingdao": (36.0671, 120.3826),
    "sao paulo": (-23.5505, -46.6333),
    "shenzhen": (22.5431, 114.0579),
    "singapore": (1.3521, 103.8198),
    "taipei": (25.0330, 121.5654),
    "tel aviv": (32.0853, 34.7818),
    "warsaw": (52.2297, 21.0122),
    "wuhan": (30.5928, 114.3055),
}

# Only generate picks for cities you can actually bet on.
# Set to None or an empty set to disable filtering (consider all cities).
TRADEABLE_CITIES = {"new york", "nyc", "miami", "chicago", "los angeles", "san francisco"}

# Forecast models, with weights for the weighted-median ensemble.
# JMA (Japan) and Meteo-France are tuned for their home regions and are
# dropped for US cities -- they were the biggest source of spread/outliers
# without adding accuracy for North America.
US_MODEL_WEIGHTS = {
    "ecmwf_ifs025": 2.0,    # generally the strongest global model
    "gfs_seamless": 1.5,    # NOAA, native to the US
    "icon_seamless": 1.0,
    "gem_seamless": 1.0,    # Environment Canada, strong for North America
}
GLOBAL_MODEL_WEIGHTS = {
    **US_MODEL_WEIGHTS,
    "jma_seamless": 1.0,
    "meteofrance_seamless": 1.0,
}


def model_weights_for_city(city: str) -> dict[str, float]:
    """Pick the model weight set for a city: US-tuned models for US cities."""
    if city in TRADEABLE_CITIES:
        return US_MODEL_WEIGHTS
    return GLOBAL_MODEL_WEIGHTS

# Polymarket sweet spot per Polymarket System.md
EDGE_MIN_PRICE = 0.60
EDGE_MAX_PRICE = 0.85

# Minimum probability gap (model vs market) to flag as a pick
MIN_EDGE = 0.10

# Approximate forecast error (std dev, in degrees Fahrenheit) for daily high
# temperature forecasts, by lead time in days. Source bucket is in °F; convert
# to °C (divide by 1.8) for °C buckets.
#
# Tuned via scripts/backtest.py against ~30 days of actual Open-Meteo forecast
# history (previous-runs API) vs observed highs for the 5 tradeable cities.
# The original table was too wide at every lead time -- actual std devs came
# in at 1.65/2.06/2.56/3.55/3.70 for leads 0-4. Kept a small margin above the
# measured values since 30 days is a limited sample.
TEMP_STD_DEV_BY_LEAD_DAYS = {
    0: 1.8,
    1: 2.2,
    2: 2.8,
    3: 3.8,
    4: 4.0,
}
TEMP_STD_DEV_MAX_LEAD = 4.5  # used for any lead time beyond the table above

# The ensemble consistently under-predicted observed highs by ~0.8-1.7°F
# across all lead times in the same backtest. Add this back to the raw
# weighted-median forecast to correct the bias.
TEMP_BIAS_CORRECTION_F = 1.2

# "Highest temperature in X on Y?" events live under this search term.
SEARCH_API_URL = "https://gamma-api.polymarket.com/public-search"
SEARCH_QUERY = "Highest temperature"
MAX_SEARCH_PAGES = 40

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
