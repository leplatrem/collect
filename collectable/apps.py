from django.apps import AppConfig


class CollectableConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "collectable"

    def ready(self) -> None:
        print(f"Starting {self.name} app...")
