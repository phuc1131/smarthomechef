from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0012_add_personalization_models'),
        ('nutrition', '0014_remove_foodverificationqueue_food_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MealPlan',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('meal_type', models.CharField(max_length=50)),
                ('servings', models.DecimalField(decimal_places=2, default=Decimal('1'), max_digits=5)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(blank=True, db_column='account_id', null=True, on_delete=models.CASCADE, to='users.account')),
                ('food', models.ForeignKey(db_column='food_id', on_delete=models.DO_NOTHING, to='nutrition.food')),
            ],
            options={
                'db_table': 'meal_plans',
            },
        ),
        migrations.CreateModel(
            name='MealTypeConfig',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('meal_type', models.CharField(max_length=50, unique=True)),
                ('label', models.CharField(max_length=100)),
                ('badge_class', models.CharField(max_length=100)),
                ('sort_order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'meal_type_configs',
            },
        ),
    ]