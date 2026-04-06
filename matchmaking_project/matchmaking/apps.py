from django.apps import AppConfig


class MatchmakingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matchmaking'

    def ready(self):
        import matchmaking.signals  # noqa — registers signal handlers