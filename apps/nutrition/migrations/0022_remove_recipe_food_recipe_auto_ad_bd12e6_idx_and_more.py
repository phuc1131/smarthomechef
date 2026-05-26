from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nutrition', '0021_remove_recipetranslation_texttranslation'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='nutritionlog',
                    name='total_calories',
                    field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
                ),
                migrations.AddField(
                    model_name='nutritionlog',
                    name='total_carbs',
                    field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
                ),
                migrations.AddField(
                    model_name='nutritionlog',
                    name='total_fat',
                    field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
                ),
                migrations.AddField(
                    model_name='nutritionlog',
                    name='total_protein',
                    field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
                ),
                migrations.AlterField(
                    model_name='nutritionlog',
                    name='date',
                    field=models.DateField(),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE IF EXISTS nutrition_logs
                        ALTER COLUMN date TYPE date
                        USING date::date;
                    """,
                    reverse_sql="""
                        ALTER TABLE IF EXISTS nutrition_logs
                        ALTER COLUMN date TYPE text
                        USING date::text;
                    """,
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE IF EXISTS nutrition_logs ADD COLUMN IF NOT EXISTS total_calories numeric(10, 2);",
                    reverse_sql="ALTER TABLE IF EXISTS nutrition_logs DROP COLUMN IF EXISTS total_calories;",
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE IF EXISTS nutrition_logs ADD COLUMN IF NOT EXISTS total_protein numeric(10, 2);",
                    reverse_sql="ALTER TABLE IF EXISTS nutrition_logs DROP COLUMN IF EXISTS total_protein;",
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE IF EXISTS nutrition_logs ADD COLUMN IF NOT EXISTS total_carbs numeric(10, 2);",
                    reverse_sql="ALTER TABLE IF EXISTS nutrition_logs DROP COLUMN IF EXISTS total_carbs;",
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE IF EXISTS nutrition_logs ADD COLUMN IF NOT EXISTS total_fat numeric(10, 2);",
                    reverse_sql="ALTER TABLE IF EXISTS nutrition_logs DROP COLUMN IF EXISTS total_fat;",
                ),
            ],
        ),
    ]
