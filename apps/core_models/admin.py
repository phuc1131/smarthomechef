from django.contrib import admin
from django.utils.html import format_html
from .models import AIRecommendation, SearchEvent
from .ai_learning_models import (
    AIRequestLog,
    RecommendationLog,
    ModelMetadata,
    Experiment,
    ExperimentAssignment,
    ExperimentMetric,
    ExperimentEvent,
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


# ============================================================================
# A/B TESTING
# ============================================================================
@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status_badge', 'assignment_strategy', 'traffic_allocation', 'created_at')
    list_filter = ('status', 'assignment_strategy', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'id')
    
    fieldsets = (
        ('Cơ bản', {
            'fields': ('id', 'name', 'description', 'status')
        }),
        ('Cấu hình biến thể', {
            'fields': ('control_variant', 'test_variants')
        }),
        ('Phân bổ', {
            'fields': ('assignment_strategy', 'traffic_allocation', 'target_users')
        }),
        ('Thời gian', {
            'fields': ('started_at', 'ended_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': '#999999',
            'active': '#28a745',
            'paused': '#ffc107',
            'completed': '#0066cc',
            'cancelled': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#999999'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Trạng thái'


@admin.register(ExperimentAssignment)
class ExperimentAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'experiment', 'account', 'variant_name', 'assigned_at')
    list_filter = ('experiment', 'variant_name', 'assigned_at')
    search_fields = ('account__username', 'experiment__name')
    readonly_fields = ('assigned_at', 'id')
    
    fieldsets = (
        ('Phân công', {
            'fields': ('id', 'experiment', 'account', 'variant_name')
        }),
        ('Thời gian', {
            'fields': ('assigned_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ExperimentMetric)
class ExperimentMetricAdmin(admin.ModelAdmin):
    list_display = ('id', 'experiment', 'variant_name', 'metric_type', 'value', 'count', 'recorded_at')
    list_filter = ('experiment', 'variant_name', 'metric_type', 'recorded_at')
    search_fields = ('experiment__name',)
    readonly_fields = ('recorded_at', 'id')
    
    fieldsets = (
        ('Chỉ số', {
            'fields': ('id', 'experiment', 'variant_name', 'metric_type', 'value')
        }),
        ('Thống kê', {
            'fields': ('count', 'mean', 'std_dev', 'min_value', 'max_value')
        }),
        ('Thời gian', {
            'fields': ('recorded_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ExperimentEvent)
class ExperimentEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'experiment', 'account', 'event_type', 'variant_name', 'food', 'value', 'created_at')
    list_filter = ('experiment', 'event_type', 'variant_name', 'created_at')
    search_fields = ('account__username', 'experiment__name', 'food__name')
    readonly_fields = ('created_at', 'id', 'metadata')
    
    fieldsets = (
        ('Sự kiện', {
            'fields': ('id', 'experiment', 'account', 'event_type', 'variant_name')
        }),
        ('Chi tiết', {
            'fields': ('food', 'value', 'metadata')
        }),
        ('Thời gian', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'


@admin.register(AIRequestLog)
class AIRequestLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider', 'intent_name', 'cache_hit', 'latency_ms', 'estimated_cost_usd', 'response_ok', 'created_at')
    list_filter = ('provider', 'cache_hit', 'response_ok', 'created_at')
    search_fields = ('query_text', 'normalized_query', 'intent_name', 'decision', 'ab_variant', 'account__username')
    readonly_fields = ('created_at', 'id', 'metadata')
    date_hierarchy = 'created_at'
