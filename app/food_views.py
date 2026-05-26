# Wrapper layer for backward compatibility - all implementation moved to apps.nutrition.views
from apps.nutrition.views import foods, foods_search

__all__ = ['foods', 'foods_search']