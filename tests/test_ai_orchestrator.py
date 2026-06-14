from app.services import ai_orchestrator_service as orchestrator
from app.features.user_panel.views import _make_chat_response_system_context, _cache_intent_matches


def test_orchestrate_returns_local_when_ranker_has_high_score(monkeypatch):
    from types import SimpleNamespace
    # avoid DB access by faking classify_intent to return a recommendation intent
    monkeypatch.setattr(orchestrator.AIOrchestratorService, 'classify_intent', staticmethod(lambda text: (SimpleNamespace(name='recommendation'), 0.9)))
    monkeypatch.setattr(orchestrator, 'rank_food_candidates', lambda account, foods, limit, user_query=None: [{'food': None, 'score': 0.7, 'reasons': []}])
    monkeypatch.setattr(orchestrator, 'GEMINI_ENABLED', False)
    # Provide a fake apps.nutrition.models module with Food.objects to avoid DB
    import sys, types
    fake_mod = types.SimpleNamespace()
    class FakeManager:
        def all(self):
            class QS:
                def order_by(self, *a, **k):
                    return [1, 2, 3]
            return QS()
    fake_mod.Food = types.SimpleNamespace(objects=FakeManager())
    monkeypatch.setitem(sys.modules, 'apps.nutrition.models', fake_mod)

    res = orchestrator.AIOrchestratorService.orchestrate('Gợi ý món ăn', None)
    assert res['path'] == 'local'
    assert 'candidates' in res and res['candidates']


def test_orchestrate_returns_intent_model_stale_flag(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(orchestrator.AIOrchestratorService, 'classify_intent', staticmethod(lambda text: (SimpleNamespace(name='recommendation'), 0.95)))
    monkeypatch.setattr(orchestrator, 'rank_food_candidates', lambda account, foods, limit, user_query=None: [{'food': None, 'score': 0.7, 'reasons': []}])
    monkeypatch.setattr(orchestrator, 'GEMINI_ENABLED', False)
    import sys, types
    fake_mod = types.SimpleNamespace()
    class FakeManager:
        def all(self):
            class QS:
                def order_by(self, *a, **k):
                    return [1, 2, 3]
            return QS()
    fake_mod.Food = types.SimpleNamespace(objects=FakeManager())
    monkeypatch.setitem(sys.modules, 'apps.nutrition.models', fake_mod)

    res = orchestrator.AIOrchestratorService.orchestrate('Gợi ý món ăn', None)
    assert 'intent_model_stale' in res
    assert isinstance(res['intent_model_stale'], bool)


def test_orchestrate_returns_gemini_on_low_confidence(monkeypatch):
    # force classify_intent to return low confidence
    monkeypatch.setattr(orchestrator.AIOrchestratorService, 'classify_intent', staticmethod(lambda text: (None, 0.0)))
    monkeypatch.setattr(orchestrator, 'GEMINI_ENABLED', True)
    res = orchestrator.AIOrchestratorService.orchestrate('Unclear query', None)
    assert res['path'] == 'gemini'
    assert 'personalization_context' in res


def test_orchestrate_gemini_includes_local_candidates_when_available(monkeypatch):
    from types import SimpleNamespace
    # force classify_intent to return intent but low confidence
    monkeypatch.setattr(orchestrator.AIOrchestratorService, 'classify_intent', staticmethod(lambda text: (SimpleNamespace(name='recommendation'), 0.4)))
    monkeypatch.setattr(orchestrator, 'GEMINI_ENABLED', True)
    monkeypatch.setattr(orchestrator, 'rank_food_candidates', lambda account, foods, limit, user_query=None: [{'food': SimpleNamespace(name='Bún chả'), 'score': 0.3, 'reasons': ['phù hợp']}])
    import sys, types
    class FakeManager:
        def all(self):
            class QS:
                def order_by(self, *a, **k):
                    return [1]
            return QS()
    fake_mod = types.SimpleNamespace(Food=types.SimpleNamespace(objects=FakeManager()))
    monkeypatch.setitem(sys.modules, 'apps.nutrition.models', fake_mod)
    res = orchestrator.AIOrchestratorService.orchestrate('Gợi ý món ăn giảm cân', None)
    assert res['path'] == 'gemini'
    assert 'candidates' in res
    assert res['candidates']


def test_orchestrate_gemini_includes_rag_evidence(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(orchestrator.AIOrchestratorService, 'classify_intent', staticmethod(lambda text: (None, 0.0)))
    monkeypatch.setattr(orchestrator, 'GEMINI_ENABLED', True)
    monkeypatch.setattr(orchestrator, 'rank_food_candidates', lambda account, foods, limit, user_query=None: [])

    import sys, types
    class FakeManager:
        def all(self):
            class QS:
                def order_by(self, *a, **k):
                    return [SimpleNamespace(name='Phở bò', category_name='Phở')]
            return QS()

    fake_mod = types.SimpleNamespace(
        Food=types.SimpleNamespace(objects=FakeManager()),
        Recipe=types.SimpleNamespace(objects=FakeManager()),
        Ingredient=types.SimpleNamespace(objects=FakeManager()),
    )
    monkeypatch.setitem(sys.modules, 'apps.nutrition.models', fake_mod)

    res = orchestrator.AIOrchestratorService.orchestrate('Tôi muốn món low carb', None)
    assert res['path'] == 'gemini'
    assert 'rag_evidence' in res
    evidence = res['rag_evidence']
    assert isinstance(evidence, dict)
    assert 'foods' in evidence
    assert 'recipes' in evidence
    assert 'ingredients' in evidence


def test_orchestrate_gemini_rag_evidence_includes_local_candidates(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(orchestrator.AIOrchestratorService, 'classify_intent', staticmethod(lambda text: (SimpleNamespace(name='recommendation'), 0.4)))
    monkeypatch.setattr(orchestrator, 'GEMINI_ENABLED', True)
    monkeypatch.setattr(orchestrator, 'rank_food_candidates', lambda account, foods, limit, user_query=None: [
        {'food': SimpleNamespace(name='Gỏi cuốn'), 'score': 0.3, 'reasons': ['phù hợp với người ăn ít dầu']}
    ])

    import sys, types
    class FakeManager:
        def all(self):
            class QS:
                def order_by(self, *a, **k):
                    return [1]
            return QS()

    fake_mod = types.SimpleNamespace(
        Food=types.SimpleNamespace(objects=FakeManager()),
        Recipe=types.SimpleNamespace(objects=FakeManager()),
        Ingredient=types.SimpleNamespace(objects=FakeManager()),
    )
    monkeypatch.setitem(sys.modules, 'apps.nutrition.models', fake_mod)

    res = orchestrator.AIOrchestratorService.orchestrate('Cho tôi món ăn nhẹ', None)
    assert res['path'] == 'gemini'
    evidence = res['rag_evidence']
    assert evidence['foods']
    assert evidence['foods'][0].get('food') is not None
    assert evidence['foods'][0].get('reasons') == ['phù hợp với người ăn ít dầu']


def test_orchestrate_ab_variant_forces_local_route(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(orchestrator.AIOrchestratorService, 'classify_intent', staticmethod(lambda text: (SimpleNamespace(name='recommendation'), 0.2)))
    monkeypatch.setattr(orchestrator.AIOrchestratorService, '_rank_local_candidates', staticmethod(lambda account, user_text, top_k=5: [{'food': None, 'score': 0.2, 'reasons': []}]))
    monkeypatch.setattr(orchestrator, 'evaluate_policies', lambda account, candidates, user_text: {'safe_candidates': candidates, 'issues': []})
    monkeypatch.setattr(orchestrator.AIOrchestratorService, '_resolve_ab_variant', staticmethod(lambda account: {
        'experiment_id': 1,
        'experiment_name': 'ai_route_comparison',
        'variant_name': 'local_llm',
    }))
    monkeypatch.setattr(orchestrator.ABTestingService, 'record_ai_route_event', staticmethod(lambda *args, **kwargs: True))

    res = orchestrator.AIOrchestratorService.orchestrate('Gợi ý món ăn', SimpleNamespace(id=1))
    assert res['path'] == 'local'
    assert res['ab_variant'] == 'local_llm'
    assert res['decision'] == 'ab_local_llm'


def test_orchestrate_ab_variant_forces_gemini_route(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(orchestrator.AIOrchestratorService, 'classify_intent', staticmethod(lambda text: (SimpleNamespace(name='nutrition'), 0.95)))
    monkeypatch.setattr(orchestrator.AIOrchestratorService, '_rank_local_candidates', staticmethod(lambda account, user_text, top_k=5: []))
    monkeypatch.setattr(orchestrator, 'evaluate_policies', lambda account, candidates, user_text: {'safe_candidates': candidates, 'issues': []})
    monkeypatch.setattr(orchestrator.AIOrchestratorService, '_resolve_ab_variant', staticmethod(lambda account: {
        'experiment_id': 1,
        'experiment_name': 'ai_route_comparison',
        'variant_name': 'gemini_rag',
    }))
    monkeypatch.setattr(orchestrator.ABTestingService, 'record_ai_route_event', staticmethod(lambda *args, **kwargs: True))

    res = orchestrator.AIOrchestratorService.orchestrate('Cho tôi thực đơn phù hợp', SimpleNamespace(id=2))
    assert res['path'] == 'gemini'
    assert res['ab_variant'] == 'gemini_rag'
    assert res['decision'] == 'ab_gemini_rag'


def test_classify_intent_prefers_db_signal_when_strong(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(
        orchestrator.AIOrchestratorService,
        '_db_intent_signal',
        staticmethod(lambda text: (SimpleNamespace(name='nutrition'), 0.8, {'source': 'db'})),
    )
    res_intent, res_conf = orchestrator.AIOrchestratorService.classify_intent('toi can xem dinh duong')
    assert getattr(res_intent, 'name', None) == 'nutrition'
    assert res_conf == 0.8


def test_orchestrate_uses_db_route_context_without_ab_variant(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(orchestrator.AIOrchestratorService, 'classify_intent', staticmethod(lambda text: (SimpleNamespace(name='recommendation'), 0.45)))
    monkeypatch.setattr(orchestrator.AIOrchestratorService, '_rank_local_candidates', staticmethod(lambda account, user_text, top_k=5: [{'food': None, 'score': 0.41, 'reasons': []}]))
    monkeypatch.setattr(orchestrator, 'evaluate_policies', lambda account, candidates, user_text: {'safe_candidates': candidates, 'issues': []})
    monkeypatch.setattr(orchestrator.AIOrchestratorService, '_resolve_ab_variant', staticmethod(lambda account: None))
    monkeypatch.setattr(orchestrator.AIOrchestratorService, '_build_route_context', staticmethod(lambda account, user_text, candidates: {
        'cache_hit': True,
        'local_evidence': 0.9,
        'rag_density': 0.1,
        'candidate_count': 1,
    }))

    res = orchestrator.AIOrchestratorService.orchestrate('goi y bua toi', None)
    assert res['path'] == 'local'
    assert res['decision'] == 'db_router_policy'
    assert res['route_context']['cache_hit'] is True


def test_chat_system_context_prioritizes_latest_user_request():
    system_context = _make_chat_response_system_context('Ban la tro ly AI', 'Toi muon hoi ve dinh duong')
    assert 'Toi muon hoi ve dinh duong' in system_context
    assert 'Uu tien tuyet doi cau hoi hien tai' in system_context
    assert 'Khong lan man' in system_context


def test_cache_intent_must_match_when_both_present():
    assert _cache_intent_matches('nutrition', 'nutrition')
    assert not _cache_intent_matches('nutrition', 'recipe')
    assert _cache_intent_matches('', 'recipe')
