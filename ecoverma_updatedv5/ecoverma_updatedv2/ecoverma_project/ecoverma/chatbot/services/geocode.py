"""
01 - Geocoding: place name -> (lat, lon, display_name), via Nominatim.
Almost everything else in this package needs coordinates, so this is
usually the first call made for a new destination.
"""

import logging

import requests

from .common import HEADERS, cached_call

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def _fetch(place):
    response = requests.get(
        NOMINATIM_URL,
        params={"q": place, "format": "json", "limit": 1},
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    results = response.json()

    if not results:
        return None

    item = results[0]
    return {
        "lat": float(item["lat"]),
        "lon": float(item["lon"]),
        "display_name": item["display_name"],
    }


def geocode(place):
    """
    Turn a place name into a dict {lat, lon, display_name}, or None if
    nothing matched. Cached, since a city's coordinates never change and
    Nominatim's usage policy caps requests at one per second.
    """
    if not place:
        return None

    try:
        return cached_call(f"geocode:{place.lower().strip()}", lambda: _fetch(place))
    except requests.exceptions.RequestException as exc:
        logger.warning("Geocoding failed for %s: %s", place, exc)
        return None
