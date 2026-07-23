"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import UserAccountViewSet
from apps.allocations.views import GoalAllocationViewSet
from apps.catalog.views import ProductGroupViewSet, ProductSubgroupViewSet, ProductViewSet
from apps.cycles.views import CycleViewSet
from apps.hierarchy.views import FeristaCoverageViewSet, HierarchyNodeViewSet

router = DefaultRouter()
router.register("hierarchy/nodes", HierarchyNodeViewSet, basename="hierarchy-node")
router.register("hierarchy/ferista-coverages", FeristaCoverageViewSet, basename="ferista-coverage")
router.register("cycles", CycleViewSet, basename="cycle")
router.register("allocations", GoalAllocationViewSet, basename="goal-allocation")
router.register("catalog/groups", ProductGroupViewSet, basename="product-group")
router.register("catalog/subgroups", ProductSubgroupViewSet, basename="product-subgroup")
router.register("catalog/products", ProductViewSet, basename="product")
router.register("accounts/users", UserAccountViewSet, basename="user-account")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.sales_history.urls")),
    path("api/", include(router.urls)),
]
