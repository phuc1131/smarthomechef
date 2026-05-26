# Generated migration to renumber chat tables IDs

from django.db import migrations


def renumber_chat_tables(apps, schema_editor):
    """Renumber all chat tables to have sequential IDs starting from 1."""
    print("\n=== Skipping legacy chat renumber migration; IDs are maintained elsewhere ===\n")
    return


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
        ('chat', '0005_remove_chatresponsecache_chat_respon_account_98657b_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(renumber_chat_tables, reverse_op),
    ]
