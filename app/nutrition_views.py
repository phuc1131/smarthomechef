# Wrapper layer for backward compatibility - all implementation moved to apps.nutrition.views
from apps.nutrition.views import nutrition, nutrition_log, nutrition_delete

__all__ = ['nutrition', 'nutrition_log', 'nutrition_delete']