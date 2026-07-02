"""LLM tool-use orchestrator: send request with tools, loop on function calls."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from django.db.models import Q

logger = logging.getLogger(__name__)

try:
    from apps.chat.models import ChatMessage
except Exception:
    ChatMessage = None

try:
    from app.services.tool_registry import execute_tool, get_tools_schema
except Exception:
    execute_tool = None
    get_tools_schema = None

try:
    from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL
except Exception:
    GEMINI_API_KEY = GEMINI_MODEL = GEMINI_BASE_URL = None

try:
    from app.services.external_apis import _ollama_qwen_generate_with_tools
except Exception:
    _ollama_qwen_generate_with_tools = None

try:
    from app.services.tool_converter import gemini_tools_to_openai, parse_tool_call_from_message
except Exception:
    gemini_tools_to_openai = None
    parse_tool_call_from_message = None

try:
    import requests
except Exception:
    requests = None

_GEMINI_DEFAULT_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta'


def call_llm_with_tools(chat_session, user_text, tools_schema, system_instruction=None, max_tool_rounds=3):
    if not execute_tool or not get_tools_schema:
        raise RuntimeError('Tool registry not available')
    if not GEMINI_API_KEY or not requests:
        raise RuntimeError('AI client not configured')

    all_messages = ChatMessage.objects.filter(session=chat_session).order_by('created_at')
    recent_history = []
    for msg in all_messages:
        role = 'user' if msg.role == 'user' else 'model'
        recent_history.append({'role': role, 'parts': [{'text': msg.content}]})
    if len(recent_history) > 20:
        recent_history = recent_history[-20:]

    current_question = ''
    for msg in reversed(list(all_messages)):
        if getattr(msg, 'role', '') == 'user' and (getattr(msg, 'content', '') or '').strip():
            current_question = (msg.content or '').strip()
            break

    final_system = (
        'Ban la "Nội Trợ AI", tro ly am thuc thong minh cho nguoi Viet. '
        'Ban duoc phep su dung cac cong tu du lieu de tra loi cau hoi cua nguoi dung. '
        'Tra loi bang tieng Viet, ngan gon. '
        'Khong hien thi thong so ky thuat nhu confidence hay query_sim. '
        'Neu can thong tin, hay goi cong cu phu hop truoc khi tra loi.'
    )
    if system_instruction:
        final_system = f"{final_system}\n{system_instruction}"

    contents = []
    if recent_history:
        contents.extend(recent_history[:-1])
    if current_question:
        contents.append({'role': 'user', 'parts': [{'text': current_question}]})

    endpoint_base = (GEMINI_BASE_URL or _GEMINI_DEFAULT_BASE_URL).rstrip('/')
    endpoint = f"{endpoint_base}/models/{GEMINI_MODEL}:generateContent"
    payload = {
        'contents': contents,
        'tools': tools_schema,
        'generationConfig': {
            'temperature': 0.0,
            'maxOutputTokens': 4096,
        },
    }
    if final_system:
        payload['systemInstruction'] = {'parts': [{'text': final_system}]}

    for rnd in range(max_tool_rounds):
        try:
            response = requests.post(
                endpoint,
                params={'key': GEMINI_API_KEY},
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            response_data = response.json()
        except Exception as exc:
            logger.exception('Tool-use LLM request failed round %s: %s', rnd, exc)
            raise RuntimeError(f'Loi goi AI (round {rnd+1}): {exc}') from exc

        candidates = response_data.get('candidates') or []
        if not candidates:
            return 'Khong co phan hoi tu AI.'

        candidate = candidates[0]
        content = candidate.get('content') or {}
        parts = content.get('parts') or []

        function_calls = [part.get('functionCall') for part in parts if part.get('functionCall')]

        if not function_calls:
            text = ''
            for part in parts:
                text = str(part.get('text') or '').strip()
                if text:
                    break
            if not text:
                text = str(response_data.get('text') or '').strip()
            if not text:
                raise RuntimeError('Dich vu AI khong tra ve noi dung')
            return text

        tool_results_texts = []
        for fc in function_calls:
            tool_name = fc.get('name', '')
            tool_args = fc.get('args', {}) or {}
            result = execute_tool(tool_name, tool_args)
            result_str = json.dumps(result, ensure_ascii=False, default=str)
            tool_results_texts.append(f"Ket qua cong cu {tool_name}:\n{result_str}")

        contents.append(candidate.get('content'))
        contents.append({
            'role': 'user',
            'parts': [{'text': '\n'.join(tool_results_texts)}],
        })
        payload['contents'] = contents

    return 'Da dat gioi han so vong goi cong cu.'


def call_llm_with_tools_qwen(chat_session, user_text, tools_schema, system_instruction=None, max_tool_rounds=3):
    if not execute_tool or not get_tools_schema:
        raise RuntimeError('Tool registry not available')
    if not parse_tool_call_from_message or not gemini_tools_to_openai:
        raise RuntimeError('Tool converter not available')

    all_messages = ChatMessage.objects.filter(session=chat_session).order_by('created_at')
    messages = []
    for msg in all_messages:
        role = 'user' if msg.role == 'user' else 'assistant'
        content = (msg.content or '').strip()
        if content:
            messages.append({'role': role, 'content': content})

    if user_text and str(user_text).strip():
        messages.append({'role': 'user', 'content': str(user_text).strip()})

    openai_tools = gemini_tools_to_openai(tools_schema or [])

    final_system = (
        'Ban la "Nội Trợ AI", tro ly am thuc thong minh cho nguoi Viet. '
        'Ban duoc phep su dung cac cong tu du lieu de tra loi cau hoi cua nguoi dung. '
        'Tra loi bang tieng Viet, ngan gon. '
        'Khong hien thi thong so ky thuat nhu confidence hay query_sim. '
        'Neu can thong tin, hay goi cong cu phu hop truoc khi tra loi.'
    )
    if system_instruction:
        final_system = f'{final_system}\n{system_instruction}'
    if final_system and (not messages or messages[0].get('role') != 'system'):
        messages.insert(0, {'role': 'system', 'content': final_system})

    for _round in range(max_tool_rounds):
        message = None
        try:
            if not _ollama_qwen_generate_with_tools:
                raise RuntimeError('Ollama tool helper not available')
            message = _ollama_qwen_generate_with_tools(messages, openai_tools, max_tokens=4096)
        except Exception as exc:
            logger.exception('Qwen tool-use failed, falling back to Gemini: %s', exc)
            return call_llm_with_tools(chat_session, user_text, tools_schema, system_instruction=system_instruction, max_tool_rounds=max_tool_rounds)

        tool_calls = parse_tool_call_from_message(message)
        assistant_text = (getattr(message, 'content', None) or '').strip()

        if not tool_calls:
            if assistant_text:
                return assistant_text
            return 'Khong co phan hoi tu AI.'

        if assistant_text:
            messages.append({'role': 'assistant', 'content': assistant_text, 'tool_calls': []})
        else:
            messages.append({'role': 'assistant', 'content': None, 'tool_calls': []})

        for tool_call in tool_calls:
            tool_name = tool_call.get('name', '')
            tool_args = tool_call.get('args', {}) or {}
            result = execute_tool(tool_name, tool_args)
            messages.append(
                {
                    'role': 'tool',
                    'tool_call_id': getattr(getattr(tool_call, 'id', None), 'id', None) or tool_name,
                    'name': tool_name,
                    'content': json.dumps(result, ensure_ascii=False, default=str),
                }
            )

    return 'Da dat gioi han so vong goi cong cu.'
