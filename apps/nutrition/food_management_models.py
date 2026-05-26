"""
Nutrition & Food Enhancement Models
- food_categories: Danh mục thực phẩm
- food_verification_queue: Kiểm duyệt thực phẩm
"""

from django.db import models
from apps.nutrition.models import Food
from apps.users.models import Account


class FoodCategory(models.Model):
    """Danh mục thực phẩm"""
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=255, blank=True, help_text='Icon name or URL')
    order_index = models.IntegerField(default=0, help_text='Display order')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'food_categories'
        ordering = ['order_index', 'name']
    
    def __str__(self):
        return self.name


class FoodVerificationQueue(models.Model):
    """Kiểm duyệt thực phẩm trước khi sử dụng"""
    STATUS_CHOICES = [
        ('pending', 'Đang chờ'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Bị từ chối'),
    ]
    
    food = models.OneToOneField(Food, on_delete=models.CASCADE, related_name='verification_queue')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    submitted_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='food_submissions')
    verified_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='food_verifications')
    
    reason_submitted = models.TextField(blank=True, help_text='Tại sao submit')
    reason_verdict = models.TextField(blank=True, help_text='Kết quả duyệt')
    
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'food_verification_queue'
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.food.name} - {self.status}"
