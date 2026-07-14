from django.urls import path

from .views import SyncDataView

urlpatterns = [
    path("sales-history/sync/", SyncDataView.as_view(), name="sales-history-sync"),
]
