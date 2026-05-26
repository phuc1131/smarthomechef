from django.apps import AppConfig


class CoreModelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core_models'
    verbose_name = 'Core Models'

    def ready(self):
        """Import signals when Django app is ready."""
        import apps.core_models.signals  # noqa
