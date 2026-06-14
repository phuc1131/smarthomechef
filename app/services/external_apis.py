"""
Module tích hợp các external API (Gemini, Spoonacular).

Mục đích:
- Gọi Google Gemini LLM để generate text responses (chat)
- Gọi Spoonacular API để lấy thông tin dinh dưỡng thực phẩm
- Cache kết quả Spoonacular vào bảng Food để tránh API calls lặp lại

GHI NHỚ QUAN TRỌNG:
- AI_AVAILABLE flag để gracefully fallback nếu Gemini không available
- Tất cả exception được catch và return error dict để tránh crash
- Spoonacular results được cache vào database → giảm API quota
"""

import logging
import os
import json
import re
import unicodedata
from decimal import Decimal

from app.config import (
    GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL, GEMINI_ENABLED,
    OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_API_KEY, OLLAMA_ENABLED,
    SPOONACULAR_API_KEY, SPOONACULAR_ENABLED, SPOONACULAR_TIMEOUT, SPOONACULAR_RETRIES,
    SPOONACULAR_BASE_URL,
    SPOONACULAR_SEARCH_URL, SPOONACULAR_INGREDIENT_SEARCH_URL, SPOONACULAR_COMPLEX_SEARCH_URL,
    SPOONACULAR_RECIPE_INFO_URL_TEMPLATE, SPOONACULAR_INGREDIENT_INFO_URL_TEMPLATE,
    THEMEALDB_BASE_URL, THEMEALDB_SEARCH_URL, THEMEALDB_LOOKUP_URL, THEMEALDB_AUTO_TRANSLATE
)
import requests
import time

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

from apps.chat.models import ChatMessage
from apps.nutrition.models import Food, FoodCategory, Recipe


_SPOONACULAR_LAST_ERROR = None


def _set_spoonacular_last_error(message):
    global _SPOONACULAR_LAST_ERROR
    _SPOONACULAR_LAST_ERROR = message


def _clear_spoonacular_last_error():
    global _SPOONACULAR_LAST_ERROR
    _SPOONACULAR_LAST_ERROR = None


def get_spoonacular_last_error():
    return _SPOONACULAR_LAST_ERROR


# ============================================================================
# PHáº¦N 1: GEMINI LLM INTEGRATION
# ============================================================================


def _is_cacheable_chat_response(response_text):
    text = (response_text or '').strip()
    if not text:
        return False
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
    return not any(marker in text for marker in invalid_markers)

_GEMINI_DEFAULT_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta'

# AI is considered available when we have Ollama/Qwen or Gemini available.
OLLAMA_READY = bool(OLLAMA_ENABLED and OpenAI is not None)
AI_AVAILABLE = bool(OLLAMA_READY or (GEMINI_ENABLED and GEMINI_API_KEY and GEMINI_API_KEY != 'dummy'))

_OLLAMA_CLIENT = None


# ============================================================================
# PH?N 2: SPOONACULAR API INTEGRATION
# ============================================================================

# All Spoonacular & TheMealDB endpoints are imported from app.config
# (see top of file: SPOONACULAR_BASE_URL, SPOONACULAR_SEARCH_URL, etc.)


def _extract_json_object(text):
    """TÃ¡ch JSON object tá»« text model tráº£ vá» (cÃ³ thá»ƒ kÃ¨m markdown fences)."""
    if not text:
        return None

    raw = str(text).strip()
    if raw.startswith('```'):
        lines = raw.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        raw = '\n'.join(lines).strip()

    start_idx = raw.find('{')
    end_idx = raw.rfind('}')
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return None

    candidate = raw[start_idx:end_idx + 1]
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _normalize_ascii_text(value):
    text = str(value or '').strip().lower()
    if not text:
        return ''
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r'\s+', ' ', text).strip()


def _strip_markdown_fences(text):
    raw = str(text or '').strip()
    if raw.startswith('```'):
        lines = raw.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        raw = '\n'.join(lines).strip()
    return raw


def _cleanup_local_llm_output(text):
    raw = _strip_markdown_fences(text)
    if not raw:
        return ''

    quote_match = re.search(r'"([^"\n]{20,})"', raw, flags=re.DOTALL)
    if quote_match:
        raw = quote_match.group(1).strip()

    cleaned_lines = []
    skip_prefixes = (
        'day la',
        'duoi day la',
        'tra loi nhu sau',
        'giai thich',
        'phan loai',
        'toi co the tra loi',
        'nguyen van can',
    )
    for line in raw.splitlines():
        stripped = line.strip().strip('"').strip("'").strip()
        if not stripped:
            if cleaned_lines:
                cleaned_lines.append('')
            continue
        normalized = _normalize_ascii_text(stripped)
        if any(marker in normalized for marker in ('goi y nhu sau', 'tra loi nhu sau', 'tom tat cuoc hoi thoai nay')):
            suffix = stripped.split(':', 1)[1].strip() if ':' in stripped else ''
            if suffix:
                cleaned_lines.append(suffix)
            continue
        if any(normalized.startswith(prefix) for prefix in skip_prefixes):
            continue
        if normalized in {'json', '```'}:
            continue
        cleaned_lines.append(stripped)

    cleaned = '\n'.join(cleaned_lines).strip()
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(
        r'(?i)\b(duoi day la|day la|toi co the (tra loi|goi y)( cho ban)?|tra loi nhu sau|tom tat cuoc hoi thoai nay)\b\s*:?',
        '',
        cleaned,
    )
    cleaned = re.sub(r'(?i)\bnguyen van can\b', '', cleaned)
    cleaned = re.sub(r'^[\s,.:;-]+', '', cleaned)
    return cleaned.strip(' "\'')


def _get_ollama_client():
    """Get or create OpenAI client connected to Ollama."""
    global _OLLAMA_CLIENT
    if not OLLAMA_READY:
        raise RuntimeError('Ollama không khả dụng hoặc OpenAI package chưa được cài đặt')
    if _OLLAMA_CLIENT is None:
        _OLLAMA_CLIENT = OpenAI(
            base_url=OLLAMA_BASE_URL.rstrip('/'),
            api_key=OLLAMA_API_KEY,
        )
    return _OLLAMA_CLIENT


def _ollama_qwen_generate_text(prompt, system_instruction=None, max_output_tokens=2048):
    """Call Qwen2.5:7b via Ollama using OpenAI-compatible API."""
    client = _get_ollama_client()
    messages = []
    if system_instruction:
        messages.append({
            'role': 'system',
            'content': str(system_instruction).strip(),
        })
    messages.append({
        'role': 'user',
        'content': str(prompt),
    })
    
    response = client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=messages,
        max_tokens=int(max_output_tokens),
        temperature=0.0,
    )
    
    result = response.choices[0].message.content if response.choices else ''
    return result.strip() if result else 'Không có phản hồi từ Qwen'


def _local_llm_generate_text(prompt, system_instruction=None, max_output_tokens=2048):
    """Generate text with local Ollama/Qwen only. Return empty string on failure."""
    if not OLLAMA_READY:
        return ''
    try:
        return _cleanup_local_llm_output(_ollama_qwen_generate_text(
            prompt,
            system_instruction=system_instruction,
            max_output_tokens=max_output_tokens,
        ))
    except Exception as exc:
        logger.exception('Local LLM generation failed: %s', exc)
        return ''


def classify_intent_with_local_llm(user_text):
    """Classify intent with local LLM first. Return dict or None."""
    text = (user_text or '').strip()
    if not text:
        return None

    prompt = (
        'Phan loai y dinh nguoi dung thanh dung 1 nhan trong danh sach sau: '
        'greeting, recommendation, nutrition, meal_plan, recipe, shopping, ingredient, general.\n'
        'Chi duoc tra ve DUNG 1 JSON object, khong markdown, khong giai thich, khong text bo sung.\n'
        'Mau bat buoc: {"intent":"...", "confidence":0.0, "reason":"..."}\n'
        'reason phai viet bang tieng Viet, rat ngan gon.\n'
        f'Noi dung nguoi dung: {text}'
    )
    raw = _ollama_qwen_generate_text(
        prompt,
        system_instruction=(
            'Ban la bo phan phan loai intent. '
            'Chi tra ve JSON hop le. Khong viet them bat ky cau nao khac.'
        ),
        max_output_tokens=256,
    )
    parsed = _extract_json_object(raw)
    if not parsed:
        return None

    intent = str(parsed.get('intent') or '').strip()
    confidence = parsed.get('confidence', 0.0)
    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0
    if not intent:
        return None
    return {
        'intent': intent,
        'confidence': max(0.0, min(confidence, 1.0)),
        'reason': _cleanup_local_llm_output(parsed.get('reason') or ''),
        'raw': raw,
    }


def summarize_chat_with_local_llm(history_lines, max_output_tokens=256):
    """Summarize chat history with local LLM only."""
    lines = [str(line).strip() for line in (history_lines or []) if str(line).strip()]
    if not lines:
        return ''

    prompt = (
        'Hay tom tat cuoc hoi thoai nay trong 3-5 dong ngan gon.\n'
        'Chi tap trung vao y chinh, muc tieu cua nguoi dung, va ket qua da tra loi.\n'
        'Khong viet mo dau kieu "Duoi day la tom tat".\n'
        + '\n'.join(lines)
    )
    return _local_llm_generate_text(
        prompt,
        system_instruction='Ban la he thong tom tat hoi thoai.',
        max_output_tokens=max_output_tokens,
    )


def generate_basic_chat_reply_with_local_llm(user_text, context_text='', max_output_tokens=512):
    """Generate a basic answer with local LLM only."""
    text = (user_text or '').strip()
    if not text:
        return ''

    extra_context = (context_text or '').strip()
    prompt_parts = [
        'Tra loi truc tiep cho cau hoi hien tai cua nguoi dung.',
        f'Cau hoi: {text}',
    ]
    if extra_context:
        prompt_parts.extend([
            'Boi canh noi bo de tham khao:',
            extra_context,
        ])
    prompt_parts.extend([
        'Yeu cau bat buoc:',
        '- Chi tra loi cho cau hoi hien tai.',
        '- Neu nguoi dung dang can goi y, dua ra 2-4 goi y cu the va ly do ngan gon.',
        '- Neu khong du du lieu thi noi ro phan thieu.',
        '- Khong viet cac cau mo dau nhu "Day la", "Tra loi nhu sau", "Nguyen van can".',
        '- Khong giai thich cach ban suy nghi, khong dua markdown code block.',
        'Tra loi cuoi cung:',
    ])
    prompt = '\n'.join(prompt_parts).strip()
    return _local_llm_generate_text(
        prompt,
        system_instruction=(
            'Ban la tro ly AI noi bo cho ung dung am thuc. '
            'Tra loi bang tieng Viet, ngan gon, ro rang, dung trong tam. '
            'Tuyet doi khong tao loi dan nhap, khong tu gioi thieu, khong viet meta-commentary. '
            'Neu co du lieu noi bo trong prompt thi uu tien du lieu do.'
        ),
        max_output_tokens=max_output_tokens,
    )


def _gemini_generate_text(prompt, system_instruction=None, max_output_tokens=2048):
    """Gá»i Gemini hoặc local Qwen vÃ  tráº£ text; raise exception Ä‘á»ƒ caller tá»± quyáº¿t Ä‘á»‹nh fallback."""
    if not AI_AVAILABLE:
        raise RuntimeError('AI client khong san sang')

    if OLLAMA_READY:
        try:
            return _ollama_qwen_generate_text(prompt, system_instruction=system_instruction, max_output_tokens=max_output_tokens)
        except Exception as exc:
            logger.exception('Ollama/Qwen generation failed, falling back to Gemini if available: %s', exc)
            if not (GEMINI_ENABLED and GEMINI_API_KEY and GEMINI_API_KEY != 'dummy'):
                raise

    endpoint_base = (GEMINI_BASE_URL or _GEMINI_DEFAULT_BASE_URL).rstrip('/')
    endpoint = f'{endpoint_base}/models/{GEMINI_MODEL}:generateContent'
    payload = {
        'contents': [
            {
                'role': 'user',
                'parts': [{'text': str(prompt)}],
            }
        ],
        'generationConfig': {
            'temperature': 0.0,
            'maxOutputTokens': int(max_output_tokens),
        },
    }
    if system_instruction:
        payload['systemInstruction'] = {
            'parts': [{'text': str(system_instruction)}],
        }

    try:
        response = requests.post(
            endpoint,
            params={'key': GEMINI_API_KEY},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        response_data = response.json()
    except requests.HTTPError as exc:
        response = getattr(exc, 'response', None)
        status_code = getattr(response, 'status_code', None)
        detail = ''
        if response is not None:
            try:
                response_data = response.json()
                error_payload = response_data.get('error') if isinstance(response_data, dict) else None
                if isinstance(error_payload, dict):
                    detail = str(error_payload.get('message') or '').strip()
            except Exception:
                detail = ''
            if not detail:
                detail = (getattr(response, 'text', '') or '').strip()
        if status_code == 429:
            raise RuntimeError(
                f'Dịch vụ AI bị giới hạn lưu lượng (HTTP 429). {detail or "Too Many Requests"}'
            ) from exc
        raise RuntimeError(
            f'Yêu cầu dịch vụ AI thất bại (HTTP {status_code or "unknown"}). {detail or str(exc)}'
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError(f'Lỗi mạng khi gọi dịch vụ AI: {exc}') from exc

    text = ''
    candidates = response_data.get('candidates') or []
    if candidates:
        content = candidates[0].get('content') or {}
        parts = content.get('parts') or []
        if parts:
            text = str(parts[0].get('text') or '').strip()
    if not text:
        text = str(response_data.get('text') or '').strip()
    if not text:
        raise RuntimeError('Dịch vụ AI không trả về nội dung')
    return text


def _looks_vietnamese(text):
    """Heuristic nháº¹ Ä‘á»ƒ nháº­n diá»‡n text tiáº¿ng Viá»‡t sau khi dá»‹ch."""
    if not isinstance(text, str) or not text.strip():
        return False

    lower_text = text.lower()
    if any(ch in lower_text for ch in 'ÄƒÃ¢Ä‘ÃªÃ´Æ¡Æ°Ã¡Ã áº£Ã£áº¡áº¥áº§áº©áº«áº­áº¯áº±áº³áºµáº·Ã©Ã¨áº»áº½áº¹áº¿á»á»ƒá»…á»‡Ã³Ã²á»Ãµá»á»‘á»“á»•á»—á»™á»›á»á»Ÿá»¡á»£ÃºÃ¹á»§Å©á»¥á»©á»«á»­á»¯á»±Ã­Ã¬á»‰Ä©á»‹Ã½á»³á»·á»¹á»µ'):
        return True

    common_tokens = (' va ', ' mon ', ' nuoc ', ' them ', ' khuay ', ' den ', ' cho ', ' voi ', ' trong ')
    padded = f' {lower_text} '
    return any(token in padded for token in common_tokens)


def _translate_text_vi_with_gemini(text, text_type='other', source_context=None):
    """
    Dá»‹ch 1 Ä‘oáº¡n text sang tiáº¿ng Viá»‡t báº±ng Gemini, fallback vá» text gá»‘c náº¿u lá»—i.
    
    Chiáº¿n lÆ°á»£c cache:
    1. Kiá»ƒm tra TextTranslation cache trÆ°á»›c (by original_text + text_type)
    2. Náº¿u tÃ¬m tháº¥y, return cached translation
    3. Náº¿u khÃ´ng, gá»i Gemini API dá»‹ch
    4. Cache káº¿t quáº£ vÃ o TextTranslation table
    5. Return translated text
    
    Tham sá»‘:
    - text: Text gá»‘c cáº§n dá»‹ch
    - text_type: Loáº¡i text (instruction, ingredient_name, etc.) - dÃ¹ng cho cache lookup
    - source_context: Context Ä‘á»ƒ trace (recipe_id=123, food_id=456, etc.)
    
    Tráº£ vá»:
    - string: Text dá»‹ch sang Tiáº¿ng Viá»‡t (hoáº·c text gá»‘c náº¿u lá»—i/khÃ´ng available)
    """
    if not isinstance(text, str) or not text.strip():
        return text
    if not AI_AVAILABLE:
        return text

    source_text = text.strip()
    
    # BÆ¯á»šC 1: Check cache trÆ°á»›c (disabled - TextTranslation table removed)
    # Cache lookup disabled

    try:
        prompt = (
            'Dich sang tieng Viet tu nhien, chi tra ve ban dich, khong giai thich.\n\n'
            'Vi du:\n'
            'Bring water to a boil. -> Äun sÃ´i nÆ°á»›c.\n\n'
            f'VAN BAN:\n{source_text}'
        )
        translated = _gemini_generate_text(
            prompt,
            system_instruction='Ban la dich gia am thuc tieng Viet. Luon tra ve tieng Viet.',
            max_output_tokens=512,
        )
        if _looks_vietnamese(translated):
            # BÆ¯á»šC 2: Cache successful translation (disabled - TextTranslation table removed)
            return translated

        retry_prompt = (
            'Dich CHINH XAC sang tieng Viet. '
            'Khong duoc giu nguyen tieng Anh. '
            'Khong giai thich, khong them chu thich.\n\n'
            'Vi du:\n'
            'Bring water to a boil. -> Äun sÃ´i nÆ°á»›c.\n\n'
            f'VAN BAN:\n{source_text}'
        )
        retry_translated = _gemini_generate_text(
            retry_prompt,
            system_instruction='Dich sang tieng Viet.',
            max_output_tokens=512,
        )
        result = retry_translated if _looks_vietnamese(retry_translated) else translated or text
        
        # BÆ¯á»šC 3: Cache retry translation if Vietnamese (disabled - TextTranslation table removed)
        
        return result
    except Exception:
        return text


def _translate_mealdb_recipe_payload_vi(recipe_payload, source_recipe_id=None):
    """
    Dá»‹ch payload recipe TheMealDB sang tiáº¿ng Viá»‡t báº±ng Gemini, cÃ³ fallback an toÃ n.
    
    Chiáº¿n lÆ°á»£c cache:
    1. Náº¿u cÃ³ source_recipe_id, check RecipeTranslation cache (by source_api='themealdb', source_recipe_id)
    2. Náº¿u tÃ¬m tháº¥y, return cached translated_payload
    3. Náº¿u khÃ´ng, dá»‹ch toÃ n bá»™ recipe báº±ng Gemini
    4. Cache káº¿t quáº£ vÃ o RecipeTranslation table
    5. Return translated payload
    
    Tham sá»‘:
    - recipe_payload: Dict payload tá»« TheMealDB hoáº·c Spoonacular
    - source_recipe_id: ID recipe tá»« source API (Ä‘á»ƒ cache lookup)
    
    Tráº£ vá»:
    - dict: Recipe payload sau dá»‹ch (hoáº·c gá»‘c náº¿u lá»—i/khÃ´ng available)
    """
    if not isinstance(recipe_payload, dict):
        return recipe_payload

    if not THEMEALDB_AUTO_TRANSLATE or not AI_AVAILABLE:
        return recipe_payload

   # BƯỚC 1: Kiểm tra cache nếu có source_recipe_id
# (Đã tạm vô hiệu hóa vì bảng RecipeTranslation đã bị xóa)

# if source_recipe_id:
#     try:
#         cached = RecipeTranslation.objects.filter(
#             source_api='themealdb',
#             source_recipe_id=str(source_recipe_id)
#         ).first()
#
#         if cached and cached.translated_payload:
#             return cached.translated_payload
#
#     except Exception:
#         pass  # Lỗi khi kiểm tra cache → tiếp tục dịch dữ liệu
    try:
        translate_input = {
            'title': recipe_payload.get('title') or '',
            'summary': recipe_payload.get('summary') or '',
            'instructions': recipe_payload.get('instructions') or '',
            'ingredients': recipe_payload.get('ingredients') or [],
        }

        prompt = (
            'Ban la dich gia am thuc. Dich toan bo noi dung sau sang tieng Viet tu nhien. '
            'Giu nguyen nghia nau an, giu ten rieng neu can, khong bo sung thong tin moi. '
            'Tra ve DUY NHAT mot JSON object hop le voi dung cac key: '
            'title, summary, instructions, ingredients. '
            'Trong ingredients, giu nguyen cau truc tung phan tu va dich cac truong text nhu '
            'name, original.\n\n'
            f'Input JSON:\n{json.dumps(translate_input, ensure_ascii=False)}'
        )

        translated_text = _gemini_generate_text(
            prompt,
            system_instruction='You translate recipe JSON into Vietnamese and must preserve JSON structure.',
            max_output_tokens=4096,
        )
        translated = _extract_json_object(translated_text)
        if not translated:
            translated = {}

        merged = dict(recipe_payload)
        for key in ('title', 'summary', 'instructions'):
            translated_value = translated.get(key)
            if isinstance(translated_value, str) and translated_value.strip():
                merged[key] = translated_value.strip()

        translated_ingredients = translated.get('ingredients')
        if isinstance(translated_ingredients, list) and translated_ingredients:
            merged['ingredients'] = translated_ingredients

        # Fallback dá»‹ch tá»«ng trÆ°á»ng náº¿u model khÃ´ng tráº£ JSON há»£p lá»‡ hoáº·c cÃ²n giá»¯ nguyÃªn tiáº¿ng Anh.
        if not _looks_vietnamese(merged.get('instructions') or ''):
            merged['instructions'] = _translate_text_vi_with_gemini(
                recipe_payload.get('instructions') or '',
                text_type='instruction',
                source_context=f'recipe_id={source_recipe_id}' if source_recipe_id else None
            )

        if recipe_payload.get('summary') and not _looks_vietnamese(merged.get('summary') or ''):
            merged['summary'] = _translate_text_vi_with_gemini(
                recipe_payload.get('summary') or '',
                text_type='summary',
                source_context=f'recipe_id={source_recipe_id}' if source_recipe_id else None
            )

        if recipe_payload.get('title') and not _looks_vietnamese(merged.get('title') or ''):
            translated_title = _translate_text_vi_with_gemini(
                recipe_payload.get('title') or '',
                text_type='title',
                source_context=f'recipe_id={source_recipe_id}' if source_recipe_id else None
            )
            if _looks_vietnamese(translated_title):
                merged['title'] = translated_title

        ingredient_items = merged.get('ingredients') if isinstance(merged.get('ingredients'), list) else []
        if ingredient_items:
            translated_ings = []
            for item in ingredient_items:
                if not isinstance(item, dict):
                    translated_ings.append(item)
                    continue

                updated_item = dict(item)
                ingredient_name = updated_item.get('name')
                if isinstance(ingredient_name, str) and ingredient_name.strip():
                    updated_item['name'] = _translate_text_vi_with_gemini(
                        ingredient_name,
                        text_type='ingredient_name',
                        source_context=f'recipe_id={source_recipe_id}' if source_recipe_id else None
                    )

                ingredient_original = updated_item.get('original')
                if isinstance(ingredient_original, str) and ingredient_original.strip():
                    updated_item['original'] = _translate_text_vi_with_gemini(
                        ingredient_original,
                        text_type='ingredient_original',
                        source_context=f'recipe_id={source_recipe_id}' if source_recipe_id else None
                    )
                translated_ings.append(updated_item)
            merged['ingredients'] = translated_ings

        # BÆ¯á»šC 2: Cache successful translation if source_recipe_id provided (disabled - RecipeTranslation table removed)
        # if source_recipe_id:
        #     try:
        #         RecipeTranslation.objects.update_or_create(
        #             source_api='themealdb',
        #             source_recipe_id=str(source_recipe_id),
        #             defaults={
        #                 'original_title': recipe_payload.get('title') or '',
        #                 'translated_title': merged.get('title') or '',
        #                 'translated_payload': merged,
        #             }
        #         )
        #     except Exception:
        #         pass  # Cache save failed, but still return merged translation

        return merged
    except Exception:
        return recipe_payload


def _extract_json_array(text):
    """Tách JSON array từ text model trả về (có thể kèm markdown fences)."""
    if not text:
        return None

    raw = str(text).strip()
    if raw.startswith('```'):
        lines = raw.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        raw = '\n'.join(lines).strip()

    start_idx = raw.find('[')
    end_idx = raw.rfind(']')
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return None

    candidate = raw[start_idx:end_idx + 1]
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, list) else None
    except Exception:
        return None


def generate_ingredient_aliases_with_gemini(ingredient_name, max_aliases=10):
    if not ingredient_name or not AI_AVAILABLE:
        return []

    prompt = f"""Bạn là chuyên gia chuẩn hóa nguyên liệu nấu ăn.

Hãy đưa ra danh sách alias và tên đồng nghĩa phổ biến cho nguyên liệu sau.

Yêu cầu:
- Trả về một JSON object duy nhất.
- Không thêm lời giải thích hay văn bản khác.
- Trường `name` là tên chuẩn của nguyên liệu.
- Trường `aliases` là một array các alias / tên khác thường dùng.

Ví dụ:
{{
  "name": "cá hồi",
  "aliases": ["salmon", "cá hồi tươi", "cá hồi xông khói"]
}}

Nguyên liệu: "{ingredient_name}"
"""
    try:
        response_text = _gemini_generate_text(
            prompt,
            system_instruction='Bạn là chuyên gia ẩm thực, chỉ trả về JSON object.',
            max_output_tokens=512,
        )
        payload = _extract_json_object(response_text) or {}
        aliases = payload.get('aliases')
        if not isinstance(aliases, list):
            aliases = _extract_json_array(response_text) or []
        if not isinstance(aliases, list):
            return []

        normalized_aliases = []
        canonical_lower = ingredient_name.strip().lower()
        for alias in aliases:
            if not isinstance(alias, str):
                continue
            alias_text = alias.strip()
            if not alias_text:
                continue
            if alias_text.lower() == canonical_lower:
                continue
            if alias_text.lower() not in {a.lower() for a in normalized_aliases}:
                normalized_aliases.append(alias_text)
            if len(normalized_aliases) >= max_aliases:
                break

        return normalized_aliases
    except Exception:
        return []


def fetch_spoonacular_ingredient_search(query, number=5):
    if not SPOONACULAR_ENABLED:
        return None
    params = {
        'query': query,
        'number': number,
        'apiKey': SPOONACULAR_API_KEY,
    }
    last_exc = None
    for attempt in range(1, max(1, SPOONACULAR_RETRIES) + 1):
        try:
            response = requests.get(SPOONACULAR_INGREDIENT_SEARCH_URL, params=params, timeout=SPOONACULAR_TIMEOUT)
            if response.status_code != 200:
                _set_spoonacular_last_error(f'Spoonacular ingredient search failed: {response.status_code}')
                return None
            return response.json()
        except Exception as exc:
            last_exc = exc
            _set_spoonacular_last_error(f'Spoonacular ingredient search error (attempt {attempt}): {exc}')
            if attempt < SPOONACULAR_RETRIES:
                time.sleep(attempt * 1.5)
    return None


def fetch_spoonacular_ingredient_info(ingredient_id):
    if not SPOONACULAR_ENABLED:
        return None
    url = SPOONACULAR_INGREDIENT_INFO_URL_TEMPLATE.format(id=ingredient_id)
    last_exc = None
    for attempt in range(1, max(1, SPOONACULAR_RETRIES) + 1):
        try:
            response = requests.get(url, params={'apiKey': SPOONACULAR_API_KEY}, timeout=SPOONACULAR_TIMEOUT)
            if response.status_code != 200:
                _set_spoonacular_last_error(f'Spoonacular ingredient info failed: {response.status_code}')
                return None
            return response.json()
        except Exception as exc:
            last_exc = exc
            _set_spoonacular_last_error(f'Spoonacular ingredient info error (attempt {attempt}): {exc}')
            if attempt < SPOONACULAR_RETRIES:
                time.sleep(attempt * 1.5)
    return None


def fetch_spoonacular_ingredient_by_name(ingredient_name):
    search_payload = fetch_spoonacular_ingredient_search(ingredient_name)
    if not search_payload:
        return None
    results = search_payload.get('results') or []
    if not isinstance(results, list) or not results:
        return None
    first = results[0]
    ingredient_id = first.get('id')
    if not ingredient_id:
        return None
    return fetch_spoonacular_ingredient_info(ingredient_id)


def _parse_spoonacular_ingredient_payload(payload):
    if not isinstance(payload, dict):
        return None

    nutrition = payload.get('nutrition') or {}
    nutrients = nutrition.get('nutrients') or []

    def _find_nutrient(nutrient_name):
        for item in nutrients:
            name = str(item.get('name') or '').strip().lower()
            if name == nutrient_name.lower():
                return item.get('amount')
        return None

    result = {
        'name': payload.get('name') or payload.get('nameClean'),
        'calories': _find_nutrient('Calories'),
        'protein': _find_nutrient('Protein'),
        'carbs': _find_nutrient('Carbohydrates'),
        'fat': _find_nutrient('Fat'),
        'fiber': _find_nutrient('Fiber'),
        'sugar': _find_nutrient('Sugar'),
        'sodium': _find_nutrient('Sodium'),
        'cholesterol': _find_nutrient('Cholesterol'),
        'vitamin_a': _find_nutrient('Vitamin A'),
        'vitamin_c': _find_nutrient('Vitamin C'),
        'calcium': _find_nutrient('Calcium'),
        'iron': _find_nutrient('Iron'),
        'serving_size': None,
        'image': payload.get('image'),
        'aisle': payload.get('aisle'),
    }

    amount = payload.get('amount')
    unit = payload.get('unit')
    if amount and unit:
        result['serving_size'] = f'{amount}{unit}'

    return result


def fetch_spoonacular_ingredient_info_by_name(ingredient_name):
    payload = fetch_spoonacular_ingredient_by_name(ingredient_name)
    if not payload:
        return None
    return payload


def _extract_spoonacular_nutrient(nutrition_data, nutrient_name):
    """Láº¥y giÃ¡ trá»‹ dinh dÆ°á»¡ng tá»« payload Spoonacular theo tÃªn nutrient."""
    if not nutrition_data:
        return None

    if isinstance(nutrition_data, dict):
        if nutrient_name in nutrition_data:
            return nutrition_data.get(nutrient_name)

        nutrients = nutrition_data.get('nutrients')
        if isinstance(nutrients, list):
            for nutrient in nutrients:
                if str(nutrient.get('name', '')).strip().lower() == nutrient_name.lower():
                    return nutrient.get('amount')

    return None


def _normalize_spoonacular_food_payload(raw_data, fallback_name=None):
    """Chuáº©n hÃ³a payload Spoonacular Ä‘á»ƒ parse/save dÃ¹ng chung cho food search vÃ  ingredient info."""
    if not isinstance(raw_data, dict):
        return None

    food_name = (raw_data.get('name') or raw_data.get('title') or fallback_name or '').strip()
    if not food_name:
        return None

    nutrition = raw_data.get('nutrition') or {}
    normalized_nutrition = {
        'calories': _extract_spoonacular_nutrient(nutrition, 'calories'),
        'protein': _extract_spoonacular_nutrient(nutrition, 'protein'),
        'carbohydrates': _extract_spoonacular_nutrient(nutrition, 'carbohydrates'),
        'fat': _extract_spoonacular_nutrient(nutrition, 'fat'),
        'fiber': _extract_spoonacular_nutrient(nutrition, 'fiber'),
    }

    return {
        'name': food_name,
        'type': (raw_data.get('type') or raw_data.get('aisle') or '').strip(),
        'image': raw_data.get('image') or raw_data.get('image_url') or None,
        'aisle': raw_data.get('aisle') or raw_data.get('category') or '',
        'nutrition': normalized_nutrition,
        'source_name': raw_data.get('source_name') or raw_data.get('sourceName') or 'Spoonacular',
        'recipe_payload': raw_data.get('recipe_payload') if isinstance(raw_data.get('recipe_payload'), dict) else None,
    }


def _normalize_mealdb_recipe_payload(raw_data):
    """Chuáº©n hÃ³a payload recipe tá»« TheMealDB Ä‘á»ƒ lÆ°u vÃ o báº£ng Recipe."""
    if not isinstance(raw_data, dict):
        return None

    title = (raw_data.get('strMeal') or '').strip()
    if not title:
        return None

    ingredients = []
    for idx in range(1, 21):
        ingredient_name = (raw_data.get(f'strIngredient{idx}') or '').strip()
        if not ingredient_name:
            continue
        measure = (raw_data.get(f'strMeasure{idx}') or '').strip()
        ingredients.append({
            'name': ingredient_name,
            'measure': measure,
            'original': f'{measure} {ingredient_name}'.strip(),
        })

    normalized = {
        'external_id': int(raw_data['idMeal']) if raw_data.get('idMeal') and str(raw_data.get('idMeal')).isdigit() else None,
        'title': title,
        'summary': (raw_data.get('strCategory') or '') + (f" - {raw_data.get('strArea')}" if raw_data.get('strArea') else ''),
        'source_url': raw_data.get('strSource') or raw_data.get('strYoutube') or None,
        'image_url': raw_data.get('strMealThumb') or None,
        'ready_in_minutes': None,
        'servings': None,
        'instructions': (raw_data.get('strInstructions') or '').strip() or None,
        'ingredients': ingredients or None,
        'analyzed_instructions': None,
        'nutrition': None,
        'source_name': 'TheMealDB',
    }

    return _translate_mealdb_recipe_payload_vi(normalized)


def _normalize_food_payload_from_mealdb(raw_data, fallback_name=None):
    """Chuyá»ƒn dá»¯ liá»‡u TheMealDB thÃ nh payload food Ä‘á»ƒ cache vÃ o báº£ng foods."""
    recipe_payload = _normalize_mealdb_recipe_payload(raw_data)
    if not recipe_payload:
        return None

    return {
        'name': recipe_payload.get('title') or fallback_name,
        'type': (raw_data.get('strCategory') or 'Meal').strip(),
        'image': raw_data.get('strMealThumb') or None,
        'aisle': raw_data.get('strArea') or 'Recipe',
        'nutrition': {
            # TheMealDB khÃ´ng cung cáº¥p macro máº·c Ä‘á»‹nh
            'calories': None,
            'protein': None,
            'carbohydrates': None,
            'fat': None,
            'fiber': None,
        },
        'source_name': 'TheMealDB',
        'recipe_payload': recipe_payload,
    }


def _normalize_food_payload_from_recipe(recipe_data, fallback_name=None):
    """Chuyá»ƒn payload recipe thÃ nh payload Food Ä‘á»ƒ cÃ³ thá»ƒ cache vÃ o báº£ng foods."""
    if not isinstance(recipe_data, dict):
        return None

    title = (recipe_data.get('title') or fallback_name or '').strip()
    if not title:
        return None

    nutrition_data = recipe_data.get('nutrition') or {}
    normalized_nutrition = {
        'calories': _extract_spoonacular_nutrient(nutrition_data, 'calories'),
        'protein': _extract_spoonacular_nutrient(nutrition_data, 'protein'),
        'carbohydrates': _extract_spoonacular_nutrient(nutrition_data, 'carbohydrates'),
        'fat': _extract_spoonacular_nutrient(nutrition_data, 'fat'),
        'fiber': _extract_spoonacular_nutrient(nutrition_data, 'fiber'),
    }

    if not any(normalized_nutrition.values()):
        return None

    return {
        'name': title,
        'type': 'recipe',
        'image': recipe_data.get('image_url') or recipe_data.get('image') or None,
        'aisle': 'Recipe',
        'nutrition': normalized_nutrition,
    }


def _normalize_spoonacular_recipe_payload(raw_data, fallback_name=None):
    """Chuáº©n hÃ³a payload recipe tá»« Spoonacular Ä‘á»ƒ cache vÃ o CSDL."""
    if not isinstance(raw_data, dict):
        return None

    title = (raw_data.get('title') or fallback_name or '').strip()
    if not title:
        return None

    ingredients = []
    for ingredient in raw_data.get('extendedIngredients') or []:
        if not isinstance(ingredient, dict):
            continue
        ingredients.append({
            'id': ingredient.get('id'),
            'name': ingredient.get('name') or ingredient.get('originalName') or '',
            'original_name': ingredient.get('originalName') or '',
            'amount': ingredient.get('amount'),
            'unit': ingredient.get('unit') or '',
            'aisle': ingredient.get('aisle') or '',
            'image': ingredient.get('image') or '',
            'original': ingredient.get('original') or '',
        })

    steps = []
    for section in raw_data.get('analyzedInstructions') or []:
        if not isinstance(section, dict):
            continue
        for step in section.get('steps') or []:
            if not isinstance(step, dict):
                continue
            steps.append({
                'number': step.get('number'),
                'step': step.get('step') or '',
                'ingredients': [
                    {
                        'id': item.get('id'),
                        'name': item.get('name') or '',
                        'image': item.get('image') or '',
                    }
                    for item in (step.get('ingredients') or [])
                    if isinstance(item, dict)
                ],
                'equipment': [
                    {
                        'id': item.get('id'),
                        'name': item.get('name') or '',
                        'image': item.get('image') or '',
                    }
                    for item in (step.get('equipment') or [])
                    if isinstance(item, dict)
                ],
            })

    nutrition = raw_data.get('nutrition') or {}

    return {
        'external_id': raw_data.get('id'),
        'title': title,
        'summary': raw_data.get('summary') or '',
        'source_url': raw_data.get('sourceUrl') or raw_data.get('spoonacularSourceUrl') or None,
        'image_url': raw_data.get('image') or raw_data.get('image_url') or None,
        'ready_in_minutes': raw_data.get('readyInMinutes'),
        'servings': raw_data.get('servings'),
        'instructions': raw_data.get('instructions') or '',
        'ingredients': ingredients,
        'analyzed_instructions': raw_data.get('analyzedInstructions') or steps,
        'nutrition': nutrition,
        'source_name': raw_data.get('sourceName') or 'Spoonacular',
    }


def call_gemini_with_debug(chat_session, system_context):
    """
    Gá»i Gemini API Ä‘á»ƒ generate response cho chat session.
    
    Luá»“ng:
    1. Check AI_AVAILABLE + client ready
    2. Query táº¥t cáº£ ChatMessage trong session (ordered by created_at)
    3. Convert messages thÃ nh genai.Content format (role: 'user' hoáº·c 'model')
    4. Call _gemini_client.models.generate_content() vá»›i:
       - system_instruction: Context Ä‘áº·c biá»‡t cho domain (nutrition, health)
       - max_output_tokens: 8192 tokens (~3k words)
    5. Return (text_response, None) náº¿u thÃ nh cÃ´ng
    6. Return (None, error_dict) náº¿u lá»—i (Ä‘á»ƒ graceful fallback)
    
    Tham sá»‘:
    - chat_session: ChatSession object (query messages tá»« session nÃ y)
    - system_context: String instruction cho AI (vÃ­ dá»¥: "You are a nutrition expert")
    
    Tráº£ vá»:
    - (response_text, None): ThÃ nh cÃ´ng
    - (None, error_dict): Lá»—i {'error': ERROR_TYPE, 'msg': error_message}
    
    GHI NHá»š QUAN TRá»ŒNG:
    - Conversation history Ä‘Æ°á»£c build tá»« database (cÃ³ thá»ƒ long)
    - system_instruction Ä‘Æ°á»£c pass Ä‘á»ƒ guide AI behavior
    - max_output_tokens=8192 lÃ  safe limit (avoid overly long responses)
    - Táº¥t cáº£ exception Ä‘Æ°á»£c catch (ValueError, timeout, etc)
    - error_dict Ä‘Æ°á»£c tráº£ vá» Ä‘á»ƒ caller cÃ³ thá»ƒ handle (retry, fallback, v.v.)
    
    VÃ­ dá»¥ error dict:
    {'error': 'AI_UNAVAILABLE', 'msg': 'AI client khÃ´ng sáºµn sÃ ng'}
    {'error': 'INVALID_REQUEST', 'msg': 'Invalid system instruction'}
    {'error': 'AuthenticationError', 'msg': 'Invalid API key'}
    """
    try:
        if not AI_AVAILABLE:
            return None, {'error': 'AI_UNAVAILABLE', 'msg': 'AI client khong san sang'}

        all_messages = ChatMessage.objects.filter(session=chat_session).order_by('created_at')
        history_lines = []
        for msg in all_messages:
            prefix = 'Tro ly' if msg.role == 'assistant' else 'Nguoi dung'
            history_lines.append(f'{prefix}: {msg.content}')

        recent_history = '\n'.join(history_lines[-10:])
        current_question = ''
        for msg in reversed(list(all_messages)):
            if getattr(msg, 'role', '') == 'user' and (getattr(msg, 'content', '') or '').strip():
                current_question = (msg.content or '').strip()
                break

        prompt = (
            f'{recent_history}\n'
            f'Cau hoi hien tai cua nguoi dung: {current_question or "Khong co noi dung hoi truoc do."}'
        ).strip()
        response_text = _gemini_generate_text(
            prompt,
            system_instruction=system_context,
            max_output_tokens=8192,
        )
        return response_text or 'Khong co cau tra loi.', None
    except ValueError as exc:
        # Validation error (invalid input format, etc)
        return None, {'error': 'INVALID_REQUEST', 'msg': str(exc)[:200]}
    except Exception as exc:
        # Catch-all (timeout, auth error, server error, etc)
        return None, {'error': type(exc).__name__, 'msg': str(exc)[:200]}


# ============================================================================
# PHáº¦N 3: SPOONACULAR FOOD API INTEGRATION
# ============================================================================

def fetch_spoonacular_food(food_name):
    """
    Gá»i Spoonacular API Ä‘á»ƒ tÃ¬m kiáº¿m thá»±c pháº©m + láº¥y nutrition info.
    
    Luá»“ng:
    1. Kiá»ƒm tra API key cÃ³ Ä‘Æ°á»£c set
    2. Build query: food_name + number=1 (chá»‰ láº¥y top result)
    3. Call API vá»›i timeout=SPOONACULAR_TIMEOUTs (trÃ¡nh hang)
    4. Parse JSON response â†’ láº¥y results[0] (first match)
    5. Return API payload (chÆ°a save vÃ o DB)
    
    Tham sá»‘:
    - food_name: TÃªn thá»±c pháº©m cáº§n tÃ¬m (vÃ­ dá»¥: "chicken breast")
    
    Tráº£ vá»:
    - dict: API payload chá»©a name, nutrition, image, type, etc.
    - None: Náº¿u API key missing, request fail, hoáº·c no results
    
    GHI NHá»š QUAN TRá»ŒNG:
    - Chá»‰ tráº£ vá» raw API data, chÆ°a convert sang Food model
    - NÃªn dÃ¹ng parse_and_save_spoonacular_food() sau Ä‘á»ƒ cache result
    - Timeout=5s Ä‘á»ƒ trÃ¡nh slow API calls block request
    - Táº¥t cáº£ exception (timeout, JSON parse, etc) return None (safe)
    - API key tá»« environment, nÃªn verify á»Ÿ startup
    
    VÃ­ dá»¥ API response:
    {
        'name': 'Chicken Breast',
        'type': 'meat',
        'nutrition': {
            'calories': 165,
            'protein': 31,
            'carbohydrates': 0,
            'fat': 3.6,
            'fiber': 0
        },
        'image': 'https://...',
        'aisle': 'Meat'
    }
    """
    if not SPOONACULAR_API_KEY:
        _set_spoonacular_last_error('SPOONACULAR_API_KEY chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh')
        return None

    params = {
        'query': food_name,
        'number': 1,  # Chá»‰ láº¥y top result
        'apiKey': SPOONACULAR_API_KEY,
    }

    try:
        response = requests.get(SPOONACULAR_SEARCH_URL, params=params, timeout=SPOONACULAR_TIMEOUT)
        if response.status_code != 200:
            if response.status_code == 402:
                _set_spoonacular_last_error('Spoonacular quota exceeded for today')
            else:
                _set_spoonacular_last_error(f'Spoonacular lá»—i HTTP {response.status_code}')
            ingredient_fallback = fetch_spoonacular_ingredient_food(food_name)
            if ingredient_fallback:
                return ingredient_fallback

            recipe_fallback = fetch_spoonacular_recipe(food_name)
            recipe_based_food = _normalize_food_payload_from_recipe(recipe_fallback, fallback_name=food_name)
            if recipe_based_food:
                return recipe_based_food
            return fetch_mealdb_food(food_name)

        data = response.json()
        results = data.get('results') if isinstance(data, dict) else None
        if not results:
            ingredient_fallback = fetch_spoonacular_ingredient_food(food_name)
            if ingredient_fallback:
                return ingredient_fallback

            recipe_fallback = fetch_spoonacular_recipe(food_name)
            recipe_based_food = _normalize_food_payload_from_recipe(recipe_fallback, fallback_name=food_name)
            if recipe_based_food:
                return recipe_based_food
            return fetch_mealdb_food(food_name)

        normalized = _normalize_spoonacular_food_payload(results[0], fallback_name=food_name)
        if normalized and any(normalized['nutrition'].values()):
            _clear_spoonacular_last_error()
            return normalized

        ingredient_fallback = fetch_spoonacular_ingredient_food(food_name)
        if ingredient_fallback:
            return ingredient_fallback

        recipe_fallback = fetch_spoonacular_recipe(food_name)
        recipe_based_food = _normalize_food_payload_from_recipe(recipe_fallback, fallback_name=food_name)
        if recipe_based_food:
            return recipe_based_food
        return fetch_mealdb_food(food_name)
    except Exception:
        # Timeout, JSON parse error, connection error, etc
        _set_spoonacular_last_error('KhÃ´ng thá»ƒ káº¿t ná»‘i Spoonacular, vui lÃ²ng thá»­ láº¡i sau')
        ingredient_fallback = fetch_spoonacular_ingredient_food(food_name)
        if ingredient_fallback:
            return ingredient_fallback

        recipe_fallback = fetch_spoonacular_recipe(food_name)
        recipe_based_food = _normalize_food_payload_from_recipe(recipe_fallback, fallback_name=food_name)
        if recipe_based_food:
            return recipe_based_food
        return fetch_mealdb_food(food_name)


def fetch_mealdb_food(food_name):
    """Fallback tá»« TheMealDB: tÃ¬m theo tÃªn rá»“i lookup chi tiáº¿t theo idMeal."""
    query = (food_name or '').strip()
    if not query:
        return None

    try:
        search_res = requests.get(THEMEALDB_SEARCH_URL, params={'s': query}, timeout=7)
        if search_res.status_code != 200:
            return None

        search_data = search_res.json() if search_res.content else {}
        meals = search_data.get('meals') if isinstance(search_data, dict) else None
        if not meals:
            return None

        first_meal = meals[0] or {}
        meal_id = first_meal.get('idMeal')

        detailed_meal = first_meal
        if meal_id:
            detail_res = requests.get(THEMEALDB_LOOKUP_URL, params={'i': meal_id}, timeout=7)
            if detail_res.status_code == 200:
                detail_data = detail_res.json() if detail_res.content else {}
                detail_meals = detail_data.get('meals') if isinstance(detail_data, dict) else None
                if detail_meals:
                    detailed_meal = detail_meals[0] or first_meal

        normalized = _normalize_food_payload_from_mealdb(detailed_meal, fallback_name=query)
        if normalized:
            _clear_spoonacular_last_error()
        return normalized
    except Exception:
        return None


def fetch_spoonacular_ingredient_food(food_name):
    """Fallback tra cá»©u nguyÃªn liá»‡u Ä‘á»ƒ láº¥y nutrition chi tiáº¿t khi search food khÃ´ng Ä‘á»§ dá»¯ liá»‡u."""
    if not SPOONACULAR_API_KEY:
        _set_spoonacular_last_error('SPOONACULAR_API_KEY chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh')
        return None

    search_params = {
        'query': food_name,
        'number': 1,
        'apiKey': SPOONACULAR_API_KEY,
    }

    try:
        search_response = requests.get(SPOONACULAR_INGREDIENT_SEARCH_URL, params=search_params, timeout=SPOONACULAR_TIMEOUT)
        if search_response.status_code != 200:
            if search_response.status_code == 402:
                _set_spoonacular_last_error('Spoonacular quota exceeded for today')
            return None

        search_data = search_response.json()
        results = search_data.get('results') if isinstance(search_data, dict) else None
        if not results:
            return None

        ingredient = results[0] or {}
        ingredient_id = ingredient.get('id')
        if not ingredient_id:
            return None

        info_url = SPOONACULAR_INGREDIENT_INFO_URL_TEMPLATE.format(id=ingredient_id)
        info_params = {
            'amount': 100,
            'unit': 'g',
            'apiKey': SPOONACULAR_API_KEY,
        }
        info_response = requests.get(info_url, params=info_params, timeout=SPOONACULAR_TIMEOUT)
        if info_response.status_code != 200:
            return None

        info_data = info_response.json()
        normalized = _normalize_spoonacular_food_payload(info_data, fallback_name=ingredient.get('name') or food_name)
        if normalized:
            _clear_spoonacular_last_error()
            return normalized
        return None
    except Exception:
        _set_spoonacular_last_error('KhÃ´ng thá»ƒ káº¿t ná»‘i Spoonacular, vui lÃ²ng thá»­ láº¡i sau')
        return None


def fetch_spoonacular_recipe(food_name):
    """Gá»i Spoonacular recipe search + recipe information Ä‘á»ƒ láº¥y cÃ´ng thá»©c náº¥u Äƒn."""
    if not SPOONACULAR_API_KEY:
        _set_spoonacular_last_error('SPOONACULAR_API_KEY chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh')
        return None

    params = {
        'query': food_name,
        'number': 1,
        'addRecipeInformation': 'true',
        'fillIngredients': 'true',
        'instructionsRequired': 'true',
        'apiKey': SPOONACULAR_API_KEY,
    }

    try:
        response = requests.get(SPOONACULAR_COMPLEX_SEARCH_URL, params=params, timeout=7)
        if response.status_code != 200:
            if response.status_code == 402:
                _set_spoonacular_last_error('Spoonacular quota exceeded for today')
            return None

        data = response.json()
        results = data.get('results') if isinstance(data, dict) else None
        if not results:
            return None

        top_result = results[0] or {}
        recipe_id = top_result.get('id')
        if not recipe_id:
            return _normalize_spoonacular_recipe_payload(top_result, fallback_name=food_name)

        info_url = SPOONACULAR_RECIPE_INFO_URL_TEMPLATE.format(id=recipe_id)
        info_params = {
            'includeNutrition': 'true',
            'apiKey': SPOONACULAR_API_KEY,
        }
        info_response = requests.get(info_url, params=info_params, timeout=7)
        if info_response.status_code != 200:
            return _normalize_spoonacular_recipe_payload(top_result, fallback_name=food_name)

        info_data = info_response.json()
        normalized = _normalize_spoonacular_recipe_payload(info_data, fallback_name=food_name)
        if normalized:
            _clear_spoonacular_last_error()
            return normalized

        return _normalize_spoonacular_recipe_payload(top_result, fallback_name=food_name)
    except Exception:
        _set_spoonacular_last_error('KhÃ´ng thá»ƒ káº¿t ná»‘i Spoonacular, vui lÃ²ng thá»­ láº¡i sau')
        return None


def parse_and_save_spoonacular_recipe(food, api_data):
    """Parse payload recipe vÃ  cache vÃ o báº£ng Recipe cho má»™t Food cá»¥ thá»ƒ."""
    try:
        if not food or not api_data:
            return None

        normalized_data = _normalize_spoonacular_recipe_payload(api_data, fallback_name=getattr(food, 'name', None))
        if not normalized_data:
            return None

        instructions = normalized_data.get('instructions') or normalized_data.get('summary') or 'Chưa có hướng dẫn.'
        defaults = {
            'title': normalized_data.get('title') or food.name,
            'instructions': instructions,
        }

        recipe, _ = Recipe.objects.update_or_create(food=food, defaults=defaults)
        return recipe
    except Exception:
        return None


def parse_and_save_recipe_payload(food, recipe_payload):
    """LÆ°u recipe payload Ä‘Ã£ chuáº©n hÃ³a (Spoonacular hoáº·c TheMealDB) vÃ o báº£ng Recipe."""
    try:
        if not food or not isinstance(recipe_payload, dict):
            return None

        defaults = {
            'title': recipe_payload.get('title') or food.name,
            'instructions': recipe_payload.get('instructions') or recipe_payload.get('summary') or 'Chưa có hướng dẫn.',
        }
        recipe, _ = Recipe.objects.update_or_create(food=food, defaults=defaults)
        return recipe
    except Exception:
        return None


def ensure_recipe_for_food(food, query_name=None):
    """Tá»± Ä‘á»™ng fetch + cache recipe náº¿u food chÆ°a cÃ³ cÃ´ng thá»©c trong CSDL."""
    try:
        if not food:
            return None

        existing = Recipe.objects.filter(food=food).first()
        if existing:
            return existing

        recipe_query = query_name or food.name
        recipe_data = fetch_spoonacular_recipe(recipe_query)
        if not recipe_data and query_name and query_name != food.name:
            recipe_data = fetch_spoonacular_recipe(food.name)

        if not recipe_data:
            return None

        return parse_and_save_spoonacular_recipe(food, recipe_data)
    except Exception:
        return None


def parse_and_save_spoonacular_food(api_data):
    """
Parse dữ liệu từ Spoonacular API và cache vào bảng Food.

Luồng xử lý:
1. Lấy food_name từ api_data
2. Kiểm tra Food đã tồn tại hay chưa (theo name, không phân biệt hoa thường)
3. Nếu đã tồn tại thì return Food hiện có để tránh duplicate
4. Parse các trường dinh dưỡng từ api_data['nutrition']
5. Tạo Food record với:
   - name, category, calories, protein, carbs, fat, fiber
   - image_url, serving_size='100g'
   - description: ghi chú nguồn dữ liệu từ Spoonacular
6. Return Food vừa tạo

Tham số:
- api_data: Dict được trả về từ fetch_spoonacular_food()

Trả về:
- Food object: Food mới tạo hoặc đã tồn tại
- None: Nếu api_data không hợp lệ hoặc parse thất bại

GHI NHỚ QUAN TRỌNG:
- Chuyển calories/protein/carbs/fat sang Decimal để tránh lỗi sai số float
- serving_size='100g' được dùng làm mặc định nếu API không trả về khẩu phần
- description lưu thông tin nguồn để debug và audit
- Cache strategy: mỗi món ăn chỉ lưu 1 lần, các lần sau sẽ dùng dữ liệu đã cache
- Sử dụng iexact để lookup không phân biệt hoa thường
  Ví dụ: "Chicken" = "chicken"

Ví dụ luồng hoạt động:
1. User tìm "cà chua"
2. get_or_fetch_food() gọi Spoonacular API
3. parse_and_save_spoonacular_food() lưu kết quả vào bảng Food
4. User tìm "cà chua" lần nữa → lấy trực tiếp từ database, không gọi API
    """
    
    try:
        normalized_data = _normalize_spoonacular_food_payload(api_data)
        if not normalized_data:
            return None

        food_name = normalized_data.get('name', '').strip()
        if not food_name:
            return None

        # Check if already cached
        existing = Food.objects.filter(name__iexact=food_name).first()
        if existing:
            return existing

        # Parse nutrition data
        nutrition = normalized_data.get('nutrition', {})
        calories = nutrition.get('calories')
        protein = nutrition.get('protein')
        carbs = nutrition.get('carbohydrates')
        fat = nutrition.get('fat')
        fiber = nutrition.get('fiber')

        source_name = normalized_data.get('source_name') or 'Spoonacular'
        recipe_payload = normalized_data.get('recipe_payload') if isinstance(normalized_data.get('recipe_payload'), dict) else None

        # Create + save Food record
        category_name = (normalized_data.get('type') or '').strip()
        category_obj = None
        if category_name:
            category_obj, _ = FoodCategory.objects.get_or_create(name=category_name)

        food = Food.objects.create(
            name=food_name,
            category=category_obj,
            total_calories=Decimal(str(calories)) if calories is not None else Decimal('0'),
            total_protein=Decimal(str(protein)) if protein is not None else Decimal('0'),
            total_carbs=Decimal(str(carbs)) if carbs is not None else Decimal('0'),
            total_fat=Decimal(str(fat)) if fat is not None else Decimal('0'),
        )

        if recipe_payload:
            parse_and_save_recipe_payload(food, recipe_payload)
        else:
            ensure_recipe_for_food(food, query_name=food_name)

        return food
    except Exception:
        return None


# ============================================================================


# ============================================================================
# PHaN 4: CHAT RESPONSE CACHING (Gemini)
# ============================================================================

def get_or_create_chat_response_from_cache(account, user_query, source_intent=None):
    """
    Get cached chat response for similar queries with intent-aware matching.
    
    Chiến lược:
    1. Tìm cache trong nhóm intent tương tự (nếu có source_intent)
    2. Tính Jaccard similarity >= 0.85 (tăng từ 0.75 để đảm bảo chính xác)
    3. Kiểm tra các từ khóa quan trọng (protein, calo, giảm cân, ...)
    4. Fallback sang general cache nếu không tìm thấy intent-specific
    5. Trả về response với similarity metadata
    """
    try:
        from app.services.chat_text_service import tokenize_chat_text
        from apps.chat.models import ChatResponseCache
        from app.services.similarity_service import compute_smart_similarity
        
        normalized_query = " ".join(tokenize_chat_text(user_query))
        if not normalized_query:
            return None
        
        best_match = None
        best_similarity = 0.0
        
        # Lấy các cache gần đây (giới hạn số lượng để đảm bảo hiệu năng)
        # Ưu tiên các cache có cùng intent trước
        entries = []
        if source_intent:
            entries = list(ChatResponseCache.objects.filter(intent_name=source_intent).order_by("-created_at")[:30])
        
        # Nếu chưa đủ 30 entries, lấy thêm từ general cache
        if len(entries) < 30:
            general_limit = 30 - len(entries)
            general_entries = ChatResponseCache.objects.exclude(intent_name=source_intent) if source_intent else ChatResponseCache.objects.all()
            entries.extend(list(general_entries.order_by("-created_at")[:general_limit]))

        for entry in entries:
            # Sử dụng thuật toán thông minh hơn thay vì chỉ Jaccard cơ bản
            similarity = compute_smart_similarity(
                user_query, 
                entry.original_query, 
                source_intent_a=source_intent, 
                source_intent_b=entry.intent_name
            )
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = entry
        
        # Ngưỡng thông minh: 0.82 (cao hơn 0.75 cũ nhưng linh hoạt hơn do thuật toán mới)
        if best_match and best_similarity >= 0.90:
            requested_intent = (source_intent or '').strip().lower()
            cached_intent = (best_match.intent_name or '').strip().lower()
            if requested_intent and cached_intent and requested_intent != cached_intent:
                return None
            if not _is_cacheable_chat_response(best_match.response):
                best_match.delete()
                return None

            best_match.usage_count += 1
            best_match.save(update_fields=["usage_count"])
            
            return {
                "response": best_match.response,
                "similarity": best_similarity,
                "cached_at": best_match.created_at,
                "intent_name": best_match.intent_name,
            }
        
        return None
    except Exception:
        return None


def save_chat_response_to_cache(account, user_query, gemini_response, source_intent=None):
    """
    Save Gemini response to ChatResponseCache for reuse on similar queries.
    
    Cải thiện:
    - Lưu intent_name để cache được sắp xếp theo intent
    - Hỗ trợ intent-aware matching khi retrieve
    """
    try:
        from app.services.chat_text_service import tokenize_chat_text
        from apps.chat.models import ChatResponseCache

        if not _is_cacheable_chat_response(gemini_response):
            return None
        
        normalized_query = " ".join(tokenize_chat_text(user_query))
        if not normalized_query:
            return None
        
        cache_entry, created = ChatResponseCache.objects.update_or_create(
            normalized_query=normalized_query,
            defaults={
                "original_query": user_query,
                "response": gemini_response,
                "intent_name": source_intent,  # Lưu intent để grouping cache
                "usage_count": 0,
            }
        )
        
        return cache_entry if created else None
    except Exception:
        return None
