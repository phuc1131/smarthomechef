from types import SimpleNamespace
import sys

from app.services.personalization_service import semantic_search_foods


def test_semantic_search_basic(monkeypatch):
    # Create fake Food objects
    foods = [
        SimpleNamespace(name='Phở bò', category_name='Phở', id=1),
        SimpleNamespace(name='Cơm gà', category_name='Cơm', id=2),
        SimpleNamespace(name='Bún chả', category_name='Bún', id=3),
    ]

    class FakeManager:
        def all(self):
            class QS:
                def order_by(self, *a, **k):
                    return foods
            return QS()

    # Patch the Food symbol imported into the personalization_service module
    import app.services.personalization_service as ps
    monkeypatch.setattr(ps, 'Food', SimpleNamespace(objects=FakeManager()))

    from app.services.personalization_service import semantic_search_with_scores
    results = semantic_search_with_scores('pho bo', limit=5)
    assert results
    names = [getattr(item['food'], 'name', '').lower() for item in results]
    assert any(n.startswith('phở') or n.startswith('pho') for n in names)
