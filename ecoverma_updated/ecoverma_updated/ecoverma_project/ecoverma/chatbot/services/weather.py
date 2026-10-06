"""
06 - Weather: current conditions + 3-day outlook via Open-Meteo. No key,
no signup, generous limits - and weather is fine to call live (unlike
Overpass/Nominatim map data, it genuinely changes turn to turn).
"""

import logging

import requests

from .common import HEADERS

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather(lat, lon):
    """
    Returns {"current": {...}, "daily": [{"date","temp_max","rain","advice"}]}
    or None if the API call failed.
    """
    try:
        response = requests.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,precipitation,wind_speed_10m",
                "daily": "temperature_2m_max,precipitation_sum",
                "forecast_days": 3,
                "timezone": "auto",
            },
            headers=HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as exc:
        logger.warning("Weather lookup failed: %s", exc)
        return None

    current = data.get("current", {})
    daily = data.get("daily", {})

    days = []
    for i, date in enumerate(daily.get("time", [])):
        tmax = daily["temperature_2m_max"][i]
        rain = daily["precipitation_sum"][i]
        days.append(
            {
                "date": date,
                "temp_max": tmax,
                "rain_mm": rain,
                "advice": travel_advice(tmax, rain),
            }
        )

    return {
        "current": {
            "temperature": current.get("temperature_2m"),
            "precipitation": current.get("precipitation"),
            "wind_speed": current.get("wind_speed_10m"),
        },
        "daily": days,
    }


def travel_advice(temperature, precipitation):
    """Turn raw numbers into a one-line recommendation."""
    if precipitation and precipitation > 5:
        return "wet - plan indoor activities and public transport over cycling"
    if temperature is None:
        return "conditions look reasonable for travel"
    if temperature < 5:
        return "cold - walking tours will be hard going"
    if temperature > 30:
        return "hot - avoid long walks or cycling in the middle of the day"
    return "good conditions for walking and cycling"
