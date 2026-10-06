"""
04 - Cultural experiences: museums and visit-worthy historic sites, via
Overpass. Uses nwr (node+way+relation) rather than node-only, since
larger sites are usually mapped as building outlines (ways), and
constrains "historic" to values a visitor would actually go see.
"""

import logging

import requests

from .common import HEADERS, cached_call

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

VISITABLE_HISTORIC = "castle|monument|ruins|fort|archaeological_site|city_gate"


def _fetch(lat, lon, radius_m, limit):
    query = f"""
    [out:json][timeout:25];
    (
      nwr["tourism"="museum"](around:{radius_m},{lat},{lon});
      nwr["historic"~"^({VISITABLE_HISTORIC})$"](around:{radius_m},{lat},{lon});
    );
    out center {limit};
    """
    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    sites = []
    for element in response.json().get("elements", []):
        tags = element.get("tags", {})
        if not tags.get("name"):
            continue

        center = element.get("center", {})
        sites.append(
            {
                "name": tags["name"],
                "kind": tags.get("tourism") or tags.get("historic"),
                "lat": element.get("lat") or center.get("lat"),
                "lon": element.get("lon") or center.get("lon"),
            }
        )
    return sites


def find_attractions(lat, lon, radius_m=1500, limit=8):
    cache_key = f"attractions:{round(lat, 3)}:{round(lon, 3)}:{radius_m}:{limit}"
    try:
        return cached_call(cache_key, lambda: _fetch(lat, lon, radius_m, limit))
    except requests.exceptions.RequestException as exc:
        logger.warning("Attractions lookup failed: %s", exc)
        return []
