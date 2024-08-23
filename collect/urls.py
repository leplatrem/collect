from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, reverse_lazy
from django.views.generic.base import RedirectView


urlpatterns = i18n_patterns(
    path(
        "",
        RedirectView.as_view(url=reverse_lazy("index"), permanent=False),
        name="home",
    ),
    path("collectable/", include("collectable.urls")),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
)

if settings.ADMIN_ENABLED:
    urlpatterns.append(path("admin/", admin.site.urls))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += debug_toolbar_urls()
