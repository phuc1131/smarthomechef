import re
import math
from typing import List, Set, Dict, Optional
from difflib import SequenceMatcher

def compute_smart_similarity(query_a: str, query_b: str, source_intent_a: Optional[str] = None, source_intent_b: Optional[str] = None) -> float:
    """
    Tính toán độ tương đồng thông minh giữa hai câu truy vấn.
    Kết hợp:
    1. Jaccard Similarity (Token-based)
    2. SequenceMatcher (Pattern/Structure-based)
    3. Keyword Weighting (Quan trọng hóa các từ khóa ẩm thực/dinh dưỡng)
    4. Intent Match (Thưởng điểm nếu cùng ý định)
    """
    if not query_a or not query_b:
        return 0.0

    # 1. Tiền xử lý
    def normalize(text):
        text = text.lower().strip()
        # Loại bỏ dấu câu cơ bản
        text = re.sub(r'[^\w\s]', '', text)
        return text

    norm_a = normalize(query_a)
    norm_b = normalize(query_b)

    if norm_a == norm_b:
        return 1.0

    # 2. Tokenization
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    
    if not tokens_a or not tokens_b:
        return 0.0

    # 3. Weighted Jaccard
    # Các từ khóa quan trọng được nhân hệ số
    CRITICAL_KEYWORDS = {
        'protein', 'calo', 'calory', 'calories', 'béo', 'đạm', 'carbs', 'tinh bột',
        'giảm cân', 'tăng cơ', 'tiểu đường', 'huyết áp', 'thực đơn', 'món ăn',
        'công thức', 'cách làm', 'nguyên liệu', 'giá', 'bao nhiêu', 'nấu', 'tuần', 'tháng'
    }

    def get_weighted_score(tokens_a: Set[str], tokens_b: Set[str]) -> float:
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        
        weighted_inter = 0.0
        for t in intersection:
            weight = 2.5 if t in CRITICAL_KEYWORDS else 1.0
            weighted_inter += weight
            
        weighted_union = 0.0
        for t in union:
            weight = 2.5 if t in CRITICAL_KEYWORDS else 1.0
            weighted_union += weight
            
        return weighted_inter / weighted_union if weighted_union > 0 else 0.0

    jaccard_score = get_weighted_score(tokens_a, tokens_b)

    # 4. Sequence Similarity (Cấu trúc câu)
    seq_score = SequenceMatcher(None, norm_a, norm_b).ratio()

    # 5. Intent Boost
    intent_boost = 0.0
    if source_intent_a and source_intent_b and source_intent_a == source_intent_b:
        intent_boost = 0.15

    # 6. Final Combined Score
    # Ưu tiên Jaccard cho nội dung, Sequence cho hình thức
    final_score = (jaccard_score * 0.6) + (seq_score * 0.4) + intent_boost
    
    return min(1.0, final_score)

def is_query_similar(query_a: str, query_b: str, threshold: float = 0.80, **kwargs) -> bool:
    return compute_smart_similarity(query_a, query_b, **kwargs) >= threshold
