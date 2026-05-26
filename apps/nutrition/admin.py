from django.contrib import admin
from .models import (
    DailyNutritionSummary,
    Food,
    FoodCategory,
    FoodIngredient,
    FoodPopularity,
    Ingredient,
    IngredientNutrition,
    IngredientPrice,
    NutritionLog,
    Recipe,
    UnitConversion,
)


# ============================================================================
# FOOD CATEGORY
# ============================================================================
@admin.register(FoodCategory)
class FoodCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    readonly_fields = ('id',)


# ============================================================================
# FOOD MANAGEMENT
# ============================================================================
@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category_name', 'calories', 'protein', 'carbs', 'fat', 'created_at')
    list_filter = ('category__name', 'is_vegetarian', 'is_diabetes_friendly', 'created_at')
    search_fields = ('name', 'category__name', 'description')
    readonly_fields = ('created_at', 'id', 'normalized_name')
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('id', 'name', 'normalized_name', 'category', 'description', 'image_url')
        }),
        ('Dinh dưỡng (trên 100g)', {
            'fields': ('calories', 'protein', 'carbs', 'fat', 'fiber', 'sugar', 'sodium', 'cholesterol')
        }),
        ('Vi chất', {
            'fields': ('vitamin_a', 'vitamin_c', 'calcium', 'iron')
        }),
        ('Đặc tính', {
            'fields': ('is_vegetarian', 'is_diabetes_friendly', 'is_weight_loss_friendly', 'tags')
        }),
        ('Thời gian', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'


# ============================================================================
# FOOD POPULARITY TRACKING
# ============================================================================
@admin.register(FoodPopularity)
class FoodPopularityAdmin(admin.ModelAdmin):
    list_display = ('food', 'view_count', 'click_count', 'like_count', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('food__name',)
    readonly_fields = ('updated_at',)
    date_hierarchy = 'updated_at'


# ============================================================================
# INGREDIENT MANAGEMENT
# ============================================================================
@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'normalized_name', 'is_deleted')
    list_filter = ('is_deleted',)
    search_fields = ('name', 'normalized_name')
    readonly_fields = ('id', 'normalized_name')


@admin.register(IngredientNutrition)
class IngredientNutritionAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'calories', 'protein', 'carbs', 'fat', 'fiber')
    search_fields = ('ingredient__name',)
    readonly_fields = ('ingredient',)


@admin.register(IngredientPrice)
class IngredientPriceAdmin(admin.ModelAdmin):
    list_display = ('id', 'ingredient', 'price_per_unit', 'unit_type', 'updated_at')
    list_filter = ('unit_type', 'updated_at')
    search_fields = ('ingredient__name',)
    readonly_fields = ('updated_at', 'id')
    
    date_hierarchy = 'updated_at'      # Giữ nguyên
    list_per_page = 100                # Tăng số lượng hiển thị mỗi trang
    
    def get_queryset(self, request):
        """
        Giải quyết vấn đề date_hierarchy tự động lọc chỉ hiện dữ liệu của tháng hiện tại.
        Chỉ áp dụng filter thời gian khi người dùng thực sự chọn trên giao diện.
        """
        qs = super().get_queryset(request)
        
        # Nếu chưa có bất kỳ filter nào liên quan đến updated_at → hiển thị TẤT CẢ dữ liệu
        has_date_filter = any(
            key.startswith('updated_at') for key in request.GET.keys()
        )
        
        if not has_date_filter:
            return qs  # Trả về full queryset
        
        return qs


@admin.register(UnitConversion)
class UnitConversionAdmin(admin.ModelAdmin):
    list_display = ('id', 'ingredient', 'from_unit', 'conversion_factor')
    list_filter = ('from_unit',)
    search_fields = ('ingredient__name', 'from_unit')
    readonly_fields = ('id',)


# ============================================================================
# FOOD INGREDIENTS COMPOSITION
# ============================================================================
@admin.register(FoodIngredient)
class FoodIngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'food', 'ingredient', 'quantity_grams')
    list_filter = ('food__category',)
    search_fields = ('food__name', 'ingredient__name')
    readonly_fields = ('id',)


# ============================================================================
# RECIPES
# ============================================================================
@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'food', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'food__name', 'summary')
    readonly_fields = ('created_at', 'id')
    fieldsets = (
        ('Thông tin công thức', {
            'fields': ('id', 'food', 'title', 'summary', 'image_url')
        }),
        ('Chi tiết', {
            'fields': ('instructions', 'ingredients_json', 'nutrition_json', 'source_url')
        }),
        ('Thời gian', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'


# ============================================================================
# NUTRITION LOG & SUMMARY
# ============================================================================
@admin.register(NutritionLog)
class NutritionLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_id', 'food', 'date', 'meal_type', 'servings', 'computed_total_calories')
    list_filter = ('meal_type', 'date', 'created_at')
    search_fields = ('food__name', 'account__username')
    readonly_fields = ('created_at', 'id')
    date_hierarchy = 'date'

    def computed_total_calories(self, obj):
        servings = obj.servings or 0
        food = obj.food
        return round(float((food.calories if food else 0) or 0) * float(servings), 2)

    computed_total_calories.short_description = 'total_calories'


@admin.register(DailyNutritionSummary)
class DailyNutritionSummaryAdmin(admin.ModelAdmin):
    list_display = ('id', 'account_id', 'date', 'total_calories', 'total_protein', 'total_carbs', 'total_fat')
    list_filter = ('date',)
    search_fields = ('account__username',)
    readonly_fields = ('id',)
    date_hierarchy = 'date'