import re
import unicodedata
from decimal import Decimal

from django.db import models
try:
    from django.contrib.postgres.search import SearchVectorField
    HAS_POSTGRES_SEARCH = True
except ImportError:
    HAS_POSTGRES_SEARCH = False


def _normalize_text(value):
    text = (value or '').strip().lower()
    if not text:
        return ''
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r'[^a-z0-9\s-]+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _decimal_or_none(value):
    if value in (None, ''):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return None


class FoodCategory(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'food_categories'

    def __str__(self):
        return self.name


class FoodTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'food_tags'

    def __str__(self):
        return self.name


class Food(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, null=True, blank=True)
    category = models.ForeignKey(
        FoodCategory,
        on_delete=models.SET_NULL,
        db_column='category_id',
        null=True,
        blank=True,
        related_name='foods',
    )
    calories = models.DecimalField(max_digits=8, decimal_places=2, default=0, db_column='calories')
    protein = models.DecimalField(max_digits=8, decimal_places=2, default=0, db_column='protein')
    carbs = models.DecimalField(max_digits=8, decimal_places=2, default=0, db_column='carbs')
    fat = models.DecimalField(max_digits=8, decimal_places=2, default=0, db_column='fat')
    fiber = models.DecimalField(max_digits=8, decimal_places=2, default=0, db_column='fiber')
    is_vegetarian = models.BooleanField(default=False)
    is_diabetes_friendly = models.BooleanField(default=False)
    is_weight_loss_friendly = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    image_url = models.TextField(null=True, blank=True)
    @property
    def price(self):
        return None
    search_vector = models.TextField(null=True, blank=True)  # Keep TextField unless full Postgres search support is enabled
    # Fields from FoodDetail (consolidated)
    sugar = models.FloatField(null=True, blank=True)
    sodium = models.FloatField(null=True, blank=True)
    cholesterol = models.FloatField(null=True, blank=True)
    vitamin_a = models.FloatField(null=True, blank=True)
    vitamin_c = models.FloatField(null=True, blank=True)
    calcium = models.FloatField(null=True, blank=True)
    iron = models.FloatField(null=True, blank=True)
    # Tags (consolidated from FoodTagMap)
    tags = models.JSONField(default=list, blank=True, help_text='List of tag IDs or names')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'foods'
        ordering = ['name', 'id']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category_id']),
        ]

    def __str__(self):
        return self.name

    # Keep legacy property names consistent for code that expects them
    @property
    def total_calories(self):
        return _decimal_or_none(self.calories) or Decimal('0')

    @property
    def total_protein(self):
        return _decimal_or_none(self.protein) or Decimal('0')

    @property
    def total_carbs(self):
        return _decimal_or_none(self.carbs) or Decimal('0')

    @property
    def total_fat(self):
        return _decimal_or_none(self.fat) or Decimal('0')

    @property
    def category_name(self):
        return self.category.name if self.category else None


class Ingredient(models.Model):
    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'ingredients'

    def __str__(self):
        return self.name or f'Ingredient #{self.pk}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class IngredientAlias(models.Model):
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        db_column='ingredient_id',
        related_name='aliases',
    )
    alias = models.CharField(max_length=200)

    class Meta:
        db_table = 'ingredient_aliases'

    def __str__(self):
        return f'{self.alias} → {self.ingredient.name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class IngredientNutrition(models.Model):
    ingredient = models.OneToOneField(
        Ingredient,
        on_delete=models.CASCADE,
        db_column='ingredient_id',
        primary_key=True,
        related_name='nutrition',
    )
    calories = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    protein = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    carbs = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    fat = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    fiber = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))

    class Meta:
        db_table = 'ingredient_nutrition'

    def __str__(self):
        return f'Nutrition for {self.ingredient.name}'


class FoodIngredient(models.Model):
    food = models.ForeignKey(Food, on_delete=models.CASCADE, db_column='food_id')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, db_column='ingredient_id')
    quantity_grams = models.DecimalField(max_digits=8, decimal_places=2, db_column='quantity')

    class Meta:
        db_table = 'food_ingredients'
        unique_together = ('food', 'ingredient')

    def __str__(self):
        return f"{self.food.name} - {self.ingredient.name}"

    @property
    def quantity(self):
        return self.quantity_grams

    @quantity.setter
    def quantity(self, value):
        self.quantity_grams = _decimal_or_none(value) or Decimal('0')


class IngredientPrice(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, db_column='ingredient_id')
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2)
    unit_type = models.CharField(max_length=50, default='kg')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingredient_prices'


class UnitConversion(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, db_column='ingredient_id')
    from_unit = models.CharField(max_length=20)
    conversion_factor = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        db_table = 'unit_conversions'


class Recipe(models.Model):
    food = models.OneToOneField(Food, on_delete=models.CASCADE, db_column='food_id', related_name='recipe')
    title = models.CharField(max_length=255)
    summary = models.TextField(null=True, blank=True)
    instructions = models.TextField()
    ingredients_json = models.JSONField(null=True, blank=True)
    nutrition_json = models.JSONField(null=True, blank=True)
    source_url = models.TextField(null=True, blank=True)
    image_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'food_recipes'
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f'Recipe #{self.pk}'


class RecipeRating(models.Model):
    """
    Mô hình lưu đánh giá từ user cho mỗi công thức.
    
    Chiến lược:
    - User có thể đánh giá công thức từ 1-5 sao
    - Mỗi user chỉ có 1 rating cho mỗi công thức (update nếu rate lại)
    - Tự động cập nhật avg_rating của Recipe khi có rating mới
    
    Trường:
    - recipe: Link tới công thức
    - account: Người đánh giá
    - rating: Điểm số 1-5
    - comment: Bình luận (optional)
    - created_at: Lúc tạo
    - updated_at: Lúc cập nhật
    """
    recipe = models.ForeignKey(
        Recipe, 
        on_delete=models.CASCADE, 
        db_column='recipe_id',
        related_name='ratings'
    )
    account = models.ForeignKey(
        'users.Account',
        on_delete=models.CASCADE,
        db_column='account_id'
    )
    rating = models.IntegerField(
        choices=[(i, f'{i} sao') for i in range(1, 6)],
        help_text='Đánh giá từ 1-5 sao'
    )
    comment = models.TextField(
        null=True,
        blank=True,
        max_length=500,
        help_text='Bình luận về công thức (tùy chọn)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recipe_ratings'
        unique_together = [['recipe', 'account']]  # Mỗi user 1 rating/recipe
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipe', '-rating']),
            models.Index(fields=['account']),
        ]

    def __str__(self):
        return f"{self.recipe.title} - {self.account} - {self.rating} stars"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class NutritionLog(models.Model):
    """Ghi log thực phẩm ăn vào theo ngày."""
    id = models.BigAutoField(primary_key=True)
    account = models.ForeignKey('users.Account', on_delete=models.CASCADE, db_column='account_id')
    food = models.ForeignKey(Food, on_delete=models.CASCADE, db_column='food_id')
    date = models.DateField()
    meal_type = models.CharField(max_length=50)
    servings = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('1'))
    total_calories = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_protein = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_carbs = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_fat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nutrition_logs'

    def __str__(self):
        return f"{self.food.name} - {self.date}"

    @property
    def computed_total_calories(self):
        if self.total_calories is not None:
            return self.total_calories
        return (self.food.calories or Decimal('0')) * (self.servings or Decimal('0'))

    @property
    def computed_total_protein(self):
        if self.total_protein is not None:
            return self.total_protein
        return (self.food.protein or Decimal('0')) * (self.servings or Decimal('0'))

    @property
    def computed_total_carbs(self):
        if self.total_carbs is not None:
            return self.total_carbs
        return (self.food.carbs or Decimal('0')) * (self.servings or Decimal('0'))

    @property
    def computed_total_fat(self):
        if self.total_fat is not None:
            return self.total_fat
        return (self.food.fat or Decimal('0')) * (self.servings or Decimal('0'))
class ShoppingList(models.Model):
    account = models.ForeignKey('users.Account', on_delete=models.CASCADE, db_column='account_id')
    name = models.CharField(max_length=200, default='Danh sách mua sắm')
    date_start = models.DateField(null=True, blank=True)
    date_end = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shopping_lists'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.date_start or '...'} - {self.date_end or '...'})"


class ShoppingItem(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, db_column='shopping_list_id', related_name='items')
    ingredient_name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=50, default='g')
    notes = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'shopping_items'
        ordering = ['ingredient_name']

    def __str__(self):
        return f"{self.ingredient_name}: {self.quantity} {self.unit}"


class DailyNutritionSummary(models.Model):
    #     Mô hình tóm tắt dinh dưỡng hàng ngày.
#     Có thể dùng cho caching hoặc báo cáo nhanh (thay vì sum() hàng trăm log mỗi lần).
#     
#     Trường:
#     - account: Người dùng
#     - date: Ngày tóm tắt
#     - total_calories, total_protein, total_carbs, total_fat: Tổng hàng ngày
#     
#     GHI NHỚ:
#     - Có thể được tính tự động từ NutritionLog qua trigger hoặc task định kỳ
#     - Hoặc tính on-demand khi cần (hiện tại không dùng nhiều)
    account = models.ForeignKey('users.Account', on_delete=models.DO_NOTHING, db_column='account_id', null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    total_calories = models.FloatField(null=True, blank=True)
    total_protein = models.FloatField(null=True, blank=True)
    total_carbs = models.FloatField(null=True, blank=True)
    total_fat = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'daily_nutrition_summary'


class FoodPopularity(models.Model):
    food = models.OneToOneField(Food, on_delete=models.CASCADE, db_column='food_id', primary_key=True)
    view_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'food_popularity'

    def __str__(self):
        return f"{self.food.name} (views={self.view_count})"
