# Generated migration for Recipe Rating System

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('nutrition', '0012_add_food_management_models'),
        ('users', '0001_initial'),  # Adjust this based on actual users migrations
    ]

    operations = [
        # Add fields to Recipe model
        migrations.AddField(
            model_name='recipe',
            name='auto_added',
            field=models.BooleanField(
                default=False,
                help_text='True nếu công thức được tạo tự động từ Gemini AI'
            ),
        ),
        migrations.AddField(
            model_name='recipe',
            name='created_by',
            field=models.CharField(
                max_length=20,
                choices=[('manual', 'Manual'), ('ai', 'AI - Gemini'), ('api', 'API - ThirdParty')],
                default='manual',
                help_text='Nguồn tạo công thức'
            ),
        ),
        migrations.AddField(
            model_name='recipe',
            name='avg_rating',
            field=models.FloatField(
                default=0.0,
                null=True,
                blank=True,
                help_text='Điểm đánh giá trung bình (1-5 sao)'
            ),
        ),
        migrations.AddField(
            model_name='recipe',
            name='total_ratings',
            field=models.IntegerField(
                default=0,
                help_text='Số lượng người đánh giá'
            ),
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='recipe',
            index=models.Index(fields=['auto_added', '-avg_rating'], name='recipe_auto_rating_idx'),
        ),
        migrations.AddIndex(
            model_name='recipe',
            index=models.Index(fields=['created_by'], name='recipe_created_by_idx'),
        ),
        
        # Create RecipeRating model
        migrations.CreateModel(
            name='RecipeRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(
                    choices=[(1, '1 sao'), (2, '2 sao'), (3, '3 sao'), (4, '4 sao'), (5, '5 sao')],
                    help_text='Đánh giá từ 1-5 sao'
                )),
                ('comment', models.TextField(
                    null=True,
                    blank=True,
                    max_length=500,
                    help_text='Bình luận về công thức (tùy chọn)'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(db_column='account_id', on_delete=django.db.models.deletion.CASCADE, to='users.account')),
                ('recipe', models.ForeignKey(db_column='recipe_id', on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='nutrition.recipe')),
            ],
            options={
                'db_table': 'recipe_ratings',
                'ordering': ['-created_at'],
                'unique_together': {('recipe', 'account')},
            },
        ),
        
        # Add indexes for RecipeRating
        migrations.AddIndex(
            model_name='reciperating',
            index=models.Index(fields=['recipe', '-rating'], name='rating_recipe_idx'),
        ),
        migrations.AddIndex(
            model_name='reciperating',
            index=models.Index(fields=['account'], name='rating_account_idx'),
        ),
    ]
