from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Collectable, Possession


@admin.register(Collectable)
class CollectableAdmin(SimpleHistoryAdmin):
    readonly_fields = (
        "created_at",
        "modified_at",
    )
    list_display = ["created_at", "modified_at", "tag_list"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


admin.site.register(Possession)
