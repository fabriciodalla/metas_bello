"""URL configuration for METAS_BELLO."""

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path


def healthcheck(_request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", healthcheck, name="healthcheck"),
]
