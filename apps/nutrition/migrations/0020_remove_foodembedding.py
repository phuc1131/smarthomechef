# Generated migration: Remove FoodEmbedding model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('nutrition', '0019_merge_foodtagmap_into_food_tags'),
    ]

    operations = [
        migrations.DeleteModel(
            name='FoodEmbedding',
        ),
    ]
