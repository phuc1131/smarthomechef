"""Lightweight local RAG/local-response generator.

This is a safe, dependency-free fallback that synthesizes a short
response from RAG evidence and local candidates without calling Gemini.
It acts as `Local LLM` placeholder until a proper local LLM is integrated.
"""

from typing import Any, Dict, List, Optional


def generate_local_response(account: Any, user_text: str, rag_evidence: Dict[str, Any], local_candidates: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """Generate a short, deterministic response from local evidence.

    Returns a string response when enough evidence exists, otherwise None.
    """
    # Basic heuristics: if we have at least one food or recipe evidence, synthesize.
    foods = rag_evidence.get('foods') if isinstance(rag_evidence, dict) else None
    recipes = rag_evidence.get('recipes') if isinstance(rag_evidence, dict) else None

    items = []
    if foods:
        for f in foods[:3]:
            # f may be either Food object or dict from semantic_search_with_scores
            if isinstance(f, dict):
                name = getattr(f.get('food'), 'name', None) or f.get('food') or f.get('title') or ''
                items.append(str(name))
            else:
                items.append(str(getattr(f, 'name', f)))

    if recipes and not items:
        for r in recipes[:2]:
            title = r.get('title') if isinstance(r, dict) else getattr(r, 'title', None)
            if title:
                items.append(str(title))

    if not items and local_candidates:
        for c in local_candidates[:3]:
            food = c.get('food')
            if not food:
                continue
            items.append(getattr(food, 'name', str(food)))

    if not items:
        return None

    # Build a concise response
    items_text = ', '.join([it for it in items if it])
    response = f"Mình tìm thấy một số gợi ý phù hợp: {items_text}. Bạn muốn mình lọc theo sở thích, bệnh lý hay nguyên liệu không?"
    return response
