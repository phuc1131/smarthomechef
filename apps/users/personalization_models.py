"""
User Personalization Models
- user_budgets: Ngân sách ăn uống
- user_behavior_profiles: Sở thích ăn uống
- user_health_goals: Mục tiêu sức khỏe
- diseases: Bệnh lý tham khảo
"""

from django.db import models
from django.contrib.auth.models import User as DjangoUser
from decimal import Decimal
from apps.users.models import Account

class UserBudget(models.Model):
    """Ngân sách người dùng"""
    PERIOD_CHOICES = [
        ('daily', 'Hàng ngày'),
        ('weekly', 'Hàng tuần'),
        ('monthly', 'Hàng tháng'),
    ]
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='budgets')
    budget_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text='VND')
    budget_period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='daily')
    currency = models.CharField(max_length=10, default='VND')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_budgets'
        unique_together = ('account', 'budget_period')
        indexes = [
            models.Index(fields=['account', 'budget_period', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.account} - {self.budget_amount} {self.currency}/{self.budget_period}"

class UserHealthGoal(models.Model):
    """Mục tiêu sức khỏe"""
    GOAL_TYPES = [
        ('weight_loss', 'Giảm cân'),
        ('muscle_gain', 'Tăng cơ'),
        ('maintain', 'Duy trì'),
        ('energy_boost', 'Tăng năng lượng'),
    ]
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='health_goals')
    goal_type = models.CharField(max_length=50, choices=GOAL_TYPES)
    target_weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text='kg')
    target_calories = models.IntegerField(null=True, blank=True, help_text='kcal/day')
    target_macros = models.JSONField(default=dict, blank=True, help_text='{"protein": 30, "carbs": 50, "fat": 20}')
    
    start_date = models.DateField(auto_now_add=True)
    target_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_health_goals'
        indexes = [
            models.Index(fields=['account', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.account} - {self.goal_type}"
