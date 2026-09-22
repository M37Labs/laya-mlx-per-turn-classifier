from django.core.management.base import BaseCommand

from classifier import seed
from classifier.models import Example, Field, UseCase


class Command(BaseCommand):
    help = "Load the demo use cases. Existing ones are kept unless --reset is given."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Replace demo use cases with the defaults, discarding admin edits to them.",
        )

    def handle(self, *args, reset=False, **options):
        n = seed.load(UseCase, Field, Example, reset=reset)
        self.stdout.write(self.style.SUCCESS(f"Loaded {n} use case(s)."))
