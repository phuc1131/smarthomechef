from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import connection


REQUIRED_TABLES = {
    'users',
    'user_profiles',
    'user_goals',
    'user_feedback',
    'user_preference_profiles',
    'intents',
    'patterns',
    'chat_sessions',
    'chat_messages',
    'message_intents',
    'intent_embeddings',
    'chat_response_caches',
    'foods',
    'food_details',
    'food_ingredients',
    'food_recipes',
    'nutrition_logs',
    'daily_nutrition_summary',
    'meal_plans',
    'meal_type_configs',
    'search_events',
    'ai_recommendations',
}


def _build_required_table_columns():
    required_columns = {}
    for model in apps.get_models():
        table_name = model._meta.db_table
        if table_name not in REQUIRED_TABLES:
            continue

        columns = set()
        for field in model._meta.get_fields():
            if not getattr(field, 'concrete', False):
                continue
            if getattr(field, 'many_to_many', False):
                continue
            if getattr(field, 'column', None):
                columns.add(field.column)

        required_columns[table_name] = columns

    return required_columns


def _find_column_mismatches(existing_tables):
    required_table_columns = _build_required_table_columns()
    missing_columns_by_table = {}

    with connection.cursor() as cursor:
        for table_name, expected_columns in required_table_columns.items():
            if table_name not in existing_tables:
                continue

            table_description = connection.introspection.get_table_description(cursor, table_name)
            actual_columns = {col.name for col in table_description}
            missing_columns = sorted(expected_columns - actual_columns)
            if missing_columns:
                missing_columns_by_table[table_name] = missing_columns

    return missing_columns_by_table


class Command(BaseCommand):
    help = 'Kiem tra schema DB theo mo hinh hien tai; reset DB neu schema sai (SQLite).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-reset',
            action='store_true',
            help='Bo qua kiem tra va reset DB ngay (chi ap dung tu dong cho SQLite).',
        )

    def handle(self, *args, **options):
        vendor = connection.vendor
        self.stdout.write(self.style.WARNING(f'DB vendor hien tai: {vendor}'))

        existing_tables = set(connection.introspection.table_names())
        missing = sorted(REQUIRED_TABLES - existing_tables)
        missing_columns_by_table = _find_column_mismatches(existing_tables)

        if missing:
            self.stdout.write(self.style.WARNING('Schema DB dang thieu cac bang:'))
            for table_name in missing:
                self.stdout.write(f'  - {table_name}')
        elif not missing_columns_by_table:
            self.stdout.write(self.style.SUCCESS('Schema DB da co day du bang can thiet.'))

        if missing_columns_by_table:
            self.stdout.write(self.style.WARNING('Schema DB khong khop truong du lieu hien tai:'))
            for table_name, missing_columns in missing_columns_by_table.items():
                self.stdout.write(f'  - {table_name}: thieu cot {", ".join(missing_columns)}')

        needs_reset = bool(missing) or bool(missing_columns_by_table) or options['force_reset']
        if not needs_reset:
            self.stdout.write(self.style.SUCCESS('Khong can reset DB.'))
            return

        if vendor != 'sqlite':
            self.stdout.write(
                self.style.ERROR(
                    'DB hien tai khong phai SQLite. Vui long backup va drop/create schema thu cong, '
                    'sau do chay migrate.'
                )
            )
            return

        db_name = settings.DATABASES['default']['NAME']
        db_path = Path(str(db_name))
        if db_path.exists():
            db_path.unlink()
            self.stdout.write(self.style.WARNING(f'Da drop SQLite DB: {db_path}'))

        call_command('migrate', interactive=False, verbosity=1)
        self.stdout.write(self.style.SUCCESS('Da tao lai DB va migrate thanh cong.'))
