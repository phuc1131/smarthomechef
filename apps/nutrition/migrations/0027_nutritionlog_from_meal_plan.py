from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nutrition', '0026_renumber_all_ids_sequential'),
    ]

    operations = [
        migrations.AddField(
            model_name='nutritionlog',
            name='from_meal_plan',
            field=models.BooleanField(default=False, help_text='Được tạo tự động từ kế hoạch thực đơn'),
        ),
    ]
