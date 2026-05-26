# Generated migration to renumber meal_plans IDs

from django.db import migrations


def renumber_meal_plans(apps, schema_editor):
    """Renumber meal_plans table IDs to start from 1."""
    cursor = schema_editor.connection.cursor()
    vendor = schema_editor.connection.vendor

    print("\nRenumbering meal_plans table...")
    
    # Get current data
    try:
        cursor.execute("SELECT COUNT(*) FROM meal_plans")
        row_count = cursor.fetchone()[0]
    except:
        print("  meal_plans table not found, skipping")
        return

    if row_count == 0:
        print("  meal_plans is empty, resetting sequence only")
        _reset_sequence(cursor, vendor, 'meal_plans')
        return

    # Get all rows ordered by current ID
    cursor.execute("SELECT id FROM meal_plans ORDER BY id")
    old_ids = [row[0] for row in cursor.fetchall()]
    
    print(f"  Current: {row_count} rows, ID range {min(old_ids)} to {max(old_ids)}")

    # Create mapping
    id_mapping = {old_id: new_id for new_id, old_id in enumerate(old_ids, start=1)}

    # Update IDs
    for old_id, new_id in sorted(id_mapping.items()):
        param_format = "?" if vendor == 'sqlite' else "%s"
        cursor.execute(f"UPDATE meal_plans SET id = {param_format} WHERE id = {param_format}", [new_id, old_id])

    # Reset sequence
    _reset_sequence(cursor, vendor, 'meal_plans')
    print(f"  Reset sequence for meal_plans")
    print(f"  Renumbered to 1-{row_count}")


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
        print(f"  Warning: Could not reset sequence: {e}")


def reverse_op(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('meal_plans', '0004_create_meal_plans_table'),
    ]

    operations = [
        migrations.RunPython(renumber_meal_plans, reverse_op),
    ]
