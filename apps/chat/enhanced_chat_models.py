"""
Enhanced Chat Models for AI Learning
- ChatMessage: Messages với intent + parsed parameters
"""

from django.db import models
from apps.users.models import Account


class ChatSession(models.Model):
    """Chat session"""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, blank=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'chat_sessions'
        indexes = [
            models.Index(fields=['account', 'started_at']),
        ]
    
    def __str__(self):
        return f"Session #{self.id} - {self.account}"


class ChatMessage(models.Model):
    """Chat message với intent + parameters"""
    ROLES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_messages')
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    
    role = models.CharField(max_length=20, choices=ROLES)
    content = models.TextField()
    
    # Intent classification (for user messages)
    intent = models.CharField(max_length=100, null=True, blank=True, help_text='Classified intent')
    intent_confidence = models.FloatField(null=True, blank=True, help_text='Intent confidence score')
    
    # Parsed parameters (for user messages)
    parsed_parameters = models.JSONField(default=dict, blank=True, help_text='Extracted parameters')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_messages'
        indexes = [
            models.Index(fields=['account', 'created_at']),
            models.Index(fields=['intent']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
