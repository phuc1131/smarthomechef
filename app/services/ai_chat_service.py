"""
Service tích hợp API-Ninjas (exercise, recipe, nutrition, caloriesburned) và Ollama (local LLM routing).

- Ollama dùng để phân loại intent người dùng và tổng hợp dữ liệu API thành tiếng Việt.
- API-Ninjas dùng để truy vấn thực tế các endpoint exercise, recipe, nutrition, caloriesburned.
"""

import json
import os
import logging

import requests

from app.config import (
    API_NINJAS_API_KEY,
    API_NINJAS_BASE_URL,
    OLLAMA_URL,
    OLLAMA_MODEL,
)

logger = logging.getLogger(__name__)

# Các endpoint API-Ninjas
EXERCISE_ENDPOINT = "/v1/exercises"
RECIPE_ENDPOINT = "/v3/recipe"
NUTRITION_ENDPOINT = "/v1/nutrition"
CALORIES_BURNED_ENDPOINT = "/v1/caloriesburned"


def call_api_ninjas(path, params):
    """Gọi API-Ninjas với key đã cấu hình."""
    url = f"{API_NINJAS_BASE_URL}{path}"
    headers = {"X-Api-Key": API_NINJAS_API_KEY or ""}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.error("[API-Ninjas Error] Không thể gọi %s: %s", path, exc)
        return None


def call_ollama(messages, json_format=False):
    """Gọi mô hình Ollama cục bộ. Hỗ trợ ép đầu ra JSON."""
    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }

    if json_format:
        payload["format"] = "json"

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]
    except Exception as exc:
        logger.error("[Ollama Error] Gọi Ollama thất bại: %s", exc)
        raise


def route_with_ollama(message):
    """Phân tích tin nhắn người dùng để xác định mục đích gọi API."""
    system_prompt = (
        "You are a router for an API chatbot. "
        "Classify the user's message into exactly one intent: "
        "exercise, recipe, nutrition, caloriesburned, or unknown. "
        "Return ONLY valid JSON with keys intent and query. "
        "intent must be one of exercise, recipe, nutrition, caloriesburned, unknown. "
        "query must be the cleaned search text to send to the API. "
        "If the user asks for multiple things, choose the main one. "
        "If you cannot tell, use unknown."
    )
    user_prompt = f"User message: {message}"

    content = call_ollama(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        json_format=True,
    )

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"intent": "unknown", "query": message}

    intent = str(parsed.get("intent", "unknown")).strip().lower()
    query = str(parsed.get("query", message)).strip()

    if intent == "calories_burned":
        intent = "caloriesburned"

    if intent not in {"exercise", "recipe", "nutrition", "caloriesburned", "unknown"}:
        intent = "unknown"
    if not query:
        query = message

    return {"intent": intent, "query": query}


def answer_with_ollama(user_message, intent, api_data):
    """Tổng hợp dữ liệu nhận được từ API và trả lời người dùng bằng tiếng Việt."""
    system_prompt = (
        "You are a Vietnamese chatbot. "
        "Explain the API result naturally, helpfully, and briefly. "
        "Do not mention JSON, technical terms, or internal routing. "
        "If the result is empty or None, politely say you could not find a suitable result. "
        "Use the user's language style. "
        "Always convert all measurement units to the metric system used internationally. "
        "Use g, kg, ml, l, cm, m, and °C only. "
        "Convert ounces, pounds, cups, tablespoons, teaspoons, and Fahrenheit into metric units. "
        "Never output imperial or US customary units. "
        "For cooking steps, show temperatures in °C and quantities in metric units. "
        "Round to practical values if exact conversion is awkward."
    )
    user_prompt = json.dumps(
        {
            "user_message": user_message,
            "intent": intent,
            "api_data": api_data,
        },
        ensure_ascii=False,
    )
    return call_ollama(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        json_format=False,
    )


def handle_exercise(query):
    data = call_api_ninjas(EXERCISE_ENDPOINT, {"name": query})
    return data[:5] if isinstance(data, list) else data


def handle_recipe(query):
    return call_api_ninjas(RECIPE_ENDPOINT, {"title": query})


def handle_nutrition(query):
    return call_api_ninjas(NUTRITION_ENDPOINT, {"query": query})


def handle_caloriesburned(query):
    return call_api_ninjas(CALORIES_BURNED_ENDPOINT, {"query": query})


def process_chat_message(user_message):
    """
    Hàm tổng hợp quy trình:
    Nhận tin nhắn -> Định tuyến -> Gọi API -> Trả lời bằng tiếng Việt
    """
    route = route_with_ollama(user_message)
    intent = route["intent"]
    query = route["query"]

    logger.info("[AI Chat] Định tuyến - Ý định: %s | Từ khóa: %s", intent, query)

    api_data = None
    if intent == "exercise":
        api_data = handle_exercise(query)
    elif intent == "recipe":
        api_data = handle_recipe(query)
    elif intent == "nutrition":
        api_data = handle_nutrition(query)
    elif intent == "caloriesburned":
        api_data = handle_caloriesburned(query)

    response_text = answer_with_ollama(user_message, intent, api_data)
    return response_text
