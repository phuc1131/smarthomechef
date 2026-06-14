from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from app.config import GEMINI_ESTIMATED_COST_USD, LOCAL_LLM_ESTIMATED_COST_USD
from apps.core_models.ai_learning_models import AIRequestLog, UserFeedbackFood, UserFeedbackRecommendation


LOCAL_PROVIDERS = {'local_rule', 'local_llm'}


def estimate_ai_request_cost(provider: str) -> Decimal:
    normalized = str(provider or '').strip().lower()
    if normalized == 'gemini':
        return Decimal(str(GEMINI_ESTIMATED_COST_USD or 0.0))
    if normalized == 'local_llm':
        return Decimal(str(LOCAL_LLM_ESTIMATED_COST_USD or 0.0))
    return Decimal('0')


def log_ai_request(
    *,
    account=None,
    chat_session=None,
    query_text: str = '',
    normalized_query: str = '',
    intent_name: str = '',
    provider: str = '',
    route_path: str = '',
    decision: str = '',
    ab_variant: str = '',
    cache_hit: bool = False,
    latency_ms: int = 0,
    response_ok: bool = True,
    estimated_cost_usd: Decimal | None = None,
    metadata: Dict[str, Any] | None = None,
):
    provider_name = str(provider or 'fallback').strip().lower() or 'fallback'
    return AIRequestLog.objects.create(
        account=account,
        session_id=getattr(chat_session, 'id', None),
        query_text=str(query_text or ''),
        normalized_query=str(normalized_query or ''),
        intent_name=str(intent_name or ''),
        provider=provider_name,
        route_path=str(route_path or ''),
        decision=str(decision or ''),
        ab_variant=str(ab_variant or ''),
        cache_hit=bool(cache_hit),
        latency_ms=max(0, int(latency_ms or 0)),
        estimated_cost_usd=estimated_cost_usd if estimated_cost_usd is not None else estimate_ai_request_cost(provider_name),
        response_ok=bool(response_ok),
        metadata=metadata or {},
    )


def get_ai_quality_dashboard(days: int = 7) -> Dict[str, Any]:
    now = timezone.now()
    since = now - timedelta(days=max(1, int(days or 7)) - 1)
    logs = AIRequestLog.objects.filter(created_at__gte=since).order_by('created_at')

    total_requests = logs.count()
    provider_counts = {
        row['provider']: row['total']
        for row in logs.values('provider').annotate(total=Count('id'))
    }
    local_count = sum(provider_counts.get(name, 0) for name in LOCAL_PROVIDERS)
    gemini_count = provider_counts.get('gemini', 0)
    cache_count = provider_counts.get('cache', 0)

    aggregates = logs.aggregate(
        avg_latency_ms=Avg('latency_ms'),
        total_cost_usd=Sum('estimated_cost_usd'),
        avg_cost_usd=Avg('estimated_cost_usd'),
    )
    successful_requests = logs.filter(response_ok=True).count()

    feedback_qs = UserFeedbackRecommendation.objects.filter(created_at__gte=since)
    food_feedback_qs = UserFeedbackFood.objects.filter(created_at__gte=since)
    helpful_count = feedback_qs.filter(was_helpful=True).count()
    accepted_count = feedback_qs.filter(was_accepted=True).count()
    feedback_count = feedback_qs.count()
    avg_rating = food_feedback_qs.aggregate(value=Avg('rating')).get('value') or 0

    labels: List[str] = []
    local_series: List[int] = []
    gemini_series: List[int] = []
    cache_series: List[int] = []
    latency_series: List[float] = []

    for offset in range(max(1, int(days or 7))):
        day = (since + timedelta(days=offset)).date()
        day_logs = logs.filter(created_at__date=day)
        labels.append(day.strftime('%d/%m'))
        local_series.append(day_logs.filter(provider__in=LOCAL_PROVIDERS).count())
        gemini_series.append(day_logs.filter(provider='gemini').count())
        cache_series.append(day_logs.filter(provider='cache').count())
        day_avg_latency = day_logs.aggregate(value=Avg('latency_ms')).get('value') or 0
        latency_series.append(round(float(day_avg_latency), 1))

    provider_rows = []
    for provider_name in ('cache', 'local_rule', 'local_llm', 'gemini', 'fallback'):
        provider_logs = logs.filter(provider=provider_name)
        provider_total = provider_logs.count()
        if not provider_total:
            continue
        provider_rows.append({
            'provider': provider_name,
            'total': provider_total,
            'share': round((provider_total / total_requests) * 100, 1) if total_requests else 0.0,
            'avg_latency_ms': round(float(provider_logs.aggregate(value=Avg('latency_ms')).get('value') or 0), 1),
            'cost_usd': float(provider_logs.aggregate(value=Sum('estimated_cost_usd')).get('value') or 0),
        })

    return {
        'days': max(1, int(days or 7)),
        'summary': {
            'total_requests': total_requests,
            'local_rate': round((local_count / total_requests) * 100, 1) if total_requests else 0.0,
            'gemini_rate': round((gemini_count / total_requests) * 100, 1) if total_requests else 0.0,
            'cache_hit_rate': round((cache_count / total_requests) * 100, 1) if total_requests else 0.0,
            'avg_latency_ms': round(float(aggregates.get('avg_latency_ms') or 0), 1),
            'success_rate': round((successful_requests / total_requests) * 100, 1) if total_requests else 0.0,
            'total_cost_usd': float(aggregates.get('total_cost_usd') or 0),
            'avg_cost_usd': float(aggregates.get('avg_cost_usd') or 0),
            'feedback_count': feedback_count,
            'accepted_rate': round((accepted_count / feedback_count) * 100, 1) if feedback_count else 0.0,
            'helpful_rate': round((helpful_count / feedback_count) * 100, 1) if feedback_count else 0.0,
            'avg_rating': round(float(avg_rating or 0), 2),
        },
        'providers': provider_counts,
        'provider_rows': provider_rows,
        'trend': {
            'labels': labels,
            'local': local_series,
            'gemini': gemini_series,
            'cache': cache_series,
            'latency_ms': latency_series,
        },
    }
