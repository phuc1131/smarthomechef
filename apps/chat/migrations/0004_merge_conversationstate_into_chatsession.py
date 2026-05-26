# Generated migration: Merge ConversationState into ChatSession

from django.db import migrations, models


def migrate_conversationstate_data(apps, schema_editor):
    """Migrate data from ConversationState to ChatSession"""
    ChatSession = apps.get_model('chat', 'ChatSession')
    ConversationState = apps.get_model('chat', 'ConversationState')
    
    for state in ConversationState.objects.all():
        try:
            # Merge data - find or create a ChatSession for this account
            # If there's a session for this account, use it; otherwise skip
            session = ChatSession.objects.filter(account_id=state.account_id).first()
            if session:
                session.missing_fields = state.missing_fields
                session.ask_count = state.ask_count
                session.current_intent_id = state.current_intent_id
                session.filled_fields = state.filled_fields
                session.save()
        except Exception:
            pass  # If merging fails, continue


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_intent_alter_chatmessage_options_and_more'),
    ]

    operations = [
        # Add new fields to ChatSession
        migrations.AddField(
            model_name='chatsession',
            name='missing_fields',
            field=models.JSONField(blank=True, null=True, help_text='List of missing fields for current intent'),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='ask_count',
            field=models.IntegerField(default=0, help_text='Number of questions asked'),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='current_intent_id',
            field=models.IntegerField(blank=True, null=True, help_text='Current intent being processed'),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='filled_fields',
            field=models.JSONField(blank=True, null=True, help_text='Fields that have been filled'),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        # Migrate data
        migrations.RunPython(migrate_conversationstate_data, migrations.RunPython.noop),
        # Delete ConversationState model
        migrations.DeleteModel(
            name='ConversationState',
        ),
    ]
