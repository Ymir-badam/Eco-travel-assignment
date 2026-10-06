"""
07 - Currency exchange via Frankfurter (ECB reference rates). No key, no
account. Note this gives END-OF-DAY reference rates, not a live market
or card rate - fine for travel budgeting, but the bot says so.

Rates are stored in the ExchangeRate table (EUR base) and refreshed once a
day by chatbot/scheduler.py (or manually: `manage.py update_exchange_rates`).
convert() reads from that table; if the table is empty (first run, before
the scheduler has fired) it falls back to a live per-pair API call.
"""

import logging
from decimal import Decimal

import requests

from .common import HEADERS, cached_call

logger = logging.getLogger(__name__)

BASE_URL = "https://api.frankfurter.dev/v1"


def refresh_rates():
    """
    Fetch every EUR-based rate from Frankfurter and upsert into the
    ExchangeRate table. Returns the number of currencies stored.
    Raises requests exceptions on network failure (caller decides).
    """
    from datetime import date

    from chatbot.models import ExchangeRate

    response = requests.get(
        f"{BASE_URL}/latest",
        params={"base": "EUR"},
        headers=HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    rate_date = date.fromisoformat(data["date"])
    rates = dict(data["rates"])
    rates["EUR"] = 1  # base currency isn't included in the response

    for code, rate in rates.items():
        ExchangeRate.objects.update_or_create(
            currency_code=code.upper(),
            defaults={"rate_per_eur": Decimal(str(rate)), "rate_date": rate_date},
        )

    logger.info("Exchange rates refreshed: %d currencies, ECB date %s", len(rates), rate_date)
    return len(rates)


def _stored_rate(from_currency, to_currency):
    """Cross rate from the DB, or None if either currency isn't stored."""
    from chatbot.models import ExchangeRate

    rows = {
        r.currency_code: r
        for r in ExchangeRate.objects.filter(
            currency_code__in=[from_currency.upper(), to_currency.upper()]
        )
    }
    src, dst = rows.get(from_currency.upper()), rows.get(to_currency.upper())
    if not src or not dst:
        return None
    rate = float(dst.rate_per_eur / src.rate_per_eur)
    return {"rate": rate, "date": src.rate_date.isoformat()}


def _fetch_rate(from_currency, to_currency):
    response = requests.get(
        f"{BASE_URL}/latest",
        params={"base": from_currency, "symbols": to_currency},
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return {"rate": data["rates"][to_currency], "date": data["date"]}


def convert(amount, from_currency, to_currency):
    """
    Returns (converted_amount, rate, rate_date), or (None, None, None) on
    failure / unknown currency code.
    """
    if not from_currency or not to_currency or from_currency == to_currency:
        return amount, 1.0, None

    try:
        info = _stored_rate(from_currency, to_currency)
    except Exception as exc:  # e.g. table missing before migrate
        logger.warning("Stored-rate lookup failed: %s", exc)
        info = None

    if info:
        return amount * info["rate"], info["rate"], info["date"]

    # Fallback: nothing stored yet for this pair - hit the API (cached).
    cache_key = f"fx:{from_currency.upper()}:{to_currency.upper()}"
    try:
        info = cached_call(
            cache_key,
            lambda: _fetch_rate(from_currency.upper(), to_currency.upper()),
            ttl=60 * 60 * 12,
        )
        return amount * info["rate"], info["rate"], info["date"]
    except (requests.exceptions.RequestException, KeyError) as exc:
        logger.warning("Currency conversion failed: %s", exc)
        return None, None, None
