from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, reverse_lazy
from django.views.generic.base import RedirectView


urlpatterns = [
    path("", RedirectView.as_view(url=reverse_lazy("index"), permanent=False)),
    path("admin/", admin.site.urls),
    path("collectable/", include("collectable.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
]

if settings.DEBUG:  # new
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
