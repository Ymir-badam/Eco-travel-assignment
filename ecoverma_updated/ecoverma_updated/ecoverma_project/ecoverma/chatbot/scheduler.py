

import logging
import threading
from datetime import datetime, timedelta

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

logger = logging.getLogger(__name__)

_started = False
_lock = threading.Lock()


def _is_stale(max_age=timedelta(hours=23)):
    from chatbot.models import ExchangeRate

    latest = ExchangeRate.objects.order_by("-updated_at").first()
    return latest is None or timezone.now() - latest.updated_at > max_age


def _run_rates_job():
    from chatbot.services import currency

    close_old_connections()
    try:
        if not _is_stale():
            return
        currency.refresh_rates()
    except Exception:
      
        logger.exception("Daily exchange-rate refresh failed")
    finally:
        close_old_connections()


def _run_purge_job():
    from chatbot.services import retention

    close_old_connections()
    try:
        retention.purge_expired()
    except Exception:
        logger.exception("Retention purge failed")
    finally:
        close_old_connections()


JOBS = [
    ("CURRENCY_REFRESH_TIME", "17:00", _run_rates_job),
    ("RETENTION_PURGE_TIME", "03:00", _run_purge_job),
]


def _seconds_until(setting_name, default):
    hh, mm = getattr(settings, setting_name, default).split(":")
    now = timezone.now()
    target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def _loop(stop_event):

    for _, _, job in JOBS:
        job()
    while not stop_event.is_set():
        waits = [(_seconds_until(name, default), job) for name, default, job in JOBS]
        delay = min(w for w, _ in waits)
        if stop_event.wait(delay):
            break
        for w, job in waits:
            if w - delay < 1: 
                job()


def start():
    global _started
    with _lock:
        if _started:
            return
        _started = True
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_loop, args=(stop_event,), name="daily-scheduler", daemon=True
    )
    thread.start()
    logger.info("Daily scheduler started (rates %s, retention purge %s)",
                getattr(settings, "CURRENCY_REFRESH_TIME", "17:00"),
                getattr(settings, "RETENTION_PURGE_TIME", "03:00"))
