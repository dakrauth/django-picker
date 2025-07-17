from django.apps import AppConfig


def ensure_preference(sender, instance, created=False, **kwargs):
    if created:
        from .models import Preference

        Preference.objects.get_or_create(user=instance)


class PickerConfig(AppConfig):
    name = "picker"
    verbose_name = "Django Picker"

    def ready(self):
        from .conf import picker_settings

        auto_create = picker_settings.get("AUTO_CREATE_PREFERENCES")
        if auto_create:
            from django.db.models.signals import post_save
            from django.contrib.auth import get_user_model

            post_save.connect(ensure_preference, sender=get_user_model())
