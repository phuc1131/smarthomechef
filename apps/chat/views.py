import json
import logging
import re

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from apps.chat.models import ChatMessage, ChatSession
from apps.users.views import get_current_account, get_profile
from app.services.external_apis import (
    AI_AVAILABLE,
    _gemini_generate_text,
    get_or_create_chat_response_from_cache,
    save_chat_response_to_cache,
)
from app.services.meal_plan_generator_service import MealPlanGeneratorService
from app.services.ingredient_price_service import get_ai_price_context


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


def _is_meal_plan_request(user_text):
    text = (user_text or '').lower()
    if any(keyword in text for keyword in ['thuc don', 'thực đơn', 'meal plan', 'menu', 'lap thuc don', 'lập thực đơn']):
        return True
    if any(keyword in text for keyword in ['ngay', 'ngày', 'week', 'tuan', 'tuần', 'month', 'thang', 'tháng']):
        return any(keyword in text for keyword in ['tao', 'tạo', 'lap', 'lập', 'xay dung', 'xây dựng', 'len', 'lên'])
    return False


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

            response_text = result.get('message') or 'Đã tạo và lưu thực đơn vào trang Thực đơn.'
            if created_dates:
                response_text += f"\n\nCác ngày đã tạo: {', '.join(created_dates)}."
            response_text += '\n\nXem tại [Thực đơn](/thuc-don/).'

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

    if not AI_AVAILABLE:
        msg = ChatMessage.objects.create(
            role='assistant',
            content='Xin lỗi, tính năng AI chưa được kích hoạt. Vui lòng kiểm tra cấu hình.',
            session=session,
        )
        return JsonResponse({'role': msg.role, 'content': msg.content})

    profile = get_profile(request)
    system_context = (
        'Ban la "Noi Tro AI", tro ly noi tro thong minh nguoi Viet. '
        'Ban giup goi y mon an, tu van dinh duong va len thuc don. '
        'Hay tra loi bang tieng Viet, than thien va huu ich. '
        'Uu tien cac mon an Viet Nam truyen thong va lanh manh.\n'
    )
    if profile:
        system_context += (
            f'Nguoi dung: {profile.name}, '
            f'tuoi {profile.age or "?"}, '
            f'nang {profile.weight or "?"}kg, '
            f'muc tieu: {profile.health_goal or "chua cung cap"}.\n'
        )
    
    # THÊM DỮ LIỆU GIÁ NẾU CÂUHỎI LÀ VỀ GIÁ
    price_context = get_ai_price_context(user_text)
    if price_context:
        system_context += f"\n{price_context}\n"
        system_context += ("\nKhi trả lời về giá, hãy dùng DỮ LIỆU GIÁ NGUYÊN LIỆU THỰC TẾ từ database ở trên. "
                           "Không được trả lời chung chung hoặc giả định giá. "
                           "Nếu không có dữ liệu giá, hãy thông báo rõ ràng cho người dùng rằng "
                           "'Chưa cập nhật dữ liệu giá cho [nguyên liệu]' thay vì trả lời chung chung.")

    try:
        # Check cache first
        cache_result = None
        try:
            cache_result = get_or_create_chat_response_from_cache(account, user_text)
        except Exception:
            cache_result = None

        if cache_result:
            ai_text = cache_result.get('response') or ''
        else:
            history_lines = []
            for msg in ChatMessage.objects.filter(session=session).order_by('created_at'):
                if _is_seed_chat_message(msg):
                    continue
                prefix = 'Nguoi dung' if msg.role == 'user' else 'Tro ly'
                history_lines.append(f'{prefix}: {msg.content}')

            prompt = '\n'.join(history_lines[-20:]) or user_text
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
    payload = {'role': msg.role, 'content': msg.content}

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
                    save_chat_response_to_cache(account, user_text, ai_text)
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
        ChatMessage.objects.filter(session__in=sessions).delete()
        sessions.delete()

    return JsonResponse({'ok': True})