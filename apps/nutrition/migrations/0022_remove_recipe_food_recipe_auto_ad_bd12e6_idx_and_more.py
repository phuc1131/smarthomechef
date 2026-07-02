from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nutrition', '0021_remove_recipetranslation_texttranslation'),
    ]

    operations = [
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
    ]
