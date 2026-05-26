"""
Django migration to add Food Management models
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('nutrition', '0004_alter_ingredientalias_unique_together_and_more'),
        ('users', '0012_add_personalization_models'),
    ]

    operations = [
        # FoodCategory - just update state, table already exists from 0002
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='foodcategory',
                    name='description',
                    field=models.TextField(blank=True),
                ),
                migrations.AddField(
                    model_name='foodcategory',
                    name='icon',
                    field=models.CharField(blank=True, help_text='Icon name or URL', max_length=255),
                ),
                migrations.AddField(
                    model_name='foodcategory',
                    name='order_index',
                    field=models.IntegerField(default=0, help_text='Display order'),
                ),
                migrations.AddField(
                    model_name='foodcategory',
                    name='is_active',
                    field=models.BooleanField(default=True),
                ),
                migrations.AddField(
                    model_name='foodcategory',
                    name='created_at',
                    field=models.DateTimeField(auto_now_add=True),
                ),
            ],
            database_operations=[],
        ),
        
        # FoodVerificationQueue table
        migrations.CreateModel(
            name='FoodVerificationQueue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Đang chờ'), ('approved', 'Đã duyệt'), ('rejected', 'Bị từ chối')], default='pending', max_length=20)),
                ('reason_submitted', models.TextField(blank=True, help_text='Tại sao submit')),
                ('reason_verdict', models.TextField(blank=True, help_text='Kết quả duyệt')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('food', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='verification_queue', to='nutrition.food')),
                ('submitted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='food_submissions', to='users.account')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='food_verifications', to='users.account')),
            ],
            options={
                'db_table': 'food_verification_queue',
            },
        ),
    ]
