"""
AI Learning & Recommendation Models
- meal_recommendations: Gợi ý meal từ AI
- user_feedback_food: Phản hồi về thực phẩm
- user_feedback_recommendation: Phản hồi về gợi ý AI
- intent_patterns: Patterns để train intent classifier
"""

from django.db import models
from apps.users.models import Account
from apps.nutrition.models import Food


class MealRecommendation(models.Model):
    """Gợi ý meal từ AI"""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='meal_recommendations')
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    stt = models.IntegerField(null=True, blank=True, db_index=True)
    
    # Scores (0.0-1.0)
    score = models.DecimalField(max_digits=5, decimal_places=4, help_text='Overall score 0.0-1.0')
    match_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True, help_text='Taste match')
    budget_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True, help_text='Budget match')
    health_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True, help_text='Health match')
    
    reason = models.TextField(blank=True, help_text='Tại sao gợi ý')
    ai_model_version = models.CharField(max_length=50, default='v1', help_text='Model version used')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'meal_recommendations'
        indexes = [
            models.Index(fields=['account', '-score', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.account} -> {self.food.name} ({self.score})"


class UserFeedbackFood(models.Model):
    """Phản hồi người dùng về thực phẩm"""
    FEEDBACK_TYPES = [
        ('taste', 'Vị cảm'),
        ('health', 'Sức khỏe'),
        ('price', 'Giá cả'),
        ('convenience', 'Tiện lợi'),
        ('other', 'Khác'),
    ]
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='food_feedbacks')
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    stt = models.IntegerField(null=True, blank=True, db_index=True)
    
    rating = models.IntegerField(null=True, blank=True, help_text='1-5 stars')
    is_liked = models.BooleanField(null=True, blank=True)
    reason = models.TextField(blank=True)
    feedback_type = models.CharField(max_length=50, choices=FEEDBACK_TYPES, default='taste')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_feedback_food'
        indexes = [
            models.Index(fields=['account', 'food', 'created_at']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.account} -> {self.food.name}: {self.rating}/5"


class UserFeedbackRecommendation(models.Model):
    """Phản hồi về gợi ý của AI"""
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='recommendation_feedbacks')
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    stt = models.IntegerField(null=True, blank=True, db_index=True)
    recommendation = models.ForeignKey(MealRecommendation, on_delete=models.SET_NULL, null=True, blank=True)
    
    was_accepted = models.BooleanField(null=True, blank=True, help_text='Người dùng chấp nhận gợi ý')
    was_helpful = models.BooleanField(null=True, blank=True, help_text='Gợi ý có hữu ích')
    
    context = models.JSONField(default=dict, blank=True, help_text='Thông tin về gợi ý')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_feedback_recommendation'
        indexes = [
            models.Index(fields=['account', 'was_accepted', 'was_helpful']),
        ]
    
    def __str__(self):
        return f"{self.account} feedback on {self.food.name}"


class IntentPattern(models.Model):
    """Pattern để train intent classifier"""
    CREATED_BY_CHOICES = [
        ('admin', 'Admin'),
        ('ai', 'AI'),
        ('user', 'User'),
    ]
    
    intent = models.CharField(max_length=100, help_text='Intent type: recommendation, health, ingredient, budget')
    pattern = models.TextField(help_text='Example: "tôi muốn giảm cân"')
    
    confidence = models.FloatField(default=0.5, help_text='Pattern confidence')
    created_by = models.CharField(max_length=50, choices=CREATED_BY_CHOICES, default='admin')
    verified_by_admin = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'intent_patterns'
        indexes = [
            models.Index(fields=['intent', 'verified_by_admin']),
        ]
    
    def __str__(self):
        return f"{self.intent}: {self.pattern[:50]}"


class RecommendationLog(models.Model):
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, db_column='account_id', null=True, blank=True)
    food = models.ForeignKey(Food, on_delete=models.SET_NULL, db_column='food_id', null=True, blank=True)
    stt = models.IntegerField(null=True, blank=True, db_index=True)
    score = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    model_version = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'recommendation_log'

    def __str__(self):
        return f"Recommendation {self.food} for {self.account} ({self.score})"


class ModelMetadata(models.Model):
    model_name = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'model_metadata'

    def __str__(self):
        return f"{self.model_name} v{self.version}"
