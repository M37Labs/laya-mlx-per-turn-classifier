import os
import sys

from django.apps import AppConfig
from django.conf import settings


class ClassifierConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "classifier"
    verbose_name = "Laya demo"

    def ready(self):
        # Start loading the model when the dev server starts, but not for migrate, test, shell, etc.
        # With the autoreloader, only the child process (RUN_MAIN=true) serves requests.
        serving = "runserver" in sys.argv and (
            os.environ.get("RUN_MAIN") == "true" or "--noreload" in sys.argv
        )
        if settings.LAYA_PRELOAD and serving:
            from . import engine

            engine.start_loading()
