

from django.core.cache import cache

HEADERS = {
    "User-Agent": "BSBI-EcoTravel-Student/1.0 (AUICD; vishwanathkundey@gmail.com)",
    "Accept": "*/*",
    "Referer": "https://www.berlinsbi.com/",
}

DEFAULT_TTL_SECONDS = 60 * 60 * 6  # 6 hours - place data barely changes


def cached_call(cache_key, fetch_fn, ttl=DEFAULT_TTL_SECONDS):
    """
    Return cache[cache_key] if present, otherwise call fetch_fn(), cache
    the result (even if it's an empty list - "we checked and there's
    nothing here" is worth remembering too) and return it.
    """
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    result = fetch_fn()
    cache.set(cache_key, result, ttl)
    return result
