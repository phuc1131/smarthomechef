from django.contrib import admin
from .models import AIRecommendation, SearchEvent
from .ai_learning_models import (
    RecommendationLog,
    ModelMetadata,
)


# ============================================================================
# AI RECOMMENDATIONS
# ============================================================================
@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'food', 'score', 'budget_match_score', 'estimated_cost', 'created_at')
    list_filter = ('score', 'created_at')
    search_fields = ('account__username', 'food__name', 'reason')
    readonly_fields = ('created_at', 'id')
    fieldsets = (
        ('Gợi ý', {
            'fields': ('id', 'account', 'food')
        }),
        ('Điểm số', {
            'fields': ('score', 'budget_match_score', 'estimated_cost')
        }),
        ('Chi tiết', {
            'fields': ('reason',)
        }),
        ('Thời gian', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'


# ============================================================================
# SEARCH TRACKING
# ============================================================================
@admin.register(SearchEvent)
class SearchEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'query_text', 'result_count', 'clicked_food', 'created_at')
    list_filter = ('created_at', 'result_count')
    search_fields = ('query_text', 'normalized_query', 'account__username', 'clicked_food__name')
    readonly_fields = ('created_at', 'id')
    fieldsets = (
        ('Tìm kiếm', {
            'fields': ('id', 'account', 'query_text', 'normalized_query')
        }),
        ('Kết quả', {
            'fields': ('result_count', 'clicked_food')
        }),
        ('Thời gian', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'


# ============================================================================
# RECOMMENDATION LOG
# ============================================================================
@admin.register(RecommendationLog)
class RecommendationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'food', 'score', 'model_version', 'created_at')
    list_filter = ('model_version', 'created_at')
    search_fields = ('account__username', 'food__name', 'reason')
    readonly_fields = ('created_at', 'id')
    date_hierarchy = 'created_at'


# ============================================================================
# MODEL METADATA
# ============================================================================
@admin.register(ModelMetadata)
class ModelMetadataAdmin(admin.ModelAdmin):
    list_display = ('id', 'model_name', 'version', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('model_name', 'version', 'description')
    readonly_fields = ('created_at', 'id')
    date_hierarchy = 'created_at'
