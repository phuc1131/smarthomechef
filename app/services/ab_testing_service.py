"""
A/B Testing Service for Smart Home Chef
- Experiment assignment and variant tracking
- Metrics collection and analysis
- Statistical significance testing
"""

import hashlib
import random
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db.models import Avg, Count, StdDev, Q
from django.utils import timezone

from apps.core_models.ai_learning_models import (
    Experiment,
    ExperimentAssignment,
    ExperimentMetric,
    ExperimentEvent,
)
from apps.users.models import Account


class ABTestingService:
    """Service for managing A/B tests and variant assignments"""

    AI_ROUTE_EXPERIMENT_NAME = 'ai_route_comparison'
    AI_ROUTE_CONTROL = 'local_rule'
    AI_ROUTE_VARIANTS = ['semantic_router', 'gemini_rag', 'local_llm']
    AI_ROUTE_ALL_VARIANTS = [AI_ROUTE_CONTROL] + AI_ROUTE_VARIANTS

    @staticmethod
    def ensure_ai_route_experiment() -> Optional[Experiment]:
        """Create the default AI-routing experiment if it does not exist."""
        now = timezone.now()
        try:
            experiment, _ = Experiment.objects.get_or_create(
                name=ABTestingService.AI_ROUTE_EXPERIMENT_NAME,
                defaults={
                    'description': (
                        'Compare AI routing strategies: local rule, semantic router, '
                        'Gemini/RAG, and local LLM.'
                    ),
                    'status': 'active',
                    'control_variant': ABTestingService.AI_ROUTE_CONTROL,
                    'test_variants': ABTestingService.AI_ROUTE_VARIANTS,
                    'assignment_strategy': 'hash',
                    'traffic_allocation': 100,
                    'started_at': now,
                },
            )
            return experiment
        except Exception:
            return None

    @staticmethod
    def get_ai_route_variant(account: Optional[Account]) -> Optional[Dict[str, object]]:
        """Resolve the assigned A/B variant for AI routing experiments."""
        if not account:
            return None

        experiment = ABTestingService.ensure_ai_route_experiment()
        if not experiment:
            return None

        variant_name = ABTestingService.assign_variant(experiment.id, account)
        if not variant_name:
            return None

        return {
            'experiment_id': experiment.id,
            'experiment_name': experiment.name,
            'variant_name': variant_name,
        }

    @staticmethod
    def assign_variant(experiment_id: int, account: Account) -> Optional[str]:
        """
        Assign a user to an experiment variant.
        Returns the variant name or None if user not assigned.
        """
        try:
            experiment = Experiment.objects.get(id=experiment_id)
        except Experiment.DoesNotExist:
            return None

        # Check if experiment is active
        if not experiment.is_active():
            return None

        # Check traffic allocation
        if experiment.traffic_allocation < 100:
            if not ABTestingService._should_include_in_traffic(account.id, experiment.traffic_allocation):
                return None

        # Check if user already assigned
        try:
            assignment = ExperimentAssignment.objects.get(
                experiment=experiment, 
                account=account
            )
            return assignment.variant_name
        except ExperimentAssignment.DoesNotExist:
            pass

        # Assign based on strategy
        if experiment.assignment_strategy == 'hash':
            variant = ABTestingService._hash_based_assignment(account.id, experiment)
        elif experiment.assignment_strategy == 'random':
            variant = ABTestingService._random_assignment(experiment)
        else:
            variant = experiment.control_variant

        # Record assignment
        ExperimentAssignment.objects.create(
            experiment=experiment,
            account=account,
            variant_name=variant,
        )

        return variant

    @staticmethod
    def _should_include_in_traffic(user_id: int, traffic_allocation: int) -> bool:
        """Deterministically check if user should be in traffic sample"""
        hash_value = int(hashlib.md5(f"{user_id}".encode()).hexdigest(), 16)
        return (hash_value % 100) < traffic_allocation

    @staticmethod
    def _hash_based_assignment(user_id: int, experiment: Experiment) -> str:
        """Hash-based deterministic assignment"""
        all_variants = experiment.get_all_variants()
        hash_value = int(hashlib.md5(f"{user_id}_{experiment.id}".encode()).hexdigest(), 16)
        variant_idx = hash_value % len(all_variants)
        return all_variants[variant_idx]

    @staticmethod
    def _random_assignment(experiment: Experiment) -> str:
        """Random assignment"""
        all_variants = experiment.get_all_variants()
        return random.choice(all_variants)

    @staticmethod
    def record_event(
        experiment_id: int,
        account: Account,
        event_type: str,
        variant_name: Optional[str] = None,
        food_id: Optional[int] = None,
        value: Optional[float] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Record an event for experiment tracking.
        Event types: recommendation_shown, recommendation_clicked, recommendation_rated
        """
        try:
            experiment = Experiment.objects.get(id=experiment_id)
        except Experiment.DoesNotExist:
            return False

        # If variant not provided, get from assignment
        if not variant_name:
            variant_name = ABTestingService.assign_variant(experiment_id, account)
            if not variant_name:
                return False

        from apps.nutrition.models import Food
        food_obj = None
        if food_id:
            try:
                food_obj = Food.objects.get(id=food_id)
            except Food.DoesNotExist:
                pass

        ExperimentEvent.objects.create(
            experiment=experiment,
            account=account,
            event_type=event_type,
            variant_name=variant_name,
            food=food_obj,
            value=value,
            metadata=metadata or {},
        )

        return True

    @staticmethod
    def record_ai_route_event(
        account: Optional[Account],
        event_type: str,
        variant_name: Optional[str] = None,
        value: Optional[float] = None,
        metadata: Optional[Dict] = None,
        food_id: Optional[int] = None,
    ) -> bool:
        """Record route-level A/B events for AI orchestration experiments."""
        if not account:
            return False

        experiment = ABTestingService.ensure_ai_route_experiment()
        if not experiment:
            return False

        resolved_variant = variant_name
        if not resolved_variant:
            assignment = ABTestingService.get_ai_route_variant(account)
            resolved_variant = assignment.get('variant_name') if assignment else None
        if not resolved_variant:
            return False

        return ABTestingService.record_event(
            experiment_id=experiment.id,
            account=account,
            event_type=event_type,
            variant_name=resolved_variant,
            food_id=food_id,
            value=value,
            metadata=metadata,
        )

    @staticmethod
    def calculate_metrics(experiment_id: int, variant_name: Optional[str] = None) -> Dict:
        """
        Calculate metrics for an experiment or specific variant.
        Returns dict with metric calculations.
        """
        try:
            experiment = Experiment.objects.get(id=experiment_id)
        except Experiment.DoesNotExist:
            return {}

        events_qs = ExperimentEvent.objects.filter(experiment=experiment)
        if variant_name:
            events_qs = events_qs.filter(variant_name=variant_name)

        metrics = {}

        # Click-through rate
        shown = events_qs.filter(event_type='recommendation_shown').count()
        clicked = events_qs.filter(event_type='recommendation_clicked').count()
        metrics['click_through_rate'] = clicked / shown if shown > 0 else 0

        # Conversion rate (click as conversion)
        metrics['conversion_rate'] = metrics['click_through_rate']

        # Average rating
        rated_events = events_qs.filter(event_type='recommendation_rated')
        ratings = rated_events.filter(value__isnull=False).values_list('value', flat=True)
        if ratings:
            metrics['avg_rating'] = float(sum(ratings)) / len(ratings)
        else:
            metrics['avg_rating'] = 0

        # Food acceptance (accepted = clicked + rated)
        total_shown = shown
        accepted = clicked
        metrics['food_acceptance_rate'] = accepted / total_shown if total_shown > 0 else 0

        # Engagement score (weighted)
        engagement = (
            (clicked * 0.3) +  # Click weight
            (len(ratings) * 0.7)  # Rating weight
        )
        metrics['engagement_score'] = engagement / total_shown if total_shown > 0 else 0

        return metrics

    @staticmethod
    def get_variant_stats(experiment_id: int) -> Dict:
        """Get aggregate statistics for all variants"""
        try:
            experiment = Experiment.objects.get(id=experiment_id)
        except Experiment.DoesNotExist:
            return {}

        all_variants = experiment.get_all_variants()
        stats = {}

        for variant in all_variants:
            variant_events = ExperimentEvent.objects.filter(
                experiment=experiment,
                variant_name=variant,
            )

            shown = variant_events.filter(event_type='recommendation_shown').count()
            clicked = variant_events.filter(event_type='recommendation_clicked').count()
            
            ratings = variant_events.filter(
                event_type='recommendation_rated',
                value__isnull=False,
            ).values_list('value', flat=True)

            stats[variant] = {
                'total_events': variant_events.count(),
                'users': variant_events.values('account').distinct().count(),
                'recommendations_shown': shown,
                'recommendations_clicked': clicked,
                'click_through_rate': clicked / shown if shown > 0 else 0,
                'avg_rating': float(sum(ratings)) / len(ratings) if ratings else 0,
                'total_ratings': len(ratings),
            }

        return stats

    @staticmethod
    def is_variant_winner(experiment_id: int, min_significance: float = 0.05) -> Optional[str]:
        """
        Simple statistical significance test (Chi-square style).
        Returns winning variant name if significant difference, else None.
        """
        stats = ABTestingService.get_variant_stats(experiment_id)
        if len(stats) < 2:
            return None

        variants = list(stats.keys())
        
        # Compare first two variants by CTR
        control_ctr = stats[variants[0]]['click_through_rate']
        test_ctr = stats[variants[1]]['click_through_rate']
        
        # Simple difference test (not true chi-square)
        control_shown = stats[variants[0]]['recommendations_shown']
        test_shown = stats[variants[1]]['recommendations_shown']
        
        if control_shown == 0 or test_shown == 0:
            return None

        # Calculate z-score for proportion difference
        p_overall = (control_ctr * control_shown + test_ctr * test_shown) / (control_shown + test_shown)
        se = (p_overall * (1 - p_overall) * (1/control_shown + 1/test_shown)) ** 0.5
        
        if se == 0:
            return None
            
        z_score = abs(control_ctr - test_ctr) / se
        
        # ~95% confidence requires z > 1.96
        if z_score > 1.96:
            winner = variants[0] if control_ctr > test_ctr else variants[1]
            return winner

        return None

    @staticmethod
    def log_metric(experiment_id: int, variant_name: str, metric_type: str, value: float):
        """Log a metric for aggregated analysis"""
        try:
            experiment = Experiment.objects.get(id=experiment_id)
        except Experiment.DoesNotExist:
            return False

        try:
            metric_obj, created = ExperimentMetric.objects.get_or_create(
                experiment=experiment,
                variant_name=variant_name,
                metric_type=metric_type,
                defaults={'value': value, 'count': 1}
            )

            if not created:
                # Update existing metric (simple average)
                new_mean = (metric_obj.value * metric_obj.count + value) / (metric_obj.count + 1)
                metric_obj.value = new_mean
                metric_obj.count += 1
                metric_obj.save()

            return True
        except Exception:
            return False

    @staticmethod
    def get_experiment_summary(experiment_id: int) -> Dict:
        """Get comprehensive summary of experiment"""
        try:
            experiment = Experiment.objects.get(id=experiment_id)
        except Experiment.DoesNotExist:
            return {}

        variant_stats = ABTestingService.get_variant_stats(experiment_id)
        winner = ABTestingService.is_variant_winner(experiment_id)

        summary = {
            'experiment': {
                'id': experiment.id,
                'name': experiment.name,
                'status': experiment.status,
                'is_active': experiment.is_active(),
                'created_at': experiment.created_at.isoformat(),
                'started_at': experiment.started_at.isoformat() if experiment.started_at else None,
                'ended_at': experiment.ended_at.isoformat() if experiment.ended_at else None,
            },
            'variants': variant_stats,
            'winner': winner,
            'total_events': sum(v['total_events'] for v in variant_stats.values()),
            'total_users': sum(v['users'] for v in variant_stats.values()),
        }

        return summary
