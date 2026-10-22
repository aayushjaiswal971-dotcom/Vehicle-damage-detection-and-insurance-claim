"""
core/apps.py — AppConfig for the core Django application.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Vehicle Damage Core"

    def ready(self):
        # Register the post_save signal for VehicleImage → Gemini
        import core.signals  # noqa: F401

        # Connect allauth social signals for Google profile sync
        from core.signals import connect_allauth_signals
        connect_allauth_signals()
