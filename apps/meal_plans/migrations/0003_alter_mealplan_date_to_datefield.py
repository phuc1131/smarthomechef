from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meal_plans', '0002_remove_mealtypeconfig'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mealplan',
            name='date',
            field=models.DateField(),
        ),
    ]
