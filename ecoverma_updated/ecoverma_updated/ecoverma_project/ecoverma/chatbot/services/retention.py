
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def retention_days():
    return int(getattr(settings, "RETENTION_DAYS", 7))


def purge_expired(now=None):
   
    from chatbot.models import CarbonCalculation, Conversation, Message

    cutoff = (now or timezone.now()) - timedelta(days=retention_days())

    _, conv = Conversation.objects.filter(created_at__lt=cutoff).delete()
    _, calc = CarbonCalculation.objects.filter(created_at__lt=cutoff).delete()

    result = {
        "conversations": conv.get("chatbot.Conversation", 0),
        "messages": conv.get("chatbot.Message", 0),
        "carbon_calculations": calc.get("chatbot.CarbonCalculation", 0),
    }
    logger.info("Retention purge (older than %d days): %s", retention_days(), result)
    return result
