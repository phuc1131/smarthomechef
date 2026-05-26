"""
Django migration to add AI Learning & Admin models
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core_models', '0002_initial'),
    ]

    operations = [
        # MealRecommendation table
        migrations.CreateModel(
            name='MealRecommendation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.DecimalField(decimal_places=4, max_digits=5, help_text='Overall score 0.0-1.0')),
                ('match_score', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True, help_text='Taste match')),
                ('budget_score', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True, help_text='Budget match')),
                ('health_score', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True, help_text='Health match')),
                ('reason', models.TextField(blank=True, help_text='Tại sao gợi ý')),
                ('ai_model_version', models.CharField(default='v1', max_length=50, help_text='Model version used')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='meal_recommendations', to='users.account')),
                ('food', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nutrition.food')),
            ],
            options={
                'db_table': 'meal_recommendations',
            },
        ),
        
        # UserFeedbackFood table
        migrations.CreateModel(
            name='UserFeedbackFood',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(blank=True, help_text='1-5 stars', null=True)),
                ('is_liked', models.BooleanField(blank=True, null=True)),
                ('reason', models.TextField(blank=True)),
                ('feedback_type', models.CharField(choices=[('taste', 'Vị cảm'), ('health', 'Sức khỏe'), ('price', 'Giá cả'), ('convenience', 'Tiện lợi'), ('other', 'Khác')], default='taste', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='food_feedbacks', to='users.account')),
                ('food', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nutrition.food')),
            ],
            options={
                'db_table': 'user_feedback_food',
            },
        ),
        
        # UserFeedbackRecommendation table
        migrations.CreateModel(
            name='UserFeedbackRecommendation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('was_accepted', models.BooleanField(blank=True, help_text='Người dùng chấp nhận gợi ý', null=True)),
                ('was_helpful', models.BooleanField(blank=True, help_text='Gợi ý có hữu ích', null=True)),
                ('context', models.JSONField(blank=True, default=dict, help_text='Thông tin về gợi ý')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommendation_feedbacks', to='users.account')),
                ('food', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='nutrition.food')),
                ('recommendation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core_models.mealrecommendation')),
            ],
            options={
                'db_table': 'user_feedback_recommendation',
            },
        ),
        
        # FoodEmbedding table
        migrations.CreateModel(
            name='FoodEmbedding',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('embedding', models.BinaryField(help_text='Float32 vector')),
                ('model_version', models.CharField(default='multilingual-v1', max_length=50)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('food', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='embedding', to='nutrition.food')),
            ],
            options={
                'db_table': 'food_embeddings',
            },
        ),
        
        # IntentPattern table
        migrations.CreateModel(
            name='IntentPattern',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('intent', models.CharField(help_text='Intent type: recommendation, health, ingredient, budget', max_length=100)),
                ('pattern', models.TextField(help_text='Example: "tôi muốn giảm cân"')),
                ('confidence', models.FloatField(default=0.5, help_text='Pattern confidence')),
                ('created_by', models.CharField(choices=[('admin', 'Admin'), ('ai', 'AI'), ('user', 'User')], default='admin', max_length=50)),
                ('verified_by_admin', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'intent_patterns',
            },
        ),
        
        # AuditLog table
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('CREATE', 'Tạo'), ('UPDATE', 'Sửa'), ('DELETE', 'Xóa'), ('VERIFY', 'Duyệt'), ('REJECT', 'Từ chối'), ('EXPORT', 'Xuất'), ('IMPORT', 'Nhập')], max_length=50)),
                ('table_name', models.CharField(help_text='Table bị ảnh hưởng', max_length=100)),
                ('record_id', models.IntegerField(help_text='ID của record')),
                ('old_value', models.JSONField(blank=True, help_text='Giá trị cũ', null=True)),
                ('new_value', models.JSONField(blank=True, help_text='Giá trị mới', null=True)),
                ('reason', models.TextField(blank=True, help_text='Lý do thực hiện')),
                ('ip_address', models.CharField(blank=True, help_text='IP của admin', max_length=45)),
                ('user_agent', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('admin', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.account')),
            ],
            options={
                'db_table': 'audit_logs',
            },
        ),
        
        # AdminSetting table
        migrations.CreateModel(
            name='AdminSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('setting_key', models.CharField(help_text='Setting key', max_length=100, unique=True)),
                ('setting_value', models.JSONField(help_text='Setting value (JSON)')),
                ('description', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.account')),
            ],
            options={
                'db_table': 'admin_settings',
            },
        ),
        
        # SystemMetric table
        migrations.CreateModel(
            name='SystemMetric',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metric_name', models.CharField(choices=[('user_count', 'Số users'), ('food_count', 'Số foods'), ('meal_plan_count', 'Số meal plans'), ('recommendation_accuracy', 'Độ chính xác gợi ý'), ('api_latency', 'API latency'), ('db_size', 'Kích thước DB'), ('daily_active_users', 'DAU')], max_length=100)),
                ('metric_value', models.FloatField()),
                ('date', models.DateField(auto_now_add=True)),
                ('notes', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'system_metrics',
            },
        ),
        
        # AdminLog table
        migrations.CreateModel(
            name='AdminLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(choices=[('INFO', 'Info'), ('WARNING', 'Warning'), ('ERROR', 'Error')], default='INFO', max_length=20)),
                ('message', models.TextField()),
                ('context', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('admin', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.account')),
            ],
            options={
                'db_table': 'admin_logs',
            },
        ),
    ]
