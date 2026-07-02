from decimal import Decimal
from django.db import models


class MealPlanDayFollow(models.Model):
    """Theo dõi ngày đã theo thực đơn (đã ăn theo kế hoạch)."""
    id = models.BigAutoField(primary_key=True)
    account = models.ForeignKey('users.Account', on_delete=models.CASCADE, db_column='account_id', null=True, blank=True)
    date = models.DateField()
    followed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'meal_plan_day_follows'
        constraints = [
            models.UniqueConstraint(fields=['account', 'date'], name='uq_meal_plan_day_follow')
        ]

    def __str__(self):
        status = '✓' if self.followed else '✗'
        return f"{self.date} {status}"


class MealPlan(models.Model):
    #     Mô hình kế hoạch ăn uống (lập danh sách món ăn cho các ngày trong tuần).
    #     
    #     Trường:
    #     - account: Người dùng sở hữu kế hoạch ăn (ForeignKey đến Account, cho phép null cho guest)
    #     - food: Link đến Food (đơn vị là 1 mục ăn)
    #     - date: Ngày lập kế hoạch (format 'YYYY-MM-DD')
    #     - meal_type: Loại bữa ('Bữa sáng', 'Bữa trưa', 'Bữa tối', 'Bữa phụ')
    #     - servings: Số khẩu phần (có thể 0.5, 1, 2, v.v.)
    #     - notes: Ghi chú thêm (ví dụ: 'dùng dầu ít', 'không muối')
    #     - created_at: Thời điểm tạo kế hoạch
    #     
    #     GHI NHỚ:
    #     - MealPlan là dự tính, NutritionLog là thực tế đã ăn
    #     - Dùng servings × food.calories để tính năng lượng của mục ăn
    #     - Mỗi user có kế hoạch ăn riêng, không chia sẻ với user khác
    #     - Xóa account sẽ xóa toàn bộ meal plans của user đó
    id = models.BigAutoField(primary_key=True)
    account = models.ForeignKey('users.Account', on_delete=models.CASCADE, db_column='account_id', null=True, blank=True)
    food = models.ForeignKey('nutrition.Food', on_delete=models.DO_NOTHING, db_column='food_id')
    stt = models.IntegerField(null=True, blank=True, db_index=True)
    date = models.DateField()
    meal_type = models.CharField(max_length=50)
    servings = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1'))
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'meal_plans'

    def __str__(self):
        return f"{self.food.name} - {self.date}"
