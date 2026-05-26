"""
Django migration to add new models for ideal schema
python manage.py migrate
"""

from django.db import migrations, models
import django.db.models.deletion
import json


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        # UserBudget table
        migrations.CreateModel(
            name='UserBudget',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('budget_amount', models.DecimalField(decimal_places=2, max_digits=12, help_text='VND')),
                ('budget_period', models.CharField(choices=[('daily', 'Hàng ngày'), ('weekly', 'Hàng tuần'), ('monthly', 'Hàng tháng')], default='daily', max_length=20)),
                ('currency', models.CharField(default='VND', max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budgets', to='users.account')),
            ],
            options={
                'db_table': 'user_budgets',
            },
        ),
        
        # UserHealthGoal table
        migrations.CreateModel(
            name='UserHealthGoal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('goal_type', models.CharField(choices=[('weight_loss', 'Giảm cân'), ('muscle_gain', 'Tăng cơ'), ('maintain', 'Duy trì'), ('energy_boost', 'Tăng năng lượng')], max_length=50)),
                ('target_weight', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, help_text='kg')),
                ('target_calories', models.IntegerField(blank=True, help_text='kcal/day', null=True)),
                ('target_macros', models.JSONField(blank=True, default=dict, help_text='{"protein": 30, "carbs": 50, "fat": 20}')),
                ('start_date', models.DateField(auto_now_add=True)),
                ('target_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='health_goals', to='users.account')),
            ],
            options={
                'db_table': 'user_health_goals',
            },
        ),
    ]
