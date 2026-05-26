"""
Admin Management Models
- audit_logs: Tracking mọi thay đổi
- admin_settings: Cấu hình hệ thống
- system_metrics: Thống kê hệ thống
"""

from django.db import models
from apps.users.models import Account


class AuditLog(models.Model):
    """Audit logs - tracking mọi thay đổi"""
    ACTIONS = [
        ('CREATE', 'Tạo'),
        ('UPDATE', 'Sửa'),
        ('DELETE', 'Xóa'),
        ('VERIFY', 'Duyệt'),
        ('REJECT', 'Từ chối'),
        ('EXPORT', 'Xuất'),
        ('IMPORT', 'Nhập'),
    ]
    
    admin = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50, choices=ACTIONS)
    table_name = models.CharField(max_length=100, help_text='Table bị ảnh hưởng')
    record_id = models.IntegerField(help_text='ID của record')
    
    old_value = models.JSONField(null=True, blank=True, help_text='Giá trị cũ')
    new_value = models.JSONField(null=True, blank=True, help_text='Giá trị mới')
    reason = models.TextField(blank=True, help_text='Lý do thực hiện')
    
    ip_address = models.CharField(max_length=45, blank=True, help_text='IP của admin')
    user_agent = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['admin', 'created_at']),
            models.Index(fields=['table_name', 'action']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.admin} {self.action} {self.table_name}#{self.record_id}"


class AdminSetting(models.Model):
    """Cấu hình hệ thống"""
    setting_key = models.CharField(max_length=100, unique=True, help_text='Setting key')
    setting_value = models.JSONField(help_text='Setting value (JSON)')
    description = models.TextField(blank=True)
    
    updated_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'admin_settings'
    
    def __str__(self):
        return self.setting_key


class SystemMetric(models.Model):
    """Thống kê hệ thống"""
    METRIC_TYPES = [
        ('user_count', 'Số users'),
        ('food_count', 'Số foods'),
        ('meal_plan_count', 'Số meal plans'),
        ('recommendation_accuracy', 'Độ chính xác gợi ý'),
        ('api_latency', 'API latency'),
        ('db_size', 'Kích thước DB'),
        ('daily_active_users', 'DAU'),
    ]
    
    metric_name = models.CharField(max_length=100, choices=METRIC_TYPES)
    metric_value = models.FloatField()
    date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'system_metrics'
        indexes = [
            models.Index(fields=['metric_name', 'date']),
        ]
    
    def __str__(self):
        return f"{self.metric_name}: {self.metric_value}"


class AdminLog(models.Model):
    """Log chi tiết hoạt động admin"""
    LEVELS = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
    ]
    
    admin = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    level = models.CharField(max_length=20, choices=LEVELS, default='INFO')
    message = models.TextField()
    context = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_logs'
        indexes = [
            models.Index(fields=['admin', 'created_at']),
            models.Index(fields=['level', 'created_at']),
        ]
    
    def __str__(self):
        return f"[{self.level}] {self.message[:50]}"
