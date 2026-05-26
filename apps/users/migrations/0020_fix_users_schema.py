from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_add_userprofile_budget_limit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='email',
            field=models.EmailField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='account',
            name='role',
            field=models.CharField(default='user', max_length=50),
        ),
        migrations.AlterField(
            model_name='account',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='account',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.RunSQL(
            sql=[
                "ALTER TABLE users ALTER COLUMN email DROP NOT NULL;",
                "ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user';",
                "ALTER TABLE users ALTER COLUMN is_active SET DEFAULT true;",
                "ALTER TABLE users ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;",
                "DROP INDEX IF EXISTS users_email_0ea73cca_uniq;",
            ],
            reverse_sql=[
                "ALTER TABLE users ALTER COLUMN role DROP DEFAULT;",
                "ALTER TABLE users ALTER COLUMN is_active DROP DEFAULT;",
                "ALTER TABLE users ALTER COLUMN created_at DROP DEFAULT;",
                "CREATE UNIQUE INDEX IF NOT EXISTS users_email_0ea73cca_uniq ON public.users USING btree (email);",
            ],
        ),
    ]
