from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meal_plans', '0005_renumber_meal_plans_ids'),
    ]

    operations = [
        migrations.AddField(
            model_name='mealplan',
            name='stt',
            field=models.IntegerField(null=True, blank=True, db_index=True),
        ),
    ]
