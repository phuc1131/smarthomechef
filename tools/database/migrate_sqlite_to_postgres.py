#!/usr/bin/env python
"""
Migration script từ SQLite sang PostgreSQL
Chạy: python tools/database/migrate_sqlite_to_postgres.py
"""

import os
import django
import psycopg2
from django.core.management import call_command
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_chef.settings')
django.setup()

def check_postgres_connection():
    """Kiểm tra kết nối PostgreSQL"""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        print("✅ Kết nối PostgreSQL thành công")
        return True
    except Exception as e:
        print(f"❌ Lỗi kết nối PostgreSQL: {e}")
        return False

def backup_sqlite():
    """Backup SQLite trước migrate"""
    import shutil
    try:
        sqlite_path = 'db.sqlite3'
        if os.path.exists(sqlite_path):
            backup_path = f'db.sqlite3.backup.{django.utils.timezone.now().strftime("%Y%m%d_%H%M%S")}'
            shutil.copy2(sqlite_path, backup_path)
            print(f"✅ Backup SQLite: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Lỗi backup: {e}")
        return False

def run_migrations():
    """Chạy tất cả migrations"""
    try:
        print("\n⏳ Chạy migrations...")
        call_command('migrate', verbosity=1)
        print("✅ Migrations thành công")
        return True
    except Exception as e:
        print(f"❌ Lỗi migrations: {e}")
        return False

def import_sqlite_data():
    """Import dữ liệu từ SQLite nếu có (tuỳ chỉnh theo nhu cầu)"""
    try:
        print("\n⏳ Import dữ liệu từ SQLite...")
        # Sử dụng dumpdata/loaddata
        call_command('dumpdata', '--all', '--output=sqlite_backup.json')
        print("✅ Đã export dữ liệu SQLite ra file JSON")
        print("💡 Để import: python manage.py loaddata sqlite_backup.json")
        return True
    except Exception as e:
        print(f"⚠️  Cảnh báo khi export: {e}")
        return False

def main():
    print("=" * 60)
    print("🔄 MIGRATION SQLITE → POSTGRESQL")
    print("=" * 60)
    
    # 1. Check connection
    if not check_postgres_connection():
        print("\n❌ PostgreSQL không khả dụng!")
        print("📝 Hãy setup PostgreSQL trước:")
        print("   1. Cài đặt PostgreSQL")
        print("   2. Tạo database: createdb smart_chef")
        print("   3. Cập nhật .env với DATABASE_URL")
        return False
    
    # 2. Backup SQLite
    backup_sqlite()
    
    # 3. Run migrations
    if not run_migrations():
        print("\n❌ Migration thất bại!")
        return False
    
    # 4. Import data (optional)
    import_sqlite_data()
    
    print("\n" + "=" * 60)
    print("✅ MIGRATION HOÀN THÀNH!")
    print("=" * 60)
    print("\nBước tiếp theo:")
    print("  1. Kiểm tra dữ liệu: python manage.py shell")
    print("  2. Chạy server: python manage.py runserver")
    
    return True

if __name__ == '__main__':
    main()
