from django.db import migrations

def fix_null_names(apps, schema_editor):
    # Use a safe DO block to check for column existence before touching it.
    # This prevents errors on DB schemas that do not have `name` column.
    try:
        schema_editor.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'django_content_type' AND column_name = 'name'
            ) THEN
                BEGIN
                    EXECUTE 'DELETE FROM django_content_type WHERE name IS NULL OR name = '''''';
                EXCEPTION WHEN OTHERS THEN
                    -- ignore delete failures
                    NULL;
                END;
                BEGIN
                    EXECUTE 'ALTER TABLE django_content_type ALTER COLUMN name SET DEFAULT ''unknown''';
                EXCEPTION WHEN OTHERS THEN
                    -- ignore alter failures
                    NULL;
                END;
            END IF;
        END
        $$;
        """)
    except Exception:
        # If the database does not support DO blocks or information_schema, ignore
        pass

class Migration(migrations.Migration):

    dependencies = [
        ('core_models', '0004_modelmetadata_remove_airecommendation_context_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_null_names),
    ]
