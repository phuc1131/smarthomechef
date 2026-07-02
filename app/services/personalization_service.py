"""Internal personalization helpers for the AI system."""

from __future__ import annotations

import unicodedata
import re
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set

from django.db.models import Avg

from apps.core_models.models import AIRecommendation, SearchEvent
from apps.core_models.ai_learning_models import (
    Experiment,
    ExperimentEvent,
    MealRecommendation,
    UserFeedbackFood,
    UserFeedbackRecommendation,
)
from apps.nutrition.models import Food, NutritionLog
from apps.users.models import UserDisease, UserGoal, UserPreferenceProfile, UserProfile, UserFeedback


@dataclass(frozen=True)
class PersonalizedScore:
    food_id: int
    score: float
    reasons: List[str]


def _normalize_vietnamese_text(text: str) -> str:
    """
    Normalize Vietnamese text: xóa dấu, convert to lowercase.
    
    Xử lý:
    - NFD decompose: "á" → "a" + "´"
    - Xóa combining marks (diacritics)
    - Lowercase
    - Loại bỏ whitespace dư thừa
    """
    if not text:
        return ''
    
    # Convert to NFD form (decompose)
    text = unicodedata.normalize('NFD', text)
    
    # Remove combining characters (diacritical marks)
    # Category 'Mn' = Mark, Nonspacing (combining characters)
    text = ''.join(
        char for char in text 
        if unicodedata.category(char) != 'Mn'
    )
    
    # Lowercase + strip
    text = text.lower().strip()
    return text


def _tokenize_text(text: str) -> Set[str]:
    """Tokenize text: extract words, normalize"""
    if not text:
        return set()
    normalized = _normalize_vietnamese_text(text)
    # Split on whitespace + punctuation
    tokens = re.findall(r'\w+', normalized, flags=re.UNICODE)
    return set(tokens)


def _has_token_match(target_text: str, keywords: List[str], threshold: float = 0.6) -> bool:
    """
    Check if target_text contains any keywords using normalized token matching.
    threshold: minimum Jaccard similarity for a match (0.0-1.0)
    """
    if not target_text or not keywords:
        return False
    
    target_tokens = _tokenize_text(target_text)
    if not target_tokens:
        return False
    
    for keyword in keywords:
        keyword_tokens = _tokenize_text(keyword)
        if not keyword_tokens:
            continue
        
        intersection = len(target_tokens & keyword_tokens)
        union = len(target_tokens | keyword_tokens)
        if union == 0:
            continue
        
        similarity = intersection / union
        # Ngoài ra kiểm tra substring (nếu keyword là 1 token duy nhất)
        if len(keyword_tokens) == 1:
            keyword_token = list(keyword_tokens)[0]
            if keyword_token in target_tokens:
                return True
        
        if similarity >= threshold:
            return True
    
    return False


def _text_similarity(a: Optional[str], b: Optional[str]) -> float:
    """Compute simple Jaccard similarity between two texts using normalized tokens."""
    if not a or not b:
        return 0.0
    ta = _tokenize_text(a)
    tb = _tokenize_text(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    if union == 0:
        return 0.0
    return inter / union


def build_user_preference_profile(account):
    if not account:
        return None
    profile, _ = UserPreferenceProfile.objects.get_or_create(account=account)
    return profile


def get_personalization_context(account) -> Dict[str, Any]:
    profile = UserProfile.objects.filter(account=account).first() if account else None
    preference_profile = build_user_preference_profile(account)
    goals = list(UserGoal.objects.filter(account=account)) if account else []
    diseases = list(UserDisease.objects.filter(account=account).select_related('disease')) if account else []
    recent_logs = list(
        NutritionLog.objects.filter(account=account).select_related('food').order_by('-date')[:14]
    ) if account else []

    return {
        'profile': profile,
        'preference_profile': preference_profile,
        'goals': goals,
        'diseases': diseases,
        'recent_food_ids': [log.food_id for log in recent_logs if log.food_id],
        'recent_logs': recent_logs,
    }


def _normalize_tokens(value: Optional[Iterable[str]]) -> List[str]:
    return [str(item).strip().lower() for item in value or [] if str(item).strip()]


def filter_food_candidates(account, foods: Iterable[Food]) -> List[Food]:
    """[BỘ LỌC CÁ NHÂN HÓA - BƯỚC 1: Hard Constraints]
    
    Lọc các món ăn dựa trên hard constraints (bắt buộc phải loại bỏ):
    
    1. AVOIDED KEYWORDS:
       - Áp dụng token-based matching với Vietnamese diacritics normalization
       - Nếu tên món khớp từ khóa cần tránh → loại bỏ
       - Ví dụ: "gan niem mo" sẽ match "gan nhiễm mỡ" sau normalize
    
    2. DISEASE CONSTRAINTS:
       - Người dùng có bệnh tiểu đường
       - Món ăn không được đánh dấu is_diabetes_friendly=True → loại bỏ
    
    3. BUDGET CONSTRAINTS:
       - So sánh estimated_cost của food với budget_limit trong profile
       - Nếu vượt quá → loại bỏ
    
    Output: Danh sách safe_foods (đã loại bỏ các món bị cấm)
    
    Ghi chú:
    - Đây là hard filtering (loại bỏ hoàn toàn, không có score)
    - Các món còn lại sẽ được score_food_for_user() chấm điểm chi tiết
    """
    if not account:
        return list(foods)

    profile = UserProfile.objects.filter(account=account).first()
    preference_profile = build_user_preference_profile(account)
    diseases = list(UserDisease.objects.filter(account=account).select_related('disease'))

    preferred_categories = _normalize_tokens(getattr(preference_profile, 'preferred_categories', None) or [])
    avoided_keywords = _normalize_tokens(getattr(preference_profile, 'avoided_keywords', None) or [])
    disease_names = [getattr(item.disease, 'name', '') for item in diseases if getattr(item, 'disease', None)]

    safe: List[Food] = []
    for food in foods:
        if avoided_keywords and _has_token_match(getattr(food, 'name', '') or '', avoided_keywords, threshold=0.60):
            continue

        if disease_names:
            if getattr(food, 'is_diabetes_friendly', False) is False and _has_token_match(' '.join(disease_names), ['diabetes', 'tiểu đường', 'tieu duong'], threshold=0.60):
                continue

        if profile and getattr(profile, 'budget_limit', None) is not None:
            estimated_cost = getattr(food, 'estimated_cost', None)
            if estimated_cost is not None and float(estimated_cost or 0) > float(profile.budget_limit or 0):
                continue

        safe.append(food)

    return safe


def score_food_for_user(account, food: Food, user_query: Optional[str] = None) -> PersonalizedScore:
    """[BỘ LỌC CÁ NHÂN HÓA - BƯỚC 2: Soft Scoring]
    
    Chấm điểm chi tiết cho mỗi món ăn dựa trên nhiều yếu tố cá nhân hóa:
    
    1. RECENCY (Tính mới):
       - Nếu món ăn được ăn gần đây (< 14 ngày) → -0.12 score
       - Tránh recommend cùng một món liên tục
    
    2. QUERY MATCHING (Khớp truy vấn):
       - Tính Jaccard similarity giữa user_query và tên/danh mục food
       - Nếu sim > 0 → boost +0.20 * sim (max +0.20)
       - Dynamic personalization: món ăn nào khớp "ngô" được promote
    
    3. PREFERRED CATEGORIES (Danh mục ưa thích):
       - Token-based matching với Vietnamese normalization
       - Threshold Jaccard >= 0.60
       - Match → +0.18 score
    
    4. AVOIDED KEYWORDS (Từ khóa cần tránh):
       - Token-based matching với Vietnamese normalization
       - Mặc dù filter_food_candidates() đã lọc, hàm này thêm -0.30 score
    
    5. WEIGHT LOSS GOAL (Mục tiêu giảm cân):
       - Nếu goal_type='weight_loss':
         - Calories <= 300 → +0.10 score
         - Calories >= 600 → -0.10 score
    
    6. FATTY LIVER CONDITIONS (Gan nhiễm mỡ):
       - Detect từ profile.health_goal, medical_conditions
       - Fat <= 12g → +0.10 score (lành mạnh)
       - Fiber >= 3g → +0.05 score (bổ sung)
    
    7. LOW FAT DIET (Ăn thanh đạm):
       - Similar logic với fatty liver
    
    Output: PersonalizedScore(food_id, score 0.0-1.0, reasons[])
    
    CÁC CẢI THIỆN:
    - Token-based matching (không substring check)
    - Vietnamese normalization: dấu được ignore
    - Threshold tuning: Jaccard >= 0.60 cho fuzzy match
    - Profile text normalization trước matching
    """
    context = get_personalization_context(account)
    reasons: List[str] = []
    score = 0.5

    profile = context.get('profile')
    preference_profile = context.get('preference_profile')
    goals = context.get('goals') or []
    diseases = context.get('diseases') or []
    recent_food_ids = set(context.get('recent_food_ids') or [])

    food_name = (getattr(food, 'name', '') or '').lower()
    category_name = ''
    if getattr(food, 'category', None) and getattr(food.category, 'name', None):
        category_name = food.category.name.lower()
    elif getattr(food, 'category_name', None):
        category_name = str(food.category_name).lower()

    # Tránh recommend foods đã ăn gần đây
    if food.id in recent_food_ids:
        score -= 0.12
        reasons.append('Đã ăn gần đây')

    # Boost nếu food khớp với truy vấn hiện tại (dynamic personalization)
    if user_query:
        # similarity based on tokens between query and food name/category
        sim = _text_similarity(user_query, f'{category_name} {food_name}')
        if sim > 0:
            # scale contribution (max +0.20 when sim == 1.0)
            boost = 0.2 * sim
            score += boost
            reasons.append('Phù hợp với tìm kiếm')

    # CẢI THIỆN: dùng token matching cho preferred categories
    preferred_categories = _normalize_tokens(getattr(preference_profile, 'preferred_categories', None) or [])
    if preferred_categories and _has_token_match(f'{category_name} {food_name}', preferred_categories, threshold=0.60):
        score += 0.18
        reasons.append('Khớp danh mục ưa thích')

    # CẢI THIỆN: dùng token matching cho avoided keywords
    avoided_keywords = _normalize_tokens(getattr(preference_profile, 'avoided_keywords', None) or [])
    if avoided_keywords and _has_token_match(food_name, avoided_keywords, threshold=0.60):
        score -= 0.30
        reasons.append('Trùng từ khóa cần tránh')

    # Weight loss goal
    if goals and any(getattr(goal, 'goal_type', '') == 'weight_loss' for goal in goals):
        calories = float(getattr(food, 'total_calories', 0) or 0)
        if calories <= 300:
            score += 0.10
            reasons.append('Phù hợp giảm cân')
        elif calories >= 600:
            score -= 0.10
            reasons.append('Calories cao hơn mục tiêu giảm cân')

    # CẢI THIỆN: normalize profile text + dùng token matching cho health conditions
    profile_text = ' '.join([
        str(getattr(profile, 'health_goal', '') or ''),
        str(getattr(profile, 'medical_conditions', '') or ''),
        str(getattr(profile, 'dietary_preferences', '') or ''),
    ]).lower()
    
    # Fatty liver conditions (cải thiện: dùng token matching + normalize dấu)
    fatty_liver_keywords = ['gan nhiễm mỡ', 'gan nhiem mo', 'mo gan', 'mỡ gan', 'fatty liver', 'steatosis']
    if _has_token_match(profile_text, fatty_liver_keywords, threshold=0.60):
        fat = float(getattr(food, 'fat', 0) or 0)
        fiber = float(getattr(food, 'fiber', 0) or 0)
        if fat <= 12:
            score += 0.10
            reasons.append('Phù hợp gan nhiễm mỡ (ít chất béo)')
        elif fat <= 18:
            score += 0.05
            reasons.append('Hàm lượng chất béo vừa phải')
        if fiber >= 3:
            score += 0.05
            reasons.append('Giàu chất xơ cho gan nhiễm mỡ')

    # Low fat diet conditions (cải thiện: dùng token matching)
    low_fat_keywords = ['thanh dam', 'ăn thanh đạm', 'it chat beo', 'ít chất béo', 'low fat', 'ăn nhạt']
    if _has_token_match(profile_text, low_fat_keywords, threshold=0.60):
        fat = float(getattr(food, 'fat', 0) or 0)
        if fat <= 15:
            score += 0.08
            reasons.append('Phù hợp chế độ ít chất béo')

    # Diabetes conditions
    disease_names = [getattr(item.disease, 'name', '').lower() for item in diseases if getattr(item, 'disease', None)]
    diabetes_keywords = ['diabetes', 'tiểu đường', 'tieu duong', 'đái tháo đường']
    if disease_names and _has_token_match(' '.join(disease_names), diabetes_keywords, threshold=0.60):
        if getattr(food, 'is_diabetes_friendly', False):
            score += 0.15
            reasons.append('Thân thiện với tiểu đường')
        else:
            score -= 0.08

    # Budget consideration
    if profile and getattr(profile, 'budget_limit', None):
        estimated_cost = getattr(food, 'estimated_cost', None)
        budget_limit = float(profile.budget_limit or 0)
        if estimated_cost is not None and float(estimated_cost) <= budget_limit:
            score += 0.08
            reasons.append('Nằm trong ngân sách')

    # User feedback history
    feedback_avg = (
        UserFeedback.objects.filter(account=account).aggregate(avg_rating=Avg('rating')).get('avg_rating')
        if account else None
    )
    if feedback_avg:
        score += min(0.08, float(feedback_avg) / 100.0)

    score = max(0.0, min(1.0, round(score, 4)))
    return PersonalizedScore(food_id=food.id, score=score, reasons=reasons)


def rank_food_candidates(account, foods: Iterable[Food], limit: int = 10, user_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Rank foods using a simple learning-to-rank linear model over features.

    This is a lightweight stand-in for a proper LTR pipeline. Features are
    combined with tunable weights and the result is normalized to [0,1].
    """
    def compute_learning_score(food: Food) -> (float, List[str]):
        reasons: List[str] = []
        base = 0.5

        # query similarity
        query_sim = 0.0
        if user_query:
            try:
                query_sim = _text_similarity(user_query, f"{getattr(food, 'category_name', '')} {getattr(food, 'name', '')}")
            except Exception:
                query_sim = 0.0
        if query_sim > 0:
            reasons.append('Phù hợp với tìm kiếm của bạn')

        # preference category match
        preference_profile = build_user_preference_profile(account)
        preferred = 0.0
        preferred_categories = _normalize_tokens(getattr(preference_profile, 'preferred_categories', None) or [])
        if preferred_categories and _has_token_match(f"{getattr(food, 'category_name', '')} {getattr(food, 'name', '')}", preferred_categories, threshold=0.60):
            preferred = 1.0
            reasons.append('Thuộc danh mục bạn yêu thích')

        # nutrition/health feature
        nutrition_score = 0.0
        if getattr(food, 'is_diabetes_friendly', False):
            nutrition_score = 1.0
            reasons.append('Thân thiện với người tiểu đường')

        # budget
        budget_score = 0.0
        profile = UserProfile.objects.filter(account=account).first() if account else None
        if profile and getattr(profile, 'budget_limit', None) is not None:
            estimated_cost = getattr(food, 'estimated_cost', None)
            if estimated_cost is not None and float(estimated_cost or 0) <= float(profile.budget_limit or 0):
                budget_score = 1.0
                reasons.append('Phù hợp với ngân sách')

        # feedback average
        feedback_avg = (
            UserFeedback.objects.filter(account=account, food=food).aggregate(avg_rating=Avg('rating')).get('avg_rating')
            if account else None
        )
        feedback_score = 0.0
        if feedback_avg:
            feedback_score = min(1.0, float(feedback_avg) / 5.0)
            reasons.append('Bạn đã đánh giá tốt món này')

        # recent penalty
        recent_food_ids = set(get_personalization_context(account).get('recent_food_ids') or [])
        recent_penalty = -0.12 if getattr(food, 'id', None) in recent_food_ids else 0.0
        if recent_penalty:
            reasons.append('Bạn vừa ăn món này gần đây')

        # weights (can be learned/updated later)
        w = {
            'query': 0.35,
            'pref': 0.20,
            'nutrition': 0.15,
            'feedback': 0.15,
            'budget': 0.10,
        }

        score = base + (w['query'] * query_sim) + (w['pref'] * preferred) + (w['nutrition'] * nutrition_score) + (w['feedback'] * feedback_score) + (w['budget'] * budget_score) + recent_penalty
        score = max(0.0, min(1.0, round(score, 4)))
        return score, reasons

    ranked: List[Dict[str, Any]] = []
    for food in foods:
        score, reasons = compute_learning_score(food)
        ranked.append({'food': food, 'score': score, 'reasons': reasons})

    ranked.sort(key=lambda item: item['score'], reverse=True)
    return ranked[:limit]


def build_db_backed_candidate_pool(account, user_query: Optional[str] = None, limit: int = 60) -> List[Food]:
    """Build a candidate pool from DB signals before applying personalization."""
    candidates: List[Food] = []

    if user_query:
        try:
            semantic_items = semantic_search_with_scores(user_query, limit=max(limit // 2, 20))
            candidates.extend([item.get('food') for item in semantic_items if item.get('food') is not None])
        except Exception:
            pass

        try:
            query_tokens = [token for token in _tokenize_text(user_query) if len(token) >= 2]
            if query_tokens:
                from django.db.models import Q
                query = Q()
                for token in query_tokens:
                    query |= Q(name__icontains=token) | Q(category__name__icontains=token) | Q(description__icontains=token)
                candidates.extend(list(Food.objects.filter(query).distinct().order_by('name')[: max(limit // 2, 20)]))
        except Exception:
            pass

    if account:
        try:
            clicked_food_ids = list(
                SearchEvent.objects.filter(account=account, clicked_food__isnull=False)
                .order_by('-created_at')
                .values_list('clicked_food_id', flat=True)[:15]
            )
            if clicked_food_ids:
                candidates.extend(list(Food.objects.filter(id__in=clicked_food_ids)))
        except Exception:
            pass

        try:
            liked_food_ids = list(
                UserFeedbackFood.objects.filter(account=account, is_liked=True)
                .order_by('-created_at')
                .values_list('food_id', flat=True)[:15]
            )
            if liked_food_ids:
                candidates.extend(list(Food.objects.filter(id__in=liked_food_ids)))
        except Exception:
            pass

    if not candidates:
        try:
            candidates = list(Food.objects.all().order_by('name')[:limit])
        except Exception:
            return []

    deduped: List[Food] = []
    seen_ids = set()
    for food in candidates:
        food_id = getattr(food, 'id', None)
        if not food_id or food_id in seen_ids:
            continue
        seen_ids.add(food_id)
        deduped.append(food)

    return deduped[:limit]


def _extract_user_signal_keywords(account) -> Set[str]:
    keywords: Set[str] = set()
    if not account:
        return keywords

    profile = UserProfile.objects.filter(account=account).first()
    preference_profile = build_user_preference_profile(account)
    if profile:
        for value in (
            getattr(profile, 'health_goal', ''),
            getattr(profile, 'medical_conditions', ''),
            getattr(profile, 'dietary_preferences', ''),
        ):
            for token in _tokenize_text(str(value or '')):
                keywords.add(token)
    for value in _normalize_tokens(getattr(preference_profile, 'preferred_categories', None) or []):
        for token in _tokenize_text(value):
            keywords.add(token)
    for value in _normalize_tokens(getattr(preference_profile, 'avoided_keywords', None) or []):
        for token in _tokenize_text(value):
            keywords.add(token)
    return keywords


def _collaborative_food_signal(account, food: Food) -> float:
    if not account or not food:
        return 0.0

    profile_keywords = _extract_user_signal_keywords(account)
    if not profile_keywords:
        return 0.0

    candidates = UserFeedbackFood.objects.select_related('account', 'food').filter(
        is_liked=True,
        food__isnull=False,
    ).exclude(account=account).order_by('-created_at')[:500]

    total = 0.0
    weight = 0.0
    food_tokens = _tokenize_text(f"{getattr(food, 'name', '')} {getattr(food, 'category_name', '')}")

    for fb in candidates:
        other_keywords = _extract_user_signal_keywords(fb.account)
        if not other_keywords:
            continue
        overlap = len(profile_keywords & other_keywords)
        if overlap == 0:
            continue
        if getattr(fb.food, 'id', None) != getattr(food, 'id', None):
            if not _tokenize_text(f"{getattr(fb.food, 'name', '')} {getattr(fb.food, 'category_name', '')}") & food_tokens:
                continue

        sim = overlap / max(1, len(profile_keywords | other_keywords))
        rating_boost = 1.0
        if getattr(fb, 'rating', None):
            rating_boost = min(1.5, max(0.5, float(fb.rating) / 5.0))
        total += sim * rating_boost
        weight += 1.0

    if weight == 0:
        return 0.0
    return max(0.0, min(1.0, total / weight))


def _behavior_signal(account, food: Food, user_query: Optional[str] = None) -> float:
    if not account or not food:
        return 0.0

    score = 0.0
    query = (user_query or '').strip().lower()
    if query:
        sim = _text_similarity(query, f"{getattr(food, 'category_name', '')} {getattr(food, 'name', '')}")
        score += min(0.4, sim * 0.4)

    recent_food_ids = set(get_personalization_context(account).get('recent_food_ids') or [])
    if getattr(food, 'id', None) in recent_food_ids:
        score -= 0.15

    shown = AIRecommendation.objects.filter(account=account, food=food).count()
    if shown:
        score += min(0.1, shown / 100.0)

    feedback_avg = UserFeedbackFood.objects.filter(account=account, food=food).aggregate(avg_rating=Avg('rating')).get('avg_rating')
    if feedback_avg:
        score += min(0.15, float(feedback_avg) / 10.0)

    return max(0.0, min(1.0, score))


def hybrid_rank_food_candidates(account, foods: Iterable[Food], limit: int = 10, user_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Hybrid recommender = content-based + collaborative + constraints + behavior."""
    candidates = list(foods or [])
    if not candidates:
        return []

    safe_foods = filter_food_candidates(account, candidates)
    if not safe_foods:
        return []

    ranked: List[Dict[str, Any]] = []
    for food in safe_foods:
        content = score_food_for_user(account, food, user_query=user_query)
        collaborative = _collaborative_food_signal(account, food)
        behavior = _behavior_signal(account, food, user_query=user_query)

        final_score = (
            0.48 * float(content.score) +
            0.22 * collaborative +
            0.18 * behavior
        )

        reasons = list(content.reasons)
        if collaborative > 0:
            reasons.append('Nguoi dung tuong tu da thich mon nay')
        if behavior > 0:
            reasons.append('Phu hop voi hanh vi va truy van gan day')

        profile = get_personalization_context(account).get('profile') if account else None
        if profile and getattr(profile, 'budget_limit', None) is not None:
            estimated_cost = getattr(food, 'estimated_cost', None)
            if estimated_cost is not None and float(estimated_cost or 0) <= float(profile.budget_limit or 0):
                final_score += 0.08
                reasons.append('Nam trong ngan sach')

        final_score = max(0.0, min(1.0, round(final_score, 4)))
        ranked.append({
            'food': food,
            'score': final_score,
            'reasons': reasons,
            'components': {
                'content': float(content.score),
                'collaborative': float(collaborative),
                'behavior': float(behavior),
            },
        })

    ranked.sort(key=lambda item: item['score'], reverse=True)
    return apply_bandit_ranking(account, ranked[:limit], user_query=user_query)


def _preferred_category_match(account, food: Food) -> bool:
    preference_profile = build_user_preference_profile(account) if account else None
    preferred_categories = _normalize_tokens(getattr(preference_profile, 'preferred_categories', None) or [])
    return bool(
        preferred_categories and
        _has_token_match(
            f"{getattr(food, 'category_name', '')} {getattr(food, 'name', '')}",
            preferred_categories,
            threshold=0.60,
        )
    )


def _budget_fit(account, food: Food) -> bool:
    profile = UserProfile.objects.filter(account=account).first() if account else None
    budget_limit = getattr(profile, 'budget_limit', None)
    estimated_cost = getattr(food, 'estimated_cost', None)
    if budget_limit is None or estimated_cost is None:
        return False
    return float(estimated_cost or 0) <= float(budget_limit or 0)


def _health_fit(account, food: Food) -> bool:
    if not account:
        return False
    profile = UserProfile.objects.filter(account=account).first()
    diseases = list(UserDisease.objects.filter(account=account).select_related('disease'))
    profile_text = ' '.join([
        str(getattr(profile, 'health_goal', '') or ''),
        str(getattr(profile, 'medical_conditions', '') or ''),
        str(getattr(profile, 'dietary_preferences', '') or ''),
    ])
    disease_names = ' '.join(
        getattr(item.disease, 'name', '') for item in diseases if getattr(item, 'disease', None)
    )
    context_text = f'{profile_text} {disease_names}'.strip()
    if not context_text:
        return False
    diabetes_keywords = ['diabetes', 'tiểu đường', 'tieu duong', 'đái tháo đường']
    low_fat_keywords = ['gan nhiễm mỡ', 'gan nhiem mo', 'mỡ gan', 'mo gan', 'thanh đạm', 'it chat beo']

    if _has_token_match(context_text, diabetes_keywords, threshold=0.60):
        return bool(getattr(food, 'is_diabetes_friendly', False))
    if _has_token_match(context_text, low_fat_keywords, threshold=0.60):
        return float(getattr(food, 'fat', 0) or 0) <= 15
    return False


def _query_match(user_query: Optional[str], food: Food) -> bool:
    if not user_query:
        return False
    return _text_similarity(user_query, f"{getattr(food, 'category_name', '')} {getattr(food, 'name', '')}") >= 0.20


def _build_bandit_context(account, food: Food, user_query: Optional[str] = None) -> Dict[str, Any]:
    recent_food_ids = set(get_personalization_context(account).get('recent_food_ids') or []) if account else set()
    return {
        'query_match': _query_match(user_query, food),
        'preferred_category': _preferred_category_match(account, food),
        'budget_fit': _budget_fit(account, food),
        'health_fit': _health_fit(account, food),
        'recent_repeat': getattr(food, 'id', None) in recent_food_ids,
    }


def _bandit_state_from_history(account, user_query: Optional[str] = None) -> Dict[str, float]:
    if not account:
        return {'confidence_scale': 0.12, 'cold_start': 1.0}

    shown = AIRecommendation.objects.filter(account=account).count()
    clicked = SearchEvent.objects.filter(account=account, clicked_food__isnull=False).count()
    recommendation_feedback = UserFeedbackRecommendation.objects.filter(account=account).count()
    food_feedback = UserFeedbackFood.objects.filter(account=account).count()

    total_signal = shown + clicked + recommendation_feedback + food_feedback
    confidence_scale = 0.16 if total_signal < 10 else 0.10 if total_signal < 50 else 0.06
    cold_start = 1.0 if total_signal < 10 else 0.5 if total_signal < 50 else 0.25

    return {
        'confidence_scale': confidence_scale,
        'cold_start': cold_start,
        'shown': float(shown),
        'clicked': float(clicked),
        'recommendation_feedback': float(recommendation_feedback),
        'food_feedback': float(food_feedback),
    }


def _estimate_reward(account, food: Food) -> float:
    if not account or not food:
        return 0.0

    reward = 0.0
    liked = UserFeedbackFood.objects.filter(account=account, food=food, is_liked=True).count()
    rating_avg = UserFeedbackFood.objects.filter(account=account, food=food).aggregate(avg_rating=Avg('rating')).get('avg_rating')
    clicks = SearchEvent.objects.filter(account=account, clicked_food=food).count()
    recs = AIRecommendation.objects.filter(account=account, food=food).count()

    reward += min(1.0, liked * 0.6)
    if rating_avg:
        reward += min(0.4, float(rating_avg) / 5.0 * 0.4)
    reward += min(0.25, clicks * 0.15)
    reward += min(0.15, recs * 0.03)
    return max(0.0, min(1.0, reward))


def _extract_feedback_reward(feedback: UserFeedbackRecommendation) -> float:
    reward = 0.0
    if feedback.was_accepted:
        reward += 0.65
    if feedback.was_helpful:
        reward += 0.35
    return max(0.0, min(1.0, reward))


def _load_contextual_feedback(account, limit: int = 250) -> List[Dict[str, Any]]:
    if not account:
        return []

    events: List[Dict[str, Any]] = []

    for feedback in UserFeedbackRecommendation.objects.filter(account=account).order_by('-created_at')[:limit]:
        context = feedback.context if isinstance(feedback.context, dict) else {}
        bandit_context = context.get('bandit_context') if isinstance(context.get('bandit_context'), dict) else {}
        events.append({
            'food_id': getattr(feedback.food, 'id', None),
            'reward': _extract_feedback_reward(feedback),
            'context': bandit_context,
        })

    for feedback in UserFeedbackFood.objects.filter(account=account).order_by('-created_at')[:limit]:
        reward = 0.0
        if feedback.is_liked:
            reward += 0.6
        if feedback.rating is not None:
            reward += min(0.4, max(0.0, float(feedback.rating) / 5.0 * 0.4))
        events.append({
            'food_id': getattr(feedback.food, 'id', None),
            'reward': max(0.0, min(1.0, reward)),
            'context': {},
        })

    for event in SearchEvent.objects.filter(account=account, clicked_food__isnull=False).order_by('-created_at')[:limit]:
        events.append({
            'food_id': getattr(event.clicked_food, 'id', None),
            'reward': 0.35,
            'context': {},
        })

    return events


def _context_overlap_score(current: Dict[str, Any], observed: Dict[str, Any]) -> float:
    if not observed:
        return 0.0

    matches = 0
    comparable = 0
    for key, value in current.items():
        if key not in observed:
            continue
        comparable += 1
        if bool(observed.get(key)) == bool(value):
            matches += 1

    if comparable == 0:
        return 0.0
    return matches / comparable


def _contextual_bandit_components(account, food: Food, user_query: Optional[str] = None) -> Dict[str, Any]:
    context = _build_bandit_context(account, food, user_query=user_query)
    history = _load_contextual_feedback(account)

    weighted_reward = 0.0
    weighted_count = 0.0
    same_food_hits = 0.0

    for event in history:
        reward = float(event.get('reward', 0.0) or 0.0)
        if reward <= 0:
            continue

        overlap = _context_overlap_score(context, event.get('context') or {})
        same_food = 1.0 if event.get('food_id') == getattr(food, 'id', None) else 0.0
        weight = 0.20 + (0.55 * overlap) + (0.60 * same_food)

        weighted_reward += reward * weight
        weighted_count += weight
        same_food_hits += same_food

    alpha = 1.0 + weighted_reward
    beta = 1.0 + max(0.0, weighted_count - weighted_reward)
    posterior_mean = alpha / max(1.0, alpha + beta)
    uncertainty = math.sqrt((posterior_mean * (1.0 - posterior_mean)) / max(1.0, alpha + beta + 1.0))

    return {
        'context': context,
        'posterior_mean': max(0.0, min(1.0, posterior_mean)),
        'uncertainty': max(0.0, uncertainty),
        'same_food_hits': same_food_hits,
        'evidence_weight': weighted_count,
    }


def apply_bandit_ranking(account, ranked_items: List[Dict[str, Any]], user_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Contextual UCB re-ranker using reward history from clicks and feedback."""
    if not ranked_items:
        return []

    state = _bandit_state_from_history(account, user_query=user_query)
    confidence_scale = float(state.get('confidence_scale', 0.12))
    cold_start = float(state.get('cold_start', 1.0))

    reranked: List[Dict[str, Any]] = []
    for index, item in enumerate(ranked_items):
        food = item.get('food')
        base_score = float(item.get('score', 0.0))
        reward = _estimate_reward(account, food)
        contextual = _contextual_bandit_components(account, food, user_query=user_query)
        posterior_mean = float(contextual.get('posterior_mean', 0.5))
        uncertainty = float(contextual.get('uncertainty', 0.0))
        evidence_weight = float(contextual.get('evidence_weight', 0.0))
        exploration_bonus = confidence_scale * uncertainty * (1.0 + cold_start)
        novelty_bonus = 0.02 if not contextual['context'].get('recent_repeat') else -0.03
        sparse_history_bonus = 0.015 if evidence_weight < 1.0 and index >= 1 else 0.0

        bandit_score = max(
            0.0,
            min(
                1.0,
                round(
                    (0.64 * base_score) +
                    (0.20 * posterior_mean) +
                    (0.10 * reward) +
                    exploration_bonus +
                    novelty_bonus +
                    sparse_history_bonus,
                    4,
                ),
            ),
        )
        reranked.append({
            **item,
            'score': bandit_score,
            'bandit': {
                'base_score': base_score,
                'estimated_reward': reward,
                'posterior_mean': posterior_mean,
                'uncertainty': uncertainty,
                'confidence_scale': confidence_scale,
                'exploration_bonus': round(exploration_bonus, 4),
                'novelty_bonus': novelty_bonus,
                'evidence_weight': evidence_weight,
                'context': contextual.get('context', {}),
            },
        })

    reranked.sort(key=lambda item: item['score'], reverse=True)
    return reranked


def persist_recommendation_impressions(
    account,
    ranked_items: List[Dict[str, Any]],
    user_query: Optional[str] = None,
    source: str = 'personalization',
) -> List[Dict[str, Any]]:
    if not account or not ranked_items:
        return ranked_items

    enriched: List[Dict[str, Any]] = []
    for item in ranked_items:
        food = item.get('food')
        if not food:
            enriched.append(item)
            continue

        score = float(item.get('score', 0.0) or 0.0)
        bandit = item.get('bandit') or {}
        bandit_context = bandit.get('context') if isinstance(bandit.get('context'), dict) else _build_bandit_context(account, food, user_query=user_query)
        reason_text = '; '.join(item.get('reasons') or [])

        recommendation = None
        try:
            recommendation = MealRecommendation.objects.create(
                account=account,
                food=food,
                score=score,
                match_score=bandit.get('posterior_mean'),
                budget_score=1.0 if bandit_context.get('budget_fit') else 0.0,
                health_score=1.0 if bandit_context.get('health_fit') else 0.0,
                reason=reason_text[:1000],
                ai_model_version='contextual-bandit-v2',
            )
        except Exception:
            recommendation = None

        try:
            AIRecommendation.objects.create(
                account=account,
                food=food,
                score=score,
                budget_match_score=1.0 if bandit_context.get('budget_fit') else 0.0,
                estimated_cost=getattr(food, 'estimated_cost', None),
                reason=reason_text[:1000],
            )
        except Exception:
            pass

        enriched.append({
            **item,
            'recommendation_id': getattr(recommendation, 'id', None),
            'bandit_context': bandit_context,
            'source': source,
        })

    return enriched


def log_recommendation_bandit_event(account, food: Food, event_type: str, score: float = 0.0, metadata: Optional[Dict[str, Any]] = None) -> bool:
    if not account or not food:
        return False
    try:
        experiment = Experiment.objects.filter(status='active').order_by('-created_at').first()
        if not experiment:
            return False
        variant_name = 'bandit_v1'
        ExperimentEvent.objects.create(
            experiment=experiment,
            account=account,
            event_type=event_type,
            variant_name=variant_name,
            food=food,
            value=score,
            metadata=metadata or {},
        )
        return True
    except Exception:
        return False


def semantic_search_foods(query: str, limit: int = 50) -> List[Food]:
    """Lightweight semantic-like search over Food name and category using token similarity.

    This does not require external vector DBs and works by computing token
    Jaccard similarity between the query and food name/category. It is
    designed as a stopgap before adding embeddings+FAISS.
    """
    if not query:
        return []

    # Minimum similarity to consider a match (tunable)
    SEMANTIC_SIMILARITY_THRESHOLD = 0.10

    try:
        foods = list(Food.objects.all().order_by('name')[:500])
    except Exception:
        return []

    scored = []
    for food in foods:
        name = (getattr(food, 'name', '') or '')
        category = ''
        if getattr(food, 'category', None) and getattr(food.category, 'name', None):
            category = food.category.name
        elif getattr(food, 'category_name', None):
            category = str(food.category_name)

        sim = _text_similarity(query, f"{category} {name}")
        if sim >= SEMANTIC_SIMILARITY_THRESHOLD:
            scored.append((sim, food))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [f for _, f in scored[:limit]]


def semantic_search_with_scores(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Return foods with similarity scores for provenance.

    Returns a list of dicts: {'food': Food, 'similarity': float}
    """
    if not query:
        return []

    try:
        foods = list(Food.objects.all().order_by('name')[:500])
    except Exception:
        return []

    scored = []
    for food in foods:
        name = (getattr(food, 'name', '') or '')
        category = ''
        if getattr(food, 'category', None) and getattr(food.category, 'name', None):
            category = food.category.name
        elif getattr(food, 'category_name', None):
            category = str(food.category_name)

        sim = _text_similarity(query, f"{category} {name}")
        if sim >= 0.0:
            scored.append((sim, food))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [{'food': f, 'similarity': float(s)} for s, f in scored[:limit]]


def log_ai_recommendation(account, food: Food, score: float, reason: str = '', model_version: str = 'internal-v1'):
    if not account or not food:
        return None
    return AIRecommendation.objects.create(
        account=account,
        food=food,
        score=score,
        reason=reason,
        stt=None,
    )


def summarize_ai_activity(account) -> Dict[str, Any]:
    if not account:
        return {
            'searches': 0,
            'recommendations': 0,
            'recent_food_logs': 0,
        }

    return {
        'searches': SearchEvent.objects.filter(account=account).count(),
        'recommendations': AIRecommendation.objects.filter(account=account).count(),
        'recent_food_logs': NutritionLog.objects.filter(account=account).count(),
    }
