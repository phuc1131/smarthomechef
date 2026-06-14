"""
Tests for A/B Testing Service
"""
import pytest
from datetime import datetime, timedelta
from django.utils import timezone

from apps.users.models import Account
from apps.nutrition.models import Food, FoodCategory
from apps.core_models.ai_learning_models import Experiment, ExperimentAssignment
from app.services.ab_testing_service import ABTestingService


pytestmark = pytest.mark.django_db


@pytest.fixture
def test_user():
    return Account.objects.create(
        username="test_ab_user",
        email="test_ab@test.com",
        password_hash="hash",
        role="user",
        is_active=True,
    )


@pytest.fixture
def test_food():
    category, _ = FoodCategory.objects.get_or_create(name="Test Category")
    return Food.objects.create(
        name="Test Food",
        category=category,
        calories=100,
        protein=10,
        carbs=10,
        fat=5,
    )


@pytest.fixture
def active_experiment():
    now = timezone.now()
    return Experiment.objects.create(
        name="test_experiment_active",
        description="Active test experiment",
        status="active",
        control_variant="control",
        test_variants=["variant_a", "variant_b"],
        assignment_strategy="hash",
        traffic_allocation=100,
        started_at=now - timedelta(days=1),
        ended_at=now + timedelta(days=7),
    )


@pytest.fixture
def inactive_experiment():
    return Experiment.objects.create(
        name="test_experiment_draft",
        description="Draft experiment",
        status="draft",
        control_variant="control",
        test_variants=["variant_a"],
    )


def test_assign_variant_hash_based(test_user, active_experiment):
    """Test hash-based variant assignment"""
    variant1 = ABTestingService.assign_variant(active_experiment.id, test_user)
    assert variant1 in [active_experiment.control_variant] + active_experiment.test_variants
    
    # Should return same variant on second call (deterministic)
    variant2 = ABTestingService.assign_variant(active_experiment.id, test_user)
    assert variant1 == variant2


def test_assign_variant_inactive_experiment(test_user, inactive_experiment):
    """Test that inactive experiments don't assign variants"""
    variant = ABTestingService.assign_variant(inactive_experiment.id, test_user)
    assert variant is None


def test_assign_variant_traffic_allocation(test_user, active_experiment):
    """Test traffic allocation filtering"""
    experiment_limited = Experiment.objects.create(
        name="test_experiment_limited",
        description="Limited traffic",
        status="active",
        control_variant="control",
        test_variants=["variant_a"],
        traffic_allocation=1,  # 1% of users
        started_at=timezone.now() - timedelta(days=1),
        ended_at=timezone.now() + timedelta(days=7),
    )
    
    # Most users should be excluded
    # Create a user with ID unlikely to be in 1% traffic
    included_count = 0
    for i in range(100):
        account = Account.objects.create(
            username=f"traffic_test_{i}",
            email=f"traffic_{i}@test.com",
            password_hash="hash",
            role="user",
            is_active=True,
        )
        variant = ABTestingService.assign_variant(experiment_limited.id, account)
        if variant:
            included_count += 1
    
    # Should be roughly 1% included (0-5% tolerance)
    percentage = (included_count / 100) * 100
    assert 0 <= percentage <= 5, f"Traffic allocation {percentage}% outside expected 1%"


def test_record_event(test_user, test_food, active_experiment):
    """Test event recording"""
    success = ABTestingService.record_event(
        experiment_id=active_experiment.id,
        account=test_user,
        event_type="recommendation_shown",
        value=1.0,
    )
    assert success is True
    
    # Verify assignment and event created
    assignment = ExperimentAssignment.objects.filter(
        experiment=active_experiment,
        account=test_user,
    ).first()
    assert assignment is not None


def test_record_event_with_food(test_user, test_food, active_experiment):
    """Test event recording with food"""
    success = ABTestingService.record_event(
        experiment_id=active_experiment.id,
        account=test_user,
        event_type="recommendation_clicked",
        food_id=test_food.id,
        value=1.0,
    )
    assert success is True


def test_calculate_metrics(test_user, active_experiment):
    """Test metrics calculation"""
    # Record events
    ABTestingService.record_event(
        active_experiment.id, test_user,
        "recommendation_shown", value=1.0
    )
    ABTestingService.record_event(
        active_experiment.id, test_user,
        "recommendation_clicked", value=1.0
    )
    
    metrics = ABTestingService.calculate_metrics(active_experiment.id)
    assert metrics is not None
    assert 'click_through_rate' in metrics
    assert metrics['click_through_rate'] > 0


def test_get_variant_stats(test_user, active_experiment):
    """Test variant statistics"""
    # Record events for control variant
    ABTestingService.record_event(
        active_experiment.id, test_user,
        "recommendation_shown"
    )
    
    stats = ABTestingService.get_variant_stats(active_experiment.id)
    assert stats is not None
    assert len(stats) > 0


def test_experiment_summary(test_user, active_experiment):
    """Test experiment summary generation"""
    # Record some events
    ABTestingService.record_event(
        active_experiment.id, test_user,
        "recommendation_shown"
    )
    
    summary = ABTestingService.get_experiment_summary(active_experiment.id)
    
    assert summary is not None
    assert 'experiment' in summary
    assert summary['experiment']['name'] == active_experiment.name
    assert 'variants' in summary
    assert 'total_events' in summary
    assert summary['total_events'] >= 1


def test_experiment_is_active(active_experiment, inactive_experiment):
    """Test experiment active status check"""
    assert active_experiment.is_active() is True
    assert inactive_experiment.is_active() is False


def test_experiment_get_all_variants(active_experiment):
    """Test getting all variants"""
    all_variants = active_experiment.get_all_variants()
    assert active_experiment.control_variant in all_variants
    for var in active_experiment.test_variants:
        assert var in all_variants


def test_ensure_ai_route_experiment_creates_default_variants():
    experiment = ABTestingService.ensure_ai_route_experiment()
    assert experiment is not None
    assert experiment.name == ABTestingService.AI_ROUTE_EXPERIMENT_NAME
    assert experiment.control_variant == 'local_rule'
    assert experiment.test_variants == ['semantic_router', 'gemini_rag', 'local_llm']


def test_get_ai_route_variant_assigns_known_variant(test_user):
    assignment = ABTestingService.get_ai_route_variant(test_user)
    assert assignment is not None
    assert assignment['variant_name'] in ABTestingService.AI_ROUTE_ALL_VARIANTS
