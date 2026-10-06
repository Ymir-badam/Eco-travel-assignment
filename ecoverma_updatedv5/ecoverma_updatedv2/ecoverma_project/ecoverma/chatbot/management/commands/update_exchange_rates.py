from django.core.management.base import BaseCommand, CommandError

from chatbot.services import currency


class Command(BaseCommand):
    help = "Fetch the latest ECB exchange rates (Frankfurter) into the database."

    def handle(self, *args, **options):
        try:
            count = currency.refresh_rates()
        except Exception as exc:
            raise CommandError(f"Refresh failed: {exc}")
        self.stdout.write(self.style.SUCCESS(f"Updated {count} exchange rates."))
