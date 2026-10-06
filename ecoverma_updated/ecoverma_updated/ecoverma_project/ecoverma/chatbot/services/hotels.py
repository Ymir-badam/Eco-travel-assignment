"""
02 - Accommodation: hotels near a point, via Overpass.

THE HONESTY PROBLEM (read this before changing the scoring below)
OpenStreetMap has almost no reliable eco-certification data - a handful
of hotels carry a "green_key" or "ecolabel" tag, the overwhelming
majority carry nothing. Presenting an uncertified hotel as "eco-
certified" would be greenwashing, and the brief this bot was built for
explicitly asks that be avoided.

So this module never invents a certification. It reports one of three
states per hotel, always labelled honestly:

  * "certified"    - the data actually carries green_key / ecolabel.
  * "eco proxy"     - no certification, but PROXY indicators suggest a
                       plausibly lower-impact stay: close to public
                       transport and no on-site car park tagged. These
                       are correlations, not evidence, and the bot says
                       so every time it uses them.
  * "unknown"       - neither of the above. The bot says nothing about
                       sustainability for that hotel rather than guessing.
"""

import logging

import requests

from .common import HEADERS, cached_call
from .transport import distance_to_nearest_stop_km, find_transport

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

ECO_PROXY_DISCLAIMER = (
    "These are proxy indicators (close to public transport, no listed "
    "car park) rather than certification - OpenStreetMap doesn't reliably "
    "record eco-certification, so treat this as a rough signal, not proof."
)

NEAR_TRANSIT_KM = 0.6


def _fetch(lat, lon, radius_m, limit):
    query = f"""
    [out:json][timeout:25];
    node["tourism"="hotel"](around:{radius_m},{lat},{lon});
    out body {limit};
    """
    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    hotels = []
    for element in response.json().get("elements", []):
        tags = element.get("tags", {})
        if not tags.get("name"):
            continue
        hotels.append(
            {
                "name": tags["name"],
                "stars": tags.get("stars"),
                "certified_tag": tags.get("green_key") or tags.get("ecolabel"),
                "has_parking_tag": bool(tags.get("parking")),
                "lat": element.get("lat"),
                "lon": element.get("lon"),
            }
        )
    return hotels


def _raw_hotels(lat, lon, radius_m=2000, limit=15):
    cache_key = f"hotels:{round(lat, 3)}:{round(lon, 3)}:{radius_m}:{limit}"
    try:
        return cached_call(cache_key, lambda: _fetch(lat, lon, radius_m, limit))
    except requests.exceptions.RequestException as exc:
        logger.warning("Hotel lookup failed: %s", exc)
        return []


def find_hotels(lat, lon, radius_m=2000, limit=15):
    """
    Named hotels near (lat, lon), each annotated with an honest
    sustainability status: "certified", "eco proxy", or "unknown".
    Never claims certification the data doesn't actually carry.
    """
    hotels = _raw_hotels(lat, lon, radius_m, limit)
    if not hotels:
        return []

    transport_stops = find_transport(lat, lon, radius_m=1500)

    annotated = []
    for hotel in hotels:
        item = dict(hotel)

        if hotel["certified_tag"]:
            item["eco_status"] = "certified"
            item["eco_label"] = f"Certified ({hotel['certified_tag']})"
        else:
            near_transit = False
            if hotel.get("lat") is not None and hotel.get("lon") is not None:
                dist = distance_to_nearest_stop_km(
                    hotel["lat"], hotel["lon"], transport_stops
                )
                near_transit = dist is not None and dist <= NEAR_TRANSIT_KM

            if near_transit and not hotel["has_parking_tag"]:
                item["eco_status"] = "eco proxy"
                item["eco_label"] = "Possible eco proxy (near transit, no car park)"
            else:
                item["eco_status"] = "unknown"
                item["eco_label"] = "Sustainability: not known"

        annotated.append(item)

    return annotated
