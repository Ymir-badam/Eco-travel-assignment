"""
05 - Place descriptions via the Wikipedia REST API. Turns a bare name
into something worth saying, not just a list. Wikipedia content is
CC BY-SA - we always keep the source link so the bot can attribute it.
"""

import logging
import urllib.parse

import requests

from .common import HEADERS, cached_call

logger = logging.getLogger(__name__)


def _fetch(title, sentences):
    safe_title = urllib.parse.quote(title.replace(" ", "_"))
    response = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}",
        headers=HEADERS,
        timeout=10,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.json()

    text = data.get("extract", "")
    parts = text.split(". ")
    short = ". ".join(parts[:sentences])
    if short and not short.endswith("."):
        short += "."

    return {
        "title": data.get("title"),
        "description": data.get("description"),
        "summary": short,
        "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
    }


def describe(title, sentences=2):
    """
    Short Wikipedia summary for `title`, or None if there's no article.
    Fails cleanly - most small places simply don't have one.
    """
    if not title:
        return None
    try:
        return cached_call(
            f"wiki:{title.lower().strip()}:{sentences}",
            lambda: _fetch(title, sentences),
        )
    except requests.exceptions.RequestException as exc:
        logger.warning("Wikipedia lookup failed for %s: %s", title, exc)
        return None
