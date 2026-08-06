import requests
from math import radians, sin, cos, asin, sqrt
from django.core.cache import cache

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
KM_PER_RUPEE = 5

def geocode_address(address: str):
    """
    Returns (latitude, longitude) tuple or None if geocoding fails.
    Nominatim usage policy: max 1 req/sec, must set a User-Agent.
    Cached for 30 days.
    """
    key = f"geocode:{address.lower().strip()}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "YourAppName/1.0 (your-contact@email.com)"},
            timeout=5,
        )
        response.raise_for_status()
        results = response.json()
        if results:
            result = (float(results[0]["lat"]), float(results[0]["lon"]))
            cache.set(key, result, timeout=2592000)  # 30 days
            return result
    except (requests.RequestException, KeyError, ValueError, IndexError):
        pass
    return None


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = radians(float(lat2) - float(lat1))
    dlon = radians(float(lon2) - float(lon1))
    a = sin(dlat / 2) ** 2 + cos(radians(float(lat1))) * cos(radians(float(lat2))) * sin(dlon / 2) ** 2
    return R * 2 * asin(sqrt(a))


def estimate_price(hourly_rate, distance_km, hours=1):
    travel = float(distance_km) * KM_PER_RUPEE
    service = float(hourly_rate) * hours
    return round(travel, 2), round(service, 2), round(travel + service, 2)