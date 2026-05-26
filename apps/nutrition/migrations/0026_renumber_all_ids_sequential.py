# Generated migration to renumber all IDs starting from 1 with no gaps

from django.db import migrations


def renumber_all_ids(apps, schema_editor):
    """
    Renumber all table IDs to start from 1 with no gaps.
    Uses temporary negative IDs to avoid PK conflicts during updates.
    """
    cursor = schema_editor.connection.cursor()
    vendor = schema_editor.connection.vendor

    print("\n=== Renumbering all table IDs ===")
    _disable_fk_constraints(cursor, vendor)

    try:
        # Process foods first with all its FKs (only list tables that actually exist)
        _renumber_table_with_fks(cursor, vendor, 'foods', [
            ('food_ingredients', 'food_id'),
            ('food_recipes', 'food_id'),
            ('food_popularity', 'food_id'),
        ])

        # Process other tables
        _renumber_table(cursor, vendor, 'food_categories')
        _renumber_table(cursor, vendor, 'meal_plans')
        _renumber_table(cursor, vendor, 'chat_sessions')
        _renumber_table(cursor, vendor, 'chat_messages')
        _renumber_table(cursor, vendor, 'intents')
        _renumber_table(cursor, vendor, 'patterns')
        _renumber_table(cursor, vendor, 'message_intents')
        _renumber_table(cursor, vendor, 'chat_summaries')
        _renumber_table(cursor, vendor, 'accounts')
        _renumber_table(cursor, vendor, 'user_profiles')
        _renumber_table(cursor, vendor, 'user_goals')
        _renumber_table(cursor, vendor, 'search_events')
        _renumber_table(cursor, vendor, 'ai_recommendations')
    finally:
        _enable_fk_constraints(cursor, vendor)

    print("\n=== Renumbering complete ===\n")


def _disable_fk_constraints(cursor, vendor):
    if vendor == 'postgresql':
        cursor.execute("SET session_replication_role = 'replica'")


def _enable_fk_constraints(cursor, vendor):
    if vendor == 'postgresql':
        cursor.execute("SET session_replication_role = 'origin'")


def _renumber_table(cursor, vendor, table_name):
    """Renumber a single table to have sequential IDs from 1."""
    if not _table_exists(cursor, vendor, table_name):
        print(f"  Skipping {table_name}: table does not exist")
        return

    print(f"\nProcessing {table_name}...")

    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]

    if row_count == 0:
        print(f"  {table_name} is empty")
        return

    # Get all current IDs
    cursor.execute(f"SELECT id FROM {table_name} ORDER BY id")
    old_ids = [row[0] for row in cursor.fetchall()]
    
    print(f"  Rows: {row_count}, ID range: {min(old_ids)}-{max(old_ids)}")

    # Use temporary negative IDs to avoid PK conflicts
    for new_id, old_id in enumerate(old_ids, start=1):
        if new_id != old_id:
            temp_id = -(new_id + 100000)
            cursor.execute(f"UPDATE {table_name} SET id = %s WHERE id = %s", [temp_id, old_id])
    
    # Update from temp to final IDs
    for new_id in range(1, row_count + 1):
        temp_id = -(new_id + 100000)
        cursor.execute(f"UPDATE {table_name} SET id = %s WHERE id = %s", [new_id, temp_id])
    
    _reset_sequence(cursor, vendor, table_name, row_count)
    print(f"  Renumbered to 1-{row_count}")


def _renumber_table_with_fks(cursor, vendor, table_name, fk_refs):
    """Renumber a table and update all its FK references."""
    if not _table_exists(cursor, vendor, table_name):
        return

    print(f"\nProcessing {table_name} (with FKs)...")
    
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]
    
    if row_count == 0:
        print(f"  {table_name} is empty")
        return

    # Get all current IDs
    cursor.execute(f"SELECT id FROM {table_name} ORDER BY id")
    old_ids = [row[0] for row in cursor.fetchall()]
    
    print(f"  Rows: {row_count}, ID range: {min(old_ids)}-{max(old_ids)}")

    # Build mapping
    id_mapping = {old_id: new_id for new_id, old_id in enumerate(old_ids, start=1)}

    # IMPORTANT: Update FKs FIRST before updating parent table to avoid FK violations
    # Update all child tables with temporary IDs
    for old_id, new_id in id_mapping.items():
        if new_id != old_id:
            temp_id = -(new_id + 100000)
            
            # Update all FKs to temp IDs
            for fk_table, fk_col in fk_refs:
                if _table_exists(cursor, vendor, fk_table):
                    try:
                        cursor.execute(f"UPDATE {fk_table} SET {fk_col} = %s WHERE {fk_col} = %s", [temp_id, old_id])
                    except Exception:
                        pass
            
            # THEN update parent table ID
            cursor.execute(f"UPDATE {table_name} SET id = %s WHERE id = %s", [temp_id, old_id])
    
    # Update parent from temp to final IDs and update FKs along the way
    for new_id in range(1, row_count + 1):
        temp_id = -(new_id + 100000)
        
        # Update FKs to final IDs first
        for fk_table, fk_col in fk_refs:
            if _table_exists(cursor, vendor, fk_table):
                try:
                    cursor.execute(f"UPDATE {fk_table} SET {fk_col} = %s WHERE {fk_col} = %s", [new_id, temp_id])
                except Exception:
                    pass
        
        # Then update parent table
        cursor.execute(f"UPDATE {table_name} SET id = %s WHERE id = %s", [new_id, temp_id])
    
    _reset_sequence(cursor, vendor, table_name, row_count)
    print(f"  Renumbered to 1-{row_count}, FKs updated")



def reverse_renumber(apps, schema_editor):
    """Reverse operation - not feasible for data transformation, so pass."""
    pass


def _table_exists(cursor, vendor, table_name):
    """Check if table exists in the current database."""
    try:
        if vendor == 'sqlite':
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                [table_name]
            )
            return cursor.fetchone() is not None
        elif vendor == 'postgresql':
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = %s
                )
                """,
                [table_name]
            )
            return bool(cursor.fetchone()[0])
        elif vendor == 'mysql':
            cursor.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_NAME=%s",
                [table_name]
            )
            return cursor.fetchone() is not None
        return False
    except Exception:
        return False


def _reset_sequence(cursor, vendor, table_name, max_id):
    """Reset the autoincrement sequence for a table."""
    try:
        if vendor == 'sqlite':
            cursor.execute(
                f"UPDATE sqlite_sequence SET seq = ? WHERE name = ?",
                [max_id, table_name]
            )
        elif vendor == 'postgresql':
            seq_name = f"{table_name}_id_seq"
            cursor.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.sequences WHERE sequence_name = %s)", [seq_name])
            if cursor.fetchone()[0]:
                cursor.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH {max_id + 1}")
        elif vendor == 'mysql':
            cursor.execute(f"ALTER TABLE {table_name} AUTO_INCREMENT = {max_id + 1}")
    except Exception:
        pass



class Migration(migrations.Migration):

    dependencies = [
        ('nutrition', '0025_add_ingredient_category'),
    ]

    operations = [
        migrations.RunPython(renumber_all_ids, reverse_renumber),
    ]
