# Generated migration: Remove RecipeTranslation and TextTranslation models

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('nutrition', '0020_remove_foodembedding'),
    ]

    operations = [
        migrations.DeleteModel(
            name='RecipeTranslation',
        ),
        migrations.DeleteModel(
            name='TextTranslation',
        ),
    ]
