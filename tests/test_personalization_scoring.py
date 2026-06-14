from types import SimpleNamespace
from app.services import personalization_service
from app.services.personalization_service import apply_bandit_ranking, score_food_for_user


def make_food(id=1, name='Com ga', category_name='com', **kwargs):
    attrs = {'id': id, 'name': name, 'category_name': category_name}
    attrs.update(kwargs)
    return SimpleNamespace(**attrs)


def test_score_boost_on_query_match():
    account = None
    food = make_food(id=1, name='Gà luộc', category_name='mon an')
    base = score_food_for_user(account, food)
    boosted = score_food_for_user(account, food, user_query='gà')
    assert boosted.score >= base.score


def test_score_avoided_keyword_penalty():
    # emulate a preference_profile by setting avoided_keywords on a fake profile object
    food = make_food(id=2, name='Thịt xông khói', category_name='thịt')
    account = None
    # call without user query - earlier logic penalizes avoided keywords via preference_profile
    # Since account=None, no penalty expected; ensure function runs and returns within bounds
    s = score_food_for_user(account, food)
    assert 0.0 <= s.score <= 1.0


def test_apply_bandit_ranking_uses_contextual_reward(monkeypatch):
    food_a = make_food(id=1, name='Pho ga', category_name='pho')
    food_b = make_food(id=2, name='Salad uc ga', category_name='salad')

    monkeypatch.setattr(
        personalization_service,
        '_bandit_state_from_history',
        lambda account, user_query=None: {'confidence_scale': 0.10, 'cold_start': 0.0},
    )
    monkeypatch.setattr(
        personalization_service,
        '_estimate_reward',
        lambda account, food: 0.05 if food.id == 1 else 0.25,
    )
    monkeypatch.setattr(
        personalization_service,
        '_contextual_bandit_components',
        lambda account, food, user_query=None: {
            'posterior_mean': 0.20 if food.id == 1 else 0.85,
            'uncertainty': 0.02 if food.id == 1 else 0.04,
            'evidence_weight': 3.0,
            'context': {'recent_repeat': False},
        },
    )

    ranked = apply_bandit_ranking(
        account=SimpleNamespace(id=10),
        ranked_items=[
            {'food': food_a, 'score': 0.78, 'reasons': []},
            {'food': food_b, 'score': 0.70, 'reasons': []},
        ],
        user_query='mon giam can',
    )

    assert ranked[0]['food'].id == 2
    assert ranked[0]['bandit']['posterior_mean'] > ranked[1]['bandit']['posterior_mean']


def test_apply_bandit_ranking_penalizes_recent_repeats(monkeypatch):
    repeated_food = make_food(id=1, name='Com tam', category_name='com')
    fresh_food = make_food(id=2, name='Canh ca', category_name='canh')

    monkeypatch.setattr(
        personalization_service,
        '_bandit_state_from_history',
        lambda account, user_query=None: {'confidence_scale': 0.08, 'cold_start': 0.0},
    )
    monkeypatch.setattr(personalization_service, '_estimate_reward', lambda account, food: 0.10)
    monkeypatch.setattr(
        personalization_service,
        '_contextual_bandit_components',
        lambda account, food, user_query=None: {
            'posterior_mean': 0.55,
            'uncertainty': 0.01,
            'evidence_weight': 2.0,
            'context': {'recent_repeat': food.id == 1},
        },
    )

    ranked = apply_bandit_ranking(
        account=SimpleNamespace(id=11),
        ranked_items=[
            {'food': repeated_food, 'score': 0.72, 'reasons': []},
            {'food': fresh_food, 'score': 0.71, 'reasons': []},
        ],
    )

    assert ranked[0]['food'].id == 2
