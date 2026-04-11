from django.db import models


class UserProfile(models.Model):
    name = models.CharField(max_length=200)
    age = models.IntegerField(null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    health_goal = models.CharField(max_length=200, null=True, blank=True)
    medical_conditions = models.TextField(null=True, blank=True)
    dietary_preferences = models.TextField(null=True, blank=True)
    activity_level = models.CharField(max_length=50, null=True, blank=True)
    daily_calorie_target = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'app_userprofile'

    def __str__(self):
        return self.name


class Food(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, null=True, blank=True)
    calories = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    protein = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    carbs = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fat = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    fiber = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    serving_size = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_vegetarian = models.BooleanField(default=False)
    is_diabetes_friendly = models.BooleanField(default=False)
    is_weight_loss_friendly = models.BooleanField(default=False)
    image_url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app_food'

    def __str__(self):
        return self.name


class MealPlan(models.Model):
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    date = models.TextField()
    meal_type = models.CharField(max_length=50)
    servings = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app_mealplan'

    def __str__(self):
        return f"{self.food.name} - {self.date}"


class NutritionLog(models.Model):
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    date = models.TextField()
    meal_type = models.CharField(max_length=50)
    servings = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    total_calories = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_protein = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_carbs = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_fat = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app_nutritionlog'

    def __str__(self):
        return f"{self.food.name} - {self.date}"


class ChatMessage(models.Model):
    role = models.CharField(max_length=20)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'app_chatmessage'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
