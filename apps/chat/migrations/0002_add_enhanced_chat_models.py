"""
Django migration to add Enhanced Chat Models
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
        ('users', '0012_add_personalization_models'),
    ]

    operations = [
        # ChatSession table
        migrations.CreateModel(
            name='ChatSession',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=255)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_sessions', to='users.account')),
            ],
            options={
                'db_table': 'chat_sessions_new',
            },
        ),
        
        # ChatMessage table (enhanced)
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant')], max_length=20)),
                ('content', models.TextField()),
                ('intent', models.CharField(blank=True, help_text='Classified intent', max_length=100, null=True)),
                ('intent_confidence', models.FloatField(blank=True, help_text='Intent confidence score', null=True)),
                ('parsed_parameters', models.JSONField(blank=True, default=dict, help_text='Extracted parameters')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='chat_messages', to='users.account')),
                ('session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chat.chatsession')),
            ],
            options={
                'db_table': 'chat_messages_new',
            },
        ),
    ]
