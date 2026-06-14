"""Semantic intent classification support using lightweight embeddings."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from apps.chat.models import IntentEmbedding
from app.services.chat_text_service import tokenize_chat_text


@dataclass(frozen=True)
class IntentEmbeddingPrediction:
    intent_name: Optional[str]
    confidence: float
    scores: Dict[str, float]
    evidence_tokens: List[str]


def _normalize_embedding_tokens(text: str) -> List[str]:
    return [token for token in tokenize_chat_text(text) if token]


def build_text_embedding_vector(text: str) -> Dict[str, float]:
    tokens = _normalize_embedding_tokens(text)
    if not tokens:
        return {}

    counts = Counter(tokens)
    total = sum(counts.values())
    return {token: float(count) / total for token, count in counts.items()}


def _load_embedding_vector(source: Any) -> Dict[str, float]:
    if not source:
        return {}
    if isinstance(source, dict):
        return {str(k): float(v) for k, v in source.items() if v is not None}
    if isinstance(source, list):
        return {str(idx): float(value) for idx, value in enumerate(source) if value is not None}
    return {}


def cosine_similarity(left: Dict[str, float], right: Dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = 0.0
    for token, left_value in left.items():
        right_value = right.get(token)
        if right_value is not None:
            dot += left_value * right_value

    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def classify_intent_by_embedding(user_text: str, threshold: float = 0.30) -> IntentEmbeddingPrediction:
    """[PHÂN LOẠI Ý ĐỊNH - PHƯƠNG PHÁP 1: Embedding Similarity]
    
    Phương pháp này sử dụng token-based embedding (TF) để tính cosine similarity giữa:
    - Tin nhắn người dùng (query vector)
    - Các intent embeddings được lưu trữ từ chat history hoặc patterns
    
    Quy trình:
    1. Token hóa tin nhắn người dùng → TF vector
    2. So sánh với tất cả intent embeddings trong DB
    3. Tính cosine similarity
    4. Chọn intent có similarity cao nhất (nếu > threshold)
    5. Trả về intent_name, confidence và evidence tokens
    
    Ưu điểm:
    - Không phụ thuộc keyword rules
    - Học từ lịch sử chat
    - Hỗ trợ các biến thể câu nói
    
    Giới hạn:
    - Cần có data training (IntentEmbedding) đầy đủ
    - Threshold cần tuning
    """
    query_vector = build_text_embedding_vector(user_text)
    if not query_vector:
        return IntentEmbeddingPrediction(None, 0.0, {}, [])

    intent_scores: Dict[str, float] = {}
    intent_best_evidence: Dict[str, List[str]] = {}

    embeddings = IntentEmbedding.objects.filter(intent_name__isnull=False)
    for embedding in embeddings:
        raw_vector = _load_embedding_vector(getattr(embedding, 'embedding_vector', None))
        if not raw_vector:
            continue

        similarity = cosine_similarity(query_vector, raw_vector)
        intent_name = (getattr(embedding, 'intent_name', None) or '').strip()
        if not intent_name:
            continue

        if similarity > intent_scores.get(intent_name, 0.0):
            intent_scores[intent_name] = similarity
            intent_best_evidence[intent_name] = _normalize_embedding_tokens(getattr(embedding, 'message', '') or '')

    if not intent_scores:
        return IntentEmbeddingPrediction(None, 0.0, {}, [])

    best_intent = max(intent_scores.items(), key=lambda item: item[1])
    best_name, best_score = best_intent
    if best_score < threshold:
        return IntentEmbeddingPrediction(None, 0.0, intent_scores, [])

    confidence = min(1.0, max(0.0, best_score * 1.05))
    evidence_tokens = intent_best_evidence.get(best_name, [])
    return IntentEmbeddingPrediction(best_name, confidence, intent_scores, evidence_tokens)


def get_intent_embedding_status() -> Dict[str, Any]:
    total = IntentEmbedding.objects.filter(intent_name__isnull=False).count()
    return {'intent_embedding_count': total}
