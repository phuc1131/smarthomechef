import calendar
import json
import logging
import re
from datetime import date, timedelta
from uuid import uuid4
import uuid

from django.contrib.auth.hashers import make_password
from apps.users.auth_utils import verify_account_password

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from app.config import REQUIRE_AUTH

# Import models từ các app tương ứng (đồng bộ với cấu trúc cơ sở dữ liệu mới)
from apps.users.models import Account, UserProfile, UserPreferenceProfile
from apps.nutrition.models import Food, NutritionLog, ShoppingItem, ShoppingList
from apps.meal_plans.models import MealPlan
from apps.chat.models import ChatMessage, ChatSession, MessageIntent, ChatResponseCache
from app.services.ai_orchestrator_service import AIOrchestratorService
from app.services.external_apis import (
    AI_AVAILABLE,
    call_gemini_with_debug as _service_call_gemini_with_debug,
    get_spoonacular_last_error as _get_spoonacular_last_error,
)
from app.services.meal_plan_generator_service import MealPlanGeneratorService
from apps.users.views import (
    _set_auth_session,
    get_current_account,
    get_default_meal_type,
    get_meal_type_choices,
    get_meal_type_color_map,
)


logger = logging.getLogger(__name__)

SEED_SESSION_PREFIX = '[SeedPersonalized]'


def _is_seed_chat_message(message):
    content = (getattr(message, 'content', '') or '').strip()
    if not content:
        return False
    if re.match(r'^\[[^\]]+\]\s*Mau\s+\d+:', content, flags=re.IGNORECASE):
        return True
    if re.match(r'^Phan hoi cho\s+.+\s+mau\s+\d+\.', content, flags=re.IGNORECASE):
        return True
    return 'He thong uu tien ca nhan hoa theo profile va muc tieu nguoi dung' in content


def parse_float(value):
    try:
        return float(value) if value not in (None, '') else None
    except (TypeError, ValueError):
        return None


def parse_int(value):
    try:
        return int(value) if value not in (None, '') else None
    except (TypeError, ValueError):
        return None


def require_auth(request):
    if not REQUIRE_AUTH:
        return None
    if get_current_account(request):
        return None
    return redirect('login')


def get_or_create_guest_account(request):
    client_ip = (request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR') or '127.0.0.1').split(',')[0].strip()

    guest_uuid = request.COOKIES.get('guest_uuid')
    if guest_uuid:
        guest_username = f'guest_{guest_uuid}'
    else:
        new_uuid = uuid4().hex
        # mark request so caller can set cookie in response
        request._guest_uuid_to_set = new_uuid
        guest_username = f'guest_{new_uuid[:8]}'

    account, _ = Account.objects.get_or_create(
        username=guest_username,
        defaults={
            'email': f'{guest_username}@local.smartchef',
            'password_hash': make_password('guest'),
            'role': 'guest',
            'is_active': True,
        },
    )
    return account


def get_profile(request_or_account=None):
    if request_or_account is None:
        return None
    if hasattr(request_or_account, 'session'):
        account = get_current_account(request_or_account)
    else:
        account = request_or_account
    if not account:
        return None
    profile, _ = UserProfile.objects.get_or_create(
        account=account,
        defaults={'name': account.username},
    )
    return profile


def get_chat_session(account):
    if not account:
        return None
    sessions = ChatSession.objects.filter(account=account).order_by('-created_at', '-id')
    for session in sessions:
        if session.title and session.title.startswith(SEED_SESSION_PREFIX):
            continue
        if ChatMessage.objects.filter(session=session).exclude(content__startswith='[').exclude(content__istartswith='Phan hoi cho ').exists():
            return session

    return ChatSession.objects.create(account=account, title=f'Chat {account.username}')


def classify_intent(user_text):
    return AIOrchestratorService.classify_intent(user_text)


def _append_health_feedback(response_text, account, user_text):
    return response_text


def _call_gemini_with_debug(profile_obj, chat_session, system_context):
    return _service_call_gemini_with_debug(chat_session, system_context)


def _search_keyword_hardcoded(user_text, account):
    query = (user_text or '').strip()
    if not query:
        return None
    food = Food.objects.filter(name__icontains=query).order_by('name').first()
    if food:
        return f'Mình tìm thấy món {food.name}.'
    return None


def _search_db_for_query(user_text, account):
    return _search_keyword_hardcoded(user_text, account)


def _find_saved_chat_answer(user_text):
    normalized = (user_text or '').strip().lower()
    if not normalized:
        return None
    cached = ChatResponseCache.objects.filter(normalized_query=normalized).order_by('-created_at').first()
    return cached.response if cached else None


def _backfill_chat_intents_from_history():
    return None


def _get_or_fetch_food(*args, **kwargs):
    return None


def _get_or_fetch_ingredient(*args, **kwargs):
    return None


def lookup_food(food_name, account=None, allow_fuzzy=False):
    if not food_name:
        return None
    return Food.objects.filter(name__iexact=food_name).first() or Food.objects.filter(name__icontains=food_name).order_by('name').first()


def search_foods(query, account=None, category=None, limit=20, allow_fuzzy=False):
    queryset = Food.objects.all().order_by('name')
    if query:
        queryset = queryset.filter(name__icontains=query)
    if category:
        queryset = queryset.filter(Q(category__name__iexact=category) | Q(category_name__iexact=category))
    return list(queryset[:limit])


def build_user_preference_profile(account):
    if not account:
        return None
    profile, _ = UserPreferenceProfile.objects.get_or_create(account=account)
    return profile


def _resolve_nutrition_targets(profile_obj):
    """Tính mục tiêu dinh dưỡng mặc định hoặc theo hồ sơ người dùng."""
    calorie_target = int(profile_obj.daily_calorie_target or 2000) if profile_obj else 2000
    weight = float(profile_obj.weight or 0) if profile_obj else 0

    protein_target = max(50, int(round(weight * 1.6))) if weight > 0 else max(50, int(round(calorie_target * 0.2 / 4)))
    carbs_target = max(120, int(round(calorie_target * 0.45 / 4)))
    fat_target = max(35, int(round(calorie_target * 0.30 / 9)))

    return {
        'calorie': calorie_target,
        'protein': protein_target,
        'carbs': carbs_target,
        'fat': fat_target,
    }


def _build_metric_insight(current_value, target_value, lower_is_better=False):
    """Tạo insight cho một chỉ số dinh dưỡng: % mục tiêu, trạng thái và phần còn thiếu/dư."""
    current_value = float(current_value or 0)
    target_value = float(target_value or 0)

    if target_value <= 0:
        return {
            'value': round(current_value, 1),
            'target': 0,
            'percent': 0,
            'status': 'chưa có mục tiêu',
            'remaining': 0,
            'direction': 'neutral',
        }

    percent = round((current_value / target_value) * 100, 1)
    remaining = round(target_value - current_value, 1)

    if lower_is_better:
        if current_value <= target_value:
            status = 'đạt'
            direction = 'good'
        elif current_value <= target_value * 1.15:
            status = 'hơi cao'
            direction = 'warn'
        else:
            status = 'vượt'
            direction = 'danger'
    else:
        if percent < 50:
            status = 'thiếu'
            direction = 'danger'
        elif percent <= 100:
            status = 'đủ'
            direction = 'good'
        else:
            status = 'vượt'
            direction = 'warn'

    return {
        'value': round(current_value, 1),
        'target': round(target_value, 1),
        'percent': max(0, percent),
        'status': status,
        'remaining': round(abs(remaining), 1),
        'direction': direction,
    }


def _build_nutrition_suggestions(today_insights):
    """Sinh gợi ý rule-based dựa trên kcal, protein, carbs và fat của hôm nay."""
    suggestions = []
    calorie = today_insights['calorie']
    protein = today_insights['protein']
    carbs = today_insights['carbs']
    fat = today_insights['fat']

    if calorie['target'] > 0 and calorie['percent'] < 50:
        suggestions.append({
            'type': 'danger',
            'title': 'Ăn còn thiếu năng lượng',
            'text': 'Bạn mới đạt dưới 50% mục tiêu kcal. Nên thêm bữa phụ giàu đạm và tinh bột tốt như sữa chua Hy Lạp, trứng, yến mạch, chuối.',
        })

    if protein['target'] > 0 and protein['percent'] < 70:
        suggestions.append({
            'type': 'primary',
            'title': 'Protein đang thấp',
            'text': 'Ưu tiên món giàu protein như ức gà, cá hồi, trứng, đậu hũ, sữa chua không đường để kéo gần mục tiêu hơn.',
        })

    if carbs['target'] > 0 and carbs['percent'] > 130:
        suggestions.append({
            'type': 'warning',
            'title': 'Carbs đang cao',
            'text': 'Carb đang vượt mức hợp lý. Nên giảm bớt cơm, bánh ngọt, nước ngọt và chuyển sang carbs phức hợp như khoai lang, yến mạch.',
        })

    if fat['target'] > 0 and fat['percent'] > 130:
        suggestions.append({
            'type': 'warning',
            'title': 'Chất béo đang cao',
            'text': 'Fat đang cao hơn mức khuyến nghị. Nên giảm đồ chiên, nước sốt béo, thịt mỡ và ưu tiên hấp, luộc, áp chảo ít dầu.',
        })

    if not suggestions:
        suggestions.append({
            'type': 'success',
            'title': 'Nhịp ăn uống ổn định',
            'text': 'Không có cảnh báo lớn. Hãy duy trì phân bổ bữa ăn đều và theo dõi thêm 1-2 ngày để xác nhận xu hướng.',
        })

    return suggestions


def _build_ai_quota_fallback_response(account, user_text):
    """Tạo phản hồi dự phòng khi AI provider hết quota hoặc tạm lỗi."""
    foods = list(Food.objects.all().order_by('name')[:5])
    if not foods:
        return (
            'AI đang quá tải nên chưa phản hồi ngay được. '
            'Bạn có thể thử lại sau ít phút hoặc nhập tên món cụ thể để mình tra cứu từ CSDL nội bộ.'
        )

    food_lines = '\n'.join(f"- {food.name}" for food in foods)
    return (
        'AI đang quá tải (hết quota tạm thời), mình chuyển sang chế độ dữ liệu nội bộ.\n'
        'Bạn có thể chọn nhanh một trong các món sau:\n'
        f'{food_lines}\n'
        'Hãy nhắn tên món bạn muốn để mình trả thông tin dinh dưỡng chi tiết.'
    )


def _build_daily_insight(metric_name, current_value, target_value, yesterday_value, weekly_avg_value, lower_is_better=False):
    """Ghép số hôm nay với hôm qua và trung bình 7 ngày để tạo thẻ so sánh."""
    insight = _build_metric_insight(current_value, target_value, lower_is_better=lower_is_better)
    return {
        'metric': metric_name,
        'current': insight['value'],
        'target': insight['target'],
        'percent': insight['percent'],
        'status': insight['status'],
        'remaining': insight['remaining'],
        'direction': insight['direction'],
        'yesterday': round(float(yesterday_value or 0), 1),
        'weekly_avg': round(float(weekly_avg_value or 0), 1),
        'vs_yesterday': round(float(current_value or 0) - float(yesterday_value or 0), 1),
        'vs_weekly_avg': round(float(current_value or 0) - float(weekly_avg_value or 0), 1),
    }


def login_page(request):
    """Hiển thị trang đăng nhập cho người dùng chưa có session."""
    if request.session.get('user_id'):
        return redirect('dashboard')
    return render(request, 'user/login.html', {'active': 'auth'})


def register_page(request):
    """Hiển thị trang đăng ký cho người dùng chưa có session."""
    if request.session.get('user_id'):
        return redirect('dashboard')
    return render(request, 'user/register.html', {'active': 'auth'})


def _resolve_plan_days(user_text):
    """Đọc số ngày từ câu chat để biết người dùng muốn tạo thực đơn bao lâu."""
    text = (user_text or '').lower()
    if any(k in text for k in ['tuan', 'tuần', 'weekly', 'ca tuan', 'cả tuần', '7 ngay', '7 ngày']):
        return 7

    match = re.search(r'(\d{1,2})\s*(ngay|ngày|day|days)', text)
    if match:
        days = int(match.group(1))
        return max(1, min(days, 14))

    if any(k in text for k in ['ngay', 'ngày', 'daily', 'hom nay', 'hôm nay', 'ngay mai', 'ngày mai']):
        return 1
    return 0


def _resolve_plan_start_date(user_text):
    """Xác định ngày bắt đầu của thực đơn, mặc định là hôm nay."""
    text = (user_text or '').lower()
    today = date.today()
    if 'ngay mai' in text or 'ngày mai' in text or 'tomorrow' in text:
        return today + timedelta(days=1)
    return today


def _is_meal_plan_update_request(user_text):
    """Kiểm tra xem người dùng đang yêu cầu cập nhật/ghi đè thực đơn hay không."""
    text = (user_text or '').lower()
    return any(k in text for k in [
        'cap nhat', 'cập nhật', 'update', 'replace', 'ghi đè', 'ghi de', 'thay the', 'thay thế', 'sua', 'sửa',
    ])


def _auto_create_meal_plan_from_chat(user_text, account):
    """Tự tạo thực đơn từ câu chat nếu người dùng có nhắc tới kế hoạch ăn."""
    text = (user_text or '').lower()
    is_plan_request = any(k in text for k in [
        'thuc don', 'thực đơn', 'meal plan', 'menu', 'len thuc don', 'lập thực đơn', 'lap thuc don',
    ])
    if not is_plan_request:
        return None

    role = (getattr(account, 'role', '') or '').strip().lower()
    if not account or role == 'guest':
        return {
            'success': False,
            'meal_plan_created': False,
            'message': 'Bạn cần đăng nhập để AI có thể tự tạo thực đơn và lưu vào trang /thuc-don/.',
        }

    start_day = _resolve_plan_start_date(user_text)
    result = MealPlanGeneratorService.generate_meal_plan(
        account=account,
        request_text=user_text,
        target_date=start_day,
    )

    if not result.get('success'):
        return {
            'success': False,
            'meal_plan_created': False,
            'message': result.get('message') or 'Không thể tạo thực đơn lúc này.',
        }

    meal_plan_url = '/thuc-don/'
    plan_dates = result.get('plan_dates') or []
    if plan_dates:
        try:
            first_plan_date = date.fromisoformat(str(plan_dates[0]))
            meal_plan_url = f'/thuc-don/?year={first_plan_date.year}&month={first_plan_date.month}'
        except Exception:
            pass

    return {
        'success': True,
        'meal_plan_created': True,
        'meal_plan_url': meal_plan_url,
        'plan_dates': plan_dates,
        'message': result.get('message') or 'Đã tạo thực đơn và lưu vào trang Thực đơn.',
    }


def dashboard(request):
    """Tổng hợp dữ liệu dinh dưỡng hôm nay, hôm qua và trung bình 7 ngày."""
    today_obj = date.today()
    today = today_obj.isoformat()
    yesterday_obj = today_obj - timedelta(days=1)
    week_start_obj = today_obj - timedelta(days=6)

    account = get_current_account(request)
    nutrition_log_fields = ('id', 'account_id', 'food_id', 'date', 'meal_type', 'servings', 'created_at', 'food__name', 'food__calories', 'food__protein', 'food__carbs', 'food__fat')

    logs_qs = NutritionLog.objects.select_related('food').only(*nutrition_log_fields)
    if account:
        logs_qs = logs_qs.filter(account=account)

    today_logs = logs_qs.filter(date=today)
    yesterday_logs = logs_qs.filter(date=yesterday_obj.isoformat())
    weekly_logs = logs_qs.filter(date__gte=week_start_obj.isoformat(), date__lte=today)
    tracking_logs = today_logs.select_related('food').order_by('meal_type', 'id')

    def _sum_metric(queryset, metric_name):
        total = 0.0
        for log in queryset:
            servings = float(log.servings or 0)
            food = log.food
            if metric_name == 'total_calories':
                total += float((food.calories if food else 0) or 0) * servings
            elif metric_name == 'total_protein':
                total += float((food.protein if food else 0) or 0) * servings
            elif metric_name == 'total_carbs':
                total += float((food.carbs if food else 0) or 0) * servings
            elif metric_name == 'total_fat':
                total += float((food.fat if food else 0) or 0) * servings
        return round(total, 1)

    today_calories = _sum_metric(today_logs, 'total_calories')
    today_protein = _sum_metric(today_logs, 'total_protein')
    today_carbs = _sum_metric(today_logs, 'total_carbs')
    today_fat = _sum_metric(today_logs, 'total_fat')

    yesterday_calories = _sum_metric(yesterday_logs, 'total_calories')
    yesterday_protein = _sum_metric(yesterday_logs, 'total_protein')
    yesterday_carbs = _sum_metric(yesterday_logs, 'total_carbs')
    yesterday_fat = _sum_metric(yesterday_logs, 'total_fat')

    weekly_days = 7
    weekly_avg = {
        'calories': round(sum(float((log.food.calories if log.food else 0) or 0) * float(log.servings or 0) for log in weekly_logs) / weekly_days, 1),
        'protein': round(sum(float((log.food.protein if log.food else 0) or 0) * float(log.servings or 0) for log in weekly_logs) / weekly_days, 1),
        'carbs': round(sum(float((log.food.carbs if log.food else 0) or 0) * float(log.servings or 0) for log in weekly_logs) / weekly_days, 1),
        'fat': round(sum(float((log.food.fat if log.food else 0) or 0) * float(log.servings or 0) for log in weekly_logs) / weekly_days, 1),
    }

    week_plans = MealPlan.objects.filter(date__gte=week_start_obj.isoformat(), date__lte=today, account=account).count()
    total_foods = Food.objects.count()
    profile_obj = get_profile(get_current_account(request))
    targets = _resolve_nutrition_targets(profile_obj)

    calorie_target = targets['calorie']
    protein_target = targets['protein']
    carbs_target = targets['carbs']
    fat_target = targets['fat']

    today_insights = {
        'calorie': _build_metric_insight(today_calories, calorie_target),
        'protein': _build_metric_insight(today_protein, protein_target),
        'carbs': _build_metric_insight(today_carbs, carbs_target),
        'fat': _build_metric_insight(today_fat, fat_target, lower_is_better=True),
    }

    metric_cards = [
        _build_daily_insight('kcal', today_calories, calorie_target, yesterday_calories, weekly_avg['calories']),
        _build_daily_insight('protein', today_protein, protein_target, yesterday_protein, weekly_avg['protein']),
        _build_daily_insight('carbs', today_carbs, carbs_target, yesterday_carbs, weekly_avg['carbs']),
        _build_daily_insight('fat', today_fat, fat_target, yesterday_fat, weekly_avg['fat'], lower_is_better=True),
    ]

    suggestions = _build_nutrition_suggestions(today_insights)

    streak = 0
    check_date = date.today()
    for _ in range(30):
        if NutritionLog.objects.filter(date=check_date.isoformat()).exists():
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    foods = list(Food.objects.all())
    import random
    food_recommendations = random.sample(foods, min(4, len(foods))) if foods else []

    tracking_rows = []
    for log in tracking_logs:
        servings = float(log.servings or 0)
        food = log.food
        tracking_rows.append({
            'id': log.pk,
            'food_name': log.food.name if log.food else 'Không rõ',
            'meal_type': log.meal_type or 'Không rõ',
            'servings': servings,
            'calories': float((food.calories if food else 0) or 0) * servings,
            'protein': float((food.protein if food else 0) or 0) * servings,
            'carbs': float((food.carbs if food else 0) or 0) * servings,
            'fat': float((food.fat if food else 0) or 0) * servings,
        })

    calorie_pct = min(100, int(today_calories / calorie_target * 100)) if calorie_target else 0

    context = {
        'today_calories': round(today_calories, 1),
        'today_protein': round(today_protein, 1),
        'today_carbs': round(today_carbs, 1),
        'today_fat': round(today_fat, 1),
        'calorie_target': calorie_target or 2000,
        'calorie_pct': calorie_pct,
        'meals_logged': today_logs.count(),
        'week_plans': week_plans,
        'total_foods': total_foods,
        'streak': streak,
        'profile': profile_obj,
        'nutrition_cards': metric_cards,
        'nutrition_insights': today_insights,
        'nutrition_suggestions': suggestions,
        'food_recommendations': food_recommendations,
        'tracking_rows': tracking_rows,
        'today_metrics': {
            'today': {
                'calories': today_calories,
                'protein': today_protein,
                'carbs': today_carbs,
                'fat': today_fat,
            },
            'yesterday': {
                'calories': yesterday_calories,
                'protein': yesterday_protein,
                'carbs': yesterday_carbs,
                'fat': yesterday_fat,
            },
            'weekly_avg': weekly_avg,
        },
        'suggestions': food_recommendations,
        'today': date.today(),
        'active': 'dashboard',
    }
    return render(request, 'user/dashboard.html', context)


def chat_page(request):
    """Render trang chat và nạp lịch sử hội thoại hiện tại."""
    gate = require_auth(request)
    if gate:
        return gate

    account = get_current_account(request)
    if not account:
        account = get_or_create_guest_account(request)

    chat_session = get_chat_session(account)
    messages = ChatMessage.objects.filter(session=chat_session).order_by('created_at')
    messages_data = [
        {'role': m.role, 'content': m.content}
        for m in messages
        if not _is_seed_chat_message(m)
    ]
    response = render(request, 'user/chat.html', {
        'messages_data': messages_data,
        'account_id': account.pk,
        'account_name': account.username,
        'active': 'chat',
    })
    # Nếu chúng ta vừa tạo guest UUID, set cookie để phiên trình duyệt lưu định danh
    if hasattr(request, '_guest_uuid_to_set'):
        try:
            response.set_cookie('guest_uuid', request._guest_uuid_to_set, max_age=60*60*24*365, httponly=True, samesite='Lax')
        except Exception:
            pass
    return response


@csrf_exempt
@require_POST
def chat_send(request):
    """Xử lý gửi tin nhắn, ghi log, phân loại intent và trả phản hồi cho chatbot."""
    try:
        data = json.loads(request.body)
        user_text = data.get('message', '').strip()
        if not user_text:
            return JsonResponse({'error': 'Tin nhan trong'}, status=400)

        account = get_current_account(request)
        if not account:
            account = get_or_create_guest_account(request)

        chat_session = get_chat_session(account)
        user_msg = ChatMessage.objects.create(session=chat_session, role='user', content=user_text)

        intent, confidence = classify_intent(user_text)
        if intent:
            MessageIntent.objects.create(message=user_msg, intent=intent, confidence=confidence)

        auto_plan_result = _auto_create_meal_plan_from_chat(user_text, account)
        if auto_plan_result:
            response_text = auto_plan_result.get('message', '')
            if auto_plan_result.get('meal_plan_created'):
                response_text = _append_health_feedback(response_text, account, user_text)
            msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
            response_payload = {'role': msg.role, 'content': msg.content}
            if auto_plan_result.get('meal_plan_created'):
                response_payload['meal_plan_created'] = True
                response_payload['meal_plan_url'] = auto_plan_result.get('meal_plan_url', '/thuc-don/')
            return JsonResponse(response_payload)

        hardcoded_result = _search_keyword_hardcoded(user_text, account)
        if hardcoded_result:
            response_text = _append_health_feedback(hardcoded_result, account, user_text)
            msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
            return JsonResponse({'role': msg.role, 'content': msg.content})

        db_result = _search_db_for_query(user_text, account)
        if db_result:
            response_text = db_result
        else:
            saved_chat_result = _find_saved_chat_answer(user_text)
            invalid_saved_markers = (
                'Loi AI [',
                'RESOURCE_EXHAUSTED',
                'He thong tam thoi gap loi',
                'Khong co phan hoi tu AI',
            )
            if saved_chat_result and not any(marker in saved_chat_result for marker in invalid_saved_markers):
                response_text = saved_chat_result
            elif not AI_AVAILABLE:
                response_text = 'Du lieu khong khop. AI chua kich hoat.'
            else:
                # BƯỚC 1: Check ChatResponseCache trước khi gọi Gemini
                from app.services.external_apis import get_or_create_chat_response_from_cache, save_chat_response_to_cache
                
                cache_result = get_or_create_chat_response_from_cache(account, user_text, source_intent=intent.name if intent else None)
                if cache_result:
                    response_text = cache_result['response']
                else:
                    # Không tìm thấy cache, gọi Gemini API
                    profile_obj = get_profile(account)
                    system_context = (
                        'Ban la "Noi Tro AI", tro ly noi tro thong minh nguoi Viet. '
                        'Ban giup goi y mon an, tu van dinh duong va len thuc don. '
                        'Hay tra loi bang tieng Viet, than thien va huu ich. '
                        'Uu tien cac mon an Viet Nam truyen thong va lanh manh.\n'
                    )
                    if profile_obj:
                        system_context += (
                            f'Nguoi dung: {profile_obj.name}, '
                            f'tuoi {profile_obj.age or "?"}, '
                            f'nang {profile_obj.weight or "?"}kg, '
                            f'muc tieu suc khoe: {profile_obj.activity_level or "chua cung cap"}.'
                        )

                    ai_text, ai_err = _call_gemini_with_debug(profile_obj, chat_session, system_context)
                    if ai_err:
                        err_code = ai_err.get('error', 'UNKNOWN')
                        err_msg = ai_err.get('msg', '')
                        if '429' in err_msg or 'RESOURCE_EXHAUSTED' in err_msg or err_code == 'RESOURCE_EXHAUSTED':
                            response_text = _build_ai_quota_fallback_response(account, user_text)
                        else:
                            response_text = 'AI tam thoi gap loi. Ban thu lai sau it phut hoac nhap ten mon cu the de minh tra CSDL noi bo.'
                    else:
                        response_text = (ai_text or '').strip()
                        if (
                            '429' in response_text
                            or 'RESOURCE_EXHAUSTED' in response_text
                            or 'exceeded your current quota' in response_text.lower()
                        ):
                            response_text = _build_ai_quota_fallback_response(account, user_text)
                        elif not response_text:
                            response_text = 'AI hien tai khong tra ve noi dung. Vui long thu lai sau it phut.'
                    
                    # BƯỚC 2: Cache successful response nếu không phải lỗi
                    if not any(marker in response_text for marker in invalid_saved_markers):
                        try:
                            save_chat_response_to_cache(
                                account, 
                                user_text, 
                                response_text, 
                                source_intent=intent.name if intent else None
                            )
                        except Exception:
                            pass  # Cache save failed, but continue with response

        response_text = _append_health_feedback(response_text, account, user_text)

        msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
        build_user_preference_profile(account)
        return JsonResponse({'role': msg.role, 'content': msg.content})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Du lieu gui len khong hop le'}, status=400)
    except Exception:
        logger.exception('chat_send failed unexpectedly')
        return JsonResponse({'error': 'He thong tam thoi gap loi. Vui long thu lai sau it phut.'}, status=500)


@csrf_exempt
@require_POST
def chat_clear(request):
    """Xóa toàn bộ lịch sử chat của tài khoản hiện tại, không xóa cache AI dùng chung."""
    account = get_current_account(request)
    if not account:
        account = get_or_create_guest_account(request)

    chat_sessions = ChatSession.objects.filter(account=account)
    if chat_sessions.exists():
        MessageIntent.objects.filter(message__session__in=chat_sessions).delete()
        ChatMessage.objects.filter(session__in=chat_sessions).delete()
        chat_sessions.delete()
    return JsonResponse({'ok': True})


def meal_plans(request):
    """Render lịch thực đơn theo tháng và nạp các plan đã lưu cho user hiện tại."""
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    cal = calendar.monthcalendar(year, month)

    first_day = f'{year}-{month:02d}-01'
    if month == 12:
        last_day = f'{year + 1}-01-01'
    else:
        last_day = f'{year}-{month + 1:02d}-01'

    # Lọc meal plans theo user hiện tại
    account = get_current_account(request)
    plans = MealPlan.objects.filter(
        date__gte=first_day,
        date__lt=last_day,
        account=account
    ).select_related('food')

    plans_by_date = {}
    for plan in plans:
        key = plan.date.isoformat() if hasattr(plan.date, 'isoformat') else str(plan.date)[:10]
        plans_by_date.setdefault(key, []).append(plan)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    month_names = ['', 'Thang 1', 'Thang 2', 'Thang 3', 'Thang 4', 'Thang 5', 'Thang 6',
                   'Thang 7', 'Thang 8', 'Thang 9', 'Thang 10', 'Thang 11', 'Thang 12']

    foods = Food.objects.all().order_by('name')
    plans_by_date_data = {
        k: [{'food': p.food.name, 'meal_type': p.meal_type, 'id': p.id} for p in v]
        for k, v in plans_by_date.items()
    }
    context = {
        'calendar': cal,
        'year': year,
        'month': month,
        'month_name': month_names[month],
        'plans_by_date': plans_by_date,
        'plans_by_date_data': plans_by_date_data,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'today': today,
        'today_str': today.isoformat(),
        'foods': foods,
        'meal_types': get_meal_type_choices(),
        'meal_type_colors': get_meal_type_color_map(),
        'active': 'meal_plans',
    }
    return render(request, 'user/meal_plans.html', context)


@csrf_exempt
@require_POST
def meal_plan_add(request):
    """Thêm một món mới vào thực đơn theo ngày và loại bữa cho user hiện tại."""
    data = json.loads(request.body)
    food = get_object_or_404(Food, id=data.get('food_id'))
    default_meal_type = get_default_meal_type()
    account = get_current_account(request)
    
    plan = MealPlan.objects.create(
        account=account,
        food=food,
        date=data.get('date', date.today().isoformat()),
        meal_type=data.get('meal_type') or default_meal_type,
        servings=float(data.get('servings', 1)),
        notes=data.get('notes', ''),
    )
    return JsonResponse({'id': plan.pk, 'food': food.name, 'date': plan.date, 'meal_type': plan.meal_type})


@csrf_exempt
@require_POST
def meal_plan_delete(request, plan_id):
    """Xóa một mục thực đơn theo id (chỉ có thể xóa thực đơn của chính user)."""
    account = get_current_account(request)
    plan = get_object_or_404(MealPlan, id=plan_id, account=account)
    plan.delete()
    return JsonResponse({'ok': True})




def shopping_list_page(request):
    """Render trang danh sách mua sắm từ Meal Plan."""
    return render(request, 'user/shopping_list.html', {
        'active': 'shopping_list',
    })


def nutrition(request):
    """Hiển thị trang theo dõi dinh dưỡng theo ngày và trend 7 ngày."""
    today = date.today()
    selected_date_str = request.GET.get('date', today.isoformat())
    try:
        date.fromisoformat(selected_date_str)
    except ValueError:
        selected_date_str = today.isoformat()

    day_logs = NutritionLog.objects.filter(date=selected_date_str).select_related('food')
    total_cal = sum(float(log.total_calories or 0) for log in day_logs)
    total_pro = sum(float(log.total_protein or 0) for log in day_logs)
    total_car = sum(float(log.total_carbs or 0) for log in day_logs)
    total_fat_v = sum(float(log.total_fat or 0) for log in day_logs)

    trend = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        logs = NutritionLog.objects.filter(date=d)
        trend.append({
            'date': (today - timedelta(days=i)).strftime('%d/%m'),
            'calories': round(sum(float(log.total_calories or 0) for log in logs), 1),
            'protein': round(sum(float(log.total_protein or 0) for log in logs), 1),
            'carbs': round(sum(float(log.total_carbs or 0) for log in logs), 1),
            'fat': round(sum(float(log.total_fat or 0) for log in logs), 1),
        })

    profile_obj = get_profile()
    calorie_target = profile_obj.daily_calorie_target if profile_obj else 2000
    foods = Food.objects.all().order_by('name')

    context = {
        'selected_date': selected_date_str,
        'day_logs': day_logs,
        'total_cal': round(total_cal, 1),
        'total_pro': round(total_pro, 1),
        'total_car': round(total_car, 1),
        'total_fat': round(total_fat_v, 1),
        'calorie_target': calorie_target or 2000,
        'calorie_pct': min(100, int(total_cal / (calorie_target or 2000) * 100)),
        'trend_data': trend,
        'foods': foods,
        'meal_types': get_meal_type_choices(),
        'active': 'nutrition',
        'today': today.isoformat(),
    }
    return render(request, 'user/nutrition.html', context)


@csrf_exempt
@require_POST
def nutrition_log(request):
    """Tạo bản ghi dinh dưỡng thực tế từ món ăn và số servings."""
    data = json.loads(request.body)
    food = get_object_or_404(Food, id=data.get('food_id'))
    servings = float(data.get('servings', 1))
    account = get_current_account(request)
    log = NutritionLog.objects.create(
        account=account,
        food=food,
        date=data.get('date', date.today().isoformat()),
        meal_type=data.get('meal_type', 'Bua sang'),
        servings=servings,
    )
    if account:
        build_user_preference_profile(account)
    return JsonResponse({'id': log.pk, 'food': food.name, 'calories': round(float(food.calories or 0) * servings, 2)})


@csrf_exempt
@require_POST
def nutrition_delete(request, log_id):
    """Xóa một bản ghi dinh dưỡng đã lưu."""
    log = get_object_or_404(NutritionLog, id=log_id)
    log.delete()
    return JsonResponse({'ok': True})


def _food_source(food):
    """Xác định nguồn dữ liệu món ăn để đồng bộ hiển thị giữa các endpoint."""
    return 'api' if food.description and 'Spoonacular' in food.description else 'database'


def _serialize_food(food, default_serving=''):
    """Chuẩn hóa payload food dùng chung cho trang món ăn, search API và lookup API."""
    return {
        'id': food.id,
        'name': food.name,
        'category': food.category.name if food.category else None,
        'calories': float(food.calories or 0),
        'protein': float(food.protein or 0),
        'carbs': float(food.carbs or 0),
        'fat': float(food.fat or 0),
        'fiber': float(food.fiber or 0),
        'serving_size': getattr(food, 'serving_size', None) or default_serving,
        'description': food.description or '',
        'image_url': food.image_url or '',
        'source': _food_source(food),
    }


def foods(request):
    """Hiển thị danh sách món ăn với bộ lọc theo tên và category."""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    account = get_current_account(request)
    if query:
        food_list = search_foods(query, account=account, category=category or None, limit=20, allow_fuzzy=False)
    else:
        food_list = list(Food.objects.all().order_by('name'))
        if category:
            food_list = [food for food in food_list if food.category_name == category]

    search_notice = ''
    if query and not food_list:
        search_notice = _get_spoonacular_last_error() or ''

    categories = Food.objects.values_list('category__name', flat=True).distinct().order_by('category__name')

    foods_data = []
    for food in food_list:
        row = _serialize_food(food)
        row.update({
            'is_vegetarian': food.is_vegetarian,
            'is_diabetes_friendly': food.is_diabetes_friendly,
            'is_weight_loss_friendly': food.is_weight_loss_friendly,
        })
        foods_data.append(row)

    return render(request, 'user/foods.html', {
        'foods': food_list,
        'foods_data': foods_data,
        'query': query,
        'category': category,
        'categories': [c for c in categories if c],
        'search_notice': search_notice,
        'active': 'foods',
    })


@require_GET
def foods_search(request):
    """API tìm món ăn nhanh, ưu tiên CSDL rồi mới bổ sung từ API ngoài."""
    q = request.GET.get('q', '').strip()
    account = get_current_account(request)
    
    food_list = search_foods(q, account=account, limit=20, allow_fuzzy=False) if q else list(Food.objects.all().order_by('name')[:20])

    response = JsonResponse([_serialize_food(f) for f in food_list], safe=False)
    if q and len(food_list) == 0:
        last_error = _get_spoonacular_last_error()
        if last_error:
            response['X-Food-Search-Error'] = last_error
    return response


@require_GET
def food_lookup(request):
    """Tra cứu một món ăn theo tên, ưu tiên CSDL rồi mới gọi API ngoài."""
    food_name = request.GET.get('name', '').strip()
    if not food_name:
        return JsonResponse({'success': False, 'message': 'Tên thực phẩm không được để trống'}, status=400)

    account = get_current_account(request)
    food = lookup_food(food_name, account=account, allow_fuzzy=False)
    if not food:
        food = Food.objects.filter(name__icontains=food_name).order_by('name').first()
    
    if not food:
        return JsonResponse({
            'success': False,
            'message': f'Không tìm thấy thực phẩm "{food_name}". Vui lòng thử từ khác hoặc thêm thủ công.'
        }, status=404)
    
    return JsonResponse({
        'success': True,
        'food': _serialize_food(food, default_serving='100g')
    })


@csrf_exempt
@require_POST
def ai_parse_ingredients(request):
    """Parse nguyên liệu từ text tiếng Việt tự nhiên.

    Request body: {"text": "..."}
    Response: JSON with keys 'success' and 'ingredients'
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)

    user_text = (data.get('text') or '').strip()
    if not user_text:
        return JsonResponse({'success': False, 'message': 'Empty text'}, status=400)

    try:
        from app.services.ingredient_parser_service import parse_ingredients_from_text
        result = parse_ingredients_from_text(user_text)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}', 'ingredients': []}, status=500)


@csrf_exempt
@require_POST
def ai_recommend_recipes(request):
    """Gợi ý danh sách món ăn từ danh sách nguyên liệu.
    
    Request body:
    {
        "ingredients": ["trứng", "thịt heo", "hành"]
    }
    
    Response:
    {
        "success": true,
        "recipes": [
            {
                "name": "Cơm trứng thịt heo",
                "time": "15 phút",
                "difficulty": "easy",
                "confidence": 0.9,
                "missing_ingredients": [],
                "substitute_suggestions": {}
            }
        ],
        "message": "Found 5 recipes"
    }
    """
    try:
        data = json.loads(request.body)
        ingredients = data.get('ingredients', [])
        if not ingredients:
            return JsonResponse({'success': False, 'recipes': [], 'message': 'Danh sách nguyên liệu trống'}, status=400)
        
        from app.services.recipe_generator_service import recommend_recipes_from_ingredients
        result = recommend_recipes_from_ingredients(
            ingredients,
            limit=10,
            account=get_current_account(request) or get_or_create_guest_account(request),
        )
        
        return JsonResponse(result)
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'recipes': [], 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'recipes': [],
            'message': f'Error: {str(e)}',
        }, status=500)


@csrf_exempt
@require_POST
def ai_generate_recipe(request):
    """Tạo chi tiết công thức cho một món ăn cụ thể.
    
    Request body:
    {
        "recipe_name": "Cơm trứng thịt heo",
        "ingredients": ["trứng", "thịt heo", "hành", "cơm", "dầu ăn"]
    }
    
    Response:
    {
        "success": true,
        "recipe": {
            "name": "Cơm trứng thịt heo",
            "servings": 2,
            "time_minutes": 15,
            "ingredients": [...],
            "instructions": [...],
            "tips": [...],
            "nutrition": {...}
        },
        "message": "Recipe details generated"
    }
    """
    try:
        data = json.loads(request.body)
        recipe_name = data.get('recipe_name', '').strip()
        ingredients = data.get('ingredients', [])
        
        if not recipe_name or not ingredients:
            return JsonResponse({
                'success': False,
                'recipe': {},
                'message': 'Tên công thức hoặc nguyên liệu trống'
            }, status=400)
        
        from app.services.recipe_generator_service import generate_recipe_details
        result = generate_recipe_details(recipe_name, ingredients)
        
        return JsonResponse(result)
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'recipe': {}, 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'recipe': {},
            'message': f'Error: {str(e)}',
        }, status=500)


@csrf_exempt
@require_POST
def ai_recipe_variations(request):
    """Gợi ý biến tấu công thức khi thiếu nguyên liệu.
    
    Request body:
    {
        "recipe_name": "Cơm trứng thịt heo",
        "available_ingredients": ["trứng", "thịt heo", "hành", "cơm"],
        "missing_ingredients": ["dầu ăn", "nước mắm"]
    }
    
    Response:
    {
        "success": true,
        "original_recipe": "Cơm trứng thịt heo",
        "variations": [
            {
                "name": "Cơm trứng thịt heo (không dầu ăn, nước mắm)",
                "missing": ["dầu ăn", "nước mắm"],
                "substitutions": {},
                "instructions_changes": [...],
                "impact": "minimal",
                "confidence": 0.7
            }
        ],
        "message": "Generated 2 recipe variations"
    }
    """
    try:
        data = json.loads(request.body)
        recipe_name = data.get('recipe_name', '').strip()
        available_ingredients = data.get('available_ingredients', [])
        missing_ingredients = data.get('missing_ingredients', [])
        
        if not recipe_name:
            return JsonResponse({
                'success': False,
                'variations': [],
                'message': 'Tên công thức trống'
            }, status=400)
        
        from app.services.recipe_variations_service import generate_recipe_variations
        result = generate_recipe_variations(recipe_name, available_ingredients, missing_ingredients)
        
        return JsonResponse(result)
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'variations': [], 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'variations': [],
            'message': f'Error: {str(e)}',
        }, status=500)


@csrf_exempt
@require_POST
def ai_generate_shopping_list(request):
    """Tạo danh sách mua sắm từ Meal Plan.
    
    Request body:
    {
        "date_start": "2026-04-30",  # Optional, default: today
        "date_end": "2026-05-07"      # Optional, default: today + 7 days
    }
    
    Response:
    {
        "success": true,
        "shopping_items": [
            {
                "ingredient_id": 1,
                "ingredient_name": "Trứng",
                "total_quantity": 12,
                "unit": "cái",
                "meals": [
                    {"food_name": "Cơm trứng", "date": "2026-04-30", "quantity": 6}
                ]
            }
        ],
        "meal_plan_count": 15,
        "date_range": {"start": "2026-04-30", "end": "2026-05-07"},
        "message": "Generated shopping list from 15 meal plans"
    }
    """
    try:
        account = get_current_account(request)
        if not account:
            return JsonResponse({
                'success': False,
                'shopping_items': [],
                'message': 'Bạn cần đăng nhập'
            }, status=401)
        
        data = json.loads(request.body) if request.body else {}
        date_start = data.get('date_start')  # YYYY-MM-DD
        date_end = data.get('date_end')
        budget = data.get('budget')
        
        from app.services.grocery_list_service import (
            generate_shopping_list_from_meal_plan,
            calculate_shopping_cost_estimate,
            suggest_shopping_optimization,
        )
        
        result = generate_shopping_list_from_meal_plan(account, date_start, date_end, budget=budget)
        
        if result['success'] and result['shopping_items']:
            # Nếu budget được gửi, đã được tính trong service
            if 'cost_breakdown' not in result:
                cost_result = calculate_shopping_cost_estimate(result['shopping_items'])
                result['estimated_cost'] = cost_result['total_cost']
                result['cost_breakdown'] = cost_result
            
            # Thêm gợi ý tối ưu hóa
            optimization = suggest_shopping_optimization(result['shopping_items'])
            result['optimization'] = optimization
        
        return JsonResponse(result)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'shopping_items': [],
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'shopping_items': [],
            'message': f'Error: {str(e)}',
        }, status=500)


def _resolve_weight_status(bmi_value):
    """Phân loại trạng thái cân nặng dựa trên BMI."""
    if bmi_value is None:
        return 'Chưa xác định'

    bmi_value = float(bmi_value)
    if bmi_value < 18.5:
        return 'Thiếu cân'
    if bmi_value < 23:
        return 'Bình thường'
    if bmi_value < 25:
        return 'Thừa cân'
    return 'Béo phì'


def profile(request):
    """Hiển thị hồ sơ cá nhân của người dùng hiện tại."""
    gate = require_auth(request)
    if gate:
        return gate

    prof = get_profile(get_current_account(request))
    bmi_display = None
    if prof:
        if prof.bmi is not None:
            bmi_display = round(float(prof.bmi), 1)
        elif prof.weight and prof.height:
            try:
                bmi_display = round(float(prof.weight) / ((float(prof.height) / 100) ** 2), 1)
            except ZeroDivisionError:
                bmi_display = None

    return render(request, 'user/profile.html', {
        'profile': prof,
        'profile_bmi_display': bmi_display,
        'profile_weight_status': _resolve_weight_status(bmi_display),
        'active': 'profile',
    })


@csrf_exempt
@require_POST
def profile_save(request):
    """Lưu hoặc cập nhật hồ sơ dinh dưỡng và sức khỏe của người dùng."""
    data = json.loads(request.body)
    account = get_current_account(request)
    prof = get_profile(account)

    height = parse_float(data.get('height'))
    weight = parse_float(data.get('weight'))
    bmi = None
    if height and weight:
        bmi = round(weight / ((height / 100) ** 2), 2)

    fields = {
        'name': (data.get('name') or '').strip(),
        'age': parse_int(data.get('age')),
        'weight': weight,
        'height': height,
        'gender': (data.get('gender') or '').strip() or None,
        'health_goal': (data.get('health_goal') or '').strip() or None,
        'medical_conditions': (data.get('medical_conditions') or '').strip() or None,
        'dietary_preferences': (data.get('dietary_preferences') or '').strip() or None,
        'activity_level': (data.get('activity_level') or '').strip() or None,
        'daily_calorie_target': parse_int(data.get('daily_calorie_target')),
        'bmi': bmi,
    }
    if prof:
        for k, v in fields.items():
            setattr(prof, k, v)
        prof.save()
    else:
        prof = UserProfile.objects.create(account=account, **fields)
    return JsonResponse({'ok': True, 'name': prof.name})


@csrf_exempt
@require_POST
def auth_google(request):
    """Chặn tạm tính năng đăng nhập Google/Gmail và trả thông báo rõ ràng."""
    content_type = (request.META.get('CONTENT_TYPE') or '').lower()
    is_json = 'application/json' in content_type
    message = 'Tam thoi da tat dang nhap/xac thuc bang Google va Gmail.'
    if is_json:
        return JsonResponse({'error': message}, status=503)
    return redirect('login')


@csrf_exempt
@require_POST
def auth_register(request):
    """Đăng ký tài khoản local bằng username/password."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Du lieu khong hop le'}, status=400)

    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return JsonResponse({'error': 'Vui long nhap day du thong tin'}, status=400)
    if len(username) < 3:
        return JsonResponse({'error': 'Ten tai khoan toi thieu 3 ky tu'}, status=400)
    if len(password) < 8:
        return JsonResponse({'error': 'Mat khau toi thieu 8 ky tu'}, status=400)
    if Account.objects.filter(username__iexact=username).exists():
        return JsonResponse({'error': 'Ten tai khoan da ton tai'}, status=400)

    email = f'{username.lower()}.{uuid4().hex[:8]}@local.user'
    account = Account.objects.create(
        username=username,
        email=email,
        password_hash=make_password(password),
        role='user',
    )
    _set_auth_session(request, account.pk, account.username, account.email)
    return JsonResponse({'ok': True, 'username': account.username})


@csrf_exempt
@require_POST
def auth_login(request):
    """Đăng nhập tài khoản local và lưu thông tin vào session."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Du lieu khong hop le'}, status=400)

    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    if not username or not password:
        return JsonResponse({'error': 'Vui long nhap ten tai khoan va mat khau'}, status=400)

    account = Account.objects.filter(
        Q(username__iexact=username) | Q(email__iexact=username),
    ).first()
    if not account:
        return JsonResponse({'error': 'Tai khoan chua ton tai. Hay dang ky truoc.'}, status=404)
    if not account.is_active:
        return JsonResponse({'error': 'Tai khoan da bi khoa hoac chua duoc kich hoat.'}, status=403)
    if not verify_account_password(account, password):
        return JsonResponse({'error': 'Mat khau khong dung'}, status=401)

    role = (account.role or '').strip().lower()
    if role == 'admin':
        return JsonResponse({'error': 'Tai khoan admin vui long dang nhap tai /admin-panel/login/'}, status=403)

    _set_auth_session(request, account.pk, account.username, account.email)
    return JsonResponse({'ok': True, 'username': account.username})


@csrf_exempt
@require_POST
def auth_logout(request):
    """Xóa session hiện tại để đăng xuất người dùng."""
    request.session.flush()
    return JsonResponse({'ok': True})


def auth_me(request):
    """Trả về trạng thái đăng nhập hiện tại từ session."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'logged_in': False})
    return JsonResponse({
        'logged_in': True,
        'name': request.session.get('user_name', ''),
        'email': request.session.get('user_email', ''),
        'avatar': request.session.get('user_avatar', ''),
    })
