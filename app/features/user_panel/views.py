import calendar
import json
import logging
import re
import time
import unicodedata
from datetime import date, timedelta
from typing import Optional
from urllib.parse import urlparse
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
from apps.core_models.models import AIRecommendation, SearchEvent

# Import models từ các app tương ứng (đồng bộ với cấu trúc cơ sở dữ liệu mới)
from apps.users.models import Account, UserProfile, UserPreferenceProfile
from apps.nutrition.models import Food, FoodIngredient, NutritionLog, ShoppingItem, ShoppingList, Recipe, Ingredient
from apps.meal_plans.models import MealPlan
from apps.chat.models import ChatMessage, ChatSession, MessageIntent, ChatResponseCache
from apps.core_models.ai_learning_models import MealRecommendation, UserFeedbackFood, UserFeedbackRecommendation
from apps.users.models import UserFeedback
from app.services.ai_orchestrator_service import AIOrchestratorService
from app.services.ai_quality_service import log_ai_request
from app.services.ai_request_guard_service import (
    analyze_user_request,
    build_response_contract,
    validate_response_against_request,
)
from app.services.chat_text_service import tokenize_chat_text
from app.services.personalization_service import (
    get_personalization_context,
    hybrid_rank_food_candidates,
    log_recommendation_bandit_event,
    persist_recommendation_impressions,
    rank_food_candidates,
    score_food_for_user,
)
from app.services.external_apis import (
    AI_AVAILABLE,
    OLLAMA_READY,
    generate_basic_chat_reply_with_local_llm,
    call_gemini_with_debug as _service_call_gemini_with_debug,
    get_spoonacular_last_error as _get_spoonacular_last_error,
)
from app.services.ingredient_price_service import (
    BUDGET_MEAL_PLAN,
    GENERAL_MEAL_PLAN,
    INGREDIENT_COST_QUERY,
    PRICE_QUERY,
    RECIPE_COST_QUERY,
    classify_food_price_intent,
    handle_multi_ingredient_cost_query,
    handle_recipe_cost_query,
    handle_single_ingredient_price_query,
)
from app.services.meal_plan_generator_service import MealPlanGeneratorService
from app.services.grocery_list_service import generate_shopping_list_from_meal_plan
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


def _normalize_query(text):
    """Chuẩn hóa câu truy vấn để so sánh và tìm kiếm gần đúng."""
    if not text:
        return ''
    normalized = ' '.join(tokenize_chat_text(text))
    return normalized.strip()


def _log_chat_search_event(account, user_text, response_text, clicked_food=None):
    try:
        AIOrchestratorService.log_search_event(
            account,
            user_text,
            result_count=1 if response_text else 0,
            clicked_food=clicked_food,
        )
    except Exception:
        pass


def _log_chat_ai_request(account, chat_session, user_text, intent_name, provider, latency_ms, **kwargs):
    try:
        log_ai_request(
            account=account,
            chat_session=chat_session,
            query_text=user_text,
            normalized_query=_normalize_query(user_text),
            intent_name=intent_name,
            provider=provider,
            latency_ms=latency_ms,
            **kwargs,
        )
    except Exception:
        pass


def _log_rejected_ai_response(account, chat_session, user_text, intent_name, provider, issues, metadata=None):
    try:
        log_ai_request(
            account=account,
            chat_session=chat_session,
            query_text=user_text,
            normalized_query=_normalize_query(user_text),
            intent_name=intent_name,
            provider=provider,
            route_path='rejected',
            decision='request_guard_rejected',
            latency_ms=0,
            response_ok=False,
            metadata={
                'issues': list(issues or []),
                **(metadata or {}),
            },
        )
    except Exception:
        pass


def _make_tool_use_system_instruction(request_analysis):
    guard = request_analysis or {}
    topic = guard.get('topic_name') or guard.get('topic') or 'general'
    rules = [
        'Tra loi dung chủ đề hiện tại, không lan man sang chủ đề khác.',
        'Nếu cần tra cứu dữ liệu, hãy gọi công cụ phù hợp.',
        'Không hiển thị confidence, query_sim hay các chỉ số kỹ thuật.',
    ]
    return 'Chủ đề: ' + str(topic) + '. ' + ' '.join(rules)


def _log_llm_tool_use_event(account, chat_session, user_text, intent_name, response_text):
    try:
        log_ai_request(
            account=account,
            chat_session=chat_session,
            query_text=user_text,
            normalized_query=_normalize_query(user_text),
            intent_name=intent_name,
            provider='llm_tool_use',
            route_path='llm_tool_use',
            decision='llm_autonomous',
            latency_ms=0,
            response_ok=True,
            metadata={'tool_system': 'gemini_function_calling'},
        )
    except Exception:
        pass


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


def _is_greeting_message(user_text):
    text = (user_text or '').strip().lower()
    if not text:
        return False
    greeting_phrases = {
        'chao', 'chào', 'hello', 'hi', 'hey', 'alo', 'xin chao', 'xin chào',
        'chao ban', 'chào bạn', 'ad oi', 'ad ơi', 'bot oi', 'bot ơi',
    }
    return text in greeting_phrases


def _build_greeting_response():
    return (
        'Xin chào! Mình là trợ lý Nội Trợ AI. '
        'Mình có thể giúp bạn gợi ý món ăn, tư vấn dinh dưỡng hoặc lên thực đơn. '
        'Bạn muốn mình hỗ trợ gì?'
    )


def _is_greeting_message_safe(user_text):
    text = (user_text or '').strip().lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    if not text:
        return False
    return text in {
        'chao', 'xin chao', 'chao ban', 'hello', 'hi', 'hey', 'alo', 'ad oi', 'bot oi',
    }


def _append_health_feedback(response_text, account, user_text):
    if not response_text:
        return ""
    return response_text


def _clean_reasons_for_display(reasons):
    clean_reasons = []
    for reason in reasons or []:
        if not reason:
            continue
        reason_text = str(reason)
        if 'query_sim' in reason_text or 'score' in reason_text or 'sim=' in reason_text:
            continue
        clean_reasons.append(reason_text)
    return clean_reasons


def _format_local_candidates_response(candidates):
    lines = []
    for item in candidates[:5]:
        food = item.get('food')
        if not food:
            continue
        name = getattr(food, 'name', 'Món ăn')
        reasons = item.get('reasons') or []
        # Việt hóa lý do và loại bỏ thông tin kỹ thuật
        clean_reasons = _clean_reasons_for_display(reasons)
        
        reason_text = f' (phù hợp vì: {", ".join(clean_reasons)})' if clean_reasons else ''
        lines.append(f'- {name}{reason_text}')

    if not lines:
        return ''

    return (
        'Mình đã tìm thấy một số món ăn phù hợp với yêu cầu của bạn: \n'
        + '\n'.join(lines)
        + '\nBạn có muốn mình hướng dẫn chi tiết cách nấu món nào không?'
    )


def _retrieve_rag_evidence(account, user_text, local_candidates=None):
    evidence = {
        'foods': local_candidates or [],
        'recipes': [],
        'ingredients': [],
    }
    query = (user_text or '').strip()
    normalized_query = _normalize_query(query)
    if not normalized_query:
        return evidence

    try:
        recipes = Recipe.objects.filter(
            Q(title__icontains=normalized_query)
            | Q(summary__icontains=normalized_query)
            | Q(instructions__icontains=normalized_query)
        ).order_by('-created_at')[:3]
        for recipe in recipes:
            evidence['recipes'].append({
                'title': getattr(recipe, 'title', ''),
                'summary': getattr(recipe, 'summary', ''),
            })
    except Exception:
        pass

    try:
        ingredients = Ingredient.objects.filter(name__icontains=normalized_query).order_by('name')[:3]
        evidence['ingredients'] = [getattr(ingredient, 'name', '') for ingredient in ingredients if getattr(ingredient, 'name', None)]
    except Exception:
        pass

    if not evidence['foods']:
        try:
            foods = Food.objects.filter(
                Q(name__icontains=normalized_query)
                | Q(category__name__icontains=normalized_query)
                | Q(category_name__icontains=normalized_query)
            ).order_by('name')[:5]
            evidence['foods'] = [
                {'food': food, 'score': 0.0, 'reasons': ['match query']}
                for food in foods
            ]
        except Exception:
            pass

    return evidence


def _build_gemini_system_context(account, user_text, intent_name=None, local_candidates=None, rag_evidence=None):
    system_context = (
        'Bạn là "Nội Trợ AI", trợ lý ẩm thực thông minh dành cho người Việt. '
        'Hãy trả lời bằng tiếng Việt, thân thiện, ngắn gọn và hữu ích. '
        'Ưu tiên gợi ý món ăn lành mạnh, phù hợp theo sở thích, mục tiêu sức khỏe, ngân sách và bệnh lý người dùng.\n'
        'QUY TẮC QUAN TRỌNG:\n'
        '1. Luôn trả lời đúng trọng tâm câu hỏi và yêu cầu của người dùng.\n'
        '2. KHÔNG bao giờ hiển thị các thông số kỹ thuật như "query_sim", "score", "confidence" trong câu trả lời.\n'
        '3. Nếu người dùng muốn lên thực đơn, hãy giải thích các món được chọn dựa trên hồ sơ của họ.\n'
        '4. Luôn giữ thái độ lịch sự, chuyên nghiệp của một đầu bếp và chuyên gia dinh dưỡng.\n'
    )

    if intent_name:
        system_context += f'Mục đích người dùng: {intent_name}.\n'

    profile_text = _build_personalization_context_text(account)
    if profile_text:
        system_context += f'Thông tin người dùng: {profile_text}.\n'

    evidence = rag_evidence or {}
    foods = evidence.get('foods') or local_candidates or []
    recipes = evidence.get('recipes') or []
    ingredients = evidence.get('ingredients') or []

    if foods:
        candidate_lines = []
        for item in foods[:5]:
            food = item.get('food') if isinstance(item, dict) else item
            if not food:
                continue
            name = getattr(food, 'name', 'Món ăn')
            # Loại bỏ score và các lý do kỹ thuật khỏi system context để AI không bắt chước
            reasons = item.get('reasons') or [] if isinstance(item, dict) else []
            clean_reasons = _clean_reasons_for_display(reasons)
            reason_text = f' ({", ".join(clean_reasons)})' if clean_reasons else ''
            candidate_lines.append(f'* {name}{reason_text}')
        system_context += (
            'Dưới đây là các gợi ý từ cơ sở dữ liệu: \n'
            + '\n'.join(candidate_lines)
            + '\n'
        )

    if recipes:
        recipe_lines = [f'* {recipe.get("title", "")}: {recipe.get("summary", "")}'.strip() for recipe in recipes]
        system_context += (
            'Các công thức liên quan từ dữ liệu nội bộ: \n'
            + '\n'.join(recipe_lines)
            + '\n'
        )

    if ingredients:
        system_context += (
            'Các nguyên liệu liên quan từ dữ liệu nội bộ: \n'
            + '\n'.join(f'* {name}' for name in ingredients)
            + '\n'
        )

    system_context += (
        'Sử dụng các thông tin nội bộ trên làm bằng chứng khi cố gắng trả lời. '
        'Hãy trả về phương án tốt nhất dựa trên dữ liệu và bối cảnh hiện có. '
        'Nếu thiếu thông tin, hãy đưa ra lựa chọn hợp lý nhất thay vì hỏi thêm người dùng.\n'
    )

    system_context += f'Người dùng hỏi: "{user_text}"\n'
    return system_context


def _build_personalization_context_text(account):
    context = get_personalization_context(account)
    profile = context.get('profile')
    preference_profile = context.get('preference_profile')
    diseases = context.get('diseases') or []

    if not profile:
        return ''

    parts = []
    if getattr(profile, 'name', None):
        parts.append(f'Người dùng {profile.name}')
    if getattr(profile, 'age', None):
        parts.append(f'{profile.age} tuổi')
    if getattr(profile, 'gender', None):
        parts.append(f'giới tính {profile.gender}')
    if getattr(profile, 'weight', None):
        parts.append(f'{profile.weight}kg')
    if getattr(profile, 'height', None):
        parts.append(f'{profile.height}cm')
    if getattr(profile, 'health_goal', None):
        parts.append(f'Mục tiêu: {profile.health_goal}')
    if getattr(profile, 'medical_conditions', None):
        parts.append(f'Bệnh lý: {profile.medical_conditions}')
    if getattr(profile, 'dietary_preferences', None):
        parts.append(f'Sở thích ăn: {profile.dietary_preferences}')
    if getattr(profile, 'budget_limit', None):
        parts.append(f'Ngân sách: {profile.budget_limit}')
    if preference_profile and getattr(preference_profile, 'preferred_categories', None):
        parts.append(f'Danh mục ưa thích: {preference_profile.preferred_categories}')
    if preference_profile and getattr(preference_profile, 'avoided_keywords', None):
        parts.append(f'Từ khóa tránh: {preference_profile.avoided_keywords}')
    if diseases:
        disease_names = ', '.join([str(getattr(item.disease, 'name', '') or '').strip() for item in diseases if getattr(item, 'disease', None)])
        if disease_names:
            parts.append(f'Bệnh lý đã ghi: {disease_names}')

    return ' '.join(parts).strip()


def _append_personalization_to_system_context(system_context, account):
    personalization_text = _build_personalization_context_text(account)
    if personalization_text:
        return f"{system_context}\nThông tin cá nhân: {personalization_text}"
    return system_context


def _make_chat_response_system_context(system_context, user_text):
    """Add a hard constraint so the model answers the latest user request only."""
    return (
        f"{system_context}\n"
        "RANG BUOC BO SUNG:\n"
        f'- Cau hoi hien tai cua nguoi dung: "{user_text}"\n'
        "- Uu tien tuyet doi cau hoi hien tai, khong dua phan hoi dua tren chu de cu trong lich su.\n"
        "- Neu cau hoi hien tai khong lien quan am thuc/dinh duong/thuc don/nguyen lieu, tra loi dung chu de do.\n"
        "- Khong lan man, khong chuyen chu de.\n"
    )


def _response_matches_current_request(account, chat_session, user_text, response_text, intent_name, provider, analysis=None):
    guard_result = validate_response_against_request(
        user_text,
        response_text,
        analysis=analysis,
        intent_name=intent_name,
    )
    if guard_result.get('ok'):
        return True

    _log_rejected_ai_response(
        account,
        chat_session,
        user_text,
        intent_name,
        provider,
        guard_result.get('issues') or [],
        metadata={'request_analysis': guard_result.get('analysis') or {}},
    )
    return False


def _cache_intent_matches(requested_intent, cached_intent):
    requested = (requested_intent or '').strip().lower()
    cached = (cached_intent or '').strip().lower()
    return not requested or not cached or requested == cached


def _get_food_recommendations_response(account, user_text):
    foods = list(Food.objects.all().order_by('name')[:100])
    if not foods:
        return 'Mình chưa tìm thấy dữ liệu món ăn để gợi ý lúc này.'

    ranked_foods = hybrid_rank_food_candidates(account, foods, limit=5, user_query=user_text)
    ranked_foods = persist_recommendation_impressions(
        account,
        ranked_foods,
        user_query=user_text,
        source='user_panel',
    )
    if not ranked_foods:
        return 'Mình chưa thể gợi ý món ăn lúc này.'

    lines = []
    for item in ranked_foods[:3]:
        food = item['food']
        try:
            log_recommendation_bandit_event(
                account,
                food,
                event_type='recommendation_shown',
                score=float(item.get('score', 0.0)),
                metadata={'source': 'user_panel', 'components': item.get('components', {})},
            )
        except Exception:
            pass
        name = getattr(food, 'name', 'Món ăn')
        reasons = item.get('reasons') or []
        # Lọc bỏ thông tin kỹ thuật
        clean_reasons = _clean_reasons_for_display(reasons)
        reason_text = '; '.join(clean_reasons) if clean_reasons else ''
        lines.append(f'- {name}' + (f' ({reason_text})' if reason_text else ''))

    return (
        'Dưới đây là một số món ăn mình gợi ý cho bạn:\n' + '\n'.join(lines) +
        '\nNếu bạn có yêu cầu cụ thể hơn như giảm cân, tăng cơ hay theo ngân sách, hãy cho mình biết nhé!'
    )


def _get_nutrition_summary_response(account):
    if not account:
        return 'Bạn cần đăng nhập để mình có thể xem và tóm tắt thông tin dinh dưỡng cá nhân.'

    today_str = date.today().isoformat()
    logs = NutritionLog.objects.filter(account=account, date=today_str).select_related('food')
    if not logs.exists():
        return (
            'Hôm nay bạn chưa ghi nhật ký dinh dưỡng nào. Hãy thêm món ăn bạn đã ăn để mình tóm tắt chi tiết nhé. '
            'Hoặc nếu bạn muốn, mình có thể giúp bạn lập một thực đơn mới phù hợp với mục tiêu sức khỏe của bạn!'
        )

    total_calories = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0

    for log in logs:
        servings = float(log.servings or 0)
        food = log.food
        total_calories += float(getattr(food, 'calories', 0) or 0) * servings
        total_protein += float(getattr(food, 'protein', 0) or 0) * servings
        total_carbs += float(getattr(food, 'carbs', 0) or 0) * servings
        total_fat += float(getattr(food, 'fat', 0) or 0) * servings

    profile_obj = get_profile(account)
    targets = _resolve_nutrition_targets(profile_obj)
    calorie_status = 'đạt' if total_calories <= targets['calorie'] else 'vượt'

    return (
        f'Hôm nay bạn đã nạp {round(total_calories,1)} kcal, {round(total_protein,1)}g protein, '
        f'{round(total_carbs,1)}g carbs và {round(total_fat,1)}g fat. '
        f'Mục tiêu kcal của bạn là {targets["calorie"]} kcal, hiện tại bạn {calorie_status} mục tiêu.'
    )



def _extract_dish_name_from_query(text):
    """Trich xuat ten mon an tu cau hoi cua nguoi dung."""
    if not text:
        return ''
    try:
        from app.services.intent_classifier import extract_dish_name
        dish = extract_dish_name(text)
        if dish:
            return dish
    except Exception:
        pass
    cleaned = str(text).lower()
    for word in [
        'công thức', 'cong thuc', 'cách làm', 'cach lam', 'hướng dẫn', 'huong dan',
        'cho tôi biết', 'cho toi biet', 'chỉ tôi', 'chi toi',
        'làm thế nào', 'lam the nao', 'nấu như thế nào', 'nau nhu the nao',
        'chế biến', 'che bien', 'làm món', 'lam mon', 'nấu món', 'nau mon',
        'recipe', 'của', 'cua', 'món', 'mon',
    ]:
        cleaned = cleaned.replace(word, '')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ?!.,:;-')
    return cleaned.strip()


def _looks_like_recipe_request(user_text):
    text = (user_text or '').strip().lower()
    if not text:
        return False
    normalized = unicodedata.normalize('NFKD', text)
    normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    keywords = [
        'cong thuc', 'cach lam', 'huong dan', 'recipe', 'nau mon', 'lam mon', 'che bien',
    ]
    return any(keyword in normalized for keyword in keywords)



def _get_recipe_response(user_text, account):
    query = (user_text or '').strip()
    if not query:
        return None

    dish_name = _extract_dish_name_from_query(user_text) or query
    if not dish_name:
        dish_name = query

    recipes = Recipe.objects.select_related('food').filter(
        Q(title__icontains=dish_name)
        | Q(food__name__icontains=dish_name)
        | Q(summary__icontains=dish_name)
        | Q(instructions__icontains=dish_name)
    ).order_by('-created_at')[:3]

    if recipes:
        primary = recipes[0]
        food = getattr(primary, 'food', None)
        dish_title = (getattr(primary, 'title', None) or getattr(food, 'name', None) or dish_name).strip()
        ingredients = _extract_recipe_ingredients(primary, food)[:10] if food else []
        steps = _extract_instruction_steps(primary)[:6]

        lines = [f'Cong thuc {dish_title}:']
        if ingredients:
            lines.append('Nguyen lieu:')
            lines.extend([f'- {item}' for item in ingredients])
        else:
            lines.append('Nguyen lieu: hien chua co danh sach chi tiet trong du lieu.')

        if steps:
            lines.append('Cach lam:')
            lines.extend([f'{idx}. {step}' for idx, step in enumerate(steps, 1)])
        else:
            lines.append('Cach lam: hien chua co huong dan tung buoc trong du lieu.')

        other_recipes = [r.title for r in recipes[1:] if getattr(r, 'title', None)]
        if other_recipes:
            lines.append('Ban co the tham khao them: ' + ', '.join(other_recipes[:2]))

        return '\n'.join(lines)
    return None



def _get_shopping_list_response(account):
    if not account or getattr(account, 'role', '').lower() == 'guest':
        return 'Bạn cần đăng nhập để mình có thể tạo danh sách mua sắm từ thực đơn của bạn.'

    result = generate_shopping_list_from_meal_plan(
        account,
        date_start=date.today(),
        date_end=date.today() + timedelta(days=6),
    )

    if not result.get('shopping_items'):
        return (
            'Mình chưa tìm thấy thực đơn phù hợp trong 7 ngày tới để tạo danh sách mua sắm. '
            'Bạn có thể hỏi mình tạo thực đơn trước nhé.'
        )

    lines = []
    for item in result['shopping_items'][:5]:
        lines.append(f"- {item['ingredient_name']}: {item['total_quantity']} {item['unit']}")

    return (
        f'Mình đã tạo danh sách mua sắm từ {result.get("meal_plan_count", 0)} thực đơn:\n'
        + '\n'.join(lines)
        + '\nBạn có thể mở trang danh sách mua để xem chi tiết.'
    )


def _get_ingredient_lookup_response(user_text, account):
    query = (user_text or '').strip()
    if not query:
        return None

    ingredient = Ingredient.objects.filter(name__icontains=query).order_by('name').first()
    if ingredient:
        return f'Nguyên liệu {ingredient.name}: đây là thông tin sẵn có trong hệ thống.'

    food = Food.objects.filter(name__icontains=query).order_by('name').first()
    if food:
        calories = getattr(food, 'calories', 0) or 0
        protein = getattr(food, 'protein', 0) or 0
        carbs = getattr(food, 'carbs', 0) or 0
        fat = getattr(food, 'fat', 0) or 0
        return (
            f'Thông tin {food.name}: {calories} kcal, {protein}g protein, {carbs}g carbs, {fat}g fat. '
            'Nếu bạn muốn, mình có thể gợi ý món ăn hoặc công thức phù hợp với nguyên liệu này.'
        )

    return None


def _route_chat_intent(intent, user_text, account, chat_session):
    if _looks_like_recipe_request(user_text):
        recipe_text = _get_recipe_response(user_text, account)
        if recipe_text:
            return {'response': recipe_text}
        return {
            'response': (
                'Mình hiểu bạn đang hỏi công thức, nhưng mình chưa tìm thấy món khớp trong dữ liệu hiện có. '
                'Bạn có thể ghi rõ tên món, ví dụ: "công thức mì ý sốt bò bằm".'
            )
        }

    if not intent:
        return None
    intent_name = (getattr(intent, 'name', '') or '').lower().strip()
    if not intent_name:
        return None

    if intent_name == 'greeting':
        return {'response': 'Xin chào! Mình là trợ lý Nội Trợ AI. Mình có thể giúp bạn gợi ý món ăn, xem dinh dưỡng hoặc lập thực đơn hàng ngày. Bạn cần mình giúp gì không?'}
    if intent_name == 'meal_plan':
        return _auto_create_meal_plan_from_chat(user_text, account, force=True)
    if intent_name == 'recommendation':
        return {'response': _get_food_recommendations_response(account, user_text)}
    if intent_name == 'nutrition':
        # Chỉ trả về tóm tắt nếu có từ khóa tóm tắt hoặc nhật ký
        nutrition_keywords = ['tóm tắt', 'tom tat', 'nhật ký', 'nhat ky', 'đã ăn', 'da an', 'thống kê', 'thong ke']
        if any(kw in user_text.lower() for kw in nutrition_keywords):
            return {'response': _get_nutrition_summary_response(account)}
        # Nếu không, hãy để AI trả lời (nutrition lookup)
        return None
    if intent_name == 'recipe':
        recipe_text = _get_recipe_response(user_text, account)
        if recipe_text:
            return {'response': recipe_text}
    if intent_name == 'shopping':
        return {'response': _get_shopping_list_response(account)}
    if intent_name == 'ingredient':
        ingredient_text = _get_ingredient_lookup_response(user_text, account)
        if ingredient_text:
            return {'response': ingredient_text}

    return None


def _call_gemini_with_debug(account, chat_session, system_context, user_text=''):
    system_context = _append_personalization_to_system_context(system_context, account)
    system_context = _make_chat_response_system_context(system_context, user_text)
    return _service_call_gemini_with_debug(chat_session, system_context)


def _filter_and_rank_foods_by_personalization(account, foods, limit=3, user_text: Optional[str] = None):
    """
    Filter & rank foods based on user personalization profile.
    
    CẢI THIỆN:
    - Tránh recommend foods trong avoided_keywords
    - Score foods theo user preferences (calories, categories, budget, vv)
    - Rank theo personalization scores
    """
    if not foods or not account:
        return []
    
    try:
        # Rank foods dùng personalization service (pass current user query for dynamic boosts)
        ranked = rank_food_candidates(account, foods, limit=limit, user_query=user_text)
        
        # Filter out foods có scores quá thấp (< 0.35 = không phù hợp)
        filtered = [item for item in ranked if item['score'] >= 0.35]
        
        return filtered if filtered else ranked[:limit]
    except Exception:
        # Fallback: trả về foods original nếu personalization fail
        return [{'food': food, 'score': 0.5, 'reasons': []} for food in foods[:limit]]


def _search_keyword_hardcoded(user_text, account):
    """
    Search foods từ query, với personalization filtering.
    
    CẢI THIỆN:
    - Dùng personalization để filter & rank foods
    - Tránh recommend avoided foods
    - Show ranking reasons
    """
    query = (user_text or '').strip()
    if not query:
        return None

    normalized_query = _normalize_query(query)
    if not normalized_query:
        return None

    # Search foods từ DB
    foods = Food.objects.filter(
        Q(name__iexact=query)
        | Q(name__iexact=normalized_query)
        | Q(name__icontains=normalized_query)
        | Q(category__name__iexact=normalized_query)
        | Q(category__name__icontains=normalized_query)
    ).order_by('name')[:10]  # Lấy top 10 để filter

    if not foods:
        # Fallback: semantic search over names and categories
        from app.services.personalization_service import semantic_search_with_scores
        scored = semantic_search_with_scores(query)
        foods = [item['food'] for item in scored][:10]

    if not foods:
        return None
    
    # CẢI THIỆN: Filter & rank foods theo personalization
    ranked_foods = _filter_and_rank_foods_by_personalization(account, foods, limit=3, user_text=query)
    
    if not ranked_foods:
        return None
    
    # Trả về top-ranked food
    top_food = ranked_foods[0]['food']
    # Lọc bỏ thông tin kỹ thuật từ lý do
    clean_reasons = [r for r in ranked_foods[0]['reasons'] if 'query_sim' not in r and 'score' not in r]
    reasons_text = ', '.join(clean_reasons) if clean_reasons else ''
    
    if reasons_text:
        return f'Mình đã tìm thấy món {top_food.name} rất phù hợp với bạn vì: {reasons_text}.'
    else:
        return f'Mình tìm thấy món {top_food.name} khá phù hợp với yêu cầu của bạn.'


def _search_db_for_query(user_text, account):
    return _search_keyword_hardcoded(user_text, account)


def _find_saved_chat_answer(user_text, source_intent=None, request_analysis=None):
    if not user_text:
        return None

    if request_analysis and request_analysis.skip_cache:
        return None

    try:
        from app.services.external_apis import get_or_create_chat_response_from_cache
        from app.services.similarity_service import compute_smart_similarity

        # 1. Ưu tiên sử dụng cache service với thuật toán similarity thông minh
        cache_result = get_or_create_chat_response_from_cache(
            None,
            user_text,
            source_intent=source_intent,
        )
        if cache_result and _cache_intent_matches(source_intent, cache_result.get('intent_name')):
            return cache_result

        # 2. Fallback: Duyệt trực tiếp qua các cache gần đây nếu cache service không tìm thấy (đề phòng)
        recent_caches = ChatResponseCache.objects.all().order_by('-created_at')[:50]
        best_cached = None
        max_sim = 0.0

        for cached in recent_caches:
            sim = compute_smart_similarity(
                user_text, 
                cached.original_query, 
                source_intent_a=source_intent, 
                source_intent_b=cached.intent_name
            )
            if sim > max_sim:
                max_sim = sim
                best_cached = cached
        
        if best_cached and max_sim >= 0.90 and _cache_intent_matches(source_intent, best_cached.intent_name):
            response_text = (best_cached.response or '').strip()
            if not _is_invalid_chat_response(response_text):
                return {
                    'response': response_text,
                    'intent_name': best_cached.intent_name,
                    'similarity': max_sim
                }
    except Exception:
        pass

    return None


def _is_invalid_chat_response(response_text):
    text = (response_text or '').strip()
    if not text:
        return True
    invalid_markers = (
        'Loi AI [',
        'RESOURCE_EXHAUSTED',
        'He thong tam thoi gap loi',
        'Khong co phan hoi tu AI',
        'AI tam thoi gap loi',
        'AI tạm thời gặp lỗi',
        'AI hien tai khong tra ve noi dung',
        'AI hiện tại không trả về nội dung',
        'Xin lỗi, tôi gặp sự cố khi kết nối AI',
        'Dịch vụ AI đang bị giới hạn tần suất',
    )
    return any(marker in text for marker in invalid_markers)


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
    """Tạo phản hồi dự phòng từ dữ liệu nội bộ khi AI không trả lời được."""
    recommendations = []
    if account:
        recommendations = list(
            AIRecommendation.objects.filter(account=account)
            .select_related('food')
            .order_by('-score', '-created_at')[:5]
        )

    if recommendations:
        lines = []
        for item in recommendations:
            food_name = getattr(getattr(item, 'food', None), 'name', '') or 'Món gợi ý'
            reason = (item.reason or '').strip()
            if reason:
                lines.append(f"- {food_name}: {reason}")
            else:
                lines.append(f"- {food_name}")
        return (
            'Mình chưa trả lời bằng AI ngay lúc này, nhưng đây là gợi ý từ dữ liệu nội bộ phù hợp hơn:\n'
            f"{chr(10).join(lines)}\n"
            'Nếu bạn muốn, hãy nhắn rõ mục tiêu như "giảm cân", "tăng cơ" hoặc "ăn nhẹ buổi tối" để mình lọc kỹ hơn.'
        )

    foods = list(Food.objects.all().order_by('name')[:5])
    if not foods:
        return (
            'Mình chưa trả lời được ngay lúc này. '
            'Bạn có thể thử lại sau ít phút hoặc nhập tên món cụ thể để mình tra cứu từ CSDL nội bộ.'
        )

    food_lines = '\n'.join(f"- {food.name}" for food in foods)
    return (
        'Mình chưa trả lời bằng AI ngay lúc này, nên chuyển sang dữ liệu nội bộ.\n'
        'Bạn có thể chọn nhanh một trong các món sau:\n'
        f'{food_lines}\n'
        'Hãy nhắn tên món bạn muốn hoặc nêu mục tiêu như giảm cân, tăng cơ, ăn nhẹ để mình gợi ý sát hơn.'
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


def _auto_create_meal_plan_from_chat(user_text, account, force=False):
    """Tự tạo thực đơn từ chat khi intent đã được phân loại là meal_plan."""
    if not force:
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


def _format_meal_plan_result_for_chat(result):
    budget_context = result.get('budget_context') or {}
    shopping_summary = result.get('shopping_summary') or {}
    total_cost = result.get('total_estimated_cost')
    budget_remaining = result.get('budget_remaining')
    request_type = result.get('request_type')

    lines = []
    if request_type == 'budget' and budget_context.get('has_budget'):
        total_budget = budget_context.get('total_budget')
        daily_budget = budget_context.get('daily_budget')
        lines.append(f'Mình đã tạo thực đơn theo ngân sách cho {result.get("plan_days", 1)} ngày.')
        if total_budget is not None:
            lines.append(f'Ngân sách tổng: {float(total_budget):,.0f}đ.')
        if daily_budget is not None:
            lines.append(f'Ngân sách trung bình mỗi ngày: {float(daily_budget):,.0f}đ.')
    else:
        lines.append(f'Mình đã tạo thực đơn cho {result.get("plan_days", 1)} ngày dựa trên hồ sơ và mục tiêu sức khỏe của bạn.')

    if total_cost is not None:
        lines.append(f'Tổng chi phí dự kiến từ database nguyên liệu: {float(total_cost):,.0f}đ.')
    if budget_remaining is not None:
        if budget_remaining >= 0:
            lines.append(f'Ngân sách còn lại: {float(budget_remaining):,.0f}đ.')
        else:
            lines.append(f'Đang vượt ngân sách khoảng {abs(float(budget_remaining)):,.0f}đ.')

    shopping_items = shopping_summary.get('shopping_items') or []
    if shopping_items:
        lines.append('Một số nguyên liệu chính cần mua:')
        for item in shopping_items[:5]:
            lines.append(f"- {item['ingredient_name']}: {item['total_quantity']} {item['unit']}")

    notes = result.get('budget_filter_notes') or []
    if notes:
        lines.append('Lưu ý dữ liệu:')
        for note in notes[:3]:
            lines.append(f'- {note}')

    lines.append('Thực đơn đã được lưu tại trang Thực đơn: /thuc-don/.')
    return '\n'.join(lines)


def _handle_database_first_chat_query(account, user_text):
    try:
        intent_name = classify_food_price_intent(user_text, account=account)

        if intent_name == PRICE_QUERY:
            return handle_single_ingredient_price_query(user_text)

        if intent_name == INGREDIENT_COST_QUERY:
            return handle_multi_ingredient_cost_query(user_text)

        if intent_name == RECIPE_COST_QUERY:
            return handle_recipe_cost_query(user_text)

        if intent_name in {BUDGET_MEAL_PLAN, GENERAL_MEAL_PLAN}:
            role = (getattr(account, 'role', '') or '').strip().lower()
            if not account or role == 'guest':
                try:
                    from app.services.external_apis import generate_basic_chat_reply_with_local_llm, OLLAMA_READY
                    if OLLAMA_READY:
                        ai_response = generate_basic_chat_reply_with_local_llm(
                            user_text,
                            context_text='Ban la chuyen gia am thuc. Nguoi dung khach muon tao thuc don. Hay goi y thuc don chi tiet bang tieng Viet voi cac mon an cu the.',
                            max_output_tokens=1024,
                        )
                        if ai_response:
                            return {'success': True, 'intent': intent_name, 'response': ai_response}
                except Exception:
                    pass
                return {'success': False, 'intent': intent_name, 'response': 'Ban can dang nhap de luu thuc don. Minh co the goi y mon an!'}
            result = MealPlanGeneratorService.generate_meal_plan(
                account=account,
                request_text=user_text,
                target_date=_resolve_plan_start_date(user_text),
            )
            if not result.get('success'):
                return {
                    'success': False,
                    'intent': intent_name,
                    'response': result.get('message') or 'Không thể tạo thực đơn lúc này.',
                    'meal_plan_created': False,
                }

            plan_dates = result.get('plan_dates') or []
            meal_plan_url = '/thuc-don/'
            if plan_dates:
                try:
                    first_plan_date = date.fromisoformat(str(plan_dates[0]))
                    meal_plan_url = f'/thuc-don/?year={first_plan_date.year}&month={first_plan_date.month}'
                except Exception:
                    pass

            return {
                'success': True,
                'intent': intent_name,
                'response': _format_meal_plan_result_for_chat(result),
                'meal_plan_created': True,
                'meal_plan_url': meal_plan_url,
            }

    except Exception:
        logger.exception('database_first_chat_query failed')
        normalized_text = (user_text or '').lower()
        if any(keyword in normalized_text for keyword in ['gia', 'chi phi', 'bao nhieu', 'price', 'cost']):
            return {
                'success': False,
                'intent': PRICE_QUERY,
                'response': 'Du lieu gia trong he thong hien chua san sang day du de tra loi chinh xac cau hoi nay.',
            }
    return None


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

    # CẢI THIỆN: Rank foods theo personalization thay vì random
    import random
    all_foods = list(Food.objects.all())
    
    if all_foods and account:
        try:
            # Rank foods dùng personalization service
            ranked_foods = rank_food_candidates(account, all_foods, limit=20)
            # Filter foods có score >= 0.35 (phù hợp)
            good_foods = [item['food'] for item in ranked_foods if item['score'] >= 0.35]
            food_recommendations = good_foods[:4] if good_foods else [item['food'] for item in ranked_foods[:4]]
        except Exception:
            # Fallback: random recommendation nếu personalization fail
            food_recommendations = random.sample(all_foods, min(4, len(all_foods)))
    else:
        # Fallback: random recommendation nếu không có account
        food_recommendations = random.sample(all_foods, min(4, len(all_foods))) if all_foods else []

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
    response_text = None
    started_at = time.perf_counter()
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

        if _is_greeting_message_safe(user_text):
            response_text = _build_greeting_response()
            msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
            _log_chat_search_event(account, user_text, response_text)
            _log_chat_ai_request(
                account,
                chat_session,
                user_text,
                'greeting',
                'local_rule',
                int((time.perf_counter() - started_at) * 1000),
                route_path='local',
                decision='greeting_fast_path',
                response_ok=True,
            )
            return JsonResponse({'role': msg.role, 'content': msg.content})

        db_first_response = _handle_database_first_chat_query(account, user_text)
        if db_first_response and db_first_response.get('response'):
            response_text = _append_health_feedback(db_first_response['response'], account, user_text)
            msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
            _log_chat_search_event(account, user_text, response_text)
            _log_chat_ai_request(
                account,
                chat_session,
                user_text,
                db_first_response.get('intent', ''),
                'database',
                int((time.perf_counter() - started_at) * 1000),
                route_path='database_first',
                decision='database_first_flow',
                response_ok=bool(db_first_response.get('success')),
                metadata={'meal_plan_created': bool(db_first_response.get('meal_plan_created'))},
            )
            payload = {'role': msg.role, 'content': msg.content}
            if db_first_response.get('meal_plan_created'):
                payload['meal_plan_created'] = True
                payload['meal_plan_url'] = db_first_response.get('meal_plan_url', '/thuc-don/')
            return JsonResponse(payload)

        if AI_AVAILABLE and OLLAMA_READY:
            try:
                from app.services.llm_tool_orchestrator import call_llm_with_tools_qwen
                from app.services.tool_registry import get_tools_schema

                tools = get_tools_schema()
                llm_response = call_llm_with_tools_qwen(
                    chat_session,
                    user_text,
                    tools,
                    system_instruction=_make_tool_use_system_instruction(request_analysis),
                )
                if llm_response:
                    response_text = str(getattr(llm_response, 'content', llm_response)).strip()
                    if (
                        response_text
                        and not _is_invalid_chat_response(response_text)
                        and _response_matches_current_request(
                            account,
                            chat_session,
                            user_text,
                            response_text,
                            intent_name,
                            'llm_tool_use',
                            analysis=request_analysis,
                        )
                    ):
                        response_text = _append_health_feedback(response_text, account, user_text)
                        msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
                        _log_chat_search_event(account, user_text, response_text)
                        _log_llm_tool_use_event(account, chat_session, user_text, intent_name, response_text)
                        return JsonResponse({
                            'role': msg.role,
                            'content': msg.content,
                            'orchestrator_path': 'llm_tool_use',
                        })
            except Exception:
                logger.exception('llm_tool_use path failed')

        intent, confidence = classify_intent(user_text)
        intent_name = getattr(intent, 'name', None) if intent else ''
        request_analysis = analyze_user_request(user_text, intent_name=intent_name)
        if intent:
            MessageIntent.objects.create(message=user_msg, intent=intent, confidence=confidence)
        if chat_session:
            chat_session.current_intent_id = getattr(intent, 'id', None) if intent else None
            chat_session.save(update_fields=['current_intent_id', 'updated_at'])

        # 1. Xử lý theo ý định (Meal Plan, Greeting, ...)
        intent_response = _route_chat_intent(intent, user_text, account, chat_session)
        if intent_response:
            response_text = intent_response.get('response', intent_response.get('message', ''))
            if response_text and _response_matches_current_request(
                account,
                chat_session,
                user_text,
                response_text,
                intent_name,
                'local_rule',
                analysis=request_analysis,
            ):
                response_text = _append_health_feedback(response_text, account, user_text)
                msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
                _log_chat_search_event(account, user_text, response_text)
                _log_chat_ai_request(
                    account,
                    chat_session,
                    user_text,
                    intent_name,
                    'local_rule',
                    int((time.perf_counter() - started_at) * 1000),
                    route_path='local',
                    decision='intent_route',
                    response_ok=True,
                    metadata={'meal_plan_created': bool(intent_response.get('meal_plan_created'))},
                )
                payload = {'role': msg.role, 'content': msg.content}
                if intent_response.get('meal_plan_created'):
                    payload['meal_plan_created'] = True
                    payload['meal_plan_url'] = intent_response.get('meal_plan_url', '/thuc-don/')
                return JsonResponse(payload)

        # 2. Kiểm tra bộ nhớ đệm (Cache)
        saved_chat_result = _find_saved_chat_answer(
            user_text,
            source_intent=getattr(intent, 'name', None),
            request_analysis=request_analysis,
        )
        if saved_chat_result:
            if isinstance(saved_chat_result, dict):
                response_text = saved_chat_result.get('response', '')
            else:
                response_text = saved_chat_result
            
            if response_text and _response_matches_current_request(
                account,
                chat_session,
                user_text,
                response_text,
                intent_name,
                'cache',
                analysis=request_analysis,
            ):
                response_text = _append_health_feedback(response_text, account, user_text)
                msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
                _log_chat_search_event(account, user_text, response_text)
                _log_chat_ai_request(
                    account,
                    chat_session,
                    user_text,
                    intent_name,
                    'cache',
                    int((time.perf_counter() - started_at) * 1000),
                    route_path='cache',
                    decision='cache_hit',
                    cache_hit=True,
                    response_ok=True,
                )
                return JsonResponse({'role': msg.role, 'content': msg.content})

        # 4. Sử dụng AI (Gemini/Local RAG)
        if AI_AVAILABLE:
            from app.services.external_apis import save_chat_response_to_cache

            orchestrator_choice = AIOrchestratorService.orchestrate(
                user_text,
                account,
                chat_session,
                call_gemini=False,
                top_k=5,
            )
            candidate_items = orchestrator_choice.get('candidates') or []
            rag_evidence = orchestrator_choice.get('rag_evidence')
            route_path = orchestrator_choice.get('path')
            ab_variant = orchestrator_choice.get('ab_variant')
             
            system_context = _build_gemini_system_context(
                account,
                user_text,
                intent_name=getattr(intent, 'name', None),
                local_candidates=candidate_items,
                rag_evidence=rag_evidence,
            )
            system_context = f"{system_context}\nRANG BUOC TRA LOI:\n{build_response_contract(request_analysis)}\n"

            if route_path == 'local' and ab_variant == 'local_rule' and candidate_items:
                response_text = _format_local_candidates_response(candidate_items)
                if _response_matches_current_request(
                    account,
                    chat_session,
                    user_text,
                    response_text,
                    intent_name,
                    'local_rule',
                    analysis=request_analysis,
                ):
                    response_text = _append_health_feedback(response_text, account, user_text)
                    msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
                    _log_chat_search_event(account, user_text, response_text)
                    _log_chat_ai_request(
                        account,
                        chat_session,
                        user_text,
                        intent_name,
                        'local_rule',
                        int((time.perf_counter() - started_at) * 1000),
                        route_path=route_path,
                        decision=orchestrator_choice.get('decision', 'ab_local_rule'),
                        ab_variant=ab_variant or '',
                        response_ok=True,
                        metadata={'candidate_count': len(candidate_items)},
                    )
                    return JsonResponse({
                        'role': msg.role,
                        'content': msg.content,
                        'ab_variant': ab_variant,
                        'orchestrator_path': route_path,
                    })

            if route_path == 'local':
                response_text = generate_basic_chat_reply_with_local_llm(user_text, context_text=system_context)
                if (
                    response_text
                    and not _is_invalid_chat_response(response_text)
                    and _response_matches_current_request(
                        account,
                        chat_session,
                        user_text,
                        response_text,
                        intent_name,
                        'local_llm',
                        analysis=request_analysis,
                    )
                ):
                    save_chat_response_to_cache(
                        account,
                        user_text,
                        response_text,
                        source_intent=getattr(intent, 'name', None),
                    )
                    response_text = _append_health_feedback(response_text, account, user_text)
                    msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
                    _log_chat_search_event(account, user_text, response_text)
                    _log_chat_ai_request(
                        account,
                        chat_session,
                        user_text,
                        intent_name,
                        'local_llm',
                        int((time.perf_counter() - started_at) * 1000),
                        route_path=route_path,
                        decision=orchestrator_choice.get('decision', 'local_llm'),
                        ab_variant=ab_variant or '',
                        response_ok=True,
                        metadata={'candidate_count': len(candidate_items)},
                    )
                    return JsonResponse({
                        'role': msg.role,
                        'content': msg.content,
                        'ab_variant': ab_variant,
                        'orchestrator_path': route_path,
                    })

            ai_text, ai_err = _call_gemini_with_debug(account, chat_session, system_context, user_text)
            if not ai_err and ai_text:
                response_text = ai_text.strip()
                if (
                    not _is_invalid_chat_response(response_text)
                    and _response_matches_current_request(
                        account,
                        chat_session,
                        user_text,
                        response_text,
                        intent_name,
                        'gemini',
                        analysis=request_analysis,
                    )
                ):
                    save_chat_response_to_cache(
                        account,
                        user_text,
                        response_text,
                        source_intent=getattr(intent, 'name', None),
                    )
                    response_text = _append_health_feedback(response_text, account, user_text)
                    msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
                    _log_chat_search_event(account, user_text, response_text)
                    _log_chat_ai_request(
                        account,
                        chat_session,
                        user_text,
                        intent_name,
                        'gemini',
                        int((time.perf_counter() - started_at) * 1000),
                        route_path=route_path or 'gemini',
                        decision=orchestrator_choice.get('decision', 'gemini'),
                        ab_variant=ab_variant or '',
                        response_ok=True,
                        metadata={'candidate_count': len(candidate_items)},
                    )
                    return JsonResponse({
                        'role': msg.role,
                        'content': msg.content,
                        'ab_variant': ab_variant,
                        'orchestrator_path': route_path or 'gemini',
                    })

        # 4. Ollama Direct Chat Fallback (flexible response for any query)
        ollama_fallback_text = None
        if OLLAMA_READY:
            try:
                from app.services.external_apis import generate_basic_chat_reply_with_local_llm
                ollama_fallback_text = generate_basic_chat_reply_with_local_llm(
                    user_text,
                    context_text=(
                        'Nguoi dung hoi ve am thuc, nau an, thuc don hoac dinh duong. '
                        'Hay tra loi truc tiep, huu ich, bang tieng Viet. '
                        'Neu ho yeu cau cong thuc, hay dua ra huong dan tung buoc. '
                        'Hay than thien, nhiet tinh nhu mot nguoi noi tro.'
                    ),
                    max_output_tokens=1024,
                )
            except Exception:
                pass

        # 5. Fallback: Keyword Hardcoded hoặc Database
        hardcoded_result = _search_keyword_hardcoded(user_text, account)
        if hardcoded_result:
            response_text = hardcoded_result
        elif ollama_fallback_text:
            response_text = ollama_fallback_text
        else:
            response_text = _build_ai_quota_fallback_response(account, user_text)

        if not _response_matches_current_request(
            account,
            chat_session,
            user_text,
            response_text,
            intent_name,
            'fallback',
            analysis=request_analysis,
        ):
            response_text = (
                'Mình chưa có đủ dữ liệu để trả lời chính xác đúng yêu cầu này ngay lúc này. '
                'Bạn hãy gửi lại thật ngắn theo đúng mục tiêu như: giá nguyên liệu, dinh dưỡng, công thức, thực đơn hoặc danh sách mua sắm.'
            )

        response_text = _append_health_feedback(response_text, account, user_text)
        msg = ChatMessage.objects.create(session=chat_session, role='assistant', content=response_text)
        _log_chat_search_event(account, user_text, response_text)
        _log_chat_ai_request(
            account,
            chat_session,
            user_text,
            intent_name,
            'fallback',
            int((time.perf_counter() - started_at) * 1000),
            route_path='fallback',
            decision='fallback_response',
            response_ok=True,
        )
        return JsonResponse({'role': msg.role, 'content': msg.content})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Du lieu gui len khong hop le'}, status=400)
    except Exception:
        logger.exception('chat_send failed unexpectedly')
        if 'account' in locals() and 'chat_session' in locals() and 'user_text' in locals():
            _log_chat_ai_request(
                account,
                chat_session,
                user_text,
                locals().get('intent_name', ''),
                'fallback',
                int((time.perf_counter() - started_at) * 1000),
                route_path='error',
                decision='exception',
                response_ok=False,
            )
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


def _extract_recipe_ingredients(recipe, food):
    ingredients = []
    payload = getattr(recipe, 'ingredients_json', None) if recipe else None

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, str):
                label = item.strip()
            elif isinstance(item, dict):
                name = (item.get('name') or item.get('ingredient') or item.get('original') or '').strip()
                amount = str(item.get('amount') or item.get('quantity') or '').strip()
                unit = str(item.get('unit') or '').strip()
                pieces = [part for part in [amount, unit, name] if part]
                label = ' '.join(pieces).strip()
            else:
                label = ''

            if label:
                ingredients.append(label)

    if ingredients:
        return ingredients

    relation_qs = (
        FoodIngredient.objects
        .select_related('ingredient')
        .filter(food_id=food.id)
        .order_by('ingredient__name')
    )
    for rel in relation_qs:
        ingredient_name = rel.ingredient.name if rel.ingredient else ''
        quantity = float(rel.quantity_grams or 0)
        if ingredient_name:
            if quantity > 0:
                ingredients.append(f'{quantity:g}g {ingredient_name}')
            else:
                ingredients.append(ingredient_name)

    return ingredients


def _extract_instruction_steps(recipe):
    raw_instructions = getattr(recipe, 'instructions', '') if recipe else ''
    if not raw_instructions:
        return []

    steps = []
    for line in re.split(r'\r?\n+', str(raw_instructions)):
        cleaned = line.strip().lstrip('-').strip()
        if cleaned:
            steps.append(cleaned)
    return steps


def _resolve_food_origin(food, recipe):
    if recipe and recipe.source_url:
        hostname = (urlparse(recipe.source_url).netloc or '').replace('www.', '').strip()
        if hostname:
            return f'Dữ liệu công thức từ {hostname}'
    if food.description and 'spoonacular' in food.description.lower():
        return 'Dữ liệu đồng bộ từ Spoonacular API'
    return 'Dữ liệu nội bộ của Smart Home Chef'


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


def food_detail(request, food_id):
    """Hiển thị chi tiết món ăn: dinh dưỡng, công thức và nguồn dữ liệu."""
    food = get_object_or_404(Food.objects.select_related('category'), id=food_id)
    recipe = getattr(food, 'recipe', None)
    account = get_current_account(request)
    if account:
        try:
            SearchEvent.objects.create(
                account=account,
                query_text=f'food_detail:{food.name}',
                normalized_query=f'food_detail:{food.name}'.lower(),
                result_count=1,
                clicked_food=food,
                clicked_food_stt=getattr(food, 'id', None),
            )
            log_recommendation_bandit_event(
                account,
                food,
                event_type='recommendation_clicked',
                score=1.0,
                metadata={'source': 'food_detail'},
            )
        except Exception:
            pass

    ingredients = _extract_recipe_ingredients(recipe, food)
    instruction_steps = _extract_instruction_steps(recipe)

    nutrition = {
        'calories': float(food.calories or 0),
        'protein': float(food.protein or 0),
        'carbs': float(food.carbs or 0),
        'fat': float(food.fat or 0),
        'fiber': float(food.fiber or 0),
        'sugar': float(food.sugar or 0),
        'sodium': float(food.sodium or 0),
        'cholesterol': float(food.cholesterol or 0),
    }

    return render(request, 'user/food_detail.html', {
        'food': food,
        'recipe': recipe,
        'ingredients': ingredients,
        'instruction_steps': instruction_steps,
        'nutrition': nutrition,
        'origin_text': _resolve_food_origin(food, recipe),
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
def recommendation_feedback(request):
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    account = get_current_account(request)
    if not account:
        return JsonResponse({'ok': False, 'error': 'Vui long dang nhap'}, status=401)

    food_id = data.get('food_id')
    event_type = (data.get('event_type') or 'recommendation_clicked').strip()
    rating = data.get('rating')
    liked = data.get('liked')
    context = data.get('context') or {}
    recommendation_id = data.get('recommendation_id') or context.get('recommendation_id')

    if not food_id:
        return JsonResponse({'ok': False, 'error': 'Missing food_id'}, status=400)

    food = Food.objects.filter(pk=food_id).first()
    if not food:
        return JsonResponse({'ok': False, 'error': 'Food not found'}, status=404)

    recommendation = None
    if recommendation_id:
        recommendation = MealRecommendation.objects.filter(
            pk=recommendation_id,
            account=account,
            food=food,
        ).first()

    if event_type == 'recommendation_rated' and rating is not None:
        try:
            rating_value = float(rating)
        except (TypeError, ValueError):
            return JsonResponse({'ok': False, 'error': 'Invalid rating'}, status=400)
        liked = bool(rating_value >= 4 if liked is None else liked)
        try:
            UserFeedbackFood.objects.update_or_create(
                account=account,
                food=food,
                defaults={
                    'rating': int(round(rating_value)),
                    'is_liked': liked,
                    'reason': str(context.get('reason') or '').strip(),
                    'feedback_type': str(context.get('feedback_type') or 'taste').strip() or 'taste',
                },
            )
        except Exception:
            pass
    else:
        rating_value = None

    was_accepted = None
    was_helpful = None
    if event_type == 'recommendation_clicked':
        was_accepted = True
    elif event_type == 'recommendation_rated':
        was_helpful = bool(liked) if liked is not None else bool((rating_value or 0) >= 4)
        was_accepted = was_helpful

    try:
        feedback_context = {
            **context,
            'event_type': event_type,
            'food_id': food.id,
        }
        if recommendation_id:
            feedback_context['recommendation_id'] = recommendation_id

        UserFeedbackRecommendation.objects.create(
            account=account,
            food=food,
            recommendation=recommendation,
            was_accepted=was_accepted,
            was_helpful=was_helpful,
            context=feedback_context,
        )
    except Exception:
        pass

    ok = log_recommendation_bandit_event(
        account,
        food,
        event_type=event_type,
        score=float(rating or 1.0) if event_type == 'recommendation_rated' else 1.0,
        metadata=context,
    )
    return JsonResponse({'ok': ok, 'food_id': food.id, 'event_type': event_type})


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


def meal_plan_toggle_follow(request):
    from django.http import JsonResponse
    return JsonResponse({'success': False, 'error': 'Chua duoc trien khai'})
