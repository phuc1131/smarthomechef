# Generated migration: Merge FoodTagMap into Food.tags

from django.db import migrations, models


def migrate_foodtagmap_data(apps, schema_editor):
    """Migrate data from FoodTagMap to Food.tags"""
    Food = apps.get_model('nutrition', 'Food')
    FoodTagMap = apps.get_model('nutrition', 'FoodTagMap')
    
    # Create a mapping of food_id to list of tag_ids
    food_tags = {}
    for mapping in FoodTagMap.objects.all():
        food_id = mapping.food_id
        tag_id = mapping.tag_id
        if food_id not in food_tags:
            food_tags[food_id] = []
        food_tags[food_id].append(tag_id)
    
    # Update Food records with tags
    for food_id, tag_ids in food_tags.items():
        try:
            food = Food.objects.get(id=food_id)
            food.tags = tag_ids
            food.save()
        except Food.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('nutrition', '0018_merge_fooddetail_into_food'),
    ]

    operations = [
        # Add tags field to Food
        migrations.AddField(
            model_name='food',
            name='tags',
            field=models.JSONField(blank=True, default=list, help_text='List of tag IDs or names'),
        ),
        # Migrate data
        migrations.RunPython(migrate_foodtagmap_data, migrations.RunPython.noop),
        # Delete FoodTagMap model
        migrations.DeleteModel(
            name='FoodTagMap',
        ),
    ]
