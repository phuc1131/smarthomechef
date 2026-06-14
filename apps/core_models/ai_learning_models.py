"""
AI Learning & Recommendation Models
- meal_recommendations: Gợi ý meal từ AI
- user_feedback_food: Phản hồi về thực phẩm
- user_feedback_recommendation: Phản hồi về gợi ý AI
- intent_patterns: Patterns để train intent classifier
- experiments: A/B testing framework
"""

from django.db import models
from django.utils import timezone
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


class Experiment(models.Model):
    """A/B Testing Experiment Configuration"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=200, unique=True, help_text='Experiment name (e.g., "personalization_v2")')
    description = models.TextField(blank=True, help_text='Experiment description')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Variant configuration
    control_variant = models.CharField(max_length=50, default='control', help_text='Control variant name')
    test_variants = models.JSONField(default=list, help_text='List of test variant names: ["variant_a", "variant_b"]')
    
    # Assignment strategy
    ASSIGNMENT_CHOICES = [
        ('hash', 'Hash-based (user_id % num_variants)'),
        ('random', 'Random assignment'),
        ('manual', 'Manual assignment'),
    ]
    assignment_strategy = models.CharField(max_length=20, choices=ASSIGNMENT_CHOICES, default='hash')
    
    # Traffic allocation (percentage)
    traffic_allocation = models.IntegerField(default=100, help_text='Percentage of users to include (1-100)')
    
    # Targeting
    target_users = models.JSONField(default=dict, blank=True, help_text='User filters: {"min_id": 1, "max_id": 100}')
    
    # Dates
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'experiments'
        indexes = [
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    def is_active(self):
        """Check if experiment is currently running"""
        if self.status != 'active':
            return False
        now = timezone.now()
        if self.started_at and now < self.started_at:
            return False
        if self.ended_at and now > self.ended_at:
            return False
        return True
    
    def get_all_variants(self):
        """Get all variant names including control"""
        return [self.control_variant] + self.test_variants


class ExperimentAssignment(models.Model):
    """Track which variant each user is assigned to"""
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='assignments')
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    
    variant_name = models.CharField(max_length=50, help_text='Variant assigned to user')
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'experiment_assignments'
        unique_together = [['experiment', 'account']]
        indexes = [
            models.Index(fields=['experiment', 'variant_name']),
            models.Index(fields=['account', 'experiment']),
        ]
    
    def __str__(self):
        return f"{self.account} -> {self.experiment.name}:{self.variant_name}"


class ExperimentMetric(models.Model):
    """Track metrics for A/B test analysis"""
    METRIC_TYPES = [
        ('click_through_rate', 'Click Through Rate'),
        ('conversion_rate', 'Conversion Rate'),
        ('avg_rating', 'Average Rating'),
        ('food_acceptance_rate', 'Food Acceptance Rate'),
        ('engagement_score', 'Engagement Score'),
        ('nutritional_match_score', 'Nutritional Match Score'),
    ]
    
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='metrics')
    variant_name = models.CharField(max_length=50, default='control')
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES, default='click_through_rate')
    
    value = models.FloatField(default=0.0, help_text='Metric value')
    count = models.IntegerField(default=1, help_text='Number of samples')
    
    # For aggregated metrics
    mean = models.FloatField(null=True, blank=True)
    std_dev = models.FloatField(null=True, blank=True)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'experiment_metrics'
        unique_together = [['experiment', 'variant_name', 'metric_type']]
        indexes = [
            models.Index(fields=['experiment', 'variant_name']),
            models.Index(fields=['metric_type', 'recorded_at']),
        ]
    
    def __str__(self):
        return f"{self.experiment.name}:{self.variant_name} - {self.metric_type}: {self.value}"


class ExperimentEvent(models.Model):
    """Track individual user events for detailed analysis"""
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='events')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, db_index=True)
    
    event_type = models.CharField(max_length=50, db_index=True, help_text='recommendation_shown, recommendation_clicked, recommendation_rated')
    variant_name = models.CharField(max_length=50)
    
    food = models.ForeignKey(Food, on_delete=models.SET_NULL, null=True, blank=True)
    
    value = models.FloatField(null=True, blank=True, help_text='Event value (e.g., rating score)')
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional context')
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'experiment_events'
        indexes = [
            models.Index(fields=['experiment', 'event_type', 'variant_name']),
            models.Index(fields=['account', 'experiment']),
        ]
    
    def __str__(self):
        return f"{self.experiment.name}:{self.account}:{self.event_type}"


class AIRequestLog(models.Model):
    """Operational telemetry for AI routing, latency, cache and cost."""

    PROVIDER_CHOICES = [
        ('cache', 'Cache'),
        ('local_rule', 'Local rule'),
        ('local_llm', 'Local LLM'),
        ('gemini', 'Gemini'),
        ('fallback', 'Fallback'),
    ]

    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_request_logs')
    session_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    query_text = models.TextField(blank=True)
    normalized_query = models.TextField(blank=True)
    intent_name = models.CharField(max_length=100, blank=True)
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, db_index=True)
    route_path = models.CharField(max_length=50, blank=True, db_index=True)
    decision = models.CharField(max_length=100, blank=True)
    ab_variant = models.CharField(max_length=50, blank=True)
    cache_hit = models.BooleanField(default=False, db_index=True)
    latency_ms = models.IntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    response_ok = models.BooleanField(default=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'ai_request_logs'
        indexes = [
            models.Index(fields=['created_at', 'provider']),
            models.Index(fields=['provider', 'cache_hit', 'created_at']),
            models.Index(fields=['intent_name', 'created_at']),
        ]

    def __str__(self):
        return f"{self.provider}:{self.intent_name or 'unknown'} ({self.latency_ms}ms)"
