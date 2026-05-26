from django.contrib import admin
from .models import (
    Account,
    Disease,
    DiseaseNutritionRule,
    UserBehaviorLog,
    UserBehaviorProfile,
    UserDisease,
    UserFeedback,
    UserGoal,
    UserProfile,
)


# ============================================================================
# ACCOUNT MANAGEMENT
# ============================================================================
@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('username', 'email')
    readonly_fields = ('created_at', 'id')
    fieldsets = (
        ('Thông tin tài khoản', {
            'fields': ('id', 'username', 'email', 'password_hash')
        }),
        ('Quyền hạn', {
            'fields': ('role', 'is_active')
        }),
        ('Thời gian', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    actions = ['activate_accounts', 'deactivate_accounts']

    def activate_accounts(self, request, queryset):
        queryset.update(is_active=True)
    activate_accounts.short_description = 'Kích hoạt tài khoản đã chọn'

    def deactivate_accounts(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_accounts.short_description = 'Vô hiệu hóa tài khoản đã chọn'


# ============================================================================
# USER PROFILE MANAGEMENT
# ============================================================================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'account', 'age', 'gender', 'bmi', 'daily_calorie_target', 'updated_at')
    list_filter = ('gender', 'activity_level', 'updated_at')
    search_fields = ('name', 'account__username', 'account__email')
    readonly_fields = ('created_at', 'updated_at', 'id')
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('id', 'account', 'name', 'age', 'gender')
        }),
        ('Chỉ số sức khỏe', {
            'fields': ('height', 'weight', 'bmi', 'activity_level')
        }),
        ('Mục tiêu và sức khỏe', {
            'fields': ('health_goal', 'medical_conditions', 'dietary_preferences', 'daily_calorie_target')
        }),
        ('Ngân sách', {
            'fields': ('budget_limit',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'updated_at'


# ============================================================================
# USER GOALS
# ============================================================================
@admin.register(UserGoal)
class UserGoalAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'goal_type', 'target_weight', 'daily_calorie_target', 'created_at')
    list_filter = ('goal_type', 'created_at')
    search_fields = ('account__username', 'goal_type')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


# ============================================================================
# USER FEEDBACK & RATINGS
# ============================================================================
@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'food', 'rating', 'liked', 'created_at')
    list_filter = ('rating', 'liked', 'created_at')
    search_fields = ('account__username', 'food__name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


# ============================================================================
# USER BEHAVIOR & PREFERENCES
# ============================================================================
@admin.register(UserBehaviorProfile)
class UserBehaviorProfileAdmin(admin.ModelAdmin):
    list_display = ('account', 'healthy_score', 'unhealthy_score', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('account__username',)
    readonly_fields = ('updated_at',)


@admin.register(UserBehaviorLog)
class UserBehaviorLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'action_type', 'target_type', 'target_id', 'created_at')
    list_filter = ('action_type', 'target_type', 'created_at')
    search_fields = ('account__username', 'action_type', 'target_type')
    readonly_fields = ('created_at', 'id')
    date_hierarchy = 'created_at'


# ============================================================================
# DISEASE MANAGEMENT
# ============================================================================
@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name', 'description')
    readonly_fields = ('id',)


@admin.register(UserDisease)
class UserDiseaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'disease', 'severity')
    list_filter = ('severity', 'disease')
    search_fields = ('account__username', 'disease__name')
    readonly_fields = ('id',)


@admin.register(DiseaseNutritionRule)
class DiseaseNutritionRuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'disease', 'nutrient', 'rule_type', 'threshold_value')
    list_filter = ('rule_type', 'disease')
    search_fields = ('disease__name', 'nutrient')
    readonly_fields = ('id',)
    fieldsets = (
        ('Quy tắc dinh dưỡng', {
            'fields': ('disease', 'nutrient', 'rule_type', 'threshold_value')
        }),
    )
