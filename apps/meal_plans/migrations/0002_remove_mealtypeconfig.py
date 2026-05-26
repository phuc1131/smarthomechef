# Generated migration: Remove MealTypeConfig model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('meal_plans', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='MealTypeConfig',
                ),
            ],
            database_operations=[],
        ),
    ]
