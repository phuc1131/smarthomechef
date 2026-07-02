import json
import logging
import re
import unicodedata
from decimal import Decimal

from django.conf import settings
from django.db.models import Q
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from apps.chat.models import ChatMessage, ChatSession, ChatSummary, MessageIntent, IntentEmbedding, Pattern
from apps.nutrition.models import Food, FoodIngredient, IngredientPrice
from apps.users.views import get_current_account, get_profile
from app.services.chat_text_service import normalize_chat_text
from app.services.external_apis import (
    AI_AVAILABLE,
    classify_intent_with_local_llm,
    generate_basic_chat_reply_with_local_llm,
    summarize_chat_with_local_llm,
    _gemini_generate_text,
    get_or_create_chat_response_from_cache,
    save_chat_response_to_cache,
)
from app.services.meal_plan_generator_service import MealPlanGeneratorService
from app.services.ingredient_price_service import get_ai_price_context
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
from app.services.ai_chat_service import process_chat_message as process_api_chat_message
from app.services.ai_orchestrator_service import AIOrchestratorService
from app.services.personalization_service import (
    get_personalization_context,
    hybrid_rank_food_candidates,
    persist_recommendation_impressions,
    rank_food_candidates,
)
from app.services.semantic_intent_service import build_text_embedding_vector


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


def get_chat_session(account):
    """Get or create chat session for user."""
    if not account:
        return None
    sessions = ChatSession.objects.filter(account=account).order_by('-created_at', '-id')
    for session in sessions:
        if session.title and session.title.startswith(SEED_SESSION_PREFIX):
            continue
        if ChatMessage.objects.filter(session=session).exclude(content__startswith='[').exclude(content__istartswith='Phan hoi cho ').exists():
            return session

    return ChatSession.objects.create(account=account, title=f'Chat {account.username}')


def _is_budget_meal_plan_request(user_text):
    text = (user_text or '').lower()
    if not text:
        return False

    amount_match = re.search(r'(\d+(?:[\.,]\d+)?)\s*(k|ngh[ìi]n|nghin|ng[àa]n|trieu|tri[ư]u|vn[dđ]|vn[đ])\b', text)
    time_match = re.search(r'\b(\d+)\s*(ngày|ngay|tuần|tuan|tháng|thang)\b', text)
    if amount_match and time_match and 'ăn' in text:
        return True

    if 'ngân sách' in text or 'ngan sach' in text or 'chi phí' in text or 'mua sắm' in text:
        if any(keyword in text for keyword in ['ăn', 'ăn được', 'ăn đc', 'lên', 'lập', 'gợi ý', 'gợi ý', 'menu', 'thực đơn']):
            return True

    return False


def _estimate_food_price(food, servings=1.0):
    total_cost = Decimal('0')
    if not food:
        return None

    ingredients = FoodIngredient.objects.filter(food=food).select_related('ingredient')
    for fi in ingredients:
        price_obj = IngredientPrice.objects.filter(ingredient=fi.ingredient).order_by('-updated_at').first()
        if not price_obj or price_obj.price_per_unit is None or fi.quantity_grams is None:
            continue
        quantity_kg = (Decimal(str(fi.quantity_grams or 0)) * Decimal(str(servings))) / Decimal('1000')
        total_cost += quantity_kg * Decimal(str(price_obj.price_per_unit))

    return float(total_cost) if total_cost > 0 else None


def _format_food_ingredients_with_prices(food, servings=1.0):
    lines = []
    ingredients = FoodIngredient.objects.filter(food=food).select_related('ingredient')
    total_cost = Decimal('0')
    for fi in ingredients:
        ingredient = fi.ingredient
        quantity_grams = Decimal(str(fi.quantity_grams or 0)) * Decimal(str(servings))
        price_obj = IngredientPrice.objects.filter(ingredient=ingredient).order_by('-updated_at').first()
        price_text = 'chưa có giá'
        cost = None
        if price_obj and price_obj.price_per_unit is not None:
            quantity_kg = quantity_grams / Decimal('1000')
            cost = quantity_kg * Decimal(str(price_obj.price_per_unit))
            total_cost += cost
            price_text = f'{float(price_obj.price_per_unit):,.0f} VND/{price_obj.unit_type}'
        lines.append(f'  - {ingredient.name}: {float(quantity_grams):.0f}g, {price_text}')

    if not lines:
        return '  (Không tìm được nguyên liệu hoặc giá trong DB.)'

    total_cost_text = f'Tổng giá ước tính: {float(total_cost):,.0f} VND' if total_cost > 0 else 'Tổng giá ước tính: chưa có dữ liệu'
    return '\n'.join(lines + [total_cost_text])


def _build_meal_plan_response_text(result):
    meal_plans = result.get('meal_plans') or []
    if not meal_plans:
        return result.get('message') or 'Đã tạo thực đơn nhưng chưa có chi tiết.'

    foods = {}
    for plan in meal_plans:
        food = plan.food
        key = food.id
        if key not in foods:
            foods[key] = {
                'food': food,
                'meals': [],
                'servings': float(plan.servings or 1),
            }
        foods[key]['meals'].append(plan.meal_type)

    response_lines = [result.get('message') or 'Đã tạo thực đơn theo yêu cầu.']
    response_lines.append('Dưới đây là danh sách món và nguyên liệu từ DB:')

    for item in foods.values():
        food = item['food']
        meals_text = ', '.join(item['meals'])
        response_lines.append(f'- {food.name} ({meals_text}, {item["servings"]} suất):')
        response_lines.append(_format_food_ingredients_with_prices(food, servings=item['servings']))

    response_lines.append('Món ăn trên được lấy từ cơ sở dữ liệu món ăn, nguyên liệu và giá cả dựa trên dữ liệu DB hiện có.')
    return '\n'.join(response_lines)


def _is_meal_plan_request(user_text):
    text = (user_text or '').lower()
    # Các từ khóa chính về thực đơn
    if any(keyword in text for keyword in ['thuc don', 'thực đơn', 'meal plan', 'menu', 'lap thuc don', 'lập thực đơn']):
        return True
    
    # Kiểm tra yêu cầu ngân sách
    if _is_budget_meal_plan_request(user_text):
        return True
    
    # Kiểm tra yêu cầu theo thời gian + hành động tạo
    time_keywords = ['ngay', 'ngày', 'week', 'tuan', 'tuần', 'month', 'thang', 'tháng']
    action_keywords = ['tao', 'tạo', 'lap', 'lập', 'xay dung', 'xây dựng', 'len', 'lên', 'goi y', 'gợi ý']
    
    if any(tk in text for tk in time_keywords) and any(ak in text for ak in action_keywords):
        return True
        
    # Yêu cầu giàu protein/dinh dưỡng + hành động tạo
    nutrition_keywords = ['protein', 'dinh duong', 'dinh dưỡng', 'calo', 'giảm cân', 'giam can', 'tăng cơ', 'tang co']
    if any(nk in text for nk in nutrition_keywords) and any(ak in text for ak in action_keywords):
        return True

    return False


def _find_recommendation_candidate_foods(user_text):
    normalized_text = normalize_chat_text(user_text)
    tokens = [token for token in normalized_text.split() if len(token) >= 2]
    if tokens:
        query = (
            Q(name__icontains=tokens[0]) |
            Q(category__name__icontains=tokens[0]) |
            Q(description__icontains=tokens[0])
        )
        for token in tokens[1:]:
            query |= (
                Q(name__icontains=token) |
                Q(category__name__icontains=token) |
                Q(description__icontains=token)
            )
        foods = Food.objects.filter(query).distinct()[:20]
        if foods.exists():
            return foods

    fallback = Food.objects.filter(is_weight_loss_friendly=True)[:20]
    if fallback.exists():
        return fallback
    return Food.objects.all()[:20]


def _make_chat_response_system_context(system_context, user_text):
    return (
        f"{system_context}\n"
        "RANG BUOC BO SUNG:\n"
        f'- Cau hoi hien tai cua nguoi dung: "{user_text}"\n'
        "- Uu tien tuyet doi cau hoi hien tai, khong dua phan hoi dua tren chu de cu trong lich su.\n"
        "- Neu cau hoi hien tai khong lien quan am thuc/dinh duong/thuc don/nguyen lieu, tra loi dung chu de do.\n"
        "- Khong lan man, khong chuyen chu de.\n"
    )


def _cache_intent_matches(requested_intent, cached_intent):
    requested = (requested_intent or '').strip().lower()
    cached = (cached_intent or '').strip().lower()
    return not requested or not cached or requested == cached


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


def _record_intent_learning(message, intent_record, confidence):
    if not message or not intent_record:
        return

    try:
        MessageIntent.objects.update_or_create(
            message=message,
            defaults={
                'intent': intent_record,
                'confidence': float(confidence or 0.0),
            },
        )
    except Exception:
        pass

    try:
        Pattern.objects.get_or_create(
            intent=intent_record,
            text=(message.content or '').strip(),
        )
    except Exception:
        pass

    try:
        IntentEmbedding.objects.update_or_create(
            message=message,
            defaults={
                'intent_name': getattr(intent_record, 'name', None),
                'embedding_vector': build_text_embedding_vector(message.content or ''),
                'source_type': 'chat',
                'confidence': float(confidence or 0.0),
            },
        )
    except Exception:
        pass


def chat_page(request):
    account = get_current_account(request)
    if not account:
        return render(request, 'user/chat.html', {
            'messages_json': json.dumps([], ensure_ascii=False),
            'messages_data': [],
            'account_id': 'null',
            'active': 'chat',
        })

    session = get_chat_session(account)
    messages = ChatMessage.objects.filter(session=session).order_by('created_at') if session else []
    messages_data = [
        {'role': m.role, 'content': m.content}
        for m in messages
        if not _is_seed_chat_message(m)
    ]
    return render(request, 'user/chat.html', {
        'messages_json': json.dumps(messages_data, ensure_ascii=False),
        'messages_data': messages_data,
        'account_id': 'null',
        'active': 'chat',
    })


@csrf_exempt
@require_POST
def chat_send(request):
    account = get_current_account(request)
    if not account:
        return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)

    session = get_chat_session(account)
    if not session:
        return JsonResponse({'error': 'Không thể tạo chat session'}, status=500)

    data = json.loads(request.body)
    user_text = data.get('message', '').strip()
    if not user_text:
        return JsonResponse({'error': 'Tin nhan trong'}, status=400)

    ChatMessage.objects.create(role='user', content=user_text, session=session)

    if _is_greeting_message_safe(user_text):
        response_text = _build_greeting_response()
        msg = ChatMessage.objects.create(role='assistant', content=response_text, session=session)
        return JsonResponse({'role': msg.role, 'content': msg.content})

    price_intent = classify_food_price_intent(user_text, account=account)
    if price_intent in {PRICE_QUERY, INGREDIENT_COST_QUERY, RECIPE_COST_QUERY, BUDGET_MEAL_PLAN, GENERAL_MEAL_PLAN}:
        if price_intent == PRICE_QUERY:
            db_response = handle_single_ingredient_price_query(user_text)
        elif price_intent == INGREDIENT_COST_QUERY:
            db_response = handle_multi_ingredient_cost_query(user_text)
        elif price_intent == RECIPE_COST_QUERY:
            db_response = handle_recipe_cost_query(user_text)
        else:
            db_response = None

        if db_response and db_response.get('response'):
            msg = ChatMessage.objects.create(role='assistant', content=db_response['response'], session=session)
            payload = {'role': msg.role, 'content': msg.content}
            if db_response.get('intent'):
                payload['intent'] = db_response['intent']
            return JsonResponse(payload)

    if _is_meal_plan_request(user_text):
        result = MealPlanGeneratorService.generate_meal_plan(account, user_text)
        if result.get('success'):
            meal_plans = result.get('meal_plans') or []
            created_dates = sorted({str(plan.date) for plan in meal_plans})
            meal_plans_data = []
            for plan in meal_plans:
                meal_plans_data.append({
                    'id': plan.id,
                    'food': plan.food.name,
                    'date': str(plan.date),
                    'meal_type': plan.meal_type,
                    'servings': float(plan.servings),
                })

            response_text = _build_meal_plan_response_text(result)
            if created_dates:
                response_text += f"\n\nCác ngày đã tạo: {', '.join(created_dates)}."
            response_text += '\n\nXem chi tiết thực đơn tại [Thực đơn](/thuc-don/).'

            msg = ChatMessage.objects.create(role='assistant', content=response_text, session=session)
            return JsonResponse({
                'role': msg.role,
                'content': msg.content,
                'meal_plan_created': True,
                'meal_plan_url': '/thuc-don/',
                'meal_plans': meal_plans_data,
                'request_type': result.get('request_type'),
                'api_used': result.get('api_fallback_used', result.get('api_used', False)),
            })

        error_message = result.get('message') or 'Không thể tạo thực đơn ngay lúc này.'
        msg = ChatMessage.objects.create(role='assistant', content=error_message, session=session)
        return JsonResponse({
            'role': msg.role,
            'content': msg.content,
            'meal_plan_created': False,
            'request_type': result.get('request_type'),
            'error': error_message,
        })

    profile = get_profile(request)
    system_context = (
        'Bạn là "Nội Trợ AI", trợ lý nội trợ thông minh người Việt. '
        'Bạn giúp gợi ý món ăn, tư vấn dinh dưỡng và lên thực đơn. '
        'Hãy trả lời bằng tiếng Việt, thân thiện và hữu ích. '
        'Ưu tiên các món ăn Việt Nam truyền thống và lành mạnh.\n'
        'QUY TẮC QUAN TRỌNG:\n'
        '1. Luôn trả lời đúng trọng tâm nội dung người dùng hỏi.\n'
        '2. KHÔNG bao giờ hiển thị các thông số kỹ thuật như "query_sim", "score", "intent_confidence" cho người dùng.\n'
        '3. Nếu người dùng hỏi về thực đơn mà hệ thống chưa tự động tạo được, hãy hướng dẫn họ cung cấp thêm thông tin (ngân sách, số ngày, sở thích).\n'
        '4. Nếu trả lời về món ăn, hãy giải thích lý do tại sao món đó phù hợp một cách tự nhiên (ví dụ: "Món này tốt cho người tiểu đường" thay vì "is_diabetes_friendly=True").\n'
    )
    if profile:
        system_context += (
            f'Người dùng: {profile.name}, '
            f'tuổi {profile.age or "?"}, '
            f'nặng {profile.weight or "?"}kg, '
            f'mục tiêu: {profile.health_goal or "chưa cung cấp"}.\n'
        )

    cash_intent_name = None
    chat_intent_confidence = 0.0
    personalization_candidates = None

    if AI_AVAILABLE:
        intent_record, intent_confidence = AIOrchestratorService.classify_intent(user_text)
        if intent_record:
            cash_intent_name = intent_record.name
            chat_intent_confidence = intent_confidence or 0.0

        if cash_intent_name == 'greeting':
            system_context += "Người dùng đang chào hỏi. Hãy chào lại một cách thân thiện và hỏi xem bạn có thể giúp gì cho họ.\n"
        elif cash_intent_name == 'recommendation' and chat_intent_confidence >= 0.4:
            candidate_foods = _find_recommendation_candidate_foods(user_text)
            personalization_candidates = hybrid_rank_food_candidates(account, candidate_foods, limit=5, user_query=user_text)
            personalization_candidates = persist_recommendation_impressions(
                account,
                personalization_candidates,
                user_query=user_text,
                source='chat',
            )
            if personalization_candidates:
                ranked_names = ', '.join([item['food'].name for item in personalization_candidates])
                system_context += (
                    'Người dùng đang hỏi gợi ý món ăn. Hãy ưu tiên đề xuất các món phù hợp với hồ sơ người dùng, ' 
                    f'nổi bật trong số: {ranked_names}. '
                    'Giải thích nhẹ nhàng lý do phù hợp mà không dùng từ ngữ kỹ thuật.\n'
                )
        elif cash_intent_name == 'nutrition':
            system_context += "Người dùng đang hỏi về dinh dưỡng. Hãy cung cấp thông tin khoa học và dễ hiểu.\n"
        elif cash_intent_name == 'meal_plan':
            system_context += "Người dùng muốn lên thực đơn. Nếu chưa có thực đơn chi tiết ở trên, hãy hỏi thêm yêu cầu cụ thể.\n"

    try:
        _record_intent_learning(
            ChatMessage.objects.filter(session=session, role='user').order_by('-created_at').first(),
            intent_record if AI_AVAILABLE else None,
            chat_intent_confidence,
        )
    except Exception:
        pass

    system_context = (
        f"{system_context}\n"
        "RANG BUOC BO SUNG:\n"
        f'- Cau hoi hien tai cua nguoi dung: "{user_text}"\n'
        "- Uu tien tuyet doi cau hoi hien tai, khong dua phan hoi dua tren chu de cu trong lich su.\n"
        "- Neu cau hoi hien tai khong lien quan am thuc/dinh duong/thuc don/nguyen lieu, tra loi dung chu de do.\n"
        "- Khong lan man, khong chuyen chu de.\n"
    )

    if not AI_AVAILABLE:
        msg = ChatMessage.objects.create(
            role='assistant',
            content='Xin lỗi, tính năng AI chưa được kích hoạt. Vui lòng kiểm tra cấu hình.',
            session=session,
        )
        return JsonResponse({'role': msg.role, 'content': msg.content})

    # THÊM DỮ LIỆU GIÁ NẾU CÂUHỎI LÀ VỀ GIÁ
    price_context = get_ai_price_context(user_text)
    if price_context:
        system_context += f"\n{price_context}\n"
        system_context += ("\nKhi trả lời về giá, hãy dùng DỮ LIỆU GIÁ NGUYÊN LIỆU THỰC TẾ từ database ở trên. "
                           "Không được trả lời chung chung hoặc giả định giá. "
                           "Nếu không có dữ liệu giá, hãy thông báo rõ ràng cho người dùng rằng "
                           "'Chưa cập nhật dữ liệu giá cho [nguyên liệu]' thay vì trả lời chung chung.")

    price_intent = classify_food_price_intent(user_text, account=account)
    skip_cache_for_price = price_intent in {PRICE_QUERY, INGREDIENT_COST_QUERY, RECIPE_COST_QUERY, BUDGET_MEAL_PLAN, GENERAL_MEAL_PLAN}

    try:
        # Check cache first
        cache_result = None
        if not skip_cache_for_price:
            try:
                cache_result = get_or_create_chat_response_from_cache(account, user_text, source_intent=cash_intent_name)
            except Exception:
                cache_result = None

        if cache_result and _cache_intent_matches(cash_intent_name, cache_result.get('intent_name')):
            ai_text = cache_result.get('response') or ''
        else:
            history_lines = []
            for msg in ChatMessage.objects.filter(session=session).order_by('created_at'):
                if _is_seed_chat_message(msg):
                    continue
                prefix = 'Nguoi dung' if msg.role == 'user' else 'Tro ly'
                history_lines.append(f'{prefix}: {msg.content}')

            recent_history = '\n'.join(history_lines[-10:])
            prompt = (
                f'{recent_history}\n'
                f'Cau hoi hien tai cua nguoi dung: {user_text}'
            ).strip() or user_text

            routed_ai_text = ''
            if cash_intent_name in {'recipe', 'nutrition'}:
                try:
                    routed_ai_text = process_api_chat_message(user_text)
                except Exception:
                    logger.exception('API chat routing failed for account_id=%s session_id=%s', getattr(account, 'id', None), getattr(session, 'id', None))

            ai_text = routed_ai_text or generate_basic_chat_reply_with_local_llm(user_text, context_text=system_context)
            if not ai_text or _is_invalid_chat_response(ai_text):
                ai_text = _gemini_generate_text(
                    prompt,
                    system_instruction=system_context,
                    max_output_tokens=8192,
                )
    except Exception as exc:
        logger.exception(
            'chat_send AI generation failed for account_id=%s session_id=%s',
            getattr(account, 'id', None),
            getattr(session, 'id', None),
        )
        error_text = str(exc).strip()
        if '429' in error_text or 'rate limited' in error_text.lower() or 'too many requests' in error_text.lower():
            if settings.DEBUG and error_text:
                ai_text = f'Dịch vụ AI đang bị giới hạn tần suất (HTTP 429): {error_text}'
            else:
                ai_text = 'Dịch vụ AI đang bị giới hạn tần suất (HTTP 429). Vui lòng thử lại sau ít phút.'
        elif settings.DEBUG and error_text:
            ai_text = f'Xin lỗi, AI gặp lỗi: {error_text}'
        else:
            ai_text = 'Xin lỗi, tôi gặp sự cố khi kết nối AI. Vui lòng thử lại sau.'

    msg = ChatMessage.objects.create(role='assistant', content=ai_text, session=session)
    payload = {
        'role': msg.role,
        'content': msg.content,
        'intent': cash_intent_name,
        'intent_confidence': chat_intent_confidence,
    }
    if personalization_candidates:
        payload['recommendation_candidates'] = [
            {
                'food_id': item['food'].id,
                'food_name': item['food'].name,
                'score': item['score'],
                'reasons': item['reasons'],
                'recommendation_id': item.get('recommendation_id'),
                'bandit_context': item.get('bandit_context', {}),
            }
            for item in personalization_candidates
        ]

    # Save to cache if response came from AI (not from cache) and looks valid
    try:
        if not cache_result:
            invalid_saved_markers = (
                'Loi AI [',
                'RESOURCE_EXHAUSTED',
                'He thong tam thoi gap loi',
                'Khong co phan hoi tu AI',
            )
            if ai_text and not any(marker in ai_text for marker in invalid_saved_markers):
                try:
                    save_chat_response_to_cache(account, user_text, ai_text, source_intent=cash_intent_name)
                except Exception:
                    pass
    except Exception:
        pass
    if settings.DEBUG and ai_text.startswith('Xin lỗi, AI gặp lỗi:'):
        payload['error_detail'] = ai_text
    return JsonResponse(payload)


@csrf_exempt
@require_POST
def chat_clear(request):
    account = get_current_account(request)
    if not account:
        return JsonResponse({'error': 'Vui lòng đăng nhập'}, status=401)

    # Chỉ xóa dữ liệu hội thoại của user hiện tại.
    # Không đụng tới ChatResponseCache vì cache này được dùng chung để train/reuse AI.
    sessions = ChatSession.objects.filter(account=account)
    if sessions.exists():
        for session in sessions:
            try:
                history_lines = []
                for msg in ChatMessage.objects.filter(session=session).order_by('created_at'):
                    prefix = 'Nguoi dung' if msg.role == 'user' else 'Tro ly'
                    history_lines.append(f'{prefix}: {msg.content}')
                summary_text = summarize_chat_with_local_llm(history_lines)
                if summary_text:
                    ChatSummary.objects.create(session=session, summary=summary_text)
            except Exception:
                pass
        ChatMessage.objects.filter(session__in=sessions).delete()
        sessions.delete()

    return JsonResponse({'ok': True})
