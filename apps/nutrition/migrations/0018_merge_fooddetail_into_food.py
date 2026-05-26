# Generated migration: Merge FoodDetail into Food

from django.db import migrations, models


def migrate_fooddetail_data(apps, schema_editor):
    """Migrate data from FoodDetail to Food table"""
    Food = apps.get_model('nutrition', 'Food')
    FoodDetail = apps.get_model('nutrition', 'FoodDetail')
    
    for detail in FoodDetail.objects.all():
        try:
            food = Food.objects.get(id=detail.food_id)
            food.sugar = detail.sugar
            food.sodium = detail.sodium
            food.cholesterol = detail.cholesterol
            food.vitamin_a = detail.vitamin_a
            food.vitamin_c = detail.vitamin_c
            food.calcium = detail.calcium
            food.iron = detail.iron
            food.save()
        except Food.DoesNotExist:
            # Food no longer exists, skip
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('nutrition', '0017_alter_food_calories_alter_food_carbs_alter_food_fat_and_more'),
    ]

    operations = [
        # Add new fields to Food
        migrations.AddField(
            model_name='food',
            name='sugar',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='food',
            name='sodium',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='food',
            name='cholesterol',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='food',
            name='vitamin_a',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='food',
            name='vitamin_c',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='food',
            name='calcium',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='food',
            name='iron',
            field=models.FloatField(blank=True, null=True),
        ),
        # Migrate data
        migrations.RunPython(migrate_fooddetail_data, migrations.RunPython.noop),
        # Delete FoodDetail model
        migrations.DeleteModel(
            name='FoodDetail',
        ),
    ]
