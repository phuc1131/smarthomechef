"""Router and policy evaluation helpers for AI orchestrator.

This module provides lightweight policy checks and a simple routing
decision function used by `AIOrchestratorService.orchestrate()`.
"""

from typing import Any, Dict, List, Optional

from apps.nutrition.models import Food
from apps.users.models import UserPreferenceProfile, UserDisease, UserProfile
from app.services.personalization_service import _has_token_match, _normalize_tokens, build_user_preference_profile


def evaluate_policies(account, candidates: List[Dict[str, Any]], user_text: str) -> Dict[str, Any]:
    """Evaluate safety and policy constraints; return safe candidates and issues."""
    if not account:
        return {'blocked': False, 'removed_count': 0, 'safe_candidates': candidates, 'issues': []}

    preference_profile = build_user_preference_profile(account)
    avoided = _normalize_tokens(getattr(preference_profile, 'avoided_keywords', None) or [])

    diseases = [getattr(d.disease, 'name', '') for d in UserDisease.objects.filter(account=account).select_related('disease')]
    issues: List[str] = []
    safe: List[Dict[str, Any]] = []
    removed = 0

    for item in candidates:
        food = item.get('food')
        name = getattr(food, 'name', '') if food else ''

        if avoided and _has_token_match(name, avoided, threshold=0.60):
            removed += 1
            issues.append(f"removed_avoided:{name}")
            continue

        if diseases and 'diabetes' in ' '.join(diseases).lower():
            if food and not getattr(food, 'is_diabetes_friendly', False):
                removed += 1
                issues.append(f"removed_disease_mismatch:{name}")
                continue

        safe.append(item)

    return {'blocked': False, 'removed_count': removed, 'safe_candidates': safe, 'issues': issues}


def decide_route(
    intent_confidence: float,
    candidates: List[Dict[str, Any]],
    call_gemini: bool,
    gemini_enabled: bool,
    route_context: Optional[Dict[str, Any]] = None,
) -> str:
    """[QUYẾT ĐỊNH ĐIỀU PHỐI] Lựa chọn route xử lý (Ollama/Qwen vs Gemini).
    
    Logic:
    1. Nếu call_gemini=True → ưu tiên Gemini (người dùng yêu cầu)
    2. Nếu intent_confidence >= 0.6 VÀ top_score >= 0.5 → dùng Ollama/Qwen (local)
       - Đủ confident về ý định người dùng
       - Có ứng viên local (foods) chất lượng tốt
       - Tránh unnecessary LLM calls
    3. Nếu gemini_enabled VÀ (confidence < 0.6 hoặc score < 0.5) → dùng Gemini
       - Không đủ tự tin → hỏi AI bên ngoài
    4. Fallback: 'local' (tránh lỗi nếu cả hai disabled)
    
    Returns: 'local' (dùng Ollama/Qwen), 'gemini' (dùng Gemini API), hoặc fallback 'local'
    
    CÁC CẢI THIỆN:
    - Ollama/Qwen là primary backend (thay vì Gemini)
    - Quyết định dựa trên: intent confidence + candidate score + explicit flags
    - Gemini là safety net khi Ollama không khả dụ
    """
    if call_gemini:
        return 'gemini'

    context = route_context or {}
    top_score = 0.0
    if candidates:
        top_score = max((item.get('score', 0.0) for item in candidates), default=0.0)
    candidate_count = len(candidates or [])
    cache_hit = bool(context.get('cache_hit'))
    rag_density = float(context.get('rag_density', 0.0) or 0.0)
    local_evidence = float(context.get('local_evidence', 0.0) or 0.0)

    # Strong DB/cache evidence should bias toward local handling.
    if cache_hit and intent_confidence >= 0.45:
        return 'local'

    if local_evidence >= 0.7 and candidate_count >= 2 and top_score >= 0.35:
        return 'local'

    # Prefer local if high confidence and good local candidate
    if intent_confidence >= 0.6 and top_score >= 0.5:
        return 'local'

    # Rich RAG evidence but weak local ranking is a good Gemini/RAG use case.
    if gemini_enabled and rag_density >= 0.5 and top_score < 0.55:
        return 'gemini'

    # Otherwise use Gemini if enabled or no viable local results
    if gemini_enabled and (intent_confidence < 0.6 or top_score < 0.5 or not candidates):
        return 'gemini'

    return 'local'
