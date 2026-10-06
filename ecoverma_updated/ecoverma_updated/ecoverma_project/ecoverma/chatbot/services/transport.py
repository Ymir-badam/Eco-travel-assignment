"""
03 - Public transport: stations, subway entrances and tram stops near a
point, via Overpass. This tells you WHERE stops are, not live timetables
(OpenStreetMap doesn't carry those) - see transport_verdict()'s docstring.
"""

import logging
import math

import requests

from .common import HEADERS, cached_call

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def _fetch(lat, lon, radius_m):
    query = f"""
    [out:json][timeout:25];
    (
      node["railway"="station"](around:{radius_m},{lat},{lon});
      node["railway"="subway_entrance"](around:{radius_m},{lat},{lon});
      node["railway"="tram_stop"](around:{radius_m},{lat},{lon});
    );
    out body 25;
    """

    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    stops = []
    for element in response.json().get("elements", []):
        tags = element.get("tags", {})
        stops.append(
            {
                "name": tags.get("name", "(unnamed)"),
                "type": tags.get("railway", "unknown"),
                "lat": element.get("lat"),
                "lon": element.get("lon"),
            }
        )
    return stops


def find_transport(lat, lon, radius_m=1500):
    """
    List of nearby rail/metro/tram access points. Empty list (not an
    exception) if Overpass is unreachable or busy - a chat turn should
    never crash because a free, shared API timed out.
    """
    cache_key = f"transport:{round(lat, 3)}:{round(lon, 3)}:{radius_m}"
    try:
        return cached_call(cache_key, lambda: _fetch(lat, lon, radius_m))
    except requests.exceptions.RequestException as exc:
        logger.warning("Transport lookup failed: %s", exc)
        return []


def transport_verdict(stops):
    """
    Turn a list of stops into one sentence. OpenStreetMap only gives us
    locations, never live schedules, so we deliberately say "well
    connected" rather than anything implying real-time accuracy.
    """
    if not stops:
        return "limited - you would likely need a car or taxi here"
    if len(stops) >= 10:
        return "excellent - you should not need a car"
    if len(stops) >= 3:
        return "reasonable - check specific routes for your trip"
    return "limited - factor transport into your planning"


def _haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def distance_to_nearest_stop_km(lat, lon, stops):
    """Used by hotels.py to build the 'near transit' eco-proxy signal."""
    usable = [s for s in stops if s.get("lat") is not None and s.get("lon") is not None]
    if not usable:
        return None
    return min(_haversine_km(lat, lon, s["lat"], s["lon"]) for s in usable)
