from types import SimpleNamespace
from django.utils import timezone
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# ===================== ACCOUNT =====================
class Account(models.Model):
    """
    Tài khoản đăng nhập (auth + role)
    """
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    password_hash = models.TextField()
    role = models.CharField(max_length=50, default='user')
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users'
        indexes = [models.Index(fields=['username'])]

    def __str__(self):
        return self.username


# ===================== USER PROFILE =====================
class UserProfile(models.Model):
    """
    Hồ sơ người dùng (sức khỏe + mục tiêu)
    """
    id = models.BigAutoField(primary_key=True)

    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        db_column='account_id'
    )

    # Basic info
    name = models.CharField(max_length=255, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)

    # Body metrics
    height = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Lifestyle
    activity_level = models.CharField(max_length=50, null=True, blank=True)

    # Health
    health_goal = models.TextField(null=True, blank=True)
    medical_conditions = models.TextField(null=True, blank=True)
    dietary_preferences = models.TextField(null=True, blank=True)

    # Calculated
    bmi = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    daily_calorie_target = models.IntegerField(null=True, blank=True)

    # Budget
    budget_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'
        indexes = [models.Index(fields=['account_id'])]

    def __str__(self):
        return self.name or f'Profile #{self.pk}'


# ===================== USER GOAL =====================
class UserGoal(models.Model):
    """
    Mục tiêu dinh dưỡng
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, db_column='account_id')
    goal_type = models.CharField(max_length=100, default='maintain')
    target_weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    daily_calorie_target = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'user_goals'
        unique_together = ('account', 'goal_type')

    @property
    def goal(self):
        return SimpleNamespace(name=self.goal_type) if self.goal_type else None


# ===================== PREFERENCE =====================
class UserPreferenceProfile(models.Model):
    """
    Sở thích user (phục vụ AI recommend)
    """
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        db_column='account_id',
        primary_key=True
    )

    preferred_macros = models.JSONField(null=True, blank=True)
    preferred_categories = models.JSONField(null=True, blank=True)
    preferred_keywords = models.JSONField(null=True, blank=True)
    avoided_keywords = models.JSONField(null=True, blank=True)

    healthy_score = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unhealthy_score = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_preference_profiles'


UserBehaviorProfile = UserPreferenceProfile


# ===================== DISEASE =====================
class Disease(models.Model):
    """
    Bệnh lý
    """
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'diseases'


class UserDisease(models.Model):
    """
    Mapping user - bệnh
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, db_column='account_id')
    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, db_column='disease_id')
    severity = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'user_diseases'
        unique_together = ('account', 'disease')


class DiseaseNutritionRule(models.Model):
    """
    Rule dinh dưỡng theo bệnh
    """
    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, db_column='disease_id')
    nutrient = models.CharField(max_length=50)
    rule_type = models.CharField(max_length=20)
    threshold_value = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        db_table = 'disease_nutrition_rules'


# ===================== FEEDBACK =====================
class UserFeedback(models.Model):
    """
    Feedback (rating/like)
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, db_column='account_id')
    food = models.ForeignKey('nutrition.Food', on_delete=models.CASCADE, db_column='food_id')
    stt = models.IntegerField(null=True, blank=True, db_index=True)

    rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    liked = models.BooleanField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_feedback'
        indexes = [
            models.Index(fields=['account_id']),
            models.Index(fields=['food_id']),
        ]


# ===================== BEHAVIOR LOG =====================
class UserBehaviorLog(models.Model):
    """
    Log hành vi user (tracking AI)
    """
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        db_column='account_id',
        null=True,
        blank=True
    )

    action_type = models.CharField(max_length=50)
    target_type = models.CharField(max_length=50, null=True, blank=True)
    target_id = models.BigIntegerField(null=True, blank=True)

    metadata = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_behavior_log'

    def __str__(self):
        return f"{self.account} - {self.action_type}"