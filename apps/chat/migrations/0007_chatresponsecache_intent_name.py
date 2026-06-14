# Generated migration: Add intent_name field to ChatResponseCache for intent-aware caching

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0006_renumber_chat_app_ids'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatresponsecache',
            name='intent_name',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                help_text='Intent của câu hỏi (meal_plan, nutrition, recipe, recommendation, vv)',
            ),
        ),
        migrations.AddIndex(
            model_name='chatresponsecache',
            index=models.Index(fields=['intent_name', 'created_at'], name='chat_respon_intent__77ccad_idx'),
        ),
        migrations.RemoveIndex(
            model_name='chatresponsecache',
            name='chat_respon_created_fb5ac8_idx',
        ),
        migrations.AddIndex(
            model_name='chatresponsecache',
            index=models.Index(fields=['created_at'], name='chat_respon_created_fb5ac8_idx'),
        ),
    ]
