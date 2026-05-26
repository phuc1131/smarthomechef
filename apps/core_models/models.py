from django.db import models


class AIRecommendation(models.Model):
    #     Mô hình lưu trữ các khuyến nghị AI cho từng user.
#     Được tạo bằng cách gọi Gemini API với ngữ cảnh user profile + nutrition history.
#     
#     Trường:
#     - account: Người dùng được khuyến nghị
#     - food: Thực phẩm được khuyến nghị
#     - reason: Lý do khuyến nghị (ví dụ: "Giàu protein, phù hợp mục tiêu tăng cơ")
#     - score: Điểm phù hợp (0-100, cao hơn = phù hợp hơn)
#     - created_at: Thời điểm tạo khuyến nghị
#     
#     GHI NHỚ:
#     - Có thể cache/pre-compute để tránh gọi API quá nhiều
#     - Hiện tại tạo on-demand khi user request
#     - Dùng user goal, medical_conditions, dietary_preferences để filter
    account = models.ForeignKey('users.Account', on_delete=models.CASCADE, db_column='account_id')
    food = models.ForeignKey('nutrition.Food', on_delete=models.CASCADE, db_column='food_id')
    stt = models.IntegerField(null=True, blank=True, db_index=True)
    score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    budget_match_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_recommendations'


class SearchEvent(models.Model):
    account = models.ForeignKey('users.Account', on_delete=models.DO_NOTHING, db_column='account_id', null=True, blank=True)
    query_text = models.TextField()
    normalized_query = models.TextField(null=True, blank=True)
    result_count = models.IntegerField(default=0)
    clicked_food = models.ForeignKey(
        'nutrition.Food',
        on_delete=models.SET_NULL,
        db_column='clicked_food_id',
        null=True,
        blank=True,
        related_name='search_clicks',
    )
    clicked_food_stt = models.IntegerField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'search_events'