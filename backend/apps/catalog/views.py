from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.accounts.permissions import IsAppAdmin

from .models import Product, ProductGroup, ProductSubgroup
from .serializers import ProductGroupSerializer, ProductSerializer, ProductSubgroupSerializer

WRITE_ACTIONS = ("create", "update", "partial_update")


class ProductGroupViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Sem destroy: gestão de catálogo inativa grupos/subgrupos, nunca apaga (evita órfãos em
    alocações/mapeamentos externos já existentes)."""

    serializer_class = ProductGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in WRITE_ACTIONS:
            return [IsAuthenticated(), IsAppAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = ProductGroup.objects.all().order_by("nome")
        if not self.request.user.is_admin:
            queryset = queryset.filter(ativo=True)
        return queryset


class ProductSubgroupViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ProductSubgroupSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in WRITE_ACTIONS:
            return [IsAuthenticated(), IsAppAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = ProductSubgroup.objects.all().order_by("nome")
        if not self.request.user.is_admin:
            queryset = queryset.filter(ativo=True)
        group_id = self.request.query_params.get("group")
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        return queryset


class ProductViewSet(ReadOnlyModelViewSet):
    """Fora do MVP (O1, Decisão 10): granularidade do Vendedor é subgrupo, não produto — sem CRUD."""

    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Product.objects.filter(ativo=True).order_by("nome")
        subgroup_id = self.request.query_params.get("subgroup")
        if subgroup_id:
            queryset = queryset.filter(subgroup_id=subgroup_id)
        return queryset
