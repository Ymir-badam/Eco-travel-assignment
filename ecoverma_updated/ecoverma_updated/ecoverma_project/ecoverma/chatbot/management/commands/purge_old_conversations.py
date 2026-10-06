from django.core.management.base import BaseCommand

from chatbot.services import retention


class Command(BaseCommand):
    help = "Delete conversations and carbon calculations older than RETENTION_DAYS."

    def handle(self, *args, **options):
        r = retention.purge_expired()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {r['conversations']} conversations, {r['messages']} messages, "
            f"{r['carbon_calculations']} carbon calculations."
        ))
