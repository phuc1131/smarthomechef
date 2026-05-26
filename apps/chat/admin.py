from django.contrib import admin
from .models import (
    Intent, Pattern, ChatSession, ChatMessage, ChatSummary,
    MessageIntent, IntentEmbedding, ChatResponseCache
)


# ============================================================================
# INTENT & PATTERN MANAGEMENT
# ============================================================================
@admin.register(Intent)
class IntentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'topic', 'description')
    list_filter = ('topic',)
    search_fields = ('name', 'description')
    readonly_fields = ('id',)
    fieldsets = (
        ('Ý định', {
            'fields': ('id', 'name', 'topic', 'description')
        }),
        ('Cấu hình', {
            'fields': ('required_fields',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Pattern)
class PatternAdmin(admin.ModelAdmin):
    list_display = ('id', 'intent', 'text')
    list_filter = ('intent',)
    search_fields = ('text', 'intent__name')
    readonly_fields = ('id',)


# ============================================================================
# CHAT SESSION & MESSAGE MANAGEMENT
# ============================================================================
@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_id', 'title', 'current_intent_id', 'ask_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'account__username')
    readonly_fields = ('created_at', 'updated_at', 'id')
    fieldsets = (
        ('Phiên chat', {
            'fields': ('id', 'account', 'title')
        }),
        ('Trạng thái hiện tại', {
            'fields': ('current_intent_id', 'ask_count', 'filled_fields', 'missing_fields')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'content_preview', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content', 'session__title', 'session__account__username')
    readonly_fields = ('created_at', 'id')
    date_hierarchy = 'created_at'

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Nội dung'


@admin.register(ChatSummary)
class ChatSummaryAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_id', 'summary_preview', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('summary', 'session__title')
    readonly_fields = ('created_at', 'id')
    date_hierarchy = 'created_at'

    def summary_preview(self, obj):
        return obj.summary[:50] + '...' if obj.summary and len(obj.summary) > 50 else obj.summary
    summary_preview.short_description = 'Tóm tắt'


# ============================================================================
# INTENT CLASSIFICATION & EMBEDDING
# ============================================================================
@admin.register(MessageIntent)
class MessageIntentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message_id', 'intent', 'confidence')
    list_filter = ('confidence', 'intent__name')
    search_fields = ('intent__name', 'message__content')
    readonly_fields = ('id',)


@admin.register(IntentEmbedding)
class IntentEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('id', 'intent_name', 'source_type', 'confidence', 'created_at')
    list_filter = ('source_type', 'created_at', 'confidence')
    search_fields = ('intent_name',)
    readonly_fields = ('created_at', 'updated_at', 'id')
    date_hierarchy = 'created_at'


# ============================================================================
# CHAT RESPONSE CACHING
# ============================================================================
@admin.register(ChatResponseCache)
class ChatResponseCacheAdmin(admin.ModelAdmin):
    list_display = ('id', 'normalized_query', 'usage_count', 'created_at')
    list_filter = ('created_at', 'usage_count')
    search_fields = ('normalized_query', 'original_query', 'response')
    readonly_fields = ('created_at', 'id')
    fieldsets = (
        ('Cache', {
            'fields': ('id', 'original_query', 'normalized_query')
        }),
        ('Phản hồi', {
            'fields': ('response',)
        }),
        ('Thống kê', {
            'fields': ('usage_count', 'created_at')
        }),
    )
    date_hierarchy = 'created_at'
