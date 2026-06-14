from django.core.management.base import BaseCommand

from app.services.health_feedback_service import refresh_learning_from_feedback


class Command(BaseCommand):
    help = 'Refresh internal AI learning data from chat history and feedback, then retrain intent classifier.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=500, help='Max number of learning records to scan')

    def handle(self, *args, **options):
        limit = int(options['limit'] or 500)
        result = refresh_learning_from_feedback(limit=limit)
        self.stdout.write(
            self.style.SUCCESS(
                f"Retrained intent model {result.get('version')} | "
                f"learned={result.get('learned_examples', 0)} | "
                f"docs={result.get('trained_documents', 0)} | "
                f"intents={result.get('intent_count', 0)}"
            )
        )
