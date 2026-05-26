#!/usr/bin/env python
"""Inspect database tables used by Django models and report their status."""

import os
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_chef.settings")

import django

django.setup()

from django.apps import apps
from django.db import connection


def safe_count(cursor, table_name):
    try:
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        return cursor.fetchone()[0], None
    except Exception as exc:
        return None, str(exc)


def main():
    report_path = WORKSPACE_ROOT / "artifacts" / "logs" / "runtime_tables_report.txt"

    lines = []
    lines.append("=" * 100)
    lines.append("RUNTIME TABLE USAGE REPORT")
    lines.append("=" * 100)

    existing_tables = sorted(connection.introspection.table_names())
    existing_set = set(existing_tables)

    model_rows = []
    with connection.cursor() as cursor:
        for model in apps.get_models():
            app_label = model._meta.app_label
            model_name = model.__name__
            table_name = model._meta.db_table
            exists = table_name in existing_set

            row_count = None
            error = None
            if exists:
                row_count, error = safe_count(cursor, table_name)

            model_rows.append(
                {
                    "app": app_label,
                    "model": model_name,
                    "table": table_name,
                    "exists": exists,
                    "count": row_count,
                    "error": error,
                }
            )

    mapped_tables = sorted({row["table"] for row in model_rows})
    mapped_set = set(mapped_tables)
    extra_tables = [name for name in existing_tables if name not in mapped_set]

    lines.append("")
    lines.append("[A] TABLES USED BY DJANGO MODELS")
    lines.append("-" * 100)
    lines.append(f"{'APP':14} {'MODEL':32} {'TABLE':40} {'EXISTS':7} {'ROWS':10}")
    lines.append("-" * 100)

    missing_count = 0
    for row in sorted(model_rows, key=lambda x: (x["app"], x["table"], x["model"])):
        exists_text = "YES" if row["exists"] else "NO"
        rows_text = "-"
        if row["count"] is not None:
            rows_text = str(row["count"])
        elif row["error"]:
            rows_text = "ERR"

        lines.append(
            f"{row['app'][:14]:14} {row['model'][:32]:32} {row['table'][:40]:40} {exists_text:7} {rows_text:10}"
        )

        if not row["exists"]:
            missing_count += 1

    lines.append("")
    lines.append("[B] TABLES IN DATABASE NOT MAPPED TO DJANGO MODELS")
    lines.append("-" * 100)
    if extra_tables:
        for name in extra_tables:
            lines.append(f"- {name}")
    else:
        lines.append("(none)")

    lines.append("")
    lines.append("[C] SUMMARY")
    lines.append("-" * 100)
    lines.append(f"Total Django models: {len(model_rows)}")
    lines.append(f"Unique model tables: {len(mapped_tables)}")
    lines.append(f"Existing DB tables: {len(existing_tables)}")
    lines.append(f"Missing model tables: {missing_count}")
    lines.append(f"Extra DB tables (not mapped): {len(extra_tables)}")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")

    # Print a concise runtime summary for terminal output.
    print("Database engine:", connection.vendor)
    print("Total models:", len(model_rows))
    print("Unique model tables:", len(mapped_tables))
    print("Existing DB tables:", len(existing_tables))
    print("Missing model tables:", missing_count)
    print("Extra DB tables:", len(extra_tables))
    print("Report written to:", report_path)


if __name__ == "__main__":
    main()
