# Generated migration to renumber users tables IDs

from django.db import migrations


def renumber_users_tables(apps, schema_editor):
    """Renumber users-related tables safely while updating FK references."""
    cursor = schema_editor.connection.cursor()
    vendor = schema_editor.connection.vendor

    print("\n=== Renumbering users app tables ===")
    _disable_fk_constraints(cursor, vendor)

    try:
        tables_to_renumber = [
            ('users', [
                ('user_profiles', 'account_id'),
                ('user_preference_profiles', 'account_id'),
                ('user_goals', 'account_id'),
                ('user_feedback', 'account_id'),
                ('user_behavior_log', 'account_id'),
                ('user_diseases', 'account_id'),
            ]),
            ('user_profiles', []),
            ('user_goals', []),
            ('user_feedback', []),
            ('user_behavior_log', []),
            ('user_diseases', [('disease_nutrition_rules', 'disease_id')]),
            ('diseases', [('user_diseases', 'disease_id'), ('disease_nutrition_rules', 'disease_id')]),
        ]

        for table_name, fk_refs in tables_to_renumber:
            _renumber_table(cursor, vendor, table_name, fk_refs)
    finally:
        _enable_fk_constraints(cursor, vendor)

    print("\n=== Renumbering users tables complete ===\n")


def _disable_fk_constraints(cursor, vendor):
    if vendor == 'postgresql':
        cursor.execute("SET session_replication_role = 'replica'")


def _enable_fk_constraints(cursor, vendor):
    if vendor == 'postgresql':
        cursor.execute("SET session_replication_role = 'origin'")


def _table_exists(cursor, vendor, table_name):
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


def _renumber_table(cursor, vendor, table_name, fk_refs=None):
    if not _table_exists(cursor, vendor, table_name):
        print(f"  {table_name} not found, skipping")
        return

    print(f"\nProcessing {table_name}...")

    try:
        cursor.execute(f"SELECT id FROM {table_name} ORDER BY id")
    except Exception:
        print(f"  {table_name} has no id column, skipping")
        return

    old_ids = [row[0] for row in cursor.fetchall()]

    if not old_ids:
        print(f"  {table_name} is empty")
        return

    if old_ids[0] == 1 and old_ids[-1] == len(old_ids) and len(set(old_ids)) == len(old_ids):
        print(f"  {table_name} already sequential")
        return

    print(f"  Current: {len(old_ids)} rows, ID range {min(old_ids)} to {max(old_ids)}")

    param_format = "?" if vendor == 'sqlite' else "%s"
    id_mapping = {old_id: new_id for new_id, old_id in enumerate(old_ids, start=1)}

    for old_id, new_id in id_mapping.items():
        if new_id == old_id:
            continue
        temp_id = -(new_id + 100000)

        for fk_table, fk_col in fk_refs or []:
            if _table_exists(cursor, vendor, fk_table):
                try:
                    cursor.execute(
                        f"UPDATE {fk_table} SET {fk_col} = {param_format} WHERE {fk_col} = {param_format}",
                        [temp_id, old_id],
                    )
                except Exception:
                    pass

        cursor.execute(
            f"UPDATE {table_name} SET id = {param_format} WHERE id = {param_format}",
            [temp_id, old_id],
        )

    for new_id in range(1, len(old_ids) + 1):
        temp_id = -(new_id + 100000)

        for fk_table, fk_col in fk_refs or []:
            if _table_exists(cursor, vendor, fk_table):
                try:
                    cursor.execute(
                        f"UPDATE {fk_table} SET {fk_col} = {param_format} WHERE {fk_col} = {param_format}",
                        [new_id, temp_id],
                    )
                except Exception:
                    pass

        cursor.execute(
            f"UPDATE {table_name} SET id = {param_format} WHERE id = {param_format}",
            [new_id, temp_id],
        )

    _reset_sequence(cursor, vendor, table_name, len(old_ids))
    print(f"  Renumbered to 1-{len(old_ids)}")


def _reset_sequence(cursor, vendor, table_name, max_id):
    """Reset the autoincrement sequence for a table."""
    try:
        if vendor == 'sqlite':
            cursor.execute(
                f"UPDATE sqlite_sequence SET seq = ? WHERE name = ?",
                [max_id, table_name],
            )
        elif vendor == 'postgresql':
            seq_name = f"{table_name}_id_seq"
            cursor.execute(
                f"SELECT EXISTS (SELECT 1 FROM information_schema.sequences WHERE sequence_name = %s)",
                [seq_name],
            )
            if cursor.fetchone()[0]:
                cursor.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH {max_id + 1}")
        elif vendor == 'mysql':
            cursor.execute(f"ALTER TABLE {table_name} AUTO_INCREMENT = {max_id + 1}")
    except Exception as e:
        print(f"  Warning: Could not reset sequence for {table_name}: {e}")


def reverse_op(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0021_remove_account_users_email_4b85f2_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(renumber_users_tables, reverse_op),
    ]
