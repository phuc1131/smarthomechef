"""
Chuyển các câu trả lời cứng từ database thành văn bản tự nhiên, đa dạng hơn nhờ LLM.

Nguyên tắc:
- Không sửa đổi sự kiện/thông tin gốc từ database (giá, chi phí, nguyên liệu thiếu).
- Chỉ diễn đạt lại, thêm lời chuyển tiếp, kết thúc lịch sự và cá nhân hóa theo profile.
- Fallback về raw_response nếu AI không sẵn sàng.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _build_personalization_snippet(account: Any = None) -> str:
    try:
        from app.services.personalization_service import get_personalization_context
        from apps.users.models import UserProfile, UserGoal, UserDisease
        ctx = get_personalization_context(account)
        profile = ctx.get('profile')
        parts = []
        if profile:
            name = getattr(profile, 'name', None)
            age = getattr(profile, 'age', None)
            gender = getattr(profile, 'gender', None)
            if name:
                parts.append(f'Người dùng {name}')
            if age:
                parts.append(f'{age} tuổi')
            if gender:
                parts.append(f'giới tính {gender}')
        diseases = ctx.get('diseases') or []
        if diseases:
            disease_names = [getattr(d, 'name', '') for d in diseases if getattr(d, 'name', '')]
            if disease_names:
                parts.append('có bệnh lý: ' + ', '.join(disease_names))
        if not parts:
            return ''
        return 'Thông tin cá nhân: ' + '; '.join(parts) + '.'
    except Exception:
        return ''


def naturalize_db_response(
    raw_response: str,
    user_text: str,
    intent_name: str = '',
    account: Any = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    if not raw_response or not str(raw_response).strip():
        return raw_response or ''

    metadata = metadata or {}

    # Kiểm tra xem có AI khả dụng không
    try:
        from app.services.external_apis import AI_AVAILABLE, _gemini_generate_text, _local_llm_generate_text
    except Exception:
        return raw_response

    if not AI_AVAILABLE:
        return raw_response

    personalization = _build_personalization_snippet(account)

    # Tạo bối cảnh từ metadata để giữ nguyên sự thật
    extra_context_lines = []
    for key in ('missing_items', 'missing_ingredients', 'missing_price_ingredients',
                'suggested_ingredients', 'not_found', 'similar_ingredients',
                'total_cost', 'budget', 'shopping_items', 'price_per_unit', 'unit_type',
                'ingredient_name', 'food_name', 'servings', 'cost_per_serving'):
        value = metadata.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            if value:
                extra_context_lines.append(f'{key}: ' + ', '.join(str(v) for v in value))
        else:
            extra_context_lines.append(f'{key}: {value}')

    extra_context = '\n'.join(extra_context_lines) if extra_context_lines else 'Không có thông tin bổ sung.'

    prompt = (
        'Bạn là trợ lý ẩm thực thông minh dịu văn phong tự nhiên, lịch sự, ngắn gọn.\n'
        'Nhiệm vụ: viết lại đoạn sau bằng tiếng Việt tự nhiên như đang trò chuyện với bạn bè, '
        'KHÔNG thay đổi bất kỳ con số, đơn vị, tên nguyên liệu hay sự kiện nào dưới đây.\n'
        'KHÔNG bịa thêm dữ liệu, KHÔNG thêm thông tin không có trong raw.\n'
        'Giữ nguyên các thực thể: {user_text}.\n'
        f'Raw từ hệ thống:\n{raw_response}\n\n'
        f'Thông tin bổ sung (để đảm bảo không sai lệch):\n{extra_context}\n'
    )
    if personalization:
        prompt += f'\nBối cảnh người dùng: {personalization}\n'
    prompt += '\nYêu cầu:\n- Chỉ trả lời đúng trọng tâm câu hỏi.\n- Không giải thích cách bạn viết lại.\n- Không dùng markdown code block.\n- Không hiển thị từ khóa kỹ thuật như query_sim, score, confidence.\n- Thêm lời chuyển tiếp ngắn nếu phù hợp.\n'

    system_instruction = (
        'Bạn là Nội Trợ AI, trợ lý ẩm thực bằng tiếng Việt. '
        'Luôn giữ thái độ tích cực, thân thiện, chuyên nghiệp.'
    )

    try:
        generated = _gemini_generate_text(
            prompt,
            system_instruction=system_instruction,
            max_output_tokens=800,
        )
        if generated and isinstance(generated, str) and generated.strip():
            return generated.strip()
    except Exception as exc:
        logger.debug('Gemini naturalize failed: %s', exc)

    try:
        generated = _local_llm_generate_text(
            prompt,
            system_instruction=system_instruction,
            max_output_tokens=800,
        )
        if generated and isinstance(generated, str) and generated.strip():
            return generated.strip()
    except Exception as exc:
        logger.debug('Local LLM naturalize failed: %s', exc)

    return raw_response
