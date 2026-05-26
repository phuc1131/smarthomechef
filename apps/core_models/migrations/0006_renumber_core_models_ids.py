# Generated migration to renumber core_models tables IDs

from django.db import migrations


def renumber_core_models_tables(apps, schema_editor):
    """Renumber all core_models tables to have sequential IDs starting from 1."""
    cursor = schema_editor.connection.cursor()
    vendor = schema_editor.connection.vendor

    tables_to_renumber = [
        'search_events',
        'ai_recommendations',
        'model_metadata',
    ]

    print("\n=== Renumbering core_models app tables ===")

    for table_name in tables_to_renumber:
        print(f"\nProcessing {table_name}...")
        
        # Check if table exists
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
        except:
            print(f"  {table_name} not found, skipping")
            continue

        if row_count == 0:
            print(f"  {table_name} is empty, resetting sequence only")
            _reset_sequence(cursor, vendor, table_name)
            continue

        # Get all rows ordered by current ID
        cursor.execute(f"SELECT id FROM {table_name} ORDER BY id")
        old_ids = [row[0] for row in cursor.fetchall()]
        
        print(f"  Current: {row_count} rows, ID range {min(old_ids)} to {max(old_ids)}")

        # Create mapping
        id_mapping = {old_id: new_id for new_id, old_id in enumerate(old_ids, start=1)}

        # Update IDs
        for old_id, new_id in sorted(id_mapping.items()):
            param_format = "?" if vendor == 'sqlite' else "%s"
            cursor.execute(f"UPDATE {table_name} SET id = {param_format} WHERE id = {param_format}", [new_id, old_id])

        # Reset sequence
        _reset_sequence(cursor, vendor, table_name)
        print(f"  Reset sequence for {table_name}")
        print(f"  Renumbered to 1-{row_count}")

    print("\n=== Renumbering core_models tables complete ===\n")


def _reset_sequence(cursor, vendor, table_name):
    """Reset the autoincrement sequence for a table."""
    try:
        if vendor == 'sqlite':
            cursor.execute(f"SELECT MAX(id) FROM {table_name}")
            result = cursor.fetchone()
            max_id = result[0] if result and result[0] else 0
            cursor.execute(
                f"UPDATE sqlite_sequence SET seq = ? WHERE name = ?",
                [max_id, table_name]
            )
        elif vendor == 'postgresql':
            cursor.execute(f"SELECT MAX(id) FROM {table_name}")
            result = cursor.fetchone()
            max_id = result[0] if result and result[0] else 0
            seq_name = f"{table_name}_id_seq"
            cursor.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.sequences WHERE sequence_name = %s)", [seq_name])
            if cursor.fetchone()[0]:
                cursor.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH {max_id + 1}")
        elif vendor == 'mysql':
            cursor.execute(f"SELECT MAX(id) FROM {table_name}")
            result = cursor.fetchone()
            max_id = result[0] if result and result[0] else 0
            cursor.execute(f"ALTER TABLE {table_name} AUTO_INCREMENT = {max_id + 1}")
    except Exception as e:
        print(f"  Warning: Could not reset sequence for {table_name}: {e}")


def reverse_op(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core_models', '0005_fix_null_contenttype_names'),
    ]

    operations = [
        migrations.RunPython(renumber_core_models_tables, reverse_op),
    ]
