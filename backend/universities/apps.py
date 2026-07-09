from django.apps import AppConfig


class UniversitiesConfig(AppConfig):
    name = 'universities'

    def ready(self):
        from . import signals  # noqa: F401  connect catalog cache invalidation
