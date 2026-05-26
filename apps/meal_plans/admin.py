from django.contrib import admin
from .models import MealPlan


# ============================================================================
# MEAL PLAN MANAGEMENT
# ============================================================================
@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'meal_type', 'account', 'food', 'servings', 'created_at')
    list_filter = ('meal_type', 'date', 'created_at')
    search_fields = ('account__username', 'food__name', 'notes', 'date')
    readonly_fields = ('created_at', 'id')
    fieldsets = (
        ('Thông tin kế hoạch', {
            'fields': ('id', 'account', 'food', 'date', 'meal_type')
        }),
        ('Chi tiết', {
            'fields': ('servings', 'notes')
        }),
        ('Thời gian', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'date'
