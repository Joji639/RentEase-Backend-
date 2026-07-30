from django.apps import AppConfig


class TechniciansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'technicians'

    def ready(self):
        import technicians.signals  # noqa
