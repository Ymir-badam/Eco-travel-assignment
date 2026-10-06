import os
import sys

from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chatbot"

    def ready(self):
        from django.conf import settings

        if not getattr(settings, "CURRENCY_SCHEDULER_ENABLED", True):
            return

        # Only start for a real server process, not migrate/shell/test/etc.
        argv = sys.argv
        if argv and os.path.basename(argv[0]) == "manage.py":
            if len(argv) < 2 or argv[1] != "runserver":
                return
            # runserver's autoreloader spawns two processes; use the child.
            if "--noreload" not in argv and os.environ.get("RUN_MAIN") != "true":
                return

        from . import scheduler

        scheduler.start()
