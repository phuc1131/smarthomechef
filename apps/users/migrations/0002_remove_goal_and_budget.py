# Generated migration: Remove Goal, GoalNutritionRule, UserBudgetLog

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Goal',
        ),
        migrations.DeleteModel(
            name='GoalNutritionRule',
        ),
        migrations.DeleteModel(
            name='UserBudgetLog',
        ),
    ]
