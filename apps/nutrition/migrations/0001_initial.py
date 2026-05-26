from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Ingredient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, null=True, blank=True)),
            ],
            options={
                'db_table': 'ingredients',
            },
        ),
        migrations.CreateModel(
            name='IngredientAlias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alias', models.CharField(max_length=200)),
                ('source', models.CharField(default='gemini', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='aliases', db_column='ingredient_id', to='nutrition.Ingredient')),
            ],
            options={
                'db_table': 'ingredient_aliases',
                'unique_together': {('ingredient', 'alias', 'source')},
            },
        ),
        migrations.CreateModel(
            name='IngredientNutrition',
            fields=[
                ('ingredient', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, related_name='nutrition', serialize=False, db_column='ingredient_id', to='nutrition.Ingredient')),
                ('calories', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('protein', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('carbs', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('fat', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('fiber', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('sugar', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('sodium', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('cholesterol', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('vitamin_a', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('vitamin_c', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('calcium', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('iron', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('serving_size', models.CharField(blank=True, max_length=100, null=True)),
                ('source', models.CharField(default='spoonacular', max_length=50)),
                ('raw_payload', models.JSONField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'ingredient_nutrition',
            },
        ),
    ]
