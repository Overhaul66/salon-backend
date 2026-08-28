from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include, re_path
from django.views.static import serve as media_serve
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def health(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),

    # Swagger / OpenAPI documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Internal API Routes
    path("api/auth/", include("apps.users.urls")),
    path("api/", include("apps.salons.urls")),
    path("api/", include("apps.employees.urls")),
    path("api/", include("apps.scheduling.urls")),
    path("api/", include("apps.appointments.urls")),
    path("api/", include("apps.notifications.urls")),

    # Uploaded images live on the local filesystem; Django serves them since
    # WhiteNoise only covers static files.
    re_path(
        r"^media/(?P<path>.*)$",
        media_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]

